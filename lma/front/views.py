from flask import render_template, redirect, url_for
from flask_mail import Message
from flask_login import current_user

from . import mod
from lma.core import mail


@mod.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('projects.index'))
    else:
        return render_template('front/index.html')


@mod.route('/about/')
def about():
    return render_template('front/about.html')


@mod.route('/mail')
def testmail():
    msg = Message('Flask Mail Test', body='Dat is fokin test!', recipients=['romakhin@gmail.com'])
    status = mail.send(msg)
    return 'Mail sent with status %r' % status
