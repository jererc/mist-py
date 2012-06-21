#!/usr/bin/env python
import os.path
from datetime import datetime, timedelta
import logging

from syncd import env, settings
from syncd.util import get_db

from systools.system import loop, timeout, timer, dotdict
from systools.network.ssh import Host


logger = logging.getLogger(__name__)


class Sync(dotdict):
    def __init__(self, doc):
        super(Sync, self).__init__(doc)
        self.db = get_db()

    def __del__(self):
        self.update(processing=False)

    def validate(self):
        date = self.get('finished')
        if date and date + timedelta(hours=self.recurrence) > datetime.utcnow():
            return

        return self.get('hour_start', 0) <= datetime.now().hour < self.get('hour_end', 24)

    def _update_failed(self, session, params):
        col = self.db[settings.COL_FAILED]
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

        if not path_uuid or not session.path_exists(path_uuid):

            if not settings.AUTOMOUNT_UUID_DEV or retries <= 0:
                self.update(log='failed to get path for uuid %s on %s (%s)' % (uuid, session.hostname, session.host))
                return

            dev = disk.get('dev')
            if not dev:
                self.update(log='failed to get device for uuid %s on %s (%s)' % (uuid, session.hostname, session.host))
                return
            if not session.mount(dev):
                self.update(log='failed to mount device %s (uuid %s) on %s (%s)' % (dev, uuid, session.hostname, session.host))
                return

            return self._get_abs_path(session, uuid, path, retries=retries-1)

        return os.path.join(path_uuid, path.lstrip('/'))    # strip beginning '/' to avoid the filesystem root

    def _get_session(self, username=None, hwaddr=None, uuid=None):
        spec = {'alive': True}
        if username:
            spec['users.%s' % username] = {'$exists': True}
        if hwaddr:
            spec['ifconfig'] = {'$elemMatch': {'hwaddr': hwaddr}}
        if uuid:
            spec['disks'] = {'$elemMatch': {'uuid': uuid}}

        for res in self.db[settings.COL_HOSTS].find(spec):
            usernames = [username] if username else res['users'].keys()
            for username_ in usernames:
                session = Host(res['host'], username_, res['users'][username_])
                if session.logged:
                        return session

    def get_session(self, path, username=None, hwaddr=None, uuid=None, make_path=False):
        '''Get a ssh session on the host matching the sync parameters.

        :return: Ssh object
        '''
        params = {'username': username, 'hwaddr': hwaddr, 'uuid': uuid}
        session = self._get_session(**params)
        self._update_failed(session, params)
        if not session:
            return

        session.hostname = session.get_hostname()

        if uuid:
            path = self._get_abs_path(session, uuid, path)
            if not path:
                return

        if not session.path_exists(path):
            if not make_path:
                self.update(log='path %s does not exist on %s (%s)' % (path, session.hostname, session.host))
                return
            elif not session.mkdir(path, use_sudo=True):
                self.update(log='failed to make path %s on %s (%s)' % (path, session.hostname, session.host))
                return

        session.path = path
        session.path_str = '%s:%s' % (session.hostname, path)
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

        if self.s_dst.host == self.s_src.host:
            self.dst_path = self.s_dst.path
            self.ssh_password = None
        else:
            self.dst_path = '%s@%s:%s' % (self.s_dst.username, self.s_dst.host, self.s_dst.path)
            self.ssh_password = self.s_dst.password

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
    def process(self):
        '''Run the rsync command.
        '''
        cmd = self._get_cmd()

        started = datetime.utcnow()
        self.update(
                processing=True,
                started=started,
                finished=None,
                cmd=cmd,
                log='started to sync %s with %s' % (self.s_src.path_str, self.s_dst.path_str),
                )

        stdout, return_code = self.s_src.run_ssh(cmd,
                password=self.ssh_password,
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

    def update(self, **info):
        self.db[settings.COL_SYNCS].update({'_id': self._id}, {'$set': info}, safe=True)
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

@loop(60)
@timer()
def main():
    for res in get_db()[settings.COL_SYNCS].find(
            sort=[('finished', 1)],
            timeout=False):
        sync = Sync(res)
        if not sync.validate():
            continue
        if not sync.find_hosts():
            continue

        sync.process()

    clean_failed()


if __name__ == '__main__':
    main()
