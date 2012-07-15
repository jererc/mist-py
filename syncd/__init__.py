import logging

from syncd import settings
from syncd.util import get_db

from systools.network.ssh import Host


logger = logging.getLogger(__name__)


def get_users():
    res = []
    for user in get_db()[settings.COL_USERS].find():
        res.append({
            'username': user['username'],
            'password': user['password'],
            })
    return res

def get_host(**kwargs):
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
            port = info.get('port', 22)
            try:
                session = Host(res['host'], username, password, port=port)
                session.hostname = res['hostname']
                return session
            except Exception, e:
                logger.info('failed to connect to %s:%s@%s:%s: %s', username, password, res['host'], port, e)
