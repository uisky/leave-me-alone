import markdown
import json
from flask import Markup
from . import app
from .projects.models import IMPORTANCE, CHARACTERS, TaskJSONEncoder
from .utils import sanitize_html


_importance_icons = {x['id']: x['icon'] for x in IMPORTANCE}
_character_icons = {x['id']: x['icon'] for x in CHARACTERS}


@app.template_filter('markdown')
def jinja_markdown(x):
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
def jinga_status_label(x):
    return Markup('<label class="label %s">%s</label>' % (jinja_status_class(x), jinja_status_rus(x)))


@app.template_filter('importance_icon')
def importance_icon(x):
    return _importance_icons.get(x, '')


@app.template_filter('character_icon')
def character_icon(x):
    return _character_icons.get(x, '')


@app.template_filter('taskjson')
def taskjson(task):
    return json.dumps(task, cls=TaskJSONEncoder, ensure_ascii=False)


@app.template_filter('minus')
def minus(x):
    return str(x).replace('-', '−')


@app.template_filter('nl2br')
def nl2br(x):
    return Markup(x.replace('\n', '<br>'))


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


@app.template_filter('humantime')
def humantime(d):
    return d.strftime('%d.%m.%Y %H:%M')