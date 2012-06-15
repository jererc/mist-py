import re

from flask import jsonify, request, url_for, render_template, redirect

from pymongo.objectid import ObjectId

from syncd.settings import COL_SYNCS, COL_HOSTS
from syncd.util import get_db
from syncd.webui import app


@app.route('/')
def index():
    return redirect(url_for('syncs'))

@app.route('/add')
def add():
    return render_template('add.html')

@app.route('/syncs')
def syncs():
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
    action = request.args.get('action')
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

    db = get_db()
    result = action

    if action == 'add':

        print params

        if _validate_params(params['src']) and _validate_params(params['dst']):
            db[COL_SYNCS].insert(params, safe=True)

    else:
        id = request.args.get('id')
        if id:

            if action == 'reset':
                db[COL_SYNCS].update({'_id': ObjectId(id)}, {'$unset': {'finished': True}}, safe=True)

            elif action == 'remove':
                db[COL_SYNCS].remove({'_id': ObjectId(id)})

            elif action == 'save':
                if _validate_params(params['src']) and _validate_params(params['dst']):
                    db[COL_SYNCS].update({'_id': ObjectId(id)}, {'$set': params}, safe=True)

    return jsonify(result=result)

@app.route('/syncs/status')
def get_sync_status():
    id = request.args.get('id')
    res = get_db()[COL_SYNCS].find_one({'_id': ObjectId(id)})

    if res.get('processing') == True:
        result = 'processing'
    elif res.get('success') == False:
        result = 'failed'
    else:
        result = 'pending'

    return jsonify(result=result)

@app.route('/hosts')
def hosts():
    res = get_db()[COL_HOSTS].find()
    return render_template('hosts.html', items=res)

def _get_params(prefix, data):
    res = {}
    for attr in ('username', 'hwaddr', 'uuid', 'path'):
        value = data.get('%s_%s' % (prefix, attr))
        if value:
            res[attr] = value
    return res

def _validate_params(params):
    if params.get('path') and (params.get('username') or params.get('hwaddr') or params.get('uuid')):
        return True

def _get_params_str(params):
    return params.get('username') or params.get('hwaddr') or params.get('uuid') or ''
