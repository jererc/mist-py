from datetime import datetime, timedelta
import logging

from flask import request, jsonify

from bson.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING

from systools.system.webapp import crossdomain, serialize

from transfer import Transfer

from mist import User, Host, Sync, Settings, get_user
from mist.apps import app


logger = logging.getLogger(__name__)


class SyncError(Exception): pass


@app.route('/status', methods=['GET'])
@crossdomain(origin='*')
def check_status():
    return jsonify(result='mist')


#
# Host
#
@app.route('/host/list', methods=['GET'])
@crossdomain(origin='*')
def list_hosts():
    items = []
    for res in Host.find(sort=[('seen', DESCENDING)]):
        res['logged_users'] = []
        for user in res.get('users', []):
            if user.get('logged'):
                user_ = get_user(user['_id'])
                if user_:
                    res['logged_users'].append(user_['name'])

        items.append(res)

    return serialize({'result': items})

@app.route('/host/uuid/list', methods=['GET'])
@crossdomain(origin='*')
def list_uuids():
    items = []
    for res in Host.find({'disks': {'$exists': True}}):
        for disk in res['disks']:
            disk['host'] = res['host']
            items.append(disk)

    return serialize({'result': items})

@app.route('/host/reset', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*')
def reset_host():
    data = request.json
    if not data.get('id'):
        return jsonify(error='missing id')
    Host.update({'_id': ObjectId(data['id'])},
            {'$set': {'users': []}}, safe=True)
    return jsonify(result=True)


#
# User
#
@app.route('/user/create', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*')
def create_user():
    data = request.json
    if not data.get('name'):
        return jsonify(error='missing name')
    if not data.get('username'):
        return jsonify(error='missing username')
    if not data.get('password'):
        return jsonify(error='missing password')
    if not data.get('port'):
        return jsonify(error='missing port')

    if User.find_one({'$or': [
            {
                'name': data['name'],
            },
            {
                'username': data['username'],
                'password': data['password'],
                'port': int(data['port']),
            },
            ]}):
        return jsonify(error='user already exists')

    User.insert({
            'name': data['name'],
            'username': data['username'],
            'password': data['password'],
            'port': int(data['port']),
            'paths': data.get('paths', {}),
            }, safe=True)
    return jsonify(result=True)

@app.route('/user/list', methods=['GET'])
@crossdomain(origin='*')
def list_users():
    now = datetime.utcnow()
    items = []
    for res in User.find(sort=[('name', ASCENDING)]):
        if not res.get('paths'):
            res['paths'] = {}

        logged = []
        res['hosts'] = []
        for host in Host.find({'users': {'$elemMatch': {
                '_id': res['_id'],
                'logged': {'$exists': True},
                }}}):
            res['hosts'].append(host['host'])
            for user in host['users']:
                if user['_id'] == res['_id']:
                    logged.append(user['logged'])

        res['logged'] = max(logged) if logged else None
        if res['logged'] and res['logged'] > now - timedelta(minutes=30):
            res['status'] = True
        else:
            res['status'] = False

        items.append(res)

    return serialize({'result': items})

@app.route('/user/update', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*')
def update_user():
    data = request.json
    if not data.get('_id'):
        return jsonify(error='missing id')
    if not data.get('name'):
        return jsonify(error='missing name')
    if not data.get('username'):
        return jsonify(error='missing username')
    if not data.get('password'):
        return jsonify(error='missing password')
    if not data.get('port'):
        return jsonify(error='missing port')

    doc = {
        'name': data['name'],
        'username': data['username'],
        'password': data['password'],
        'port': int(data['port']),
        'paths': data.get('paths', {}),
        }
    User.update({'_id': ObjectId(data['_id'])},
            {'$set': doc}, safe=True)
    return jsonify(result=True)

@app.route('/user/remove', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*')
def remove_user():
    data = request.json
    if not data.get('id'):
        return jsonify(error='missing id')
    User.remove({'_id': ObjectId(data['id'])}, safe=True)
    return jsonify(result=True)


#
# Sync
#
def _get_sync(data):
    if not data.get('src'):
        raise SyncError('missing src')
    if not data.get('dst'):
        raise SyncError('missing dst')
    if not data.get('recurrence'):
        raise SyncError('missing recurrence')

    for type in ('src', 'dst'):
        for key in ('user', 'path'):
            if not data[type].get(key):
                raise SyncError('missing %s %s' % (type, key))

    res = {
        'src': data['src'],
        'dst': data['dst'],
        'exclusions': data.get('exclusions') or [],
        'delete': data.get('delete', True),
        'recurrence': int(data['recurrence']),
        }
    for type in ('src', 'dst'):
        for key, val in res[type].items():
            if key == 'user':
                res[type][key] = ObjectId(val)
    for key in ('hour_begin', 'hour_end'):
        res[key] = int(data[key]) if data.get(key) else None
    return res

@app.route('/sync/create', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*')
def create_sync():
    data = request.json
    try:
        sync = _get_sync(data)
    except SyncError, e:
        return jsonify(error=str(e))
    if Sync.find_one(sync):
        return jsonify(error='sync already exists')
    Sync.insert(sync, safe=True)
    return jsonify(result=True)

def _get_params_str(params):
    user_id = params.get('user')
    if user_id:
        user = get_user(user_id)
        if user:
            return user['name']
    return params.get('hwaddr') or params.get('uuid')

@app.route('/sync/list', methods=['GET'])
@crossdomain(origin='*')
def list_syncs():
    now = datetime.utcnow()
    items = []
    for res in Sync.find(sort=[('processed', DESCENDING)]):
        res['name'] = '%s to %s' % (_get_params_str(res['src']), _get_params_str(res['dst']))
        if res.get('transfer_id'):
            transfer = Transfer.find_one({'_id': ObjectId(res['transfer_id'])})
        else:
            transfer = None
        res['transfer'] = transfer or {}
        if not transfer:
            res['status'] = 'pending'
        elif transfer['finished'] and transfer['finished'] > now - timedelta(hours=res['recurrence'] + 24):
            res['status'] = 'ok'
        else:
            res['status'] = 'queued'

        items.append(res)

    return serialize({'result': items})

@app.route('/sync/update', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*')
def update_sync():
    data = request.json
    if not data.get('_id'):
        return jsonify(error='missing id')
    try:
        sync = _get_sync(data)
    except SyncError, e:
        return jsonify(error=str(e))
    Sync.update({'_id': ObjectId(data['_id'])},
            {'$set': sync}, safe=True)
    return jsonify(result=True)

@app.route('/sync/reset', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*')
def reset_sync():
    data = request.json
    if not data.get('id'):
        return jsonify(error='missing id')
    Sync.update({'_id': ObjectId(data['id'])},
            {'$set': {'reserved': None}}, safe=True)
    return jsonify(result=True)

@app.route('/sync/remove', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*')
def remove_sync():
    data = request.json
    if not data.get('id'):
        return jsonify(error='missing id')
    Sync.remove({'_id': ObjectId(data['id'])})
    return jsonify(result=True)


#
# Settings
#
@app.route('/settings/list', methods=['GET', 'OPTIONS'])
@crossdomain(origin='*')
def list_settings():
    settings = {}
    for section in ('host', 'sync'):
        settings[section] = Settings.get_settings(section)
    return serialize({'result': settings})

@app.route('/settings/update', methods=['POST', 'OPTIONS'])
@crossdomain(origin='*')
def update_settings():
    data = request.json
    for section, settings in data.items():
        Settings.set_settings(section, settings, overwrite=True)
    return jsonify(result=True)
