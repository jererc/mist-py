import re

from flask import jsonify, request, render_template

from pymongo.objectid import ObjectId

from syncd.syncd import get_db, COL_SYNCS
from syncd.webui import app


@app.route('/')
def index():
    items = []
    for res in get_db()[COL_SYNCS].find():
        res.update({
                'src_str': _get_params_str(res['src']),
                'dst_str': _get_params_str(res['dst']),
                })
        items.append(res)

    return render_template('sync.html', items=items)

@app.route('/action')
def action():
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
        if _validate_params(params['src']) and _validate_params(params['dst']):
            db[COL_SYNCS].insert(params, safe=True)

    else:
        id = request.args.get('id')
        if id:

            if action == 'reset':
                db[COL_SYNCS].update({'_id': ObjectId(id)}, {'$unset': {'processed': True}}, safe=True)

            elif action == 'remove':
                db[COL_SYNCS].remove({'_id': ObjectId(id)})

            elif action == 'save':
                if _validate_params(params['src']) and _validate_params(params['dst']):
                    db[COL_SYNCS].update({'_id': ObjectId(id)}, {'$set': params}, safe=True)

    return jsonify(result=result)

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
