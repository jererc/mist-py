from datetime import datetime
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
    id = request.args.get('id')
    res = Host.find_one({'_id': ObjectId(id)})
    if res and res.get('alive'):
        if res.get('users'):
            result = True
        else:
            result = False
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
        '_id': ObjectId(request.args.get('id')),
        'name': request.args.get('name') or '%s %s' % (username, password),
        'username': username,
        'password': password,
        'port': int(request.args.get('port')),
        }
    if doc['username'] and doc['password']:
        doc['paths'] = {
            'audio': request.args.get('path_audio', ''),
            'video': request.args.get('path_video', ''),
            }
        User.save(doc, safe=True)
        result = True

    return jsonify(result=result)

@app.route('/users/remove')
def remove_action():
    id = request.args.get('id')
    User.remove({'_id': ObjectId(id)}, safe=True)
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
        status = 'ok'
        if res['reserved'] and res['reserved'] < now:
            status = 'pending'
        res.update({
                'src_str': _get_params_str(res['src']),
                'dst_str': _get_params_str(res['dst']),
                'status': status,
                })
        items.append(res)

    return render_template('syncs.html', items=items)

@app.route('/syncs/add')
def add_sync():
    result = None

    exclusions = request.args.get('exclusions')
    exclusions = re.split(r'[,\s]+', exclusions) if exclusions else []
    params = {
        'src': _get_params('src', request.args),
        'dst': _get_params('dst', request.args),
        'exclusions': exclusions,
        'delete': 'delete' in request.args,
        'recurrence': int(request.args.get('recurrence')),
        }
    for hour in ('hour_begin', 'hour_end'):
        val = int(request.args.get(hour))
        params[hour] = val if val >= 0 else None

    if _validate_params(params['src']) and _validate_params(params['dst']):
        if not Sync.find_one(params):
            Sync.insert(params, safe=True)
            result = True

    return jsonify(result=result)

@app.route('/syncs/update')
def update_sync():
    result = None

    id = request.args.get('id')
    exclusions = request.args.get('exclusions')
    exclusions = re.split(r'[,\s]+', exclusions) if exclusions else []
    params = {
        'src': _get_params('src', request.args),
        'dst': _get_params('dst', request.args),
        'exclusions': exclusions,
        'delete': 'delete' in request.args,
        'recurrence': int(request.args.get('recurrence')),
        }
    for hour in ('hour_begin', 'hour_end'):
        val = int(request.args.get(hour))
        params[hour] = val if val >= 0 else None

    if _validate_params(params['src']) and _validate_params(params['dst']):
        Sync.update({'_id': ObjectId(id)},
                {'$set': params}, safe=True)
        result = True

    return jsonify(result=result)

@app.route('/syncs/reset')
def reset_sync():
    id = request.args.get('id')
    Sync.update({'_id': ObjectId(id)},
            {'$unset': {'processed': True}}, safe=True)
    return jsonify(result=True)

@app.route('/syncs/remove')
def remove_sync():
    id = request.args.get('id')
    Sync.remove({'_id': ObjectId(id)})
    return jsonify(result=True)


@app.route('/syncs/status')
def get_sync_status():
    result = None
    id = request.args.get('id')
    res = Sync.find_one({'_id': ObjectId(id)})
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
            res[attr] = val
    return res

def _validate_params(params):
    if not params.get('path'):
        return False
    if not (params.get('user') or params.get('hwaddr') or params.get('uuid')):
        return False
    return True

def _get_params_str(params):
    user_id = params.get('user')
    if user_id:
        user = get_user(user_id)
        if user:
            return user['name']

    return params.get('hwaddr') or params.get('uuid')
