from datetime import datetime
from copy import deepcopy
import logging

from systools.network import get_hosts
from systools.system import loop, timeout, timer
from systools.network.ssh import Host as SshHost
from systools.network.ssh import TimeoutError

from mist import settings, get_factory, User, Host


logger = logging.getLogger(__name__)


def _get_user(users, user_id):
    for user in users:
        if user['_id'] == user_id:
            return user

def _update_users(users, info):
    user_ = {'_id': info['_id']}
    if info.get('logged'):
        user_['logged'] = info.get('logged')
    if info.get('failed'):
        user_['failed'] = info.get('failed')
    user = _get_user(users, info['_id'])
    if user:
        user.update(user_)
    else:
        users.append(user_)

@loop(minutes=10)
@timeout(minutes=10)
@timer(30)
def update_host(host):
    res = Host.find_one({'host': host})
    if not res:
        return
    res.setdefault('users', [])

    # Clean host users list
    for user in res['users'][:]:
        if not User.find_one({'_id': user['_id']}):
            res['users'].remove(user)

    # Get a list of users to try
    users = []
    for user in User.find():
        user_ = _get_user(res['users'], user['_id'])
        if user_:
            user2 = deepcopy(user_)
            user2.update(user)
            users.insert(0, user2)
        else:
            users.append(user)

    port_service = None
    ports_timeout = []

    for user in users:
        port = user.get('port', 22)
        if port in ports_timeout:
            continue
        if port_service and port != port_service:
            continue
        if not user.get('logged') and user.get('failed'):
            if user['failed'] > datetime.utcnow() - settings.DELTA_FAILED_USERNAME:
                continue

        try:
            session = SshHost(host, user['username'], user['password'],
                    port=port)
            if user.get('failed'):
                del user['failed']
            user['logged'] = datetime.utcnow()
        except TimeoutError, e:
            ports_timeout.append(port)
            if user.get('logged'):
                logger.info('failed to connect to %s@%s:%s: %s' % (user['username'], host, port, str(e)))
            continue
        except Exception, e:
            if user.get('logged'):
                del user['logged']
                logger.info('failed to connect to %s@%s:%s: %s' % (user['username'], host, port, str(e)))
            user['failed'] = datetime.utcnow()
            continue
        finally:
            _update_users(res['users'], user)

        port_service = port

        updated = res.get('updated')
        if not updated or updated < datetime.utcnow() - settings.DELTA_HOST_UPDATE:
            res.update({
                'hostname': session.get_hostname(),
                'ifconfig': session.get_ifconfig(),
                'disks': session.get_disks(),
                'updated': datetime.utcnow(),
                })

    Host.save(res, safe=True)

def get_worker(host):
    return {
        'target': '%s.workers.host.update_host' % settings.PACKAGE_NAME,
        'args': (host,),
        'daemon': True,
        }

@loop(minutes=5)
@timeout(minutes=5)
@timer(30)
def run():
    hosts = get_hosts()
    if hosts is None:
        logger.debug('failed to find hosts')
        return

    factory = get_factory()
    for host in hosts:
        Host.update({'host': host}, {'$set': {
                'alive': True,
                'seen': datetime.utcnow(),
                }}, upsert=True, safe=True)

        factory.add(**get_worker(host))

    Host.update({'host': {'$nin': hosts}},
            {'$set': {'alive': False}}, safe=True, multi=True)
    Host.remove({'seen': {'$lt': datetime.utcnow() - settings.DELTA_HOST_ALIVE}},
            safe=True)

    for res in Host.find({'alive': False}):
        factory.remove(**get_worker(res['host']))
