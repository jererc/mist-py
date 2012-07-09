#!/usr/bin/env python
import os.path
from datetime import datetime, timedelta
import logging

from pymongo import ASCENDING

from syncd import env, settings
from syncd.util import get_db

from systools.system import loop, timeout, timer, dotdict
from systools.network import get_ip
from systools.network.ssh import Host


logger = logging.getLogger(__name__)


class Sync(dotdict):
    def __init__(self, doc):
        super(Sync, self).__init__(doc)
        self.callable = self.process_rsync

    def validate(self):
        date = self.get('finished')
        if date and date + timedelta(hours=self.recurrence) > datetime.utcnow():
            return

        hour_start = self.get('hour_start') or 0
        hour_end = self.get('hour_end') or 24
        return hour_start <= datetime.now().hour < hour_end

    def _update_failed(self, session, params):
        col = get_db()[settings.COL_FAILED]
        if session:
            col.remove({'params': params}, safe=True)
        else:
            res = col.find_one({'params': params})
            if not res:
                col.insert({
                        'params': params,
                        'added': datetime.utcnow(),
                        }, safe=True)
            else:
                delta = datetime.utcnow() - res['added']
                if delta > settings.DELTA_FAILED_PARAMS:
                    self.update(log='failed to find a host matching %s for %s' % (params, delta))

    def _get_disk(self, disks, uuid):
        for disk in disks:
            if disk.get('uuid') == uuid:
                return disk

    def _get_abs_path(self, session, uuid, path, retries=1):
        '''Get the absolute path for a uuid partition.
        '''
        disks = session.get_disks()
        disk = self._get_disk(disks, uuid) or {}
        path_uuid = disk.get('path')

        if not path_uuid or not session.exists(path_uuid):

            if not settings.AUTOMOUNT or retries <= 0:
                self.update(log='failed to get path for uuid %s on %s' % (uuid, session.host))
                return

            dev = disk.get('dev')
            if not dev:
                self.update(log='failed to get device for uuid %s on %s' % (uuid, session.host))
                return
            if not session.mount(dev):
                self.update(log='failed to mount device %s (uuid %s) on %s' % (dev, uuid, session.host))
                return

            return self._get_abs_path(session, uuid, path, retries=retries-1)

        return os.path.join(path_uuid, path.lstrip('/'))    # lstrip '/' to avoid getting the filesystem root with join()

    def _get_session(self, **kwargs):
        user = None
        spec = {'alive': True}

        if kwargs.get('username') and kwargs.get('password'):
            user = '%s %s' % (kwargs['username'], kwargs['password'])
            spec['users.%s' % user] = {'$exists': True}
        if kwargs.get('hwaddr'):
            spec['ifconfig'] = {'$elemMatch': {'hwaddr': kwargs['hwaddr']}}
        if kwargs.get('uuid'):
            spec['disks'] = {'$elemMatch': {'uuid': kwargs['uuid']}}

        for res in get_db()[settings.COL_HOSTS].find(spec):
            for user_, info in res['users'].items():
                if user and user_ != user:
                    continue

                username, password = user_.split(' ', 1)
                session = Host(res['host'], username, password, port=info.get('port', 22))
                if session.logged:
                    session.hostname = res['hostname']
                    return session

    def get_session(self, make_path=False, **kwargs):
        '''Get a ssh session on the host matching the sync parameters.

        :return: Ssh object
        '''
        session = self._get_session(**kwargs)
        self._update_failed(session, kwargs)
        if not session:
            return

        path = kwargs['path']

        if kwargs.get('uuid'):
            path = self._get_abs_path(session, kwargs['uuid'], path)
            if not path:
                return

        # Check rsync
        if session.run_ssh('rsync --version', use_sudo=True)[1] != 0:
            self.callable = self.process_sftp

        if not session.exists(path):
            if not make_path:
                self.update(log='path %s does not exist on %s' % (path, session.host))
                return
            elif self.callable == self.process_rsync \
                    and not session.mkdir(path):
                self.update(log='failed to make path %s on %s' % (path, session.host))
                return

        session.path = path
        session.path_str = '%s:%s' % (session.hostname or session.host, path)
        return session

    @timer()
    def find_hosts(self):
        self.s_src = self.get_session(**self.src)
        if not self.s_src:
            return
        self.src_path = self.s_src.path

        self.s_dst = self.get_session(make_path=True, **self.dst)
        if not self.s_dst:
            return
        self.dst_path = self.s_dst.path

        return True

    def _get_cmd(self):
        cmd = ['rsync']
        if settings.DEFAULT_RSYNC_ARGS:
            cmd += settings.DEFAULT_RSYNC_ARGS
        if self.get('exclusions'):
            cmd += ['--exclude=%s' % e for e in self.exclusions]
        if self.get('delete'):
            cmd.append('--delete-excluded' if self.exclusions else '--delete')
        cmd += [self.src_path, self.dst_path]

        return ' '.join(cmd)

    @timeout(settings.SYNC_TIMEOUT)
    def process_rsync(self):
        '''Sync using rsync.
        '''
        if self.s_dst.host == self.s_src.host:
            ssh_password = None
        else:
            self.dst_path = '%s@%s:%s' % (self.s_dst.username, self.s_dst.host, self.s_dst.path)
            ssh_password = self.s_dst.password

        cmd = self._get_cmd()

        self.update(
                processing=True,
                started=datetime.utcnow(),
                finished=None,
                cmd=cmd,
                log='started to sync %s with %s' % (self.s_src.path_str, self.s_dst.path_str))

        stdout, return_code = self.s_src.run_ssh(cmd,
                password=ssh_password,
                use_sudo=True,
                timeout=settings.SYNC_TIMEOUT)

        info = {
            'processing': False,
            'finished': datetime.utcnow(),
            'log': '\n'.join(stdout),
            }
        if return_code in (0, 23, 24):
            info['success'] = True
            logger.info('synced %s with %s', self.s_src.path_str, self.s_dst.path_str)
        else:
            info['success'] = False
            logger.error('failed to sync %s with %s', self.s_src.path_str, self.s_dst.path_str)

        self.update(**info)

    @timeout(settings.SYNC_TIMEOUT)
    def process_sftp(self):
        '''Sync using SFTP.
        '''
        local_ips = get_ip()
        if self.s_src.host in local_ips:
            sftp = self.s_dst
            download = False
        elif self.s_dst.host in local_ips:
            sftp = self.s_src
            download = True
        else:
            self.update(processing=False,
                    started=datetime.utcnow(),
                    finished=None,
                    log='failed to sync %s with %s using SFTP: source and destination are both remote' % (self.s_src.path_str, self.s_dst.path_str))
            return

        self.update(processing=True,
                started=datetime.utcnow(),
                finished=None,
                log='started to sync %s with %s' % (self.s_src.path_str, self.s_dst.path_str))

        exclude = self.get('exclusions')
        if exclude:
            exclude = [r'^%s' % e for e in exclude]

        try:
            sftp.sftpsync(self.src_path,
                    self.dst_path,
                    download=download,
                    exclude=exclude,
                    delete=self.get('delete'))
            info = {
                'success': True,
                'finished': datetime.utcnow(),
                'processing': False,
                'log': None,
                }
            logger.info('synced %s with %s', self.s_src.path_str, self.s_dst.path_str)
        except Exception, e:
            info = {
                'success': False,
                'finished': datetime.utcnow(),
                'processing': False,
                'log': str(e),
                }
            logger.error('failed to sync %s with %s: %s', self.s_src.path_str, self.s_dst.path_str, e)

        self.update(**info)

    def update(self, **info):
        get_db()[settings.COL_SYNCS].update({'_id': self._id}, {'$set': info}, safe=True)
        if info.get('log'):
            logger.info(info['log'])


def clean_failed():
    '''Clean parameters not found collection.
    '''
    db = get_db()
    params_list = []

    for res in db[settings.COL_SYNCS].find():
        for type in ('src', 'dst'):
            params = dict([(k, res[type].get(k)) for k in ('username', 'hwaddr', 'uuid')])
            params_list.append(params)

    db[settings.COL_FAILED].remove({'params': {'$nin': params_list}})

def clean_processing():
    get_db()[settings.COL_SYNCS].update({'processing': True},
            {'$set': {'processing': False, 'started': None}},
            safe=True,
            multi=True)

@loop(60)
@timer()
def main():
    clean_processing()

    for res in get_db()[settings.COL_SYNCS].find(
            sort=[('finished', ASCENDING)],
            timeout=False):
        sync = Sync(res)
        if not sync.validate():
            continue
        if not sync.find_hosts():
            continue
        sync.callable()

    clean_failed()


if __name__ == '__main__':
    main()
