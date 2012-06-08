from datetime import timedelta


USERS = {}  # lan usernames and passwords (<username>: <password>)
DEFAULT_RSYNC_ARGS = ['-a', '--ignore-errors']
SYNC_TIMEOUT = 7200     # seconds
AUTOMOUNT_UUID_DEV = True


# Db
DB_NAME = 'syncd'
COL_SYNCS = 'syncs'
COL_HOSTS = 'hosts'
COL_NOTFOUND = 'hosts_not_found'


USERNAME_TRIES = 3
NOTFOUND_DELTA = timedelta(days=4)
TTL_HOST = timedelta(days=7)
TTL_HOST_INFO = timedelta(seconds=120)
TTL_FAILED_USERNAME = timedelta(hours=12)


# Import local settings
try:
    from local_settings import *
except ImportError:
    pass
