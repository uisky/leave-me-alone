from flask import render_template, request, redirect, flash, url_for
from flask_login import login_required, current_user
from flask.ext.login import login_user, logout_user

from . import mod, forms
from .. import db, app
from .models import User
from ..utils import flash_errors


@mod.route('/')
def index():
    return render_template('users/index.html')


@mod.route('/login/', methods=['POST'])
def login():
    user = User.query.filter_by(email=request.form.get('email', '')).first()

    if user and User.hash_password(request.form.get('password', '')) == user.password_hash:
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


@mod.route('/settings/', methods=('GET', 'POST'))
@login_required
def settings():
    def save():
        if user.email.lower() != form.email.data.lower():
            test = User.query.filter(db.func.lower(User.email) == form.email.data.lower()).first()
            if test is not None:
                flash('Внезапно, такой e-mail уже используется каким-то юзером.', 'danger')
                return False

        user.email = form.email.data
        user.name = form.name.data

        if form.password.data:
            user.password_hash = User.hash_password(form.password.data)

        db.session.commit()

        return True

    form = forms.SettingsForm(obj=current_user)
    user = User.query.get(current_user.id)

    if form.validate_on_submit() and save():
        flash('Ок, чо.', 'success')
        return redirect(url_for('.settings'))
    else:
        flash_errors(form)

    return render_template('users/settings.html', form=form)


if app.config.get('DEBUG'):
    @mod.route('/resque/')
    def rescue():
        user = User.query.get(1)
        login_user(user)
        return redirect('/')
