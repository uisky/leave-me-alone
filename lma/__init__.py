from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_user import LoginManager
import markdown

# flask
app = Flask(__name__)
app.config.from_object('config')
app.config.from_pyfile('../local.cfg', silent=True)

# flask.sqlalchemy
db = SQLAlchemy(app)

# logging
import logging
log = logging.getLogger()
console_handler = logging.StreamHandler()
if app.config['DEBUG']:
    console_handler.setLevel(logging.DEBUG)
else:
    console_handler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s %(levelname)s: \033[32m%(message)s\033[0m [in %(pathname)s:%(lineno)d]')
console_handler.setFormatter(formatter)
log.addHandler(console_handler)


# flask.user
from .users.models import User
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(userid):
    return User.query.get(userid)


# blueprints
from .users import mod as users_module
app.register_blueprint(users_module)

from .projects import mod as projects_module
app.register_blueprint(projects_module)

from . import index, jinja