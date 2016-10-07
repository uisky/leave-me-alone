from flask import render_template, request, g

from lma.models import *
from . import mod, forms, load_project


@mod.route('/<int:project_id>/history/', methods=('GET', 'POST'))
def history(project_id):
    project, membership = load_project(project_id)

    history = TaskHistory.query\
        .join(TaskHistory.task)\
        .filter(TaskHistory.status != None)\
        .order_by(TaskHistory.created)\
        .options(db.contains_eager(TaskHistory.task))\
        .options(db.joinedload(TaskHistory.user))\
        .filter(Task.project_id == project.id)

    if request.args.get('user_id'):
        history = history.filter(TaskHistory.user_id == request.args.get('user_id', 0, type=int))

    if request.args.get('status'):
        statuses = request.args.get('status').split(',')
        history = history.filter(TaskHistory.status.in_(statuses))

    if request.args.get('start'):
        history = history.filter(TaskHistory.created >= request.args.get('start') + ' 00:00:00')

    if request.args.get('end'):
        history = history.filter(TaskHistory.created <= request.args.get('end') + ' 23:59:59')

    history = history.paginate(request.args.get('page', 1, type=int), 50)
    return render_template('projects/history.html', project=project, history=history, statuses=Task.STATUSES)


@mod.route('/<int:project_id>/gantt/')
def gantt(project_id):
    project, membership = load_project(project_id)

    tasks = []
    history = {}

    SCALE = 6000

    options = forms.OutputOptions(request.args)
    for task, seen_ in project.get_tasks_query(options):
        tasks.append(task)
        history[task.id] = [[
            'open',
            int((task.created - project.created).total_seconds() / SCALE),
            0
        ]]

    history_q = TaskHistory.query.join(Task)\
        .filter(Task.project_id == project.id)\
        .filter(TaskHistory.status != None)\
        .order_by(TaskHistory.task_id, TaskHistory.created)
    max_time = 0
    for h in history_q.all():
        pos = int((h.created - project.created).total_seconds() / SCALE)
        history.setdefault(h.task_id, [])
        if len(history[h.task_id]):
            history[h.task_id][-1][2] = pos - history[h.task_id][-1][1]
        history[h.task_id].append([h.status, pos, 0])
        if pos > max_time:
            max_time = pos

    g.now = datetime.now(tz=pytz.timezone('Europe/Moscow'))
    g.IMPORTANCE = Task.IMPORTANCE

    return render_template('projects/gantt.html', project=project, tasks=tasks, history=history, max_time=max_time)
