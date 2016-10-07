import bleach
import sqlparse
from flask import flash


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
            flash(error, 'danger')


def plural(x, var1, var2, var5):
    """
    Спряжение существительных после числительного. Например:
    У вас в штанах {{ x }} {{ x|plural('енотик', 'енотика', 'енотиков') }}
    :param x: количество
    :param var1: 1, 21, 31, ...
    :param var2: 2-4, 22-24, 33-34, ...
    :param var5: 0, 5-9, 10-20, 25-30, 35-40, ...
    :return:
    """
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
