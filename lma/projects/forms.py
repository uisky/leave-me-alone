from flask_wtf import Form
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField
from wtforms import validators as v


class TaskForm(Form):
    subject = StringField('Пароль', [v.required(message='Опишите задачу.')])
    description = TextAreaField('Ник')
    deadline = DateTimeField('Дедлайн', format='%d.%m.%Y %H:%M')
    assigned_id = IntegerField('исполнитель')