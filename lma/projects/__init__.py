from datetime import datetime
import pytz

from flask import Blueprint, abort, g, redirect, request, url_for
from flask_login import current_user

from lma.models import Project, ProjectMember, ProjectFolder, Task, ProjectNotMember
from lma.core import db

mod = Blueprint('projects', __name__, url_prefix='/projects')


def load_project(project_id):
    """
    Загружает инстансы Project и ProjectMember для текущего юзера.
    Проверяет права доступа в проект.
    Для анонима или не-члена команды, которым всё-таки можно в проект, membership будет None.
    :param project_id:
    :return:
    """
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        user_id = None
    result = db.session.query(Project, ProjectMember)\
        .outerjoin(ProjectMember, db.and_(ProjectMember.project_id == Project.id, ProjectMember.user_id == user_id))\
        .filter(Project.id == project_id)\
        .first()

    if not result:
        abort(404, 'Проект не найден.')

    project, membership = result
    if membership is None:
        if project.ac_read != 'any':
            abort(403, 'У вас нет доступа в этот проект.')

        membership = ProjectNotMember(project, current_user)

    return project, membership


@mod.before_request
def set_globals():
    g.Task = Task
    g.now = datetime.now(tz=pytz.timezone('Europe/Moscow'))


from . import views, views_project, views_members, views_tasks, views_history, views_comments

