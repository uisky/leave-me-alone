from flask import render_template, request, redirect, flash
from flask_user import login_required
from flask.ext.login import login_user, logout_user

from . import mod, forms
from .. import db
from .models import User
from ..utils import flash_errors


@mod.route('/')
def index():
    return render_template('users/index.html')


@mod.route('/login/', methods=['POST'])
def login():
    user = User.query.filter_by(email=request.form.get('email', '')).first()

    if User.hash_password(request.form.get('password', '')) == user.password_hash:
        login_user(user)
        return redirect('/projects')
    else:
        flash('Неправильный e-mail или пароль.', 'danger')

    return redirect(request.args.get('next', '/'))


@mod.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect('/')


@mod.route('/register/', methods=('GET', 'POST'))
def register():
    user = User()
    form = forms.RegisterForm(obj=user)

    if form.validate_on_submit():
        email_exists = User.query.filter(db.func.lower(User.email) == form.email.data.lower()).first()
        name_exists = User.query.filter(db.func.lower(User.name) == form.name.data.lower()).first()
        if email_exists:
            flash('Пользователь с такой электронной почтой уже зарегистрирован.', 'danger')
        if name_exists:
            flash('Пользователь с таким ником у нас уже есть. Придумайте что-нибудь пооригинальнее.', 'danger')

        if not name_exists and not email_exists:
            user.email = form.email.data
            user.name = form.name.data
            user.password_hash = User.hash_password(form.password.data)

            db.session.add(user)
            db.session.commit()

            login_user(user)
            flash('Добро пожаловать в семью, %s!' % user.name, 'success')

            return redirect(request.args.get('next', '/'))

    flash_errors(form)

    return render_template('users/register.html', form=form)
