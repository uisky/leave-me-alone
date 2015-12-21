from flask import render_template, render_template_string, request, redirect, flash, g, abort, make_response, jsonify
from datetime import datetime
import pytz

from . import mod, forms, load_project
from .models import *
from .mail import *
from .. import db
from ..utils import flash_errors, form_json_errors, sanitize_html


@mod.route('/<int:project_id>/', methods=('GET', 'POST'))
def tasks(project_id):
    project, membership = load_project(project_id)

    options = forms.OutputOptions(request.args)

    # Текущий спринт, если проект спринтованный
    if project.has_sprints:
        sprints = Sprint.query.filter_by(project_id=project.id).order_by(Sprint.sort).all()
        options.sprint.choices = [(x.id, x.name) for x in sprints] + [(0, 'Вне вех')]
        if 'sprint' not in request.args:
            options.sprint.data = int(request.cookies.get('sprint', '0'))

    # Заполняем tasks и заодно считаем стату по статусам детей каждой задачи
    tasks = OrderedDict()
    seen = {}

    for task, seen_ in project.get_tasks_query(options):
        if seen_:
            seen[task.id] = seen_
        task.children_statuses = {}
        tasks[task.id] = task

        status = task.status
        if status:
            while task.parent_id:
                if task.parent_id not in tasks:
                    print('\033[31mСтранно, у задачи %d не найден родитель (%d)\033[0m' % (task.id, task.parent_id))
                    break

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
    g.IMPORTANCE = IMPORTANCE
    g.CHARACTERS = CHARACTERS

    # Ответ
    page = render_template(
        'projects/tasks_%s.html' % project.type,
        project=project, membership=membership, options=options,
        tasks=list(tasks.values()), stats=stats,
        selected=selected, empty=empty, form_empty=form_empty, form_edit=form_edit,
        seen=seen
    )
    resp = make_response(page)
    if project.has_sprints:
        resp.set_cookie(
            'sprint', str(options.sprint.data),
            path=url_for('.tasks', project_id=project.id),
            expires=datetime(2029, 8, 8)
        )

    return resp


@mod.route('/<int:project_id>/<int:task_id>/edit/', methods=('POST',))
def task_edit(project_id, task_id):
    project, membership = load_project(project_id)
    task = Task.query.get_or_404(task_id)

    if not membership.can('edit', task):
        abort(403, 'Вы не можете редактировать эту задачу.')

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
        # task.description = sanitize_html(task.description)
        if task.character == 0:
            task.character = None

        if is_modified:
            db.session.add(hist)

            if hist.assigned_id:
                mail_assigned(project, task)
            else:
                mail_changed(project, task, hist)

        db.session.commit()

    if request.form.get('ajax'):
        if form.errors:
            return jsonify({'errors': form_json_errors(form)})

        resp = make_response(task.json(membership, current_user))
        resp.headers['Content-Type'] = 'application/json; charset=utf-8'
        return resp

    flash_errors(form)
    view_data = {'project_id': task.project_id, 'task': task.id}
    if project.has_sprints:
        view_data['sprint'] = task.sprint_id
    return redirect(url_for('.tasks', **view_data))


@mod.route('/<int:project_id>/<int:task_id>/delete/', methods=('POST',))
def task_delete(project_id, task_id):
    project, membership = load_project(project_id)
    task = Task.query.get_or_404(task_id)

    kw = {'project_id': task.project_id}
    if task.parent_id:
        kw['task'] = task.parent_id
    if project.has_sprints:
        kw['sprint'] = task.sprint_id
    redirect_url = url_for('.tasks', **kw)

    task.subtree(withme=True).delete(synchronize_session=False)

    # Остались ли у родителя детки?
    if task.parent_id:
        kids = db.session.execute('SELECT 1 FROM tasks WHERE parent_id = :id LIMIT 1', {'id': task.parent_id}).scalar()
        if kids is None:
            task.parent.status = task.status

    db.session.commit()

    if request.form.get('ajax'):
        resp = make_response(json.dumps({'id': task_id}))
        resp.headers['Content-Type'] = 'application/json; charset=utf-8'
        return resp

    return redirect(redirect_url)


@mod.route('/<int:project_id>/<parent_id>/subtask/', methods=('POST',))
@mod.route('/<int:project_id>/subtask/', methods=('POST',))
def task_subtask(project_id, parent_id=None):
    project, membership = load_project(project_id)
    if parent_id:
        parent = Task.query.get_or_404(parent_id)
    else:
        parent = None

    if not membership.can('subtask', parent):
        abort(403, 'Вы не можете создавать подзадачи к этой задаче.')

    task = Task(project_id=project.id, user_id=current_user.id, status='open')
    form = forms.TaskForm(obj=task)

    # Строим URL, куда пойти после добавления задачи
    kw = {'project_id': task.project_id}
    if parent:
        kw['task'] = parent.id
    if project.has_sprints:
        kw['sprint'] = request.form.get('sprint_id', 0, type=int)
    redirect_url = url_for('.tasks', **kw)

    if form.validate_on_submit():
        form.populate_obj(task)
        # task.description = sanitize_html(task.description)

        if project.has_sprints and request.form.get('sprint_id', 0, type=int):
            task.sprint_id = request.form.get('sprint_id', type=int)
        task.setparent(parent)

        # Удаляем статус у родительской задачи
        if parent:
            parent.status = None

        db.session.add(task)
        db.session.commit()

        # Оповещаем assignee
        mail_assigned(project, task)

    if request.form.get('ajax'):
        if form.errors:
            return jsonify({'errors': form_json_errors(form)})
        resp = make_response(task.json(membership, current_user))
        resp.headers['Content-Type'] = 'application/json; charset=utf-8'
        return resp

    flash_errors(form)
    return redirect(redirect_url)


@mod.route('/<int:project_id>/<int:task_id>/status/', methods=('POST',))
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

    kw = {'project_id': task.project_id, 'task': task.id}
    if project.has_sprints:
        kw['sprint'] = task.sprint_id

    if request.form.get('ajax'):
        resp = make_response(task.json(membership, current_user))
        resp.headers['Content-Type'] = 'application/json; charset=utf-8'
        return resp

    return redirect(url_for('.tasks', **kw))


@mod.route('/<int:project_id>/<int:task_id>/sprint/', methods=('POST',))
def task_sprint(project_id, task_id):
    def check():
        if 'lead' in membership.roles and task.parent_id is None:
            return True
        return False

    project, membership = load_project(project_id)
    task = Task.query.get_or_404(task_id)

    if check():
        task.sprint_id = request.form.get('sprint_id', type=int)
        if task.sprint_id == 0:
            task.sprint_id = None
        db.session.execute(
            'UPDATE tasks SET sprint_id = :sprint_id WHERE project_id = :project_id AND mp[1] = :mp',
            {
                'sprint_id': task.sprint_id,
                'project_id': project.id,
                'mp': task.mp[0]
            }
        )
        db.session.commit()

    return redirect(url_for('.tasks', **{'project_id': task.project_id, 'task': task.id, 'sprint': task.sprint_id}))


@mod.route('/<int:project_id>/<int:task_id>/chparent/', methods=('POST',))
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

    kw = {'project_id': task.project_id, 'task': task.id}
    if project.has_sprints:
        kw['sprint'] = task.sprint_id
    return redirect(url_for('.tasks', **kw))


@mod.route('/<int:project_id>/<int:task_id>/swap/', methods=('POST',))
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

    kw = {'project_id': project.id, 'task': sisters[0].id}
    if project.has_sprints:
        kw['sprint'] = sisters[0].sprint_id
    return redirect(url_for('.tasks', **kw))


@mod.route('/<int:project_id>/reorder/', methods=('POST',))
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


@mod.route('/<int:project_id>/<int:task_id>/comments/', methods=('GET', 'POST'))
def task_comments(project_id, task_id):
    project, membership = load_project(project_id)
    task = Task.query.get_or_404(task_id)

    seen = TaskCommentsSeen.query.filter_by(task_id=task.id, user_id=current_user.id).first()
    if not seen:
        seen = TaskCommentsSeen(
            task_id=task.id, user_id=current_user.id,
            cnt_comments=0, seen=datetime(1981, 8, 8, tzinfo=pytz.timezone('Europe/Moscow'))
        )
        db.session.add(seen)

    if request.method == 'POST':
        comment = TaskComment(task_id=task.id, user_id=current_user.id)
        comment.body = request.form.get('body', '').strip()
        comment.task = task
        if comment.body != '':
            db.session.add(comment)

            task.cnt_comments += 1
            seen.cnt_comments += 1

            mail_comment(comment)

            db.session.commit()
            return render_template_string("""
                {% from '_macros.html' import render_comment %}
                {{ render_comment(comment, lastseen, current_user) }}
            """, comment=comment, lastseen=seen.seen)
        else:
            return jsonify({'error': 'Давайте обойдёмся без дзенских реплик.'})
    else:
        seen.cnt_comments = task.cnt_comments
        lastseen = seen.seen
        seen.seen = datetime.now()
        db.session.commit()

        comments = TaskComment.query.filter_by(task_id=task.id).order_by(TaskComment.created).all()

        return render_template('projects/_comments.html', project=project, task=task, comments=comments, lastseen=lastseen)

