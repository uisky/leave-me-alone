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
