import datetime
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
    # Загружаем задачи первого уровня
    ChildrenTasks = db.aliased(Task, name='children_tasks')
    query = db.session\
        .query(Task, ChildrenTasks.id)\
        .filter(Task.project_id == project.id)\
        .filter(Task.parent_id == None)\
        .outerjoin(ChildrenTasks, ChildrenTasks.parent_id == Task.id)\
        .group_by(Task.id, db.text('users_1.id'), db.text('users_2.id'), ChildrenTasks.id)\
        .order_by(Task.mp)\
        .options(db.joinedload('user'), db.joinedload('assignee'), db.noload('tags'))

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

    if options.sprint.data:
        query = query.filter(Task.sprint_id == options.sprint.data)
    else:
        query = query.filter(Task.sprint_id == None)

    # Заполняем tasks и заодно считаем стату по статусам детей каждой задачи
    tasks = OrderedDict()
    seen = {}

    for task, has_children, seen_ in query.all():
        task.has_children = has_children
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

    # Если есть выбранная задача, то загружаем её и её подзадачи

    # Загружаем теги
    q = TaskTag.query.join(Task).filter(Task.project_id == project.id, Task.parent_id == None)
    q = q.filter(Task.sprint_id == options.sprint.data)

    for tag in q.all():
        tasks[tag.task_id].tags.append(tag)

    # Приводим children_statuses к процентам
    for id_, task in tasks.items():
        if task.children_statuses:
            cs = task.children_statuses
            cs['ready'] = int((cs.get('complete', 0) + cs.get('canceled', 0)) / sum(cs.values()) * 100)

    return tasks, seen


def set_tags(task: Task, tagslist: str) -> None:
    """Устанавливает задаче task теги из списка tagslist (через запятую)"""
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


@mod.route('/<int:project_id>/')
@mod.route('/<int:project_id>/<int:sprint_id>/')
@mod.route('/<int:project_id>/<int:sprint_id>/task/<int:task_id>/')
def tasks_list(project_id, sprint_id=None, task_id=None, top_id=None):
    """Список задач"""
    # Редиректы с устаревших урлов
    # /projects/<id>/?sprint=<sprint_id> -> /projects/<id>/<sprint_id>
    # /projects/<id>/?task_id=<task_id>  -> /projects/<id>/<sprint_id>/task/<task_id>
    if 'task_id' in request.args and sprint_id in request.args:
        return redirect(url_for('.tasks_list', project_id=project_id, sprint_id=request.args['sprint'], task_id=request.args['task_id']))
    if 'task_id' in request.args:
        return redirect(url_for('.tasks_list', project_id=project_id, sprint_id=0, task_id=request.args['task_id']))
    if 'sprint' in request.args:
        return redirect(url_for('.tasks_list', project_id=project_id, sprint_id=request.args['sprint']))

    project, membership = load_project(project_id)
    sprints = OrderedDict()
    for sprint in Sprint.query.filter_by(project_id=project.id).order_by(Sprint.sort).all():
        sprints[sprint.id] = sprint

    # Зашли в проект без указания доски, редиректимся туда
    if sprint_id is None:
        # Редиректимся на доску из куки или нулевую
        return redirect(url_for('.tasks_list', project_id=project.id, sprint_id=request.cookies.get('sprint', '0')))
    else:
        # Есть такая доска?
        if task_id is None and sprint_id != 0 and sprint_id not in sprints:
            return redirect(url_for('.tasks_list', project_id=project.id, sprint_id=0))
        # Запоминаем ID доски в куке для этого пути
        defer_cookie(
            'sprint', str(sprint_id),
            path=url_for('.tasks_list', project_id=project.id),
            expires=datetime.datetime.now() + datetime.timedelta(days=365)
        )

    # Если была выбрана задача
    selected = None
    if task_id:
        selected = Task.query.filter_by(project_id=project_id, id=task_id)\
            .first_or_404(f'Задача #{task_id} не найдена в этом проекте. Наверное, её удалили.')
        if selected.sprint_id != sprint_id and sprint_id != 0:
            print('REDIRECT', selected.sprint_id, sprint_id)
            return redirect(url_for('.tasks_list', project_id=project.id, sprint_id=selected.sprint_id, task_id=selected.id))

    #
    # В этом месте у нас sprint_id всегда либо 0, либо существующий спринт, task загружен или None
    #

    # Список всех задач спринта в tasks
    children_tasks = db.aliased(Task, name='children_tasks')
    query = db.session\
        .query(Task, children_tasks.id)\
        .filter(Task.project_id == project.id) \
        .filter(Task.sprint_id == (None if sprint_id == 0 else sprint_id))\
        .outerjoin(children_tasks, children_tasks.parent_id == Task.id)\
        .order_by(Task.mp)\
        .options(db.joinedload('user'), db.joinedload('assignee'), db.noload('tags'))

    if selected:
        if selected.top_id is None:
            # Выбрана задача 1-го уровня, добавляем её поздадачи
            query = query.filter(db.or_(Task.parent_id == None, Task.top_id == selected.id))
        else:
            # Выбрана поздадача, добавляем подзадачи той же ветки
            query = query.filter(db.or_(Task.parent_id == None, Task.top_id == selected.top_id))
    else:
        query = query.filter(Task.parent_id == None)

    if current_user.is_authenticated:
        query = query\
            .add_entity(TaskCommentsSeen)\
            .outerjoin(TaskCommentsSeen, db.and_(TaskCommentsSeen.task_id == Task.id, TaskCommentsSeen.user_id == current_user.id))
    else:
        query = query.add_columns('NULL')

    # Заполняем tasks и заодно считаем стату по статусам детей каждой задачи
    tasks = OrderedDict()
    seen = {}
    for task, has_children, seen_ in query.all():
        task.has_children = has_children
        task.seen_by_me = seen_
        tasks[task.id] = task

    # Загружаем теги
    q = TaskTag.query.join(Task).filter(Task.project_id == project.id, Task.parent_id == None, Task.sprint_id == sprint_id)
    for tag in q.all():
        tasks[tag.task_id].tags.append(tag)

    if selected:
        form_edit = forms.TaskForm(obj=selected)
        form_edit.tagslist.data = ', '.join([tag.name for tag in selected.tags])
    else:
        form_edit = None

    empty = Task(project_id=project.id, status='design.open', importance=0)
    if selected:
        empty.assigned_id = selected.assigned_id
    form_empty = forms.TaskForm(obj=empty)

    # В шаблон нужно отдать:
    # project, membership, sprint_id
    # tasks: {id: Task, ...}
    # seen: {id: Seen, ...}
    # selected: Task
    return render_template(
        'projects/tasks_list.html',
        project=project, membership=membership, sprints=sprints, sprint_id=sprint_id,
        selected=selected,
        tasks=list(tasks.values()), seen=seen,
        empty=empty, form_empty=form_empty, form_edit=form_edit,
    )


@mod.get('/<int:project_id>/task/<int:task_id>/edit')
@mod.get('/<int:project_id>/<int:sprint_id>/task/<int:task_id>/edit')
def task_edit(project_id, task_id, sprint_id=None):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()

    if not membership.can('task.edit', task):
        abort(403, 'Вы не можете редактировать эту задачу.')

    form = forms.TaskForm(obj=task)

    return render_template('projects/_task_edit.html', project=project, membership=membership, task=task, form=form)


@mod.post('/<int:project_id>/task/<int:task_id>/edit')
@mod.post('/<int:project_id>/<int:sprint_id>/task/<int:task_id>/edit')
def task_edit_post(project_id, task_id, sprint_id=None):
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

        form.populate_obj(task)
        if task.character == 0:
            task.character = None
        if form.image_.data:
            db.session.add(task)
            db.session.flush()
            task.image = form.image_.data
        elif form.image_delete.data and task.image:
            del task.image
        if form.tagslist.data:
            print(form.tagslist.data)
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
        return jsonify(task.json(membership, current_user))

    flash_errors(form)

    return redirect(url_for('.tasks_list', project_id=project.id, sprint_id=task.sprint_id, task_id=task.id))


@mod.get('/<int:project_id>/<int:sprint_id>/tasks/<parent_id>/subtask/')
@mod.get('/<int:project_id>/<int:sprint_id>/subtask/')
def task_subtask(project_id, sprint_id, parent_id=None):
    project, membership = load_project(project_id)
    if parent_id:
        parent = Task.query.filter_by(id=parent_id, project_id=project.id).first_or_404()
        if not membership.can('task.subtask', parent):
            abort(403, 'Вы не можете создавать подзадачи к этой задаче.')
    else:
        if not membership.can('project.task-level-0'):
            abort(403, 'Вы не можете создавать задачи 1-го уровня в этом проекте.')
        parent = None

    form = forms.TaskForm()

    return render_template('projects/_task_edit.html', project=project, membership=membership, sprint_id=sprint_id, parent=parent, form=form)


@mod.post('/<int:project_id>/<int:sprint_id>/tasks/<parent_id>/subtask/')
@mod.post('/<int:project_id>/<int:sprint_id>/subtask/')
def task_subtask_post(project_id, sprint_id, parent_id=None):
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

    if form.validate_on_submit():
        form.populate_obj(task)
        if task.character == 0:
            task.character = None
        if form.image_.data:
            db.session.add(task)
            db.session.flush()
            task.image = form.image_.data
        if form.tagslist:
            set_tags(task, form.tagslist.data)

        if parent:
            task.sprint_id = parent.sprint_id
        if sprint_id:
            task.sprint_id = sprint_id

        task.setparent(parent)
        db.session.add(task)
        db.session.flush()

        # Удаляем статус у родительской задачи
        if parent:
            parent.status = None

        # История!
        db.session.flush()
        hist = TaskHistory(task_id=task.id, user_id=task.user_id, status=task.status)
        db.session.add(hist)

        db.session.commit()

        # Оповещаем assignee
        mail_assigned(project, task)

    if request.form.get('ajax'):
        if form.errors:
            return jsonify({'errors': form_json_errors(form)})
        return jsonify(task.json(membership, current_user))

    flash_errors(form)

    return redirect(url_for('.tasks_list', project_id=project.id, sprint_id=task.sprint_id, task_id=parent.id if parent else task.id))


@mod.post('/<int:project_id>/task/<int:task_id>/delete/')
@mod.post('/<int:project_id>/<int:sprint_id>/task/<int:task_id>/delete/')
def task_delete(project_id, task_id, sprint_id=None):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()

    if not membership.can('task.delete', task):
        abort(403, 'Вы не можете удалять эту задачу.')

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

    return redirect(url_for('.tasks_list', project_id=project.id, sprint_id=task.sprint_id, task_id=task.parent_id))


@mod.post('/<int:project_id>/task/<int:task_id>/status/')
@mod.post('/<int:project_id>/<int:sprint_id>/task/<int:task_id>/status/')
def task_status(project_id, task_id, sprint_id=None):
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

    if request.form.get('ajax'):
        return jsonify(task.json(membership, current_user))

    return redirect(url_for('.tasks_list', project_id=project_id, sprint_id=task.sprint_id, task_id=task.id))


@mod.post('/<int:project_id>/task/<int:task_id>/sprint/')
@mod.post('/<int:project_id>/<int:sprint_id>/task/<int:task_id>/sprint/')
def task_sprint(project_id, task_id, sprint_id=None):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()
    old_sprint = task.sprint_id

    if not membership.can('task.sprint', task):
        abort(403, 'Вы не можете перенести эту задачу на другую доску.')

    # В какую доску переносим
    sprint_id = request.form.get('sprint_id', type=int)
    if sprint_id == 0:
        sprint_id = None

    task.subtree(withme=True).update({'sprint_id': sprint_id}, synchronize_session=False)
    db.session.commit()

    return redirect(url_for('.tasks_list', project_id=task.project_id, sprint_id=old_sprint or 0))


@mod.post('/<int:project_id>/tasks/<int:task_id>/chparent/')
@mod.post('/<int:project_id>/<int:sprint_id>/tasks/<int:task_id>/chparent/')
def task_chparent(project_id, task_id, sprint_id=None):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()
    subtree = task.subtree(withme=True).order_by(Task.mp).all()
    back = redirect(url_for('.tasks_list', project_id=project.id, sprint_id=task.sprint_id, task_id=task.id))
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
    task.top_id = parent.top_id if parent.top_id else parent.id

    # Меняем mp у всего поддерева исходной задачи
    cut = len(task.mp)
    for t in subtree:
        t.mp = prefix + t.mp[cut:]
        t.top_id = parent.top_id if parent.top_id else parent.id

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


@mod.post('/<int:project_id>/tasks/<int:task_id>/swap/')
@mod.post('/<int:project_id>/<int:sprint_id>/tasks/<int:task_id>/swap/')
def task_swap(project_id, task_id, sprint_id=None):
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

    if check():
        mps = [sister.mp[:] for sister in sisters]
        trees = [sister.subtree(withme=True).all() for sister in sisters]

        for t in trees[0]:
            t.mp = mps[1] + t.mp[len(mps[1]):]

        for t in trees[1]:
            t.mp = mps[0] + t.mp[len(mps[0]):]

        db.session.commit()

    return redirect(url_for('.tasks_list', project_id=project.id, sprint_id=sisters[0].sprint_id, task_id=sisters[0].id))


@mod.post('/<int:project_id>/tasks/<int:task_id>/git-branch/')
@mod.post('/<int:project_id>/<int:sprint_id>/tasks/<int:task_id>/git-branch/')
def task_set_git_branch(project_id, task_id, sprint_id=None):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()

    if not membership.can('task.set-git-branch', task):
        abort(403, 'Вы не можете указывать GIT-ветки к задачам тут.')

    task.git_branch = request.form['git_branch'].strip()
    if not task.git_branch:
        task.git_branch = None

    db.session.commit()

    return redirect(url_for('.tasks_list', project_id=project.id, sprint_id=task.sprint_id, task_id=task.id))
