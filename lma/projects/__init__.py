from datetime import datetime
import pytz

from flask import Blueprint, abort, g
from flask_login import redirect, request, url_for, current_user

from lma.models import Project, ProjectMember, ProjectFolder, Task
from lma.core import db

mod = Blueprint('projects', __name__, url_prefix='/projects')


def load_project(project_id):
    """
    Загружает инстанс Project и ProjectMember для текущего юзера и считает статистику по статусам задач
    в этом проекте.
    :param project_id:
    :return:
    """
    result = db.session.query(Project, ProjectMember)\
        .join(ProjectMember)\
        .filter(Project.id == project_id, ProjectMember.user_id == current_user.id)\
        .first()

    if not result:
        abort(403, 'У вас нет доступа в этот проект.')
        return
    else:
        project, membership = result

    return project, membership


@mod.before_request
def check_login():
    if not current_user.is_authenticated:
        return redirect(url_for('index', next=request.path))


@mod.before_request
def set_globals():
    g.Task = Task
    g.now = datetime.now(tz=pytz.timezone('Europe/Moscow'))


from . import views, views_project, views_members, views_tasks, views_history, views_comments

