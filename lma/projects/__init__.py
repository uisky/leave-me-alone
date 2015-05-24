from flask import Blueprint, abort
from flask_user import login_required, current_user

mod = Blueprint('projects', __name__, url_prefix='/projects')


@mod.before_request
def check_login():
    if not current_user.is_authenticated():
        abort(403)

from . import views, views_members, views_tasks
