from datetime import datetime
import pytz

from flask import render_template, request, redirect, flash, url_for, g, abort
from . import mod, forms, load_project
from .models import *


@mod.route('/<int:project_id>/history/', methods=('GET', 'POST'))
def history(project_id):
    project, membership = load_project(project_id)

    history = TaskHistory.query.join(Task)\
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


@mod.route('/<int:project_id>/gantt/')
def gantt(project_id):
    project, membership = load_project(project_id)

    tasks = []
    history = {}

    options = forms.OutputOptions(request.args)
    for task, seen_ in project.get_tasks_query(options):
        tasks.append(task)
        history[task.id] = [(
            int((task.created - project.created).total_seconds() / 18000),
            'open'
        )]

    history_q = TaskHistory.query.join(Task)\
        .filter(Task.project_id == project.id)\
        .filter(TaskHistory.status != None)\
        .order_by(TaskHistory.created)
    for h in history_q.all():
        history.setdefault(h.task_id, []).append((
            int((h.created - project.created).total_seconds() / 18000),
            h.status
        ))

    g.now = datetime.now(tz=pytz.timezone('Europe/Moscow'))
    g.IMPORTANCE = IMPORTANCE
    g.CHARACTERS = CHARACTERS

    return render_template('projects/gantt.html', project=project, tasks=tasks, history=history)
