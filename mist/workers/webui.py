from systools.system import webapp

from mist import settings
from mist.webui import app


def run():
    webapp.run(app, host='0.0.0.0', port=settings.WEBUI_PORT)
