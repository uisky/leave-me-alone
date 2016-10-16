from collections import OrderedDict

from flask import Blueprint, abort, g
from flask_login import redirect, request, url_for, current_user

from lma.models import Project, ProjectMember, ProjectFolder, Task
from lma.core import db

mod = Blueprint('projects', __name__, url_prefix='/projects')


def load_project(project_id):
    project = Project.query.get_or_404(project_id)
    membership = ProjectMember.query.filter_by(project_id=project.id, user_id=current_user.id).first()
    if not membership:
        abort(403, 'У вас нет доступа в этот проект.')

    my_tasks = db.session.query(Task.status, db.func.count('*'))\
        .filter(Task.project_id == project.id)\
        .filter(Task.status.in_(('open', 'progress', 'pause', 'review')))\
        .filter(
            db.or_(
                Task.assigned_id == current_user.id,
                db.and_(
                    Task.assigned_id == None, Task.user_id == current_user.id
                )
            )
        ).group_by(Task.status)

    g.my_tasks_count = {}
    for status, count in my_tasks.all():
        g.my_tasks_count[status] = count

    return project, membership


@mod.before_request
def check_login():
    if not current_user.is_authenticated:
        return redirect(url_for('index', next=request.path))


@mod.before_request
def set_globals():
    g.TASK_STATUSES = Task.STATUSES


@mod.before_request
def load_projects():
    if not current_user.is_authenticated:
        return

    query = db.session.query(Project, ProjectMember, ProjectFolder) \
        .join(ProjectMember) \
        .outerjoin(ProjectFolder) \
        .filter(ProjectMember.user_id == current_user.id) \
        .filter(db.or_(ProjectFolder.in_menu, ProjectMember.folder_id == None)) \
        .order_by(ProjectMember.folder_id.desc(), ProjectMember.added.desc())

    g.my_projects = OrderedDict()
    for project, membership, folder in query.all():
        g.my_projects.setdefault(folder, []).append(project)


from . import views, views_members, views_tasks, views_history
