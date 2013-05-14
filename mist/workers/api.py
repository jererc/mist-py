from systools.system import webapp

from mist.apps import app
from mist import settings


def run():
    webapp.run(app, host='0.0.0.0', port=settings.API_PORT)
