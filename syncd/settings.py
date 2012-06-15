from datetime import timedelta


USERS = {}  # lan usernames and passwords (<username>: <password>)
DEFAULT_RSYNC_ARGS = ['-ax', '--ignore-errors']
SYNC_TIMEOUT = 7200     # seconds
AUTOMOUNT_UUID_DEV = True


# Db
DB_NAME = 'syncd'
COL_SYNCS = 'syncs'
COL_HOSTS = 'hosts'
COL_FAILED = 'failed'


USERNAME_ATTEMPTS = 3
DELTA_HOST = timedelta(days=7)
DELTA_FAILED_PARAMS = timedelta(days=4)
DELTA_FAILED_USERNAME = timedelta(hours=12)


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
