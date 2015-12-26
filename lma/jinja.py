import markdown
import json
import pytz
from datetime import datetime
from flask import Markup, get_flashed_messages
from . import app
from .projects.models import IMPORTANCE, CHARACTERS, TaskJSONEncoder
from .utils import sanitize_html, plural


_importance_icons = {x['id']: x['icon'] for x in IMPORTANCE}


@app.template_filter('markdown')
def jinja_markdown(x):
    if x is None:
        return ''
    return Markup(sanitize_html(markdown.markdown(x, output_format='html5')))


@app.template_filter('status_class')
def jinja_status_class(x):
    return 'status-%s' % x


@app.template_filter('status_rus')
def jinja_status_rus(x):
    meanings = {
        'open': 'todo', 'progress': 'в работе', 'pause': 'пауза',
        'review': 'проверка', 'done': 'готово', 'canceled': 'отменено'
    }
    return meanings.get(x, x)


@app.template_filter('status_label')
def jinja_status_label(x):
    return Markup('<label class="label %s">%s</label>' % (jinja_status_class(x), jinja_status_rus(x)))


@app.template_filter('importance_icon')
def importance_icon(x):
    return _importance_icons.get(x, '')


@app.template_filter('character_icon')
def character_icon(x):
    return CHARACTERS.get(x, {'icon': ''})['icon']


@app.template_filter('taskjson')
def taskjson(task):
    return json.dumps(task, cls=TaskJSONEncoder, ensure_ascii=False)


@app.template_filter('minus')
def minus(x):
    return str(x).replace('-', '−')


@app.template_filter('nl2br')
def nl2br(t):
    if isinstance(t, str):
        t = str(Markup.escape(t))
        t = t.strip().replace('\r', '').replace('\n', '<br>')
    return Markup(t)


@app.template_filter('my_tasks_count')
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


@app.template_filter('datetime')
def datetime_(x):
    return x.strftime('%d.%m.%Y %H:%M')


@app.template_filter('humantime')
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


@app.template_filter('humandelta')
def humandelta(dt):
    t = []
    if dt.days:
        t.append('%d %s' % (dt.days, plural(dt.days, 'день', 'дня', 'дней')))
    t.append('%d:%02d' % (dt.seconds // 3600, (dt.seconds // 60) % 60))

    return ' '.join(t)


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

@app.template_filter('plural')
def jinja_plural(x, var1, var2, var5):
    return plural(x, var1, var2, var5)
