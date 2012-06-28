#!/usr/bin/env python
from datetime import datetime
import logging

from syncd import env, settings
from syncd.util import get_db

from systools.system import loop, timeout, timer
from systools.network import get_hosts
from systools.network.ssh import Host


logger = logging.getLogger(__name__)


@timer()
def update_hosts():
    col = get_db()[settings.COL_HOSTS]

    hosts = get_hosts()
    if hosts is None:
        logger.debug('failed to find hosts')
        return

    logger.debug('found hosts %s', hosts)

    for host in hosts:
        col.update({'host': host}, {'$set': {
                'alive': True,
                'seen': datetime.utcnow(),
                }}, upsert=True, safe=True)

    col.update({'host': {'$nin': hosts}},
            {'$set': {'alive': False}}, safe=True, multi=True)

    col.remove({'seen': {'$lt': datetime.utcnow() - settings.DELTA_HOST}},
            safe=True)

    return True

@timeout(hours=1)
@timer()
def update_info():
    col_hosts = get_db()[settings.COL_HOSTS]
    col_users = get_db()[settings.COL_USERS]

    for res in col_hosts.find({'alive': True}):
        res.setdefault('users', {})
        res.setdefault('failed', {})

        # Clean users
        for field in ('users', 'failed'):
            for user in res[field]:
                username, password = user.split(' ', 1)
                if not col_users.find_one({'username': username, 'password': password}):
                    del res[field][user]

        for user_info in col_users.find():
            username = user_info['username']
            password = user_info['password']
            port = user_info.get('port', 22)

            user = '%s %s' % (username, password)

            fval = res['failed'].get(user, 0)
            if isinstance(fval, datetime) and fval > datetime.utcnow() - settings.DELTA_FAILED_USERNAME:
                continue

            log_errors = False
            if isinstance(fval, int) and fval >= settings.USERNAME_ATTEMPTS - 1:
                log_errors = True

            session = Host(res['host'], username, password, port=port, log_errors=log_errors)
            if not session.logged:
                if isinstance(fval, datetime):
                    fval = datetime.utcnow()
                elif isinstance(fval, int):
                    fval += 1
                    if fval >= settings.USERNAME_ATTEMPTS:
                        fval = datetime.utcnow()
                        if user in res['users']:
                            del res['users'][user]
                res['failed'][user] = fval

            else:
                res['users'][user] = {'port': port}
                if user in res['failed']:
                    del res['failed'][user]

                res.update({
                    'hostname': session.get_hostname(),
                    'ifconfig': session.get_ifconfig(),
                    'disks': session.get_disks(),
                    })

        col_hosts.save(res, safe=True)

@loop(600)
def main():
    if update_hosts():
        update_info()


if __name__ == '__main__':
    main()
