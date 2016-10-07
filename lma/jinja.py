from datetime import datetime

import markdown
import pytz
from flask import Markup, get_flashed_messages

from lma.models import Task
from lma.utils import sanitize_html, plural


_importance_icons = {x['id']: x['icon'] for x in Task.IMPORTANCE}


def jinja_markdown(x):
    if x is None:
        return ''
    return Markup(sanitize_html(markdown.markdown(x, output_format='html5')))


def jinja_status_class(x):
    return 'status-%s' % x


def jinja_status_rus(x):
    meanings = {
        'open': 'todo', 'progress': 'в работе', 'pause': 'пауза',
        'review': 'проверка', 'done': 'готово', 'canceled': 'отменено'
    }
    return meanings.get(x, x)


def jinja_status_label(x):
    return Markup('<label class="label %s">%s</label>' % (jinja_status_class(x), jinja_status_rus(x)))


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


def my_tasks_count(data):
    if not isinstance(data, dict):
        return ''

    x = []
    for status, count in data.items():
        if status in ('open', 'progress', 'pause', 'review'):
            x.append('<span class="label %s">%d</span>' % (jinja_status_class(status), count))
    if x:
        return Markup(' ' + ' '.join(x))
    else:
        return ''


def datetime_(x):
    return x.strftime('%d.%m.%Y %H:%M')


def humantime(ts):
    months = [
        '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
        'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ]
    now = pytz.utc.localize(datetime.now())
    if now.year == ts.year:
        if now.month == ts.month:
            if now.day == ts.day:
                return ts.strftime('сегодня в %H:%M')
            elif (now - ts).days == 1:
                return ts.strftime('вчера в %H:%M')
        return ('%d ' % ts.day) + months[ts.month] + ts.strftime(' %H:%M')
    return ts.strftime('%d %b %Y %H:%M')


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
    app.add_template_filter(jinja_importance_icon, 'importance_icon')
    app.add_template_filter(character_icon, 'character_icon')
    app.add_template_filter(minus, 'minus')
    app.add_template_filter(nl2br, 'nl2br')
    app.add_template_filter(my_tasks_count, 'my_tasks_count')
    app.add_template_filter(datetime_, 'datetime')
    app.add_template_filter(humantime, 'humantime')
    app.add_template_filter(humandelta, 'humandelta')
    app.add_template_filter(plural, 'plural')

    @app.context_processor
    def flashes():
        """
        Возвращает flash-сообщения в виде [('error', [msg1, msg2, msg3]), ('success', [msg1, msg2]), ...]
        :return:
        """
        def make_flashes():
            result = {}
            for cat, msg in get_flashed_messages(with_categories=True):
                result.setdefault(cat, []).append(msg)
            return result

        return {'flashes': make_flashes}
