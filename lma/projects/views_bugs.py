from datetime import date, datetime
import pytz

from flask import render_template, request, g, flash, redirect, url_for
from flask_login import current_user

from lma.models import Task, Bug
from . import mod, forms, load_project
from lma.utils import print_sql, flash_errors
from lma.core import db


@mod.route('/<int:project_id>/bugs/')
def bugs(project_id):
    project, membership = load_project(project_id)

    filters = forms.BugsFilterForm(request.args)

    bugs = Bug.query.join(Task)\
        .filter(Task.project_id == project.id)\
        .order_by(Task.created.desc(), Bug.created.desc())\
        .options(db.joinedload(Bug.task))

    if not filters.with_closed.data:
        bugs = bugs.filter(Bug.status.notin_(('fixed', 'canceled')))

    bugs = bugs.paginate(request.args.get('page', 1, type=int), 50)

    return render_template('projects/bugs.html', project=project, bugs=bugs, filters=filters)


@mod.route('/<int:project_id>/<int:task_id>/bugs/', methods=('GET', 'POST'))
def task_bugs(project_id, task_id):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()

    bugs = Bug.query \
        .filter_by(task_id=task.id)\
        .order_by(Bug.created)\
        .options(db.joinedload(Bug.reporter), db.joinedload(Bug.assignee))\
        .all()

    return render_template('projects/_bugs.html', project=project, membership=membership, task=task, bugs=bugs)


@mod.route('/<int:project_id>/<int:task_id>/bugs/add/', methods=('POST',))
def task_bug_edit(project_id, task_id, bug_id=None):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()

    if bug_id:
        bug = Bug.query.filter_by(task_id=task.id, id=bug_id).first_or_404()
    else:
        bug = Bug(task_id=task.id, reporter_id=current_user.id)

    form = forms.BugForm(obj=bug)

    if form.validate_on_submit():
        form.populate_obj(bug)
        db.session.add(bug)
        db.session.commit()
    else:
        flash_errors(form)

    return redirect(url_for('.tasks', project_id=project.id, task=task.id))


@mod.route('/<int:project_id>/<int:task_id>/bugs/<int:bug_id>/status', methods=('POST',))
def task_bug_status(project_id, task_id, bug_id):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()
    bug = Bug.query.filter_by(task_id=task.id, id=bug_id).first_or_404()

    status = request.form.get('status')

    bug.status = status

    # Если это исполнитель задачи, то ставим его в assignee
    if current_user.id == task.user_id or current_user.id == task.assigned_id or (membership and 'lead' in membership.roles):
        if status == 'open':
            bug.assignee_id = None
        else:
            bug.assignee_id = current_user.id

    db.session.commit()

    return redirect(url_for('.tasks', project_id=project.id, task=task.id))
