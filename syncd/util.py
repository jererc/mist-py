#!/usr/bin/env python
from pymongo import Connection

from syncd.settings import DB_NAME

from systools.network import get_ip


def get_db():
    return Connection('localhost')[DB_NAME]

def get_localhost():
    ips = get_ip()
    if ips:
        return ips[0]
