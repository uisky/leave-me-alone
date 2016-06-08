import random
import string

from flask import render_template, request, redirect, flash, url_for
from flask_login import login_required, current_user
from flask.ext.login import login_user, logout_user

from . import mod, forms
from .models import User, PasswordResetToken
from .. import db, app, mail
from ..projects.models import ProjectFolder
from ..utils import flash_errors


@mod.route('/')
def index():
    return render_template('users/index.html')


@mod.route('/login/', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email', '')).first()

        if user and User.hash_password(request.form.get('password', '')) == user.password_hash:
            login_user(user)
            return redirect(request.args.get('next', '/projects'))
        else:
            flash('Неправильный e-mail или пароль.', 'danger')

    return render_template('users/login.html')


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
            db.session.flush()

            archive_folder = ProjectFolder(user_id=user.id, name='Архив', in_menu=False)
            db.session.add(archive_folder)

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


@mod.route('/sclerosis/', methods=('GET', 'POST'))
def sclerosis():
    if request.method == 'POST':
        user = User.query.filter(db.func.lower(User.email) == request.form.get('email').strip().lower()).first()
        if user:
            # Стираем старые токены этого юзера, если были. А заодно и другие старые токены.
            db.session.execute(
                "DELETE FROM %s WHERE user_id = :user_id OR created < now() - interval '1 day'" % PasswordResetToken.__tablename__,
                {'user_id': user.id}
            )

            token = PasswordResetToken(
                user_id=user.id,
                hash=''.join([random.choice(string.ascii_letters+string.digits) for _ in range(64)])
            )
            db.session.add(token)

            msg_text = """Здравствуйте.

Вот ссылка для восстановления пароля на Leave Me Alone:

%s

чмглов.""" % url_for('.reset', user_id=token.user_id, token=token.hash, _external=True)

            mail.send_message(
                subject='Восстановление пароля на Leave Me Alone',
                recipients=[user.email],
                body=msg_text
            )
            print(msg_text)

            db.session.commit()

        flash('Если вы ввели правильный адрес электронной почты, вам туда сейчас придёт письмо со ссылкой '
              'для восстановления пароля.<br>На всякий случай, посмотрите в папке «Спам».', 'success')
        return redirect(url_for('index'))

    return render_template('users/sclerosis.html')


@mod.route('/reset/<int:user_id>/<hash>', methods=('GET', 'POST'))
def reset(user_id, hash):
    token = PasswordResetToken.query.filter_by(user_id=user_id, hash=hash).first()

    if not token:
        flash('Ссылка для восстановления пароля повреждена или устарела. Запросите сброс пароля ещё раз.', 'danger')
        return redirect(url_for('.sclerosis'))

    if request.method == 'POST':
        if len(request.form.get('pass')) < 6:
            flash('Пароль должен быть не короче 6 символов.', 'danger')
            return redirect(url_for('.reset', user_id=user_id, hash=hash))
        if request.form.get('pass') != request.form.get('pass-check'):
            flash('Пароли не совпадают.', 'danger')
            return redirect(url_for('.reset', user_id=user_id, hash=hash))

        token.user.password_hash = User.hash_password(request.form.get('pass'))
        db.session.delete(token)
        db.session.commit()

        flash('Готово, входите с новым паролем.', 'success')
        return redirect(url_for('index'))

    return render_template('users/reset.html', user=token.user, token=token)


if app.config.get('DEBUG'):
    @mod.route('/resque/')
    def rescue():
        user = User.query.get(1)
        login_user(user)
        return redirect('/')
