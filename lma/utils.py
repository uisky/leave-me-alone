from flask import flash


def flash_errors(form):
    """
    Перетаскивает ошибки из WTF-формы form в flash(..., 'error')
    :param form: Form
    :return:
    """
    for field, errors in form.errors.items():
        for error in errors:
            flash(error, 'danger')
