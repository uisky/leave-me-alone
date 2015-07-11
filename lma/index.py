from flask import render_template
from flask_mail import Message
from . import app, mail


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about/')
def about():
    return render_template('about.html')


@app.route('/mail')
def testmail():
    msg = Message('Flask Mail Test', body='Dat is fokin test!', recipients=['romakhin@gmail.com'])
    status = mail.send(msg)
    return 'Mail sent with status %r' % status