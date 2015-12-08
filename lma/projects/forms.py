from bs4 import BeautifulSoup

from flask_wtf import Form
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, SelectField, BooleanField, DateField, \
    HiddenField, RadioField
from wtforms import validators as v

from .models import IMPORTANCE, CHARACTERS, PROJECT_TYPES


def strip_field(s):
    if isinstance(s, str):
        return s.strip()


class ProjectPropertiesForm(Form):
    name = StringField('Название', [v.required(message='Проекту нужно имя.')], filters=[strip_field])
    intro = TextAreaField('Вступительное слово', [v.optional()], filters=[strip_field])
    # type = RadioField('Тип', [v.required()], choices=PROJECT_TYPES)
    has_sprints = BooleanField('Использовать спринты')


class OutputOptions(Form):
    sort = SelectField(
        'Сортировка',
        [v.optional()],
        choices=[
            ('deadline', 'По дедлайну'),
            ('importance', 'По важности'),
            ('created', 'По дате создания'),
            ('custom', 'Как сам расставил'),
        ])

    sprint = SelectField('Спринт', [v.optional()], default=0, coerce=int)


class TaskForm(Form):
    subject = StringField('Пароль', [v.required(message='Опишите задачу.')], filters=[strip_field])
    description = TextAreaField('Ник', [v.optional()])
    deadline = DateTimeField('Дедлайн', [v.optional()], format='%d.%m.%Y %H:%M')
    assigned_id = IntegerField('Исполнитель', [v.optional()])
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


class KarmaRecordForm(Form):
    value = SelectField('Оценка', [v.required(message='Поставьте оценку')],
                        choices=[(-2, '-2'), (-1, '-1'), (0, ''), (1, '+1'), (2, '+2')],
                        coerce=int)
    comment = TextAreaField('Обоснование', [v.required(message='Обоснуйте.')], filters=[strip_field])
