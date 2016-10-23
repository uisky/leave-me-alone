from datetime import date, datetime
import pytz

from flask import render_template, request, g, flash

from lma.models import Task, TaskHistory
from . import mod, forms, load_project
from lma.utils import print_sql
from lma.core import db


@mod.route('/<int:project_id>/history/', methods=('GET', 'POST'))
def history(project_id):
    project, membership = load_project(project_id)
    _dcreated = db.func.cast(TaskHistory.created, db.Date)

    filters = forms.HistoryFiltersForm(request.args)

    history = TaskHistory.query\
        .outerjoin(TaskHistory.task)\
        .filter(Task.project_id == project.id, TaskHistory.status != None)\
        .order_by(TaskHistory.created)\
        .options(db.contains_eager(TaskHistory.task))\
        .options(db.joinedload(TaskHistory.user))

    if filters.user_id.data:
        history = history.filter(TaskHistory.user_id == request.args.get('user_id', 0, type=int))

    if filters.status.data:
        statuses = request.args.get('status').split(',')
        history = history.filter(TaskHistory.status.in_(statuses))

    # Считаем статистику: количество
    q_stat = history.with_entities(_dcreated, db.func.count('*')).group_by(_dcreated).order_by(None)
    stat, project_start = {}, date.today()
    for day, cnt in q_stat:
        project_start = min(project_start, day)
        stat[day.strftime('%d.%m.%Y')] = cnt

    try:
        when = datetime.strptime(filters.when.data, '%Y-%m-%d').date()
    except ValueError:
        when = date.today()
        filters.when.data = when.strftime('%Y-%m-%d')
    history = history.filter(_dcreated == when)

    history = history.paginate(request.args.get('page', 1, type=int), 50)
    return render_template('projects/history.html',
                           project=project, history=history,
                           stat=stat, project_start=project_start,
                           filters=filters, statuses=Task.STATUSES)


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
