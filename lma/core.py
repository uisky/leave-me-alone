from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
import flask_mail
from blinker import Namespace
from lagring import FlaskLagring


db = SQLAlchemy(session_options={'expire_on_commit': False})

csrf = CSRFProtect()

login_manager = LoginManager()

storage = FlaskLagring()

signals = Namespace()

flask_mail.message_policy = None
mail = flask_mail.Mail()
