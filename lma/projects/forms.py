from flask_wtf import Form
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, SelectField, BooleanField, DateField
from wtforms import validators as v
from .models import IMPORTANCE, CHARACTERS, PROJECT_TYPES


def strip_field(s):
    if isinstance(s, str):
        return s.strip()


class ProjectPropertiesForm(Form):
    name = StringField('Название', [v.required(message='Проекту нужно имя.')], filters=[strip_field])
    has_sprints = BooleanField('Использровать спринты')


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

    sprint = SelectField('Спринт', [v.optional()], default=0, coerce=int)


class TaskForm(Form):
    subject = StringField('Пароль', [v.required(message='Опишите задачу.')], filters=[strip_field])
    description = TextAreaField('Ник', [v.optional()])
    deadline = DateTimeField('Дедлайн', [v.optional()], format='%d.%m.%Y %H:%M')
    assigned_id = IntegerField('исполнитель', [v.optional()])
    importance = SelectField('Важность', [v.optional()],
                             choices=[(x['id'], x['name']) for x in IMPORTANCE],
                             coerce=int)
    character = SelectField('Характер', [v.optional()],
                            choices=[(0, '')] + [(x['id'], x['name']) for x in CHARACTERS],
                            coerce=int)


class SprintPropertiesForm(Form):
    name = StringField('Название', [v.required(message='У спринта должно быть название')], filters=[strip_field])
    start = DateField('Начало', [v.optional()], format='%d.%m.%Y')
    finish = DateField('Конец', [v.optional()], format='%d.%m.%Y')