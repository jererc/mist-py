from datetime import timedelta


PACKAGE_NAME = 'syncd'

DEFAULT_RSYNC_ARGS = ['-ax', '--ignore-errors']
SYNC_TIMEOUT = 3600 * 6     # seconds
AUTOMOUNT = True

# Db
DB_NAME = 'syncd'
COL_USERS = 'users'
COL_SYNCS = 'syncs'
COL_HOSTS = 'hosts'
COL_FAILED = 'failed'

DELTA_HOST_ALIVE = timedelta(days=7)
DELTA_FAILED_USERNAME = timedelta(hours=6)
DELTA_HOST_UPDATE = timedelta(minutes=10)
DELTA_FAILED_PARAMS = timedelta(days=4)

# Logging
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
LOG_DEFAULT = '/home/user/log/syncd.log'
LOG_ERRORS = '/home/user/log/syncd-errors.log'
LOG_SIZE = 100000   # Bytes
LOG_COUNT = 100


# Import local settings
try:
    from local_settings import *
except ImportError:
    pass
