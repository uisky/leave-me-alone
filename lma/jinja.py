from datetime import datetime
from collections import OrderedDict

import markdown
import pytz
from flask import Markup, get_flashed_messages
from flask_login import current_user

from lma.models import Task, Project, ProjectMember, ProjectFolder
from lma.utils import sanitize_html, plural
from lma.core import db


_importance_icons = {id_: x['icon'] for id_, x in Task.IMPORTANCE.items()}


def jinja_markdown(x):
    if x is None:
        return ''
    return Markup(sanitize_html(markdown.markdown(x, output_format='html5')))


def jinja_status_class(status):
    return 'status-%s' % status


def jinja_status_rus(status):
    meanings = {
        'open': 'todo', 'progress': 'в работе', 'pause': 'пауза',
        'review': 'проверка', 'tested': 'проверено', 'done': 'готово', 'canceled': 'отменено'
    }
    return meanings.get(status, status)


def jinja_status_label(status):
    if status is None:
        return ''
    else:
        return Markup('<label class="label %s">%s</label>' % (jinja_status_class(status), jinja_status_rus(status)))


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


def status_counters(data):
    if not isinstance(data, dict):
        return ''

    x = []
    for status, count in data.items():
        if status is not None:
            x.append('<span class="label %s">%d</span>' % (jinja_status_class(status), count))
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
    app.add_template_filter(jinja_bug_status_label, 'bug_status_label')
    app.add_template_filter(jinja_importance_icon, 'importance_icon')
    app.add_template_filter(character_icon, 'character_icon')
    app.add_template_filter(minus, 'minus')
    app.add_template_filter(nl2br, 'nl2br')
    app.add_template_filter(status_counters, 'status_counters')
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
                    .join(ProjectMember) \
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
                    .filter(db.or_(
                        Task.assigned_id == user.id,
                        db.and_(Task.assigned_id == None, Task.user_id == user.id))
                    )\
                    .filter(Task.status.in_(['open', 'progress', 'pause', 'review']))\
                    .group_by(Task.status)

                for status, count in query.all():
                    stat[status] = count

            return stat

        return {'flashes': make_flashes, 'projects_menu': projects_menu, 'tasks_stat': tasks_stat}
