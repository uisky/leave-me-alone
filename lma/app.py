import locale
import os

from flask import Flask

from .core import db, csrf, mail, login_manager
from .jinja import init_jinja_filters
from .log import init_logging


def create_app(cfg=None, purpose=None):
    """Application factory
    """
    locale.setlocale(locale.LC_ALL, '')

    app = Flask(__name__)
    app.purpose = purpose
    load_config(app, cfg)

    init_logging(app)

    db.init_app(app)

    # Вроде бы без этой хуйни не работал алембик, но на самом деле прекрасно он работает
    # with app.app_context():
    #     from . import models

    csrf.init_app(app)

    init_login(app)

    init_mail(app)

    register_blueprints(app)

    init_jinja_filters(app)

    app.logger.info('%s %s загружен' % (app.name, app.config['ENVIRONMENT']))

    return app


def load_config(app, cfg=None):
    """Загружает в app конфиг из config.py, а потом обновляет его py-файла в cfg или, если он не указан, из переменной
    окружения LMA_CFG
    """
    app.config.from_pyfile('config.py')

    if os.path.isfile('config.local.py'):
        app.config.from_pyfile('config.local.py')

    if cfg is None and 'LMA_CFG' in os.environ:
        cfg = os.environ['LMA_CFG']

    if cfg is not None:
        app.config.from_pyfile(cfg)


def register_blueprints(app):
    from . import front, users, projects

    for m in (front, users, projects):
        app.register_blueprint(m.mod)


def init_login(app):
    from lma.models import User
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)


def init_mail(app):
    mail.init_app(app)
