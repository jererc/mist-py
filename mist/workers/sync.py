import os.path
from datetime import datetime, timedelta
import logging

from transfer import Transfer

from systools.system import loop, timer

from mist import settings, get_factory, get_host, Sync


WORKERS_LIMIT = 4
DELTA_RETRY = timedelta(minutes=30)

logger = logging.getLogger(__name__)


def _get_disk(disks, uuid):
    for disk in disks:
        if disk.get('uuid') == uuid:
            return disk

def _get_abs_path(host, uuid, path, retries=1):
    '''Get the absolute path for a uuid partition.
    '''
    disks = host.get_disks()
    disk = _get_disk(disks, uuid) or {}
    path_uuid = disk.get('path')

    if not path_uuid or not host.exists(path_uuid):
        if not settings.AUTOMOUNT or retries <= 0:
            logger.info('failed to get path for uuid %s on %s' % (uuid, host.host))
            return
        dev = disk.get('dev')
        if not dev:
            logger.info('failed to get device for uuid %s on %s' % (uuid, host.host))
            return
        if not host.mount(dev):
            logger.info('failed to mount device %s (uuid %s) on %s' % (dev, uuid, host.host))
            return
        return _get_abs_path(host, uuid, path, retries=retries-1)

    return os.path.join(path_uuid, path.lstrip('/'))    # lstrip '/' to avoid getting the filesystem root with join()

def get_uris(**kwargs):
    host = get_host(**kwargs)
    if not host:
        return
    paths = kwargs['path']
    if not isinstance(paths, (list, tuple)):
        paths = [paths]

    res = []
    uuid = kwargs.get('uuid')
    for path in paths:
        if uuid:
            path = _get_abs_path(host, uuid, path)
            if not path:
                return
        res.append('rsync://%s:%s@%s%s:%s' % (host.username, host.password, host.host, path, host.port))
    return res

def set_retry(sync):
    sync['reserved'] = datetime.utcnow() + DELTA_RETRY
    Sync.save(sync, safe=True)

@timer(30)
def process_sync(sync_id):
    sync = Sync.get(sync_id)
    if not sync:
        return
    if Transfer.find_one({'sync_id': sync['_id'], 'finished': None}):
        set_retry(sync)
        return
    src = get_uris(**sync['src'])
    if not src:
        set_retry(sync)
        return
    dst = get_uris(**sync['dst'])
    if not dst:
        set_retry(sync)
        return
    dst = dst[0]

    parameters = {
        'exclusions': sync.get('exclusions'),
        'delete': sync.get('delete'),
        }
    transfer_id = Transfer.add(src, dst,
            sync_id=sync['_id'], parameters=parameters)
    logger.info('added transfer %s to %s' % (src, dst))

    sync['transfer_id'] = transfer_id
    sync['processed'] = datetime.utcnow()
    sync['reserved'] = datetime.utcnow() + timedelta(hours=sync['recurrence'])
    Sync.save(sync, safe=True)

def validate_sync(sync):
    begin = sync.get('hour_begin') or 0
    end = sync.get('hour_end') or 24
    if begin <= datetime.now().hour < end:
        return True

@loop(60)
def run():
    for sync in Sync.find({'$or': [
            {'reserved': {'$exists': False}},
            {'reserved': {'$lt': datetime.utcnow()}},
            ]}):
        if not validate_sync(sync):
            continue
        target = '%s.workers.sync.process_sync' % settings.PACKAGE_NAME
        get_factory().add(target=target, args=(sync['_id'],),
                timeout=settings.SYNC_TIMEOUT)
