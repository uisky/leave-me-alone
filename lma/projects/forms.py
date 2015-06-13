from flask_wtf import Form
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, SelectField
from wtforms import validators as v
from .models import IMPORTANCE, CHARACTERS, PROJECT_TYPES


def stripfield(s):
    if isinstance(s, str):
        return s.strip()


class ProjectPropertiesForm(Form):
    name = StringField('Название', [v.required(message='Проекту нужно имя.')], filters=[stripfield])


class OutputOptions(Form):
    sort = SelectField(
        'Сортировка',
        [v.optional()],
        choices=[
            ('created', 'По дате создания'),
            ('deadline', 'По дедлайну'),
            ('importance', 'По важности'),
            ('custom', 'Как сам расставил'),
        ])


class TaskForm(Form):
    subject = StringField('Пароль', [v.required(message='Опишите задачу.')])
    description = TextAreaField('Ник', [v.optional()])
    deadline = DateTimeField('Дедлайн', [v.optional()], format='%d.%m.%Y %H:%M')
    assigned_id = IntegerField('исполнитель', [v.optional()])
    importance = SelectField('Важность', [v.optional()],
                             choices=[(x['id'], x['name']) for x in IMPORTANCE],
                             coerce=int)
    character = SelectField('Характер', [v.optional()],
                            choices=[(0, '')] + [(x['id'], x['name']) for x in CHARACTERS],
                            coerce=int)

