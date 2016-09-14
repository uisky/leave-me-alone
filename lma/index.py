from flask import render_template, redirect, url_for
from flask_mail import Message
from flask_login import current_user
from . import app, mail


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('projects.index'))
    else:
        return render_template('index.html')


@app.route('/about/')
def about():
    return render_template('about.html')


@app.route('/mail')
def testmail():
    msg = Message('Flask Mail Test', body='Dat is fokin test!', recipients=['romakhin@gmail.com'])
    status = mail.send(msg)
    return 'Mail sent with status %r' % status