from datetime import datetime
from copy import deepcopy
import logging

from pymongo import Connection

from syncd import settings

from systools.network import get_ip
from systools.network.ssh import Host, TimeoutError
from systools.system import loop, timer


logger = logging.getLogger(__name__)


def get_db():
    return Connection('localhost')[settings.DB_NAME]

def get_localhost():
    ips = get_ip()
    if ips:
        return ips[0]

@loop(600)
@timer(30)
def update_host(host):
    db = get_db()
    col_hosts = db[settings.COL_HOSTS]
    col_users = db[settings.COL_USERS]

    res = col_hosts.find_one({'host': host})
    if not res:
        return

    res.setdefault('users', {})
    res.setdefault('failed', {})

    # Clean users
    for key in ('users', 'failed'):
        for user in deepcopy(res[key]):
            username, password = user.split(' ', 1)
            if not col_users.find_one({'username': username, 'password': password}):
                del res[key][user]

    # Get users
    users_info = []
    for user_info in col_users.find():
        user = '%s %s' % (user_info['username'], user_info['password'])
        if user in res['users']:
            users_info.insert(0, user_info)
        else:
            users_info.append(user_info)

    port_service = None
    ports_timeout = []
    for user_info in users_info:
        port = user_info.get('port', 22)
        if port in ports_timeout:
            continue
        if port_service and port != port_service:
            continue

        user = '%s %s' % (user_info['username'], user_info['password'])

        if user not in res['users']:
            failed = res['failed'].get(user)
            if failed and failed > datetime.utcnow() - settings.DELTA_FAILED_USERNAME:
                continue

        try:
            session = Host(host,
                    user_info['username'],
                    user_info['password'],
                    port=port)
        except TimeoutError, e:
            ports_timeout.append(port)
            if user in res['users']:
                logger.info('failed to connect to %s:%s@%s:%s: %s', user_info['username'], user_info['password'], host, port, e)
            continue
        except Exception, e:
            if len(res['users']) > 1 and user in res['users']:
                del res['users'][user]
            res['failed'][user] = datetime.utcnow()
            if user in res['users']:
                logger.info('failed to connect to %s:%s@%s:%s: %s', user_info['username'], user_info['password'], host, port, e)
            continue

        port_service = port

        res['users'][user] = {'port': port}
        if user in res['failed']:
            del res['failed'][user]

        updated = res.get('updated')
        if not updated or updated < datetime.utcnow() - settings.DELTA_HOST_UPDATE:
            res.update({
                'hostname': session.get_hostname(),
                'ifconfig': session.get_ifconfig(),
                'disks': session.get_disks(),
                'updated': datetime.utcnow(),
                })

    col_hosts.save(res, safe=True)
