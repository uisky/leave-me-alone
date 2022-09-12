from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, SelectField, BooleanField, DecimalField, \
    HiddenField, RadioField, FileField
from wtforms import validators as v

from lma.models import Task
from lma.utils import FiltersForm


def strip_field(s):
    if isinstance(s, str):
        return s.strip()


class ProjectPropertiesForm(FlaskForm):
    name = StringField('Название', [v.data_required(message='Проекту нужно имя.')], filters=[strip_field])
    gitlab_url = StringField('Gitlab', [v.optional()], filters=[strip_field])
    intro = TextAreaField('Вступительное слово', [v.optional()], filters=[strip_field])
    # type = RadioField('Тип', [v.data_required()], choices=PROJECT_TYPES)
    # has_sprints = BooleanField('Использовать доски')


class ProjectAccessForm(FlaskForm):
    access_levels = [('watcher', 'Член команды'), ('any', 'Кто угодно по сссылке')]
    ac_read = RadioField('Этот проект видят', [v.data_required()], choices=access_levels)
    ac_comment = RadioField('Кто может оставлять комментарии', [v.data_required()], choices=access_levels)


class ProjectFolderForm(FlaskForm):
    name = StringField('Название', [v.data_required(message='Имя забыли.')], filters=[strip_field])
    in_menu = BooleanField('Показывать проекты из этой папки в меню', default=True)


class OutputOptions(FlaskForm):
    sort = SelectField(
        'Сортировка',
        [v.optional()],
        choices=[
            ('deadline', 'По дедлайну'),
            ('importance', 'По важности'),
            ('created', 'По дате создания'),
            ('custom', 'Как сам расставил'),
        ])

    sprint = SelectField('Доска', [v.optional()], default=0, coerce=int)


class TaskForm(FlaskForm):
    subject = StringField('Название', [v.data_required(message='Опишите задачу.')], filters=[strip_field])
    description = TextAreaField('Описание', [v.optional()])
    image_ = FileField('Картинка', [v.optional()])
    image_delete = BooleanField('Стереть картинку', [v.optional()])
    tagslist = StringField('Тэги', [v.optional()])
    deadline = DateTimeField('Дедлайн', [v.optional()], format='%d.%m.%Y %H:%M')
    assigned_id = IntegerField('Исполнитель', [v.optional()])
    importance = SelectField('Важность', [v.optional()],
                             choices=[(id_, x['name']) for id_, x in Task.IMPORTANCE.items()],
                             coerce=int)
    character = SelectField('Характер', [v.optional()],
                            choices=[(0, '')] + [(x['id'], x['name']) for x in Task.CHARACTERS.values()],
                            coerce=int)
    estimate = DecimalField('Оценка по времени', [v.optional()], places=1)
    git_branch = StringField('Ветка GIT', [v.optional()])
    status = SelectField(
        'Начальный статус',
        [v.optional()],
        choices=[('design.open', 'Надо проектировать'), ('dev.open', 'Можно разрабатывать'), ('qa.open', 'Надо потестить')],
        default=None
    )


class BugForm(FlaskForm):
    subject = StringField('Тема', [v.data_required(message='Дайте хотя бы краткое описание')], filters=[strip_field])
    description = TextAreaField('Подробнее', [v.optional()])


class SprintPropertiesForm(FlaskForm):
    name = StringField('Название', [v.data_required(message='У доски должно быть название')], filters=[strip_field])


class KarmaRecordForm(FlaskForm):
    value = SelectField('Оценка', [v.data_required(message='Поставьте оценку')],
                        choices=[(-2, '-2'), (-1, '-1'), (0, ''), (1, '+1'), (2, '+2')],
                        coerce=int)
    comment = TextAreaField('Обоснование', [v.data_required(message='Обоснуйте.')], filters=[strip_field])


class HistoryFiltersForm(FiltersForm):
    user_id = IntegerField('Участник', default='')
    status = HiddenField('Статусы', default='')
    when = HiddenField('Дата', default='')


class MemberFiltersForm(FiltersForm):
    __remember_fields__ = ['sprint']

    status = HiddenField('Статусы', default='')
    sprint = SelectField('Доска', default='')


class BugsFilterForm(FiltersForm):
    with_closed = BooleanField('Включая закрытые', default=False)
    my_tasks = BooleanField('Только к моим задачам', default=False)
