from . import app
import markdown


@app.template_filter('markdown')
def jinja_markdown(x):
    return markdown.markdown(x, output_format='html5')


@app.template_filter('status_class')
def jinja_status_class(x):
    classes = {
        'open': 'info', 'progress': 'success', 'pause': 'warning',
        'review': 'primary', 'done': 'default', 'canceled': 'default'
    }
    return classes.get(x, 'default')


@app.template_filter('status_rus')
def jinja_status_rus(x):
    meanings = {
        'open': 'todo', 'progress': 'в работе', 'pause': 'пауза',
        'review': 'проверка', 'done': 'готово', 'canceled': 'отменено'
    }
    return meanings.get(x, x)


@app.template_filter('status_label')
def jinga_status_label(x):
    return '<label class="label label-%s">%s</label>' % (jinja_status_class(x), jinja_status_rus(x))
