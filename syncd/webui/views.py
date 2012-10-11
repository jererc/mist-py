import re

from flask import session, request, url_for, render_template, redirect, jsonify

from pymongo.objectid import ObjectId
from pymongo import ASCENDING

from syncd import get_db, get_users, get_user
from syncd.settings import COL_SYNCS, COL_USERS, COL_HOSTS
from syncd.webui import app


@app.route('/')
def index():
    return redirect(url_for('syncs'))

#
# Add
#
@app.route('/add')
def add():
    return render_template('add.html', users=get_users())

@app.route('/add/action')
def add_action():
    result = None

    db = get_db()
    add_type = request.args.get('type')

    if add_type == 'user':
        username = request.args.get('username')
        password = request.args.get('password')
        if username and password:
            name = request.args.get('name') or '%s %s' % (username, password)
            doc = {
                'username': username,
                'password': password,
                'port': int(request.args.get('port')),
                }
            spec = {
                '$or': [
                    {'name': name},
                    doc,
                    ],
                }
            if not db[COL_USERS].find_one(spec):
                doc['name'] = name
                db[COL_USERS].insert(doc, safe=True)
                result = True

    elif add_type == 'sync':
        exclusions = request.args.get('exclusions')
        exclusions = re.split(r'[,\s]+', exclusions) if exclusions else []
        params = {
            'src': _get_params('src', request.args),
            'dst': _get_params('dst', request.args),
            'exclusions': exclusions,
            'delete': 'delete' in request.args,
            'recurrence': int(request.args.get('recurrence')),
            }
        for hour in ('hour_start', 'hour_end'):
            val = int(request.args.get(hour))
            params[hour] = val if val >= 0 else None

        if _validate_params(params['src']) and _validate_params(params['dst']):
            if not db[COL_SYNCS].find_one(params):
                db[COL_SYNCS].insert(params, safe=True)
                result = True

    return jsonify(result=result)

#
# Users
#
@app.route('/users')
def users():
    items = []
    for res in get_db()[COL_USERS].find(sort=[('name', ASCENDING)]):
        if not res.get('paths'):
            res['paths'] = {}
        items.append(res)
    return render_template('users.html', items=items)

@app.route('/users/action')
def users_action():
    result = None

    action = request.args.get('action')
    id = request.args.get('id')
    if id:
        if action == 'remove':
            get_db()[COL_USERS].remove({'_id': ObjectId(id)})
            result = action

        elif action == 'save':
            username = request.args.get('username')
            password = request.args.get('password')
            if username and password:
                name = request.args.get('name') or '%s %s' % (username, password)
                doc = {
                    'username': username,
                    'password': password,
                    'port': int(request.args.get('port')),
                    }
                spec = {
                    '_id': {'$ne': ObjectId(id)},
                    '$or': [
                        {'name': name},
                        doc,
                        ],
                    }
                if not get_db()[COL_USERS].find_one(spec):
                    doc['name'] = name
                    doc['paths'] = {
                        'audio': request.args.get('path_audio', ''),
                        'video': request.args.get('path_video', ''),
                        }
                    get_db()[COL_USERS].update({'_id': ObjectId(id)},
                            {'$set': doc}, safe=True)
                    result = action

    return jsonify(result=result)

#
# Syncs
#
@app.route('/syncs')
def syncs():
    session['users'] = get_users()

    items = []
    for res in get_db()[COL_SYNCS].find():
        res.update({
                'src_str': _get_params_str(res['src']),
                'dst_str': _get_params_str(res['dst']),
                })
        items.append(res)

    return render_template('syncs.html', items=items)

@app.route('/syncs/action')
def syncs_action():
    result = None

    action = request.args.get('action')
    id = request.args.get('id')
    if id:
        if action == 'reset':
            get_db()[COL_SYNCS].update({'_id': ObjectId(id)},
                    {'$unset': {'finished': True}}, safe=True)
            result = action

        elif action == 'remove':
            get_db()[COL_SYNCS].remove({'_id': ObjectId(id)})
            result = action

        elif action == 'save':
            exclusions = request.args.get('exclusions')
            exclusions = re.split(r'[,\s]+', exclusions) if exclusions else []
            params = {
                'src': _get_params('src', request.args),
                'dst': _get_params('dst', request.args),
                'exclusions': exclusions,
                'delete': 'delete' in request.args,
                'recurrence': int(request.args.get('recurrence')),
                }
            for hour in ('hour_start', 'hour_end'):
                val = int(request.args.get(hour))
                params[hour] = val if val >= 0 else None

            if _validate_params(params['src']) and _validate_params(params['dst']):
                get_db()[COL_SYNCS].update({'_id': ObjectId(id)}, {'$set': params}, safe=True)
                result = action

    return jsonify(result=result)

@app.route('/syncs/status')
def get_sync_status():
    result = None
    id = request.args.get('id')

    res = get_db()[COL_SYNCS].find_one({'_id': ObjectId(id)})
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

#
# Hosts
#
@app.route('/hosts')
def hosts():
    items = []
    for res in get_db()[COL_HOSTS].find():
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
    res = get_db()[COL_HOSTS].find_one({'_id': ObjectId(id)})
    if res and res.get('alive'):
        if res.get('users'):
            result = True
        else:
            result = False

    return jsonify(result=result)
