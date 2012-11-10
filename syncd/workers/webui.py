from systools.system import webapp

from syncd import settings
from syncd.webui import app


def run():
    webapp.run(app, host='0.0.0.0', port=settings.WEBUI_PORT)
