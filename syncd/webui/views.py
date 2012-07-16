import re

from flask import jsonify, request, url_for, render_template, redirect

from pymongo.objectid import ObjectId

from syncd.settings import COL_SYNCS, COL_USERS, COL_HOSTS
from syncd.util import get_db
from syncd.webui import app
from syncd import get_users


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
    db = get_db()
    add_type = request.args.get('type')

    if add_type == 'user':
        username = request.args.get('username')
        password = request.args.get('password')

        if username and password:
            doc = {
                'username': username,
                'password': password,
                'port': int(request.args.get('port')),
                }
            if not db[COL_USERS].find_one(doc):
                db[COL_USERS].insert(doc, safe=True)
                return jsonify(result=True)

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
                return jsonify(result=True)

    return jsonify(result=False)


#
# Users
#
@app.route('/users')
def users():
    res = get_db()[COL_USERS].find()
    return render_template('users.html', items=res)

@app.route('/users/action')
def users_action():
    action = request.args.get('action')
    id = request.args.get('id')
    if id:
        if action == 'remove':
            get_db()[COL_USERS].remove({'_id': ObjectId(id)})

        elif action == 'save':
            username = request.args.get('username')
            password = request.args.get('password')
            if username and password:
                get_db()[COL_USERS].update({'_id': ObjectId(id)}, {'$set': {
                        'username': username,
                        'password': password,
                        'port': int(request.args.get('port')),
                        }}, safe=True)

    return jsonify(result=action)


#
# Syncs
#
@app.route('/syncs')
def syncs():
    items = []
    for res in get_db()[COL_SYNCS].find():
        res.update({
                'src_str': _get_params_str(res['src']),
                'dst_str': _get_params_str(res['dst']),
                })
        items.append(res)

    return render_template('syncs.html', users=get_users(), items=items)

@app.route('/syncs/action')
def syncs_action():
    action = request.args.get('action')
    id = request.args.get('id')
    if id:
        if action == 'reset':
            get_db()[COL_SYNCS].update({'_id': ObjectId(id)},
                    {'$unset': {'finished': True}}, safe=True)

        elif action == 'remove':
            get_db()[COL_SYNCS].remove({'_id': ObjectId(id)})

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

    return jsonify(result=action)

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
        value = data.get('%s_%s' % (prefix, attr))
        if value:
            if attr == 'user':
                username, password = value.split(' ', 1)
                res['username'] = username
                res['password'] = password
            else:
                res[attr] = value
    return res

def _validate_params(params):
    if not params.get('path'):
        return
    if params.get('username') and not params.get('password'):
        return
    if not params.get('username') and not params.get('hwaddr') and not params.get('uuid'):
        return
    return True

def _get_params_str(params):
    return params.get('username') or params.get('hwaddr') or params.get('uuid') or ''


#
# Hosts
#
@app.route('/hosts')
def hosts():
    items = []
    for res in get_db()[COL_HOSTS].find():
        res['usernames'] = [user.split(' ', 1)[0] for user in res.get('users', [])]
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
