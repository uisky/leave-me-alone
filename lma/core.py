from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CsrfProtect
from flask_login import LoginManager
import flask_mail
from blinker import Namespace


db = SQLAlchemy()

csrf = CsrfProtect()

login_manager = LoginManager()

signals = Namespace()

flask_mail.message_policy = None
mail = flask_mail.Mail()
