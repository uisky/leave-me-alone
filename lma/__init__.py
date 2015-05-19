from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_user import LoginManager
import markdown

# flask
app = Flask(__name__)
app.config.from_object('config')
app.config.from_pyfile('local.cfg', silent=True)

# flask.sqlalchemy
db = SQLAlchemy(app)

# flask.user
from .users.models import User
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(userid):
    return User.query.get(userid)


# jinja filters
@app.template_filter('markdown')
def jinja_markdown(x):
    return markdown.markdown(x, output_format='html5')

# blueprints
from .users import mod as users_module
app.register_blueprint(users_module)

from .projects import mod as projects_module
app.register_blueprint(projects_module)

from . import index