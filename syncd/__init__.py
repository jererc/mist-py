import logging

from pymongo.objectid import ObjectId
from pymongo import Connection, ASCENDING

from syncd import settings

from factory import Factory

from systools.network.ssh import Host


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
db_con = Connection()


def get_db():
    return db_con[settings.DB_NAME]

def get_factory():
    return Factory(collection=settings.PACKAGE_NAME)

def get_users(spec=None):
    if not spec:
        spec = {}
    return [r for r in get_db()[settings.COL_USERS].find(spec,
            sort=[('name', ASCENDING)])]

def get_user(id=None, name=None, spec=None):
    if not spec:
        spec = {}
    if id:
        spec['_id'] = ObjectId(id)
    if name:
        spec['name'] = name
    return get_db()[settings.COL_USERS].find_one(spec)

def get_host(**kwargs):
    spec = {'alive': True}

    if kwargs.get('user'):
        spec['users'] = {'$elemMatch': {
            '_id': kwargs['user'],
            'logged': {'$exists': True},
            }}
    if kwargs.get('hwaddr'):
        spec['ifconfig'] = {'$elemMatch': {'hwaddr': kwargs['hwaddr']}}
    if kwargs.get('uuid'):
        spec['disks'] = {'$elemMatch': {'uuid': kwargs['uuid']}}

    for host in get_db()[settings.COL_HOSTS].find(spec):
        for user in host['users']:
            if not user.get('logged'):
                continue
            user_ = get_user(user['_id'])
            if not user_:
                continue

            port = user_.get('port', 22)
            try:
                session = Host(host['host'], user_['username'], user_['password'],
                        port=port)
                session.hostname = host['hostname']
                return session
            except Exception, e:
                logger.info('failed to connect to %s@%s:%s: %s', user_['username'], host['host'], port, str(e))
