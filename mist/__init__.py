import socket
import logging

from bson.objectid import ObjectId
from pymongo import ASCENDING

from factory import Factory

from systools.network.ssh import Host as SshHost

from mist import settings
from mist.utils.db import Model, connect


DEFAULT_SETTINGS = {
    'host': {
        'ip_range': '192.168.1.0/24',
        'host_timeout': 60 * 24 * 7,     # minutes
        'failed_user_timeout': 60 * 6,     # minutes
        'host_update_delta': 10,    # minutes
        },
    'sync': {
        'automount': True,
        'sync_timeout': 60 * 6,     # minutes
        'sync_retry_delta': 30,     # minutes
        },
    }

logger = logging.getLogger(__name__)
connect(settings.DB_NAME)


class User(Model):
    COL = 'users'


class Host(Model):
    COL = 'hosts'


class Sync(Model):
    COL = 'syncs'


class Settings(Model):
    COL = 'settings'

    @classmethod
    def get_settings(cls, section, key=None, default=None):
        res = cls.find_one({'section': section}) or {}
        settings = res.get('settings', DEFAULT_SETTINGS.get(section, {}))
        return settings.get(key, default) if key else settings

    @classmethod
    def set_setting(cls, section, key, value):
        cls.update({'section': section},
                {'$set': {'section': section, 'settings.%s' % key: value}},
                upsert=True)

    @classmethod
    def set_settings(cls, section, settings, overwrite=False):
        doc = {
            'section': section,
            'settings': settings,
            }
        cls.update({'section': section},
                doc if overwrite else {'$set': doc}, upsert=True)


def get_factory():
    return Factory(collection=settings.PACKAGE_NAME)

def get_users(spec=None):
    if not spec:
        spec = {}
    return [r for r in User.find(spec, sort=[('name', ASCENDING)])]

def get_user(id=None, name=None, spec=None):
    if not spec:
        spec = {}
    if id:
        spec['_id'] = ObjectId(id)
    if name:
        spec['name'] = name
    return User.find_one(spec)

def get_host(**kwargs):
    spec = {'alive': True}
    if kwargs.get('host'):
        hosts = kwargs['host']
        if not isinstance(hosts, (list, tuple)):
            hosts = [hosts]
        hosts = list(set(map(socket.gethostbyname, hosts)))
        spec['host'] = {'$in': hosts}
    if kwargs.get('user'):
        spec['users'] = {'$elemMatch': {
            '_id': kwargs['user'],
            'logged': {'$exists': True},
            }}
    if kwargs.get('hwaddr'):
        spec['ifconfig'] = {'$elemMatch': {'hwaddr': kwargs['hwaddr']}}
    if kwargs.get('uuid'):
        spec['disks'] = {'$elemMatch': {'uuid': kwargs['uuid']}}

    count = 0
    for host in Host.find(spec):
        count += 1
        for user in host['users']:
            if not user.get('logged'):
                continue
            user_ = get_user(user['_id'])
            if not user_:
                continue

            port = user_.get('port', 22)
            try:
                client = SshHost(host['host'],
                        user_['username'], user_['password'], port=port)
                client.hostname = host['hostname']
                return client
            except Exception, e:
                logger.info('failed to connect to %s@%s:%s: %s', user_['username'], host['host'], port, str(e))

    if (kwargs.get('uuid') or kwargs.get('hwaddr')) and not count:
        logger.info('no host matching %s', kwargs)
