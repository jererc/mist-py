from datetime import timedelta


PACKAGE_NAME = 'syncd'

SYNC_TIMEOUT = 3600 * 6     # seconds
AUTOMOUNT = True
DELTA_HOST_ALIVE = timedelta(days=7)
DELTA_FAILED_USERNAME = timedelta(hours=6)
DELTA_HOST_UPDATE = timedelta(minutes=10)

# Db
DB_NAME = 'syncd'

WEBUI_PORT = 8003

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
