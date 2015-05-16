from flask_wtf import Form
from wtforms import StringField
from wtforms import validators as v


class RegisterForm(Form):
    email = StringField('E-mail', [
        v.required(message='Введите e-mail.'),
        v.Email(message='Неправильный адрес электронной почты.')
    ])
    password = StringField('Пароль', [v.required(message='Введите пароль.')])
    name = StringField('Ник', [v.required(message='Введите ник.')])
