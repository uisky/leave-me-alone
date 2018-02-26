from flask import render_template, redirect, url_for, current_app, abort
from flask_mail import Message
from flask_login import current_user, login_user

from . import mod
from lma.core import mail
from lma.models import User


@mod.route('/')
def index():
    return render_template('front/index.html')


@mod.route('/about/')
def about():
    return render_template('front/about.html')


@mod.route('/lee/')
def lee():
    return render_template('front/lee.html')


@mod.route('/mail')
def testmail():
    msg = Message('Flask Mail Test', body='Dat is fokin test!', recipients=['romakhin@gmail.com'])
    status = mail.send(msg)
    return 'Mail sent with status %r' % status


@mod.route('/pretend/<int:user_id>/')
def authas(user_id):
    if not current_app.config.get('DEBUG'):
        abort(404)

    user = User.query.get_or_404(user_id)
    login_user(user)

    return redirect(url_for('projects.index'))
