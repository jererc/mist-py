#!/usr/bin/env python
from datetime import datetime
import logging

from syncd import env, settings
from syncd.util import get_db

from systools.network import get_hosts
from systools.system import loop, timeout, timer


logger = logging.getLogger(__name__)


def find_hosts():
    col = get_db()[settings.COL_HOSTS]

    hosts = get_hosts()
    if hosts is None:
        logger.debug('failed to find hosts')
        return

    for host in hosts:
        col.update({'host': host}, {'$set': {
                'alive': True,
                'seen': datetime.utcnow(),
                }}, upsert=True, safe=True)

    col.update({'host': {'$nin': hosts}},
            {'$set': {'alive': False}}, safe=True, multi=True)

    col.remove({'seen': {'$lt': datetime.utcnow() - settings.DELTA_HOST_ALIVE}},
            safe=True)

@loop(300)
@timeout(120)
@timer(30)
def main():
    find_hosts()


if __name__ == '__main__':
    main()
