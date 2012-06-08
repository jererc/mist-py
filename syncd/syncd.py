#!/usr/bin/env python
import os.path
from datetime import datetime, timedelta
import logging
import logging.handlers

from pymongo import Connection

from settings import *

from systools.system import loop, timeout, popen_expect, dotdict
from systools.network import get_ip, get_hosts
from systools.network.ssh import Host


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(os.path.splitext(__file__)[0]))


def get_db():
    return Connection('localhost')[DB_NAME]

def _get_parameters(params):
    return dict([(k, params.get(k)) for k in ('username', 'hwaddr', 'uuid')])

def clean_parameters_not_found():
    '''Clean parameters not found collection.
    '''
    db = get_db()
    params_list = []
    for res in db[COL_SYNCS].find():
        for type in ('src', 'dst'):
            params_list.append(_get_parameters(res[type]))
    db[COL_NOTFOUND].remove({'params': {'$nin': params_list}})

def update_hosts():
    '''Update hosts collection.
    '''
    db = get_db()
    hosts = get_hosts()

    for host in hosts:
        db[COL_HOSTS].update({'host': host}, {'$set': {
                'alive': True,
                'seen': datetime.utcnow(),
                }}, upsert=True, safe=True)

    db[COL_HOSTS].update({'host': {'$nin': hosts}},
            {'$set': {'alive': False}},
            safe=True,
            multi=True)

    db[COL_HOSTS].remove({'seen': {'$lt': datetime.utcnow() - TTL_HOST}}, safe=True)

def get_localhost():
    ips = get_ip()
    if ips:
        return ips[0]


class Sync(dotdict):
    def __init__(self, doc):
        super(Sync, self).__init__(doc)

        self.db = get_db()

    def _get_host_session(self, host, user):
        log_errors = False
        if self.db[COL_HOSTS].find_one({
                'host': host,
                'usernames': user,
                'failed.%s' % user: {'$gte': USERNAME_TRIES - 1},
                }):
            log_errors = True

        session = Host(host, user, USERS[user], log_errors=log_errors)
        if not session.logged:
            val = self.db[COL_HOSTS].find_one({'host': host}).get('failed', {}).get(user)
            if not isinstance(val, datetime):
                self.db[COL_HOSTS].update({'host': host}, {'$inc': {'failed.%s' % user: 1}}, safe=True)

            self.db[COL_HOSTS].update({'host': host, 'failed.%s' % user: {'$gte': USERNAME_TRIES}}, {
                    '$pull': {'usernames': user},
                    '$set': {'failed.%s' % user: datetime.utcnow()},
                    }, safe=True)
            return

        self.db[COL_HOSTS].update({'host': host}, {
                '$addToSet': {'usernames': user},
                '$unset': {'failed.%s' % user: True},
                }, safe=True)

        # Get host info
        res = self.db[COL_HOSTS].find_one({
                'host': host,
                'updated': {'$gte': datetime.utcnow() - TTL_HOST_INFO},
                })
        if res:
            session.hwaddr = res['hwaddr']
            session.disks = res['disks']
        else:
            session.hwaddr = session.get_hwaddr()
            session.disks = session.get_disks()
            self.db[COL_HOSTS].update({'host': host}, {'$set': {
                    'hwaddr': session.hwaddr,
                    'disks': session.disks,
                    'updated': datetime.utcnow(),
                    }}, safe=True)

        return session

    def _get_hosts(self, username, hwaddr, uuid):
        hosts = []
        spec = {
            'alive': True,
            'usernames': username or {'$exists': True},
            }
        if hwaddr:
            spec['hwaddr'] = hwaddr
        if uuid:
            spec['disks.%s' % uuid] = {'$exists': True}

        res = self.db[COL_HOSTS].find_one(spec)
        if res:
            hosts.append(res['host'])

        for res in self.db[COL_HOSTS].find({
                'alive': True,
                'host': {'$nin': hosts},
                }):
            hosts.append(res['host'])

        return hosts

    def _get_users(self, host, username):
        if username:
            users = [username]
        else:
            users = self.db[COL_HOSTS].find_one({'host': host}).get('usernames', USERS.keys())

        failed = []
        res = self.db[COL_HOSTS].find_one({'host': host}).get('failed', {})
        for user, val in res.items():
            if isinstance(val, datetime) and val > datetime.utcnow() - TTL_FAILED_USERNAME:
                failed.append(user)

        return [u for u in users if u not in failed]

    def _get_session(self, username=None, hwaddr=None, uuid=None):
        '''Get a ssh session on a host matching the parameters.

        :return: Ssh object
        '''
        for host in self._get_hosts(username, hwaddr, uuid):
            for user in self._get_users(host, username):
                session = self._get_host_session(host, user)
                if not session:
                    continue
                if hwaddr and hwaddr not in session.hwaddr:
                    break
                if uuid and uuid not in session.disks:
                    break

                return session

    def _update_not_found(self, params):
        res = self.db[COL_NOTFOUND].find_one({'params': params})
        if not res:
            self.db[COL_NOTFOUND].insert({
                    'params': params,
                    'added': datetime.utcnow(),
                    }, safe=True)
        else:
            delta = datetime.utcnow() - res['added']
            if delta > NOTFOUND_DELTA:
                self.update(log='failed to find a host matching %s for %s' % (params, delta))

    def _get_path(self, session, uuid, path, retries=1):
        '''Get the uuid partition path with its relative path.
        '''
        path_uuid = session.disks[uuid].get('path')
        if not path_uuid or not session.path_exists(path_uuid):

            if not AUTOMOUNT_UUID_DEV or retries <= 0:
                self.update(log='failed to get path for uuid %s on %s (%s)' % (uuid, session.hostname, session.host))
                return

            dev = session.disks[uuid].get('dev')
            if not dev:
                self.update(log='failed to get device for uuid %s on %s (%s)' % (uuid, session.hostname, session.host))
                return
            if not session.mount(dev):
                self.update(log='failed to mount device %s (uuid %s) on %s (%s)' % (dev, uuid, session.hostname, session.host))
                return

            session.disks = session.get_disks()

            return self._get_path(session, uuid, path, retries=retries-1)

        return os.path.join(path_uuid, path.lstrip('/'))    # strip beginning '/' to avoid the filesystem root

    def get_session(self, path, username=None, hwaddr=None, uuid=None, make_path=False):
        '''Get a ssh session on the host matching the sync parameters.

        :return: Ssh object
        '''
        params = {'username': username, 'hwaddr': hwaddr, 'uuid': uuid}
        session = self._get_session(**params)
        if not session:
            self._update_not_found(params)
            return

        self.db[COL_NOTFOUND].remove({'params': params}, safe=True)

        session.hostname = session.get_hostname()

        if uuid:
            path = self._get_path(session, uuid, path)
            if not path:
                return

        # Check the path
        if not session.path_exists(path):
            if not make_path:
                self.update(log='path %s does not exist on %s (%s)' % (path, session.hostname, session.host))
                return
            elif not session.mkdir(path, sudo=True):
                self.update(log='failed to make path %s on %s (%s)' % (path, session.hostname, session.host))
                return

        session.path = path
        session.path_str = '%s:%s' % (session.hostname, path)
        return session

    def _check_dates(self):
        date = self.get('processed')
        if date and date + timedelta(hours=self.recurrence) > datetime.utcnow():
            return

        hour_now = datetime.now().hour
        hour_start = self.get('hour_start')
        if hour_start and hour_now < hour_start:
            return
        hour_end = self.get('hour_end')
        if hour_end and hour_now >= hour_end:
            return

        return True

    def validate(self):
        if not self._check_dates():
            return
        localhost = get_localhost()
        if not localhost:
            return

        # Get source
        self.s_src = self.get_session(**self.src)
        if not self.s_src:
            return

        if self.s_src.host == localhost:
            self.callable = popen_expect
            self.sudo = True
        else:
            self.callable = self.s_src.popen
            self.sudo = False
        self.src_path = self.s_src.path

        self.passwords = [self.s_src.password] if self.sudo else []

        # Get destination
        self.s_dst = self.get_session(make_path=True, **self.dst)
        if not self.s_dst:
            return

        if self.s_dst.host == self.s_src.host:
            self.dst_path = self.s_dst.path
        else:
            self.dst_path = '%s@%s:%s' % (self.s_dst.username, self.s_dst.host, self.s_dst.path)
            self.passwords.append(self.s_dst.password)

        return True

    def _get_cmd(self):
        exclusions = ' '.join(['--exclude=%s' % e for e in self.exclusions])
        args = '%s%s' % (DEFAULT_RSYNC_ARGS, ' %s' % exclusions or '')
        if self.get('delete'):
            args += ' --delete-excluded' if exclusions else ' --delete'

        return '%srsync %s %s %s' % ('sudo ' if self.sudo else '', args, self.src_path, self.dst_path)

    @timeout(SYNC_TIMEOUT)
    def process(self):
        '''Run the rsync command.
        '''
        cmd = self._get_cmd()
        self.update(processing=True, log='started to sync %s with %s (cmd: %s)' % (self.s_src.path_str, self.s_dst.path_str, cmd))

        started = datetime.utcnow()
        stdout, return_code = self.callable(cmd, passwords=self.passwords, timeout=SYNC_TIMEOUT)
        if return_code in (0, 23, 24):
            self.update(processing=False, processed=datetime.utcnow(), log='\n'.join(stdout[-2:]))
            logger.info('synced %s with %s in %s', self.s_src.path_str, self.s_dst.path_str, datetime.utcnow() - started)
        else:
            self.update(processing=False, log='\n'.join(stdout[-2:]))
            logger.error('failed to sync %s with %s (cmd: %s): %s', self.s_src.path_str, self.s_dst.path_str, cmd, stdout[-2:])

    def update(self, **info):
        self.db[COL_SYNCS].update({'_id': self._id}, {'$set': info}, safe=True)
        if 'log' in info:
            logger.info(info['log'])


@loop(300)
def main():
    update_hosts()
    clean_parameters_not_found()

    for res in get_db()[COL_SYNCS].find(
            sort=[('processed', 1)],
            timeout=False):
        sync = Sync(res)
        if sync.validate():
            sync.process()


if __name__ == '__main__':
    main()
