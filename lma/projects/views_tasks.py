from flask import render_template, request, redirect, flash, url_for, g, abort
from datetime import datetime
import pytz

from . import mod, forms, load_project
from .models import *
from .mail import *
from .. import db
from ..utils import flash_errors


@mod.route('/<int:project_id>/', methods=('GET', 'POST'))
def tasks(project_id):
    project, membership = load_project(project_id)

    options = forms.OutputOptions(request.args)
    options.sprint.choices = [(x.id, x.name) for x in Sprint.query.filter_by(project_id=project.id).order_by(Sprint.start).all()]

    tasks = OrderedDict()

    # Заполняем tasks и заодно считаем стату по статусам детей каждой задачи
    for task in project.get_tasks_query(options).all():
        task.children_statuses = {}
        tasks[task.id] = task

        status = task.status
        if status:
            while task.parent_id:
                if task.parent_id not in tasks:
                    print('\033[31mСтранно, у задачи %d не найден родитель (%d)' % (task.id, task.parent_id))
                    continue

                parent = tasks[task.parent_id]

                parent.children_statuses.setdefault(status, 0)
                parent.children_statuses[status] += 1

                task = parent

    # Считаем статистику по всему проекту
    stats = {}
    max_deadline = None
    for id_, task in tasks.items():
        if task.children_statuses:
            cs = task.children_statuses
            cs['complete'] = int((cs.get('done', 0) + cs.get('canceled', 0)) / sum(cs.values()) * 100)

        if task.status is not None:
            stats.setdefault(task.status, 0)
            stats[task.status] += 1
            if task.deadline is not None:
                if max_deadline is None:
                    max_deadline = task.deadline
                else:
                    max_deadline = max(task.deadline, max_deadline)
    stats['total'] = sum(stats.values())
    stats['max_deadline'] = max_deadline

    # Выбранная задача
    if request.args.get('task'):
        selected = Task.query.filter_by(id=request.args.get('task'), project_id=project.id).first()
        if not selected:
            abort(404, 'Выбранная задача не обнаружена. Может, удалили? <a href="?">Весь проект</a>.')
        form_edit = forms.TaskForm(obj=selected)
    else:
        selected = None
        form_edit = None

    empty = Task(project_id=project.id, user_id=current_user.id, status='open', importance=0)
    if selected:
        empty.assigned_id = selected.assigned_id
    form_empty = forms.TaskForm(obj=empty)

    g.now = datetime.now(tz=pytz.timezone('Europe/Moscow'))

    return render_template('projects/tasks.html',
                           project=project, membership=membership, options=options,
                           tasks=list(tasks.values()), stats=stats,
                           selected=selected, empty=empty, form_empty=form_empty, form_edit=form_edit)


@mod.route('/<int:project_id>/<int:task_id>/edit', methods=('POST',))
def task_edit(project_id, task_id):
    project, _ = load_project(project_id)
    task = Task.query.get_or_404(task_id)
    form = forms.TaskForm(obj=task)

    if form.validate_on_submit():
        # Пишем в историю, если что-то изменилось
        hist = TaskHistory(task_id=task.id, user_id=current_user.id)
        is_modified = False
        for field in ('assigned_id', 'subject', 'description', 'deadline', 'importance', 'character'):
            if getattr(form, field).data != getattr(task, field):
                setattr(hist, field, getattr(form, field).data)
                is_modified = True

        form.populate_obj(task)
        if task.character == 0:
            task.character = None

        if is_modified:
            db.session.add(hist)

            if hist.assigned_id:
                mail_assigned(project, task)
            else:
                mail_changed(project, task, hist)

        db.session.commit()
    else:
        flash_errors(form)

    return redirect(url_for('.tasks', project_id=task.project_id) + ('?task=%d' % task.id))


@mod.route('/<int:project_id>/<int:task_id>/delete', methods=('POST',))
def task_delete(project_id, task_id):
    project, _ = load_project(project_id)
    task = Task.query.get_or_404(task_id)

    redirect_url = url_for('.tasks', project_id=task.project_id)
    if task.parent_id:
        redirect_url += '?task=%d' % task.parent_id

    task.subtree(withme=True).delete(synchronize_session=False)

    # Остались ли у родителя детки?
    kids = db.session.execute('SELECT 1 FROM tasks WHERE parent_id = :id LIMIT 1', {'id': task.parent_id}).scalar()
    if kids is None:
        task.parent.status = task.status

    db.session.commit()

    return redirect(redirect_url)


@mod.route('/<int:project_id>/<parent_id>/subtask', methods=('POST',))
@mod.route('/<int:project_id>/subtask', methods=('POST',))
def task_subtask(project_id, parent_id=None):
    project, _ = load_project(project_id)
    if parent_id:
        parent = Task.query.get_or_404(parent_id)
    else:
        parent = None
    task = Task(project_id=project.id, user_id=current_user.id, status='open')

    form = forms.TaskForm(obj=task)

    redirect_url = url_for('.tasks', project_id=task.project_id)
    if parent:
        redirect_url += '?task=%d' % parent.id

    if form.validate_on_submit():
        form.populate_obj(task)
        task.setparent(parent)

        # Удаляем статус у родительской задачи
        if parent:
            parent.status = None

        db.session.add(task)
        db.session.commit()

        # Оповещаем assignee
        mail_assigned(project, task)

        return redirect(redirect_url)

    flash_errors(form)
    return redirect(redirect_url)


@mod.route('/<int:project_id>/<int:task_id>/status', methods=('POST',))
def task_status(project_id, task_id):
    def check():
        if status not in task.allowed_statuses(current_user, membership):
            flash('Вы не можете установить этой задаче такой статус.', 'danger')
            return False

        return True

    project, membership = load_project(project_id)
    task = Task.query.get_or_404(task_id)
    status = request.form.get('status')

    if check():
        task.status = status
        # Пишем в историю
        hist = TaskHistory(task_id=task.id, user_id=current_user.id, status=status)
        db.session.add(hist)
        db.session.commit()
        mail_changed(project, task, hist)

    return redirect(url_for('.tasks', project_id=project.id) + '?task=%d' % task.id)


@mod.route('/<int:project_id>/<int:task_id>/chparent', methods=('POST',))
def task_chparent(project_id, task_id):
    def check_parent():
        if task.id == parent.id:
            flash('Вы промахнулись.', 'danger')
            return False
        elif parent in subtree:
            flash('Задача не станет собственной подзадачей.', 'danger')
            return False
        return True

    project, membership = load_project(project_id)
    task = Task.query.get_or_404(task_id)
    subtree = task.subtree(withme=True).order_by(Task.mp).all()
    if task.parent_id:
        old_parent = Task.query.get(task.parent_id)
    else:
        old_parent = None

    if request.form.get('parent_id', 0, int):
        parent = Task.query.get_or_404(request.form.get('parent_id'))
        if not check_parent():
            return redirect(url_for('.tasks', project_id=project.id) + '?task=%d' % task.id)

        # Удаляем статус у нового родителя
        parent.status = None
    else:
        parent = None

    # Создаём префикс mp для поддерева
    if parent:
        prefix = parent.mp[:]
        max_mp = db.session.execute(
            "SELECT coalesce(max(mp[%d]), 0) FROM tasks WHERE project_id = :project_id and parent_id = :parent_id" %
            (len(parent.mp) + 1),
            {'project_id': project.id, 'parent_id': parent.id}
        ).scalar() + 1
        prefix += [max_mp]
        task.parent_id = parent.id
    else:
        prefix = [db.session.execute(
            "SELECT coalesce(max(mp[1]), 0) FROM tasks WHERE project_id = :project_id and parent_id is null",
            {'project_id': project.id}
        ).scalar() + 1]
        task.parent_id = None

    # Остались ли у детки у старого родителя?
    if old_parent:
        kids = db.session.execute('SELECT count(*) FROM tasks WHERE parent_id = :id', {'id': old_parent.id}).scalar()
        if kids:
            old_parent.status = task.status

    # Меняем mp у всего поддерева исходной задачи
    cut = len(task.mp)
    for t in subtree:
        t.mp = prefix + t.mp[cut:]

    db.session.commit()
    return redirect(url_for('.tasks', project_id=project.id) + '?task=%d' % task.id)


@mod.route('/<int:project_id>/<int:task_id>/swap', methods=('POST',))
def task_swap(project_id, task_id):
    project, membership = load_project(project_id)
    sisters = (
        Task.query.get_or_404(task_id),
        Task.query.get_or_404(request.form.get('sister_id', 0, type=int))
    )

    def check():
        if sisters[0].parent_id != sisters[1].parent_id:
            flash('Задачи должны быть подзадачами одной задачи.', 'danger')
            return False
        return True

    if not check():
        return redirect(url_for('.tasks', project_id=project.id) + '?task=%d' % sisters[0].id)

    mps = (sisters[0].mp[:], sisters[1].mp[:])
    trees = [x.subtree(withme=True).all() for x in sisters]

    for t in trees[0]:
        t.mp = mps[1] + t.mp[len(mps[1]):]

    for t in trees[1]:
        t.mp = mps[0] + t.mp[len(mps[0]):]

    db.session.commit()
    return redirect(url_for('.tasks', project_id=project.id) + '?task=%d' % sisters[0].id)


@mod.route('/<int:project_id>/reorder', methods=('POST',))
def reorder_tasks(project_id):
    project, membership = load_project(project_id)
    if project.type != 'list':
        abort('400')

    ids = request.form.get('order').split(',')
    for o, id_ in enumerate(ids):
        db.session.execute(
            'UPDATE tasks SET mp[1] = :order WHERE id = :id AND project_id = :project_id',
            {'id': int(id_), 'project_id': project.id, 'order': o + 1}
        )
    db.session.commit()

    return 'ok'