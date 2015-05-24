from flask import render_template, request, redirect, flash, url_for, g, abort
from . import mod, forms, load_project
from .models import *


@mod.route('/<int:project_id>/history/', methods=('GET', 'POST'))
def history(project_id):
    project, membership = load_project(project_id)

    history = TaskHistory.query.options(db.joinedload('task'))\
        .filter(Task.project_id == project.id)\
        .filter(TaskHistory.status != None)\
        .order_by(TaskHistory.created)

    if request.args.get('user_id'):
        history = history.filter_by(user_id=request.args.get('user_id', 0, type=int))

    if request.args.get('status'):
        statuses = request.args.get('status').split(',')
        history = history.filter(TaskHistory.status.in_(statuses))

    history = history.all()

    return render_template('projects/history.html', project=project, history=history, statuses=TASK_STATUSES)
