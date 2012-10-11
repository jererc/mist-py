import os.path
from datetime import datetime, timedelta
import logging

from pymongo import ASCENDING

from syncd import settings, get_host, get_db, get_factory

from systools.system import loop, timer, dotdict
from systools.network import get_ip


WORKERS_LIMIT = 4

logger = logging.getLogger(__name__)


class Sync(dotdict):
    def __init__(self, doc):
        super(Sync, self).__init__(doc)
        self.callable = self.process_rsync

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

    def get_session(self, make_path=False, **kwargs):
        '''Get a ssh session on the host matching the sync parameters.

        :return: Ssh object
        '''
        session = get_host(**kwargs)
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

    def process_rsync(self):
        '''Sync using rsync.
        '''
        if self.s_dst.host == self.s_src.host:
            ssh_password = None
        else:
            self.dst_path = '%s@%s:%s' % (self.s_dst.username, self.s_dst.host, self.s_dst.path)
            ssh_password = self.s_dst.password

        cmd = self._get_cmd()

        self.update(processing=True,
                started=datetime.utcnow(),
                finished=None,
                cmd=cmd,
                log='started to sync %s with %s' % (self.s_src.path_str, self.s_dst.path_str))

        try:
            stdout, return_code = self.s_src.run_ssh(cmd,
                    password=ssh_password,
                    use_sudo=True,
                    timeout=settings.SYNC_TIMEOUT)
        finally:
            self.s_src.stop_cmd(cmd)

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
            logger.error('failed to sync %s with %s: %s', self.s_src.path_str, self.s_dst.path_str, str(e))

        self.update(**info)

    def update(self, **info):
        get_db()[settings.COL_SYNCS].update({'_id': self._id}, {'$set': info}, safe=True)
        if info.get('log'):
            logger.info(info['log'])


def validate_sync(sync):
    date = sync.get('finished')
    if date and date + timedelta(hours=sync['recurrence']) > datetime.utcnow():
        return

    hour_start = sync.get('hour_start') or 0
    hour_end = sync.get('hour_end') or 24
    return hour_start <= datetime.now().hour < hour_end

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
            {'$set': {'processing': False}}, safe=True, multi=True)

def process_sync(sync_id):
    sync = get_db()[settings.COL_SYNCS].find_one({'_id': sync_id})
    if not sync:
        return
    sync = Sync(sync)
    if sync.find_hosts():
        sync.callable()

@loop(60)
def process_syncs():
    count = 0
    for sync in get_db()[settings.COL_SYNCS].find(
            sort=[('finished', ASCENDING)]):
        if validate_sync(sync):
            target = '%s.workers.sync.process_sync' % settings.PACKAGE_NAME
            get_factory().add(target=target, args=(sync['_id'],),
                    timeout=settings.SYNC_TIMEOUT)

            count += 1
            if count == WORKERS_LIMIT:
                break

    clean_failed()

def run():
    clean_processing()
    process_syncs()
