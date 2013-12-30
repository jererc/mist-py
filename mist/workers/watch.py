from datetime import datetime, timedelta
import logging

from systools.system import loop, timeout, timer
from systools.network.mail import Email

from mist import User, Host, Settings


logger = logging.getLogger(__name__)


def get_last_login(user_id):
    logins = []
    for host in Host.find({'users': {'$elemMatch': {
            '_id': user_id,
            'logged': {'$exists': True},
            }}}):
        for user_ in host['users']:
            if user_['_id'] == user_id:
                logins.append(user_['logged'])

    return max(logins) if logins else None

@loop(minutes=10)
@timeout(minutes=5)
@timer(30)
def run():
    settings = Settings.get_settings('email')
    if not set(['host', 'username', 'password', 'port']) <= set(settings.keys()):
        return

    server = None
    now = datetime.utcnow()
    delta = timedelta(days=settings.get('delta', 7))

    for user in User.find():
        if not user.get('email'):
            continue
        notified = user.get('notified')
        if notified and notified > now - delta:
            continue
        login = get_last_login(user['_id'])
        if login and login > now - delta:
            continue

        subject = '%s is unreachable' % user['name']
        if login:
            body = 'The device "%s" is unreachable for %d days.\n\n' % (user['name'], (now - login).days)
        else:
            body = 'The device "%s" is unreachable.\n\n'  % user['name']
        body += 'It won\'t be synchronized until your SSH server application (e.g.: QuickSSHD) is up and running on the device.'

        if not server:
            server = Email(settings['host'], settings['username'],
                    settings['password'], settings['port'])
        try:
            server.send('mist', user['email'], subject, body)
        except Exception, e:
            logger.error('failed to send email to %s: %s', user['email'], str(e))
            continue

        User.update({'_id': user['_id']},
                {'$set': {'notified': now}}, safe=True)
