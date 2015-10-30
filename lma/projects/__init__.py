from flask import Blueprint, abort, g
from flask_login import login_required, current_user
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
        abort(403)


@mod.before_request
def set_globals():
    g.TASK_STATUSES = TASK_STATUSES


@mod.before_request
def load_projects():
    if not current_user.is_authenticated:
        return

    projects = db.session.query(Project).join(ProjectMember) \
        .filter(ProjectMember.user_id == current_user.id) \
        .order_by(Project.created.desc()) \
        .all()
    g.my_projects = projects


from . import views, views_members, views_tasks, views_history
