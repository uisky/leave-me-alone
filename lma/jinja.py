from datetime import datetime
from collections import OrderedDict

import mistune
import pytz
from flask import Markup, get_flashed_messages
from flask_login import current_user

from lma.models import Task, Project, ProjectMember, ProjectFolder, Bug
from lma.utils import sanitize_html, plural
from lma.core import db


_importance_icons = {id_: x['icon'] for id_, x in Task.IMPORTANCE.items()}


def jinja_markdown(x):
    if x is None:
        return ''
    return Markup((sanitize_html(mistune.html(x))))


def jinja_status_class(status):
    if '.' in status:
        phase, state = status.split('.')
        return 'phase-{} state-{}'.format(phase, state)
    return 'phase-{}'.format(status)


def jinja_status_rus(status):
    meanings = {
        'design.open': 'Надо проектировать',
        'design.progress': 'Проектирование: идет',
        'design.pause': 'Проектирование: пауза',
        'dev.open': 'Надо Кодить',
        'dev.progress': 'Кодить: идёт',
        'dev.pause': 'Кодить: пауза',
        'qa.open': 'QA хочу',
        'qa.progress': 'QA: идёт',
        'qa.pause': 'QA: пауза',
        'qa.done': 'QA: готово',
        'review.open': 'Review хочу',
        'review.progress': 'Review: идёт',
        'review.pause': 'Review: пауза',
        'review.done': 'Review: готово',
        'debug.open': 'Надо допилить',
        'debug.progress': 'Допил: идёт',
        'debug.pause': 'Допил: пауза',
        'release.open': 'Надо релизить',
        'release.progress': 'Релиз: идёт',
        'release.pause': 'Релиз: пауза',
        'complete': 'Готово',
        'canceled': 'Отменено'
    }
    return meanings.get(status, status)


def status_button_text(new_status, task):
    """Возвращает текст для кнопки перевода задачи task в статус new_status"""

    button_texts = {
        'design.open': {
            'design.progress': 'Начать проектирование',
            'dev.open': 'Отдать в разработку',
            'canceled': 'Отменить задачу'
        },
        'design.progress': {
            'design.open': 'Бросить проектирование',
            'design.pause': 'Поставить на паузу',
            'dev.open': 'Отдать в разработку',
            'canceled': 'Отменить задачу'
        },
        'design.pause': {
            'design.open': 'Бросить проектирование',
            'design.progress': 'Продолжить проектирование',
            'dev.open': 'Отдать в разработку',
            'canceled': 'Отменить задачу'
        },

        'dev.open': {
            'design.open': 'Вернуть на допроектирование',
            'dev.progress': 'Начать разработку',
            'complete': 'Всё уже готово',
            'canceled': 'Отменить задачу'
        },
        'dev.progress': {
            'design.open': 'Вернуть на допроектирование',
            'dev.open': 'Бросить разработку',
            'dev.pause': 'Поставить на паузу',
            'qa.open': 'Попросить QA',
            'review.open': 'Попросить ревью',
            'release.open': 'Отдать на релиз',
            'complete': 'Всё готово',
            'canceled': 'Отменить задачу'
        },
        'dev.pause': {
            'design.open': 'Вернуть на допроектирование',
            'dev.open': 'Бросить разработку',
            'dev.progress': 'Продолжить разработку',
            'qa.open': 'Попросить QA',
            'review.open': 'Попросить ревью',
            'release.open': 'Отдать на релиз',
            'complete': 'Всё готово',
            'canceled': 'Отменить задачу'
        },

        'qa.open': {
            'dev.progress': 'Отменить тестирование и вернуть в разработку',
            'qa.progress': 'Начать тестирование',
        },
        'qa.progress': {
            'dev.progress': 'Отменить тестирование и вернуть в разработку',
            'qa.open': 'Отказаться от тестирования',
            'qa.pause': 'Поставить на паузу',
            'qa.done': 'Протестировано, багов нет',
            'debug.open': 'Отправить на допиливание',
            'canceled': 'Отменить задачу',
        },
        'qa.pause': {
            'dev.progress': 'Отменить тестирование и вернуть в разработку',
            'qa.open': 'Отказаться от тестирования',
            'qa.progress': 'Продолжить тестирование',
            'qa.done': 'Протестировано, багов нет',
            'debug.open': 'Отправить на допиливание',
            'canceled': 'Отменить задачу',
        },
        'qa.done': {
            'dev.progress': 'Продолжить разработку',
            'review.open': 'Отправить на ревью',
            'qa.open': 'Протестировать заново',
            'release.open': 'Отправить на релиз',
            'complete': 'Всё готово',
            'canceled': 'Отменить задачу',
        },

        'review.open': {
            'dev.progress': 'Отменить ревью и вернуть в разработку',
            'review.progress': 'Начать ревью',
        },
        'review.progress': {
            'dev.progress': 'Отменить ревью и вернуть в разработку',
            'review.open': 'Отказаться от ревью',
            'review.pause': 'Поставить на паузу',
            'review.done': 'Ревью закончено, допиливать не надо',
            'debug.open': 'Отправить на допиливание',
            'canceled': 'Отменить задачу',
        },
        'review.pause': {
            'dev.progress': 'Отменить ревью и вернуть в разработку',
            'review.open': 'Отказаться от ревью',
            'review.progress': 'Продолжить ревью',
            'review.done': 'Ревью закончено, допиливать не надо',
            'debug.open': 'Отправить на допиливание',
            'canceled': 'Отменить задачу',
        },
        'review.done': {
            'dev.progress': 'Продолжить разработку',
            'qa.open': 'Отправить на тестирование',
            'review.open': 'Переревьюить',
            'release.open': 'Отправить на релиз',
            'complete': 'Всё готово',
            'canceled': 'Отменить задачу',
        },

        'debug.open': {
            'dev.open': 'Веруть в разработку',
            'debug.progress': 'Начать допиливание',
            'qa.open': 'Вернуть на тестирование',
            'review.open': 'Вернуть на ревью',
            'complete': 'Всё готово',
            'canceled': 'Отменить задачу',
        },
        'debug.progress': {
            'debug.open': 'Отказаться от допиливания',
            'debug.pause': 'Поставить на паузу',
            'qa.open': 'Отправить на тестирование',
            'review.open': 'Отправить на ревью',
            'release.open': 'Отправить на релиз',
            'complete': 'Всё готово',
            'canceled': 'Отменить задачу',
        },
        'debug.pause': {
            'debug.open': 'Отказаться от допиливания',
            'debug.progress': 'Продолжить допиливание',
            'qa.open': 'Отправить на тестирование',
            'review.open': 'Отправить на ревью',
            'release.open': 'Отправить на релиз',
            'complete': 'Всё готово',
            'canceled': 'Отменить задачу',
        },

        'release.open': {
            'debug.open': 'Отправить на допиливание',
            'release.progress': 'Начать релиз',
            'complete': 'Всё готово',
            'canceled': 'Отменить задачу',
        },
        'release.progress': {
            'debug.open': 'Отправить на допиливание',
            'release.open': 'Отказаться от релиза',
            'release.pause': 'Поставить на паузу',
            'complete': 'Всё готово',
            'canceled': 'Отменить задачу',
        },
        'release.pause': {
            'debug.open': 'Отправить на допиливание',
            'release.open': 'Отказаться от релиза',
            'release.progress': 'Продолжить релиз',
            'complete': 'Всё готово',
            'canceled': 'Отменить задачу',
        },

        'complete': {
            'design.open': 'Вернуть на перепроектирование',
            'dev.open': 'Вернуть в разработку',
            'qa.open': 'Вернуть на тестирование',
            'review.open': 'Вернуть на ревью',
            'canceled': 'Отменить задачу'
        },
        'canceled': {
            'design.open': 'Вернуть на перепроектирование',
            'dev.open': 'Вернуть в разработку',
            'complete': 'Всё готово'
        },

    }

    text = button_texts.get(task.status, {}).get(new_status, new_status)
    if new_status.endswith('.pause'):
        text = '<i class="fa fa-pause"></i> ' + text

    return Markup(text)


def jinja_bug_status_label(status):
    if status is None:
        return ''

    statuses = {
        'open': 'Открыто',
        'progress': 'Чиним',
        'pause': 'Пауза',
        'test': 'Проверяйте',
        'fixed': 'Починено',
        'canceled': 'Отменено'
    }

    return Markup('<label class="label bug-%s">%s</label>' % (status, statuses.get(status, status)))


def jinja_status_label(status):
    if status is None:
        return ''

    html = {
        'design.open':      '<label class="label-status status-design_open" title="Надо проектировать">Proj</label>',
        'design.progress':  '<label class="label-status status-design_progress" title="Идёт проектирование"><i class="fa fa-play"></i> Proj</label>',
        'design.pause':     '<label class="label-status status-design_pause" title="Проектирование приостановлено"><i class="fa fa-pause"></i> Proj</label>',

        'dev.open':         '<label class="label-status status-dev_open" title="Надо кодить">Dev</label>',
        'dev.progress':     '<label class="label-status status-dev_progress" title="Идёт разработка"><i class="fa fa-play"></i> Dev</label>',
        'dev.pause':        '<label class="label-status status-dev_pause" title="Разработка приостановлена"><i class="fa fa-pause"></i> Dev</label>',

        'qa.open':          '<label class="label-status status-qa_open" title="Надо тестировать">QA</label>',
        'qa.progress':      '<label class="label-status status-qa_progress" title="Идёт тестирование"><i class="fa fa-play"></i> QA</label>',
        'qa.pause':         '<label class="label-status status-qa_pause" title="Тестирование приостановлено"><i class="fa fa-pause"></i> QA</label>',
        'qa.done':          '<label class="label-status status-qa_done" title="Протестировано, ошибок нет"><i class="fa fa-check"></i> QA</label>',

        'review.open':      '<label class="label-status status-review_open" title="Надо ревьюить">Review</label>',
        'review.progress':  '<label class="label-status status-review_progress" title="Идёт ревью"><i class="fa fa-play"></i> Review</label>',
        'review.pause':     '<label class="label-status status-review_pause" title="Ревью приостановлено"><i class="fa fa-pause"></i> Review</label>',
        'review.done':      '<label class="label-status status-review_done" title="Ревью готово, добработок нет"><i class="fa fa-check"></i> Review</label>',

        'debug.open':       '<label class="label-status status-debug_open" title="Надо допилить">Debug</label>',
        'debug.progress':   '<label class="label-status status-debug_progress" title="Идёт допил"><i class="fa fa-play"></i> Debug</label>',
        'debug.pause':      '<label class="label-status status-debug_pause" title="Допил приостановлен"><i class="fa fa-pause"></i> Debug</label>',

        'release.open':       '<label class="label-status status-release_open" title="Надо релизить">Release</label>',
        'release.progress':   '<label class="label-status status-release_progress" title="Идёт релиз"><i class="fa fa-play"></i> Release</label>',
        'release.pause':      '<label class="label-status status-release_pause" title="Релиз приостановлен"><i class="fa fa-pause"></i> Release</label>',

        'complete': '<label class="label-status status-complete" title="Готово: на проде, в релизе">Complete</label>',
        'canceled': '<label class="label-status status-canceled" title="Задача отменена, причина — в комментах">Canceled</label>'
    }

    return Markup(html.get(status, status))


def jinja_importance_icon(x):
    return _importance_icons.get(x, '')


def character_icon(x):
    return Task.CHARACTERS.get(x, {'icon': ''})['icon']


def minus(x):
    return str(x).replace('-', '−')


def nl2br(t):
    if isinstance(t, str):
        t = str(Markup.escape(t))
        t = t.strip().replace('\r', '').replace('\n', '<br>')
    return Markup(t)


def status_counters(data, ignore=()):
    if not isinstance(data, dict):
        return ''

    x = []
    for status, count in data.items():
        if status is not None and status not in ignore:
            x.append('<span class="badge {}" title="{}">{}</span>'.format(jinja_status_class(status), status, count))
    if x:
        return Markup(' ' + ' '.join(x))
    else:
        return ''


def bugs_status_counters(data):
    if not isinstance(data, dict):
        return ''

    x = []
    for status, count in data.items():
        if status is not None:
            x.append('<span class="label bug-%s" title="%s">%d</span>' % (status, status, count))
    if x:
        return Markup(' ' + ' '.join(x))
    else:
        return ''


def datetime_(x):
    return x.strftime('%d.%m.%Y %H:%M')


def humantime(ts, if_none=''):
    months = [
        '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
        'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ]
    if ts is None:
        return if_none
    now = pytz.utc.localize(datetime.now())
    if now.year == ts.year:
        if now.month == ts.month:
            if now.day == ts.day:
                return ts.strftime('сегодня в %H:%M')
            elif (now - ts).days <= 1:
                return ts.strftime('вчера в %H:%M')
        return ('%d ' % ts.day) + months[ts.month] + ts.strftime(' %H:%M')
    return ts.strftime('%d.%m.%Y %H:%M')


def humandelta(dt):
    t = []
    if dt.days:
        t.append('%d %s' % (dt.days, plural(dt.days, 'день', 'дня', 'дней')))
    t.append('%d:%02d' % (dt.seconds // 3600, (dt.seconds // 60) % 60))

    return ' '.join(t)


def jinja_plural(x, var1, var2, var5):
    return plural(x, var1, var2, var5)


def init_jinja_filters(app):
    app.add_template_filter(jinja_markdown, 'markdown')
    app.add_template_filter(jinja_status_class, 'status_class')
    app.add_template_filter(jinja_status_rus, 'status_rus')
    app.add_template_filter(jinja_status_label, 'status_label')
    app.add_template_filter(status_button_text, 'status_button_text')
    app.add_template_filter(jinja_bug_status_label, 'bug_status_label')
    app.add_template_filter(jinja_importance_icon, 'importance_icon')
    app.add_template_filter(character_icon, 'character_icon')
    app.add_template_filter(minus, 'minus')
    app.add_template_filter(nl2br, 'nl2br')
    app.add_template_filter(status_counters, 'status_counters')
    app.add_template_filter(bugs_status_counters, 'bugs_status_counters')
    app.add_template_filter(datetime_, 'datetime')
    app.add_template_filter(humantime, 'humantime')
    app.add_template_filter(humandelta, 'humandelta')
    app.add_template_filter(plural, 'plural')

    @app.context_processor
    def context_processors():
        def make_flashes():
            """
            Возвращает flash-сообщения в виде [('error', [msg1, msg2, msg3]), ('success', [msg1, msg2]), ...]
            :return:
            """
            result = {}
            for cat, msg in get_flashed_messages(with_categories=True):
                result.setdefault(cat, []).append(msg)
            return result

        def projects_menu(user):
            """
            Возвращает папки, которые нужно показывать в меню и проекты в них для user:
            {
                folder: [project, project, ...],
                folder: [project, project, ...]
                ...
            }
            :return: OrderedDict
            """
            menu = OrderedDict()

            if user.is_authenticated:
                query = db.session.query(Project, ProjectMember, ProjectFolder) \
                    .join(ProjectMember, ProjectMember.project_id == Project.id) \
                    .outerjoin(ProjectFolder) \
                    .filter(ProjectMember.user_id == user.id) \
                    .filter(db.or_(ProjectFolder.in_menu, ProjectMember.folder_id == None)) \
                    .order_by(ProjectMember.folder_id.desc(), ProjectMember.added.desc())

                for project, membership, folder in query.all():
                    menu.setdefault(folder, []).append(project)

            return menu

        def tasks_stat(project, user):
            """
            Возвращает количество задач юзера (назначены ему или никому не назначены, но созданы им) по статусам
            словарём {status: count, ...}
            :param project: Project
            :param user: User
            :return: dict
            """
            stat = {}

            if user.is_authenticated:
                query = db.session.query(Task.status, db.func.count('*'))\
                    .filter_by(project_id=project.id)\
                    .filter(Task.assigned_id == user.id)\
                    .group_by(Task.status) \
                    .order_by(Task.status)

                for status, count in query.all():
                    stat[status] = count

            return stat

        def bugs_stat(project):
            """
            Возвращает количество багов по статусу словарём {status: count}
            :param project: Project
            :return: dict
            """
            stat = {}

            query = db.session.query(Bug.status, db.func.count('*')) \
                .join(Task)\
                .filter(Task.project_id == project.id) \
                .filter(~Bug.status.in_(['fixed', 'canceled']))\
                .group_by(Bug.status)

            for status, count in query.all():
                    stat[status] = count

            return stat

        return {'flashes': make_flashes,
                'projects_menu': projects_menu,
                'tasks_stat': tasks_stat,
                'bugs_stat': bugs_stat}
