from datetime import datetime, timedelta
import re

from flask import session, request, url_for, render_template, redirect, jsonify

from pymongo.objectid import ObjectId
from pymongo import ASCENDING

from mist import get_users, get_user, User, Host, Sync
from mist.webui import app


@app.route('/')
def index():
    return redirect(url_for('hosts'))

#
# Hosts
#
@app.route('/hosts')
def hosts():
    items = []
    for res in Host.find():
        res['logged_users'] = []
        for user in res.get('users', []):
            if user.get('logged'):
                user_ = get_user(user['_id'])
                if user_:
                    res['logged_users'].append(user_['name'])

        items.append(res)

    return render_template('hosts.html', items=items)

@app.route('/hosts/status')
def get_host_status():
    result = None
    res = Host.find_one({'_id': ObjectId(request.args['id'])})
    if res and res.get('alive'):
        result = True if res.get('users') else False
    return jsonify(result=result)

#
# Users
#
@app.route('/users')
def users():
    items = []
    for res in User.find(sort=[('name', ASCENDING)]):
        if not res.get('paths'):
            res['paths'] = {}
        if Host.find_one({'users': {'$elemMatch': {
                '_id': res['_id'],
                'logged': {'$exists': True},
                }}}):
            res['status'] = 'up'
        else:
            res['status'] = 'down'

        items.append(res)

    return render_template('users.html', items=items)

@app.route('/users/add')
def add_user():
    result = None

    doc = {
        'username': request.args.get('username'),
        'password': request.args.get('password'),
        'port': int(request.args.get('port')),
        }
    if doc['username'] and doc['password']:
        name = request.args.get('name') or '%s %s' % (doc['username'], doc['password'])
        spec = {
            '$or': [{'name': name}, doc],
            }
        if not User.find_one(spec):
            doc['name'] = name
            User.insert(doc, safe=True)
            result = True

    return jsonify(result=result)

@app.route('/users/update')
def update_user():
    result = False

    username = request.args.get('username')
    password = request.args.get('password')
    doc = {
        '_id': ObjectId(request.args['id']),
        'name': request.args.get('name') or '%s %s' % (username, password),
        'username': username,
        'password': password,
        'port': int(request.args.get('port')),
        'paths': {},
        }
    if doc['username'] and doc['password']:
        for category in ('movies', 'tv', 'music'):
            doc['paths'][category] = request.args.get('path_%s' % category, '')
        User.save(doc, safe=True)
        result = True

    return jsonify(result=result)

@app.route('/users/remove')
def remove_action():
    User.remove({'_id': ObjectId(request.args['id'])}, safe=True)
    return jsonify(result=True)

#
# Syncs
#
@app.route('/syncs')
def syncs():
    session['users'] = get_users()

    now = datetime.utcnow()
    items = []
    for res in Sync.find():
        date_ = res.get('processed')
        if  date_ and date_ + timedelta(hours=res['recurrence']) > now:
            res['status'] = 'ok'
        else:
            res['status'] = 'pending'
        res['src_str'] = _get_params_str(res['src'])
        res['dst_str'] = _get_params_str(res['dst'])
        if isinstance(res['src']['path'], (list, tuple)):
            res['src']['path'] = ', '.join(res['src']['path'])
        items.append(res)

    return render_template('syncs.html', items=items)

@app.route('/syncs/add')
def add_sync():
    result = None

    params = _get_sync_params(request.args)
    if params and not Sync.find_one(params):
        Sync.insert(params, safe=True)
        result = True

    return jsonify(result=result)

@app.route('/syncs/update')
def update_sync():
    result = None

    params = _get_sync_params(request.args)
    if params:
        Sync.update({'_id': ObjectId(request.args['id'])},
                {'$set': params}, safe=True)
        result = True

    return jsonify(result=result)

@app.route('/syncs/reset')
def reset_sync():
    Sync.update({'_id': ObjectId(request.args['id'])},
            {'$unset': {'reserved': True}}, safe=True)
    return jsonify(result=True)

@app.route('/syncs/remove')
def remove_sync():
    Sync.remove({'_id': ObjectId(request.args['id'])})
    return jsonify(result=True)


@app.route('/syncs/status')
def get_sync_status():
    result = None
    res = Sync.find_one({'_id': ObjectId(request.args['id'])})
    if res:
        if res.get('processing') == True:
            result = 'processing'
        elif res.get('success') == False:
            result = 'failed'
        else:
            result = 'pending'

    return jsonify(result=result)

def _get_params(prefix, data):
    res = {}
    for attr in ('user', 'hwaddr', 'uuid', 'path'):
        val = data.get('%s_%s' % (prefix, attr))
        if val:
            if attr == 'user':
                val = ObjectId(val)
            elif attr == 'path' and ',' in val:
                val = [p for p in re.split(r'[,\s]+', val) if p]
            res[attr] = val
    return res

def _validate_params(params, multiple_paths=True):
    path = params.get('path')
    if not path:
        return False
    if not multiple_paths and isinstance(path, (list, tuple)) \
            and len(path) > 1:
        return False
    if not (params.get('user') or params.get('hwaddr') or params.get('uuid')):
        return False
    return True

def _get_sync_params(data):
    exclusions = data.get('exclusions')
    exclusions = re.split(r'[,\s]+', exclusions) if exclusions else []
    params = {
        'exclusions': [p for p in exclusions if p],
        'delete': 'delete' in data,
        'recurrence': int(data.get('recurrence')),
        }
    for key in ('src', 'dst'):
        params[key] = _get_params(key, data)
    for hour in ('hour_begin', 'hour_end'):
        val = int(data.get(hour))
        params[hour] = val if val >= 0 else None

    if _validate_params(params['src']) and \
            _validate_params(params['dst'], multiple_paths=False):
        return params

def _get_params_str(params):
    user_id = params.get('user')
    if user_id:
        user = get_user(user_id)
        if user:
            return user['name']

    return params.get('hwaddr') or params.get('uuid')
