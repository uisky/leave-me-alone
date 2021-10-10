from datetime import datetime
import json

from flask import render_template, request, redirect, flash, abort, make_response, jsonify

from . import mod, forms, load_project
from .mail import *
from lma.models import Sprint, Task, TaskHistory, TaskTag, TaskCommentsSeen, Bug
from lma.core import db
from lma.utils import flash_errors, form_json_errors, defer_cookie, print_sql


def load_tasks_tree(project, options):
    """
    Загружает дерево задач и TaskCommentSeen, считает статистику
    :param options: forms.OutputOptions
    :param project: Project
    :return: (OrderedDict(Task), dict(Seen), dict {'total': кол-во задач, 'max_deadline': крайний дедлайн, status: count})
    """
    query = db.session\
        .query(Task)\
        .filter_by(project_id=project.id)\
        .order_by(Task.mp)\
        .options(db.joinedload('user'), db.joinedload('assignee'), db.noload('tags'))

    query = query\
        .add_columns(db.func.count(Bug.id))\
        .outerjoin(Bug, db.and_(Bug.task_id == Task.id, ~Bug.status.in_(('fixed', 'canceled'))))\
        .group_by(Task.id, db.text('users_1.id'), db.text('users_2.id'))

    if current_user.is_authenticated:
        query = query\
            .add_entity(TaskCommentsSeen)\
            .outerjoin(
                TaskCommentsSeen,
                db.and_(TaskCommentsSeen.task_id == Task.id, TaskCommentsSeen.user_id == current_user.id)
            )\
            .group_by(TaskCommentsSeen.task_id, TaskCommentsSeen.user_id)
    else:
        query = query.add_columns('NULL')

    if project.has_sprints:
        if options.sprint.data:
            query = query.filter(Task.sprint_id == options.sprint.data)
        else:
            query = query.filter(Task.sprint_id == None)

    # Заполняем tasks и заодно считаем стату по статусам детей каждой задачи
    tasks = OrderedDict()
    seen = {}

    for task, cnt_bugs, seen_ in query.all():
        task.cnt_bugs = cnt_bugs
        if seen_:
            seen[task.id] = seen_
        task.children_statuses = {}
        tasks[task.id] = task

        # Всем родителям увеличиваем счётчик статусов детей Task.children_statuses
        if task.status:
            t = task
            try:
                while t.parent_id:
                    t.parent.children_statuses.setdefault(task.status, 0)
                    t.parent.children_statuses[task.status] += 1
                    t = t.parent
            except AttributeError:
                # Редкий случай, когда родитель не загружен в tasks (дерево поломалось)
                print('Ну, пиздец, приплыли! У задачи [%d %r %s] нет родителя id=%d' % (t.id, t.mp, t.subject, t.parent_id))
                pass

    # Загружаем теги
    q = TaskTag.query.join(Task).filter(Task.project_id == project.id)
    if project.has_sprints:
        q = q.filter(Task.sprint_id == options.sprint.data)

    for tag in q.all():
        tasks[tag.task_id].tags.append(tag)

    # Сводная стстиатика по всему спринту
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

    return tasks, seen, stats


def set_tags(task, tagslist):
    TaskTag.query.filter_by(task_id=task.id).delete(synchronize_session=False)
    tags = set()
    for tagname in tagslist.split(','):
        tagname = tagname.strip().lstrip('#').lower()
        if tagname != '':
            tags.add(tagname)

    o = []
    for tagname in tags:
        o.append(TaskTag(task_id=task.id, name=tagname))

    db.session.bulk_save_objects(o)


@mod.route('/<int:project_id>/', methods=('GET', 'POST'))
def tasks(project_id):
    project, membership = load_project(project_id)

    options = forms.OutputOptions(request.args)

    # Текущая веха, если проект с вехами
    if project.has_sprints:
        # sprints = Sprint.query.filter_by(project_id=project.id).order_by(Sprint.sort).all()
        options.sprint.choices = [(x.id, x.name) for x in project.sprints] + [(0, 'Вне вех')]
        if 'sprint' not in request.args:
            options.sprint.data = int(request.cookies.get('sprint', '0'))

        defer_cookie(
            'sprint', str(options.sprint.data),
            path=url_for('.tasks', project_id=project.id),
            expires=datetime(2029, 8, 8)
        )

    tasks, seen, stats = load_tasks_tree(project, options)

    # Выбранная задача
    task_id = request.args.get('task', type=int)
    if task_id:
        if task_id in tasks:
            selected = tasks[task_id]
        else:
            selected = Task.query.filter_by(id=request.args.get('task'), project_id=project.id).first()
            if not selected:
                abort(404, 'Выбранная задача не обнаружена. Может, удалили? <a href="?">Весь проект</a>.')
            return redirect(url_for('.tasks', project_id=project.id, sprint=selected.sprint_id or 0, task=selected.id))

        form_edit = forms.TaskForm(obj=selected)
        form_edit.tagslist.data = ', '.join([tag.name for tag in selected.tags])
    else:
        selected = None
        form_edit = None

    empty = Task(project_id=project.id, status='design.open', importance=0)
    if selected:
        empty.assigned_id = selected.assigned_id
    form_empty = forms.TaskForm(obj=empty)

    # Ответ
    return render_template(
        'projects/tasks_%s.html' % project.type,
        project=project, membership=membership, options=options,
        tasks=list(tasks.values()), stats=stats,
        selected=selected, empty=empty, form_empty=form_empty, form_edit=form_edit,
        seen=seen
    )


@mod.route('/<int:project_id>/<int:task_id>/edit/', methods=('POST',))
def task_edit(project_id, task_id):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()

    if not membership.can('task.edit', task):
        abort(403, 'Вы не можете редактировать эту задачу.')

    form = forms.TaskForm(obj=task)

    if form.validate_on_submit():
        # Пишем в историю, если что-то изменилось
        hist = TaskHistory(task_id=task.id, user_id=current_user.id)
        is_modified = False
        history_fields = ('assigned_id', 'subject', 'deadline', 'importance', 'character')
        for field in history_fields:
            if getattr(form, field).data != getattr(task, field):
                setattr(hist, field, getattr(form, field).data)
                is_modified = True
        is_modified |= all([getattr(hist, field) is None for field in history_fields])

        if form.status.data == 'None':
            form.status.data = None

        form.populate_obj(task)
        if task.character == 0:
            task.character = None
        if form.image_.data:
            db.session.add(task)
            db.session.flush()
            task.image = form.image_.data
        elif form.image_delete.data:
            del task.image

        # Теги
        if form.tagslist:
            set_tags(task, form.tagslist.data)

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
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()

    if not membership.can('task.delete', task):
        abort(403, 'Вы не можете удалять эту задачу.')

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
        parent = Task.query.filter_by(id=parent_id, project_id=project.id).first_or_404()
        if not membership.can('task.subtask', parent):
            abort(403, 'Вы не можете создавать подзадачи к этой задаче.')
    else:
        if not membership.can('project.task-level-0'):
            abort(403, 'Вы не можете создавать задачи 1-го уровня в этом проекте.')
        parent = None

    task = Task(project_id=project.id, user_id=current_user.id)
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
        if form.image_.data:
            db.session.add(task)
            db.session.flush()
            task.image = form.image_.data

        if parent:
            task.sprint_id = parent.sprint_id
        elif request.form.get('sprint_id', 0, type=int):
            task.sprint_id = request.form.get('sprint_id', type=int)

        task.setparent(parent)
        db.session.add(task)
        db.session.flush()

        if form.tagslist:
            set_tags(task, form.tagslist.data)

        # Удаляем статус у родительской задачи
        if parent:
            parent.status = None

        # История!
        db.session.flush()
        hist = TaskHistory(task_id=task.id, status=task.status, user_id=task.user_id)
        db.session.add(hist)

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
        if not membership.can('task.set-status', task, status):
            flash('Вы не можете установить этой задаче такой статус.', 'danger')
            return False

        return True

    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()
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
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()
    old_sprint = task.sprint_id

    if not membership.can('task.sprint', task):
        abort(403, 'Вы не можете перенести эту задачу в другую веху.')

    # В какую веху переносим
    sprint_id = request.form.get('sprint_id', type=int)
    if sprint_id == 0:
        sprint_id = None

    task.subtree(withme=True).update({'sprint_id': sprint_id}, synchronize_session=False)
    db.session.commit()

    return redirect(url_for('.tasks', **{'project_id': task.project_id, 'sprint': old_sprint}))


@mod.route('/<int:project_id>/<int:task_id>/chparent/', methods=('POST',))
def task_chparent(project_id, task_id):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()
    subtree = task.subtree(withme=True).order_by(Task.mp).all()
    back = redirect(url_for('.tasks', project_id=project.id, task=task.id, sprint=task.sprint_id))
    if task.parent_id:
        old_parent = Task.query.get(task.parent_id)
    else:
        old_parent = None
    new_parent_id = request.form.get('parent_id', 0, int)

    if new_parent_id:
        parent = Task.query.filter_by(project_id=project.id, id=new_parent_id).first_or_404()
        if parent in subtree:
            flash('Задача не станет собственной подзадачей.', 'danger')
            return back

        # Удаляем статус у нового родителя
        parent.status = None

        # Ставим спринт нового родителя - на случай, если сейчас спринты отключены, а потом их включат.
        task.sprint_id = parent.sprint_id
    else:
        parent = Task(project_id=project.id, mp=[])

    if not membership.can('task.chparent', task, parent):
        flash('Вы не можете переместить эту задачу сюда. Задачу можно сделать только подзадачей другой вашей задачи.', 'danger')
        return back

    # Создаём префикс mp для поддерева
    max_mp = db.session\
                 .query(db.func.coalesce(db.func.max(Task.mp[len(parent.mp)]), 0)) \
                 .filter(Task.project_id == project.id, Task.parent_id == parent.id) \
                 .scalar() + 1
    prefix = parent.mp + [max_mp]
    task.parent_id = parent.id

    # Меняем mp у всего поддерева исходной задачи
    cut = len(task.mp)
    for t in subtree:
        t.mp = prefix + t.mp[cut:]

    # Остались ли у детки у старого родителя?
    if old_parent:
        n_kids = db.session\
            .query(db.func.count(Task.id))\
            .filter(Task.parent_id == old_parent.id, Task.id != task.id)\
            .scalar()
        if not n_kids:
            old_parent.status = task.status

    db.session.commit()

    return back


@mod.route('/<int:project_id>/<int:task_id>/swap/', methods=('POST',))
def task_swap(project_id, task_id):
    project, membership = load_project(project_id)
    sisters = [
        Task.query.filter_by(project_id=project.id, id=x).first_or_404()
        for x in (task_id, request.form.get('sister_id', 0, type=int))
    ]

    def check():
        if sisters[0].parent_id != sisters[1].parent_id:
            flash('Задачи должны быть подзадачами одной задачи.', 'danger')
            return False

        if not membership.can('task.swap', *sisters):
            flash('Вы можете менять местами только свои задачи одного уровня.', 'danger')
            return False

        return True

    if not check():
        return redirect(url_for('.tasks', project_id=project.id) + '?task=%d' % sisters[0].id)

    mps = [sister.mp[:] for sister in sisters]
    trees = [sister.subtree(withme=True).all() for sister in sisters]

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
        abort(400)

    ids = request.form.get('order').split(',')
    for o, id_ in enumerate(ids):
        db.session.execute(
            'UPDATE tasks SET mp[1] = :order WHERE id = :id AND project_id = :project_id',
            {'id': int(id_), 'project_id': project.id, 'order': o + 1}
        )
    db.session.commit()

    return 'ok'
