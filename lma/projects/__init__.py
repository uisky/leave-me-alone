from flask import Blueprint, abort
from flask_login import login_required, current_user
from .models import *

mod = Blueprint('projects', __name__, url_prefix='/projects')


def load_project(project_id):
    project = Project.query.get_or_404(project_id)
    membership = ProjectMember.query.filter_by(project_id=project.id, user_id=current_user.id).first()
    if not membership:
        abort(403)
    return project, membership


@mod.before_request
def check_login():
    if not current_user.is_authenticated():
        abort(403)

from . import views, views_members, views_tasks, views_history
