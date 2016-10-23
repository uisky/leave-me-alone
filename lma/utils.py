import bleach
import sqlparse
from wtforms import Form, StringField, IntegerField, SelectMultipleField, SelectField, BooleanField
from wtforms.widgets import FileInput, ListWidget, CheckboxInput
from flask import flash, render_template, abort, g, request
from flask import current_app as app


def form_json_errors(form):
    return '\n'.join(['\n'.join(errors) for errors in form.errors.values()])


def flash_errors(form):
    """
    Перетаскивает ошибки из WTF-формы form в flash(..., 'error')
    :param form: Form
    :return:
    """
    for field, errors in form.errors.items():
        for error in errors:
            if app.config['DEBUG']:
                error = '{}: {}'.format(field, error)
            flash(error, 'danger')


def plural(x, var1, var2, var5=None):
    """
    Спряжение существительных после числительного. Например:
    У вас в штанах {{ x }} {{ x|plural('енотик', 'енотика', 'енотиков') }}
    :param x: количество
    :param var1: 1, 21, 31, ...
    :param var2: 2-4, 22-24, 33-34, ...
    :param var5: 0, 5-9, 10-20, 25-30, 35-40, ...
    :return:
    """
    var5 = var5 or var2
    x = abs(x)
    if x == 0:
        return var5
    if x % 10 == 1 and x % 100 != 11:
        return var1
    elif 2 <= (x % 10) <= 4 and (x % 100 < 10 or x % 100 >= 20):
        return var2
    else:
        return var5


ALLOWED_TAGS = [
    'strong', 'em', 'del', 'b', 'i', 'u', 's', 'span', 'a',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'p', 'code', 'blockquote', 'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'img', 'pre'
]

ALLOWED_ATTRIBUTES = {
    '*': ['style'],
    'img': ['src', 'width', 'height', 'alt'],
    'a': ['href', 'target', 'rel'],
    'table': ['class']
}

STYLES_WHITELIST = [
    'color', 'background', 'font-size', 'font-style', 'font-weight',
    'padding', 'padding-top', 'padding-bottom', 'padding-left', 'padding-right',
    'margin', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
    'border', 'box-shadow'
]


def sanitize_html(html):
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, styles=STYLES_WHITELIST)


def print_sql(query):
    print(sqlparse.format(str(query), reindent=True, keyword_case='upper'))


class FiltersForm(Form):
    """
    Для всех полей обязательно нужно указывать default!
    """
    __remember_fields__ = []

    def _cookie_name(self, field):
        return '_filters.' + self.__class__.__name__ + '.' + field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.__remember_fields__:
            if field not in request.args and self._cookie_name(field) in request.cookies:
                getattr(self, field).data = request.cookies[self._cookie_name(field)]

        for field in self.__remember_fields__:
            defer_cookie(self._cookie_name(field), getattr(self, field).data, max_age=60*60*24*7, path='/')

    @property
    def is_dirty(self):
        # У SelectField'ов без инициализации data == 'None'. Ёбаные вы wtforms!
        for field in self:
            if field.data != field.default:
                return True
        return False

    @property
    def as_dict(self):
        return {field.name: field.data or None for field in self if field.name != 'csrf_token'}

    @property
    def default_values(self):
        return {
            field.name: None if isinstance(field, BooleanField) else field.default
            for field in self if field.name != 'csrf_token'
        }


def defer_cookie(*args, **kwargs):
    """
    Запоминает, что перед тем, как отдать Response, нужно установить куку. Параметры те же, что и у Response.set_cookie()
    :param args:
    :param kwargs:
    :return:
    """
    if 'deferred_cookies' not in g:
        g.deferred_cookies = []

    g.deferred_cookies.append((args, kwargs))
