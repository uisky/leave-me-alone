from flask import render_template, request, redirect, flash, url_for, g, abort
from flask_user import current_user
from datetime import datetime
import pytz

from . import mod, forms, load_project
from .models import *
from .. import app, db
from ..utils import flash_errors
from ..users.models import User


@mod.route('/<int:project_id>/', methods=('GET', 'POST'))
def tasks(project_id):
    project, membership = load_project(project_id)
    tasks = Task.query.filter_by(project_id=project.id).order_by(Task.mp).all()

    form_empty = forms.TaskForm()
    empty = Task(project_id=project.id, user_id=current_user.id, status='open')

    if request.args.get('task'):
        selected = Task.query.get_or_404(request.args.get('task'))
        form_edit = forms.TaskForm(obj=selected)
    else:
        selected = None
        form_edit = None

    g.now = datetime.now(tz=pytz.timezone('Europe/Moscow'))

    return render_template('projects/tasks.html',
                           project=project, membership=membership, tasks=tasks,
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
        for field in ('assigned_id', 'subject', 'description', 'deadline'):
            if getattr(form, field).data != getattr(task, field):
                setattr(hist, field, getattr(form, field).data)
                is_modified = True

        form.populate_obj(task)
        if is_modified:
            db.session.add(hist)
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

        # Открываем родительскую задачу
        if parent and parent.status in('done', 'review'):
            parent.status = 'open'
            db.session.add(TaskHistory(task_id=task.id, user_id=current_user.id, status='open'))

        db.session.add(task)
        db.session.commit()
        return redirect(redirect_url)

    flash_errors(form)
    return redirect(redirect_url)


@mod.route('/<int:project_id>/<int:task_id>/status', methods=('POST',))
def task_status(project_id, task_id):
    def check():
        if status not in task.allowed_statuses(current_user, membership):
            flash('Вы не можете установить этой задаче такой статус.', 'danger')
            return False

        # Проверяем, нет ли детей в статусе 'open', 'progress'
        if status in ('done', 'review'):
            kids = task.subtree().filter(Task.status.in_(['open', 'progress', 'review'])).first()
            if kids is not None:
                flash('У задачи есть незавершённые подзадачи, завершите сперва их.', 'danger')
                return False

        return True

    project, membership = load_project(project_id)
    task = Task.query.get_or_404(task_id)
    status = request.form.get('status')

    if check():
        task.status = status
        # Пишем в историю
        db.session.add(TaskHistory(task_id=task.id, user_id=current_user.id, status=status))
        db.session.commit()

    return redirect(url_for('.tasks', project_id=project.id) + '?task=%d' % task.id)


@mod.route('/<int:project_id>/<int:task_id>/chparent', methods=('POST',))
def task_chparent(project_id, task_id, debug=False):
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
    if request.form.get('parent_id', 0, int):
        parent = Task.query.get_or_404(request.form.get('parent_id'))
        if not check_parent():
            return redirect(url_for('.tasks', project_id=project.id) + '?task=%d' % task.id)
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
