from flask_wtf import Form
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, SelectField, BooleanField, DecimalField
from wtforms import validators as v

from lma.models import Task


def strip_field(s):
    if isinstance(s, str):
        return s.strip()


class ProjectPropertiesForm(Form):
    name = StringField('Название', [v.required(message='Проекту нужно имя.')], filters=[strip_field])
    intro = TextAreaField('Вступительное слово', [v.optional()], filters=[strip_field])
    # type = RadioField('Тип', [v.required()], choices=PROJECT_TYPES)
    has_sprints = BooleanField('Использовать вехи')


class ProjectFolderForm(Form):
    name = StringField('Название', [v.required(message='Имя забыли.')], filters=[strip_field])
    in_menu = BooleanField('Показывать проекты из этой папки в меню', default=True)


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
                             choices=[(x['id'], x['name']) for x in Task.IMPORTANCE],
                             coerce=int)
    character = SelectField('Характер', [v.optional()],
                            choices=[(0, '')] + [(x['id'], x['name']) for x in Task.CHARACTERS.values()],
                            coerce=int)
    estimate = DecimalField('Оценка по времени', [v.optional()], places=1)


class SprintPropertiesForm(Form):
    name = StringField('Название', [v.required(message='У вехи должно быть название')], filters=[strip_field])


class KarmaRecordForm(Form):
    value = SelectField('Оценка', [v.required(message='Поставьте оценку')],
                        choices=[(-2, '-2'), (-1, '-1'), (0, ''), (1, '+1'), (2, '+2')],
                        coerce=int)
    comment = TextAreaField('Обоснование', [v.required(message='Обоснуйте.')], filters=[strip_field])
