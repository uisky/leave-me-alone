import bleach

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


ALLOWED_TAGS = [
    'strong', 'em', 'del', 'b', 'i', 'u', 's', 'span', 'a',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'p', 'code', 'blockquote', 'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'img'
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
