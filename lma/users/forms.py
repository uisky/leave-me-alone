from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms import validators as v


class RegisterForm(FlaskForm):
    email = StringField('E-mail', [
        v.required(message='Введите e-mail.'),
        v.Email(message='Неправильный адрес электронной почты.')
    ])
    password = StringField('Пароль', [v.required(message='Введите пароль.')])
    name = StringField('Ник', [v.required(message='Введите ник.')])


class SettingsForm(RegisterForm):
    password = StringField('Пароль', [v.optional()])
