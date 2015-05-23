from flask_wtf import Form
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField
from wtforms import validators as v


def stripfield(s):
    return s.strip()


class ProjectPropertiesForm(Form):
    name = StringField('Название', [v.required(message='Проекту нужно имя.')], filters=[stripfield])


class TaskForm(Form):
    subject = StringField('Пароль', [v.required(message='Опишите задачу.')])
    description = TextAreaField('Ник', [v.optional()])
    deadline = DateTimeField('Дедлайн', [v.optional()], format='%d.%m.%Y %H:%M')
    assigned_id = IntegerField('исполнитель', [v.optional()])