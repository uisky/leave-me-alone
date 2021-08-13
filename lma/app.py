import locale
import os

from flask import Flask, g, render_template

from .core import db, csrf, mail, login_manager, storage
from .jinja import init_jinja_filters
import flask_sa_logger


def create_app(cfg=None, purpose=None):
    """Application factory
    """
    locale.setlocale(locale.LC_ALL, '')

    app = Flask(__name__)
    app.purpose = purpose
    load_config(app, cfg)

    flask_sa_logger.init_logging(app)

    db.init_app(app)

    csrf.init_app(app)

    init_login(app)

    init_mail(app)

    register_blueprints(app)

    init_jinja_filters(app)

    storage.init_app(app)

    @app.after_request
    def deferred_cookies(response):
        for args, kwargs in g.get('deferred_cookies', []):
            response.set_cookie(*args, **kwargs)
        return response

    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    def error_401(e):
        return render_template('errors/%d.html' % e.code, e=e)

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
