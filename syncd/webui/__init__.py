from flask import Flask

app = Flask(__name__)
app.secret_key = '0049850730930927097644398656536'
app.config.from_object('syncd.settings')

from syncd.webui import views
