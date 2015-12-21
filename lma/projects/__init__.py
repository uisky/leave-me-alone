from collections import OrderedDict

from flask import Blueprint, abort, g
from flask_login import login_required, current_user, redirect, request, url_for
from .models import *

mod = Blueprint('projects', __name__, url_prefix='/projects')


def load_project(project_id):
    project = Project.query.get_or_404(project_id)
    membership = ProjectMember.query.filter_by(project_id=project.id, user_id=current_user.id).first()
    if not membership:
        abort(403)

    g.my_tasks_count = {}
    r = db.session.execute(
        """
        SELECT status, count(*) FROM tasks
        WHERE
            project_id = :project_id AND
            (assigned_id = :me OR assigned_id is null and user_id = :me) AND
            status in ('open', 'progress', 'pause', 'review')
        GROUP BY status
        """,
        {'project_id': project.id, 'me': current_user.id}
    )
    for status, count in r:
        g.my_tasks_count[status] = count

    return project, membership


@mod.before_request
def check_login():
    if not current_user.is_authenticated:
        return redirect(url_for('index', next=request.path))


@mod.before_request
def set_globals():
    g.TASK_STATUSES = TASK_STATUSES


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
