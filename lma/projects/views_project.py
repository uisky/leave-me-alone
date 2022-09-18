from collections import OrderedDict

from flask import render_template, request, redirect, flash, url_for, g, abort
from flask_login import current_user

from . import mod, forms, load_project
from ..utils import flash_errors
from lma.core import db
from lma.models import Project, ProjectMember, Sprint, Task


@mod.route('/<project_id>/about/')
def about(project_id):
    project, membership = load_project(project_id)

    edit = request.args.get('edit')
    if edit:
        editing = ProjectMember.query.get_or_404((edit, project.id))
    else:
        editing = ProjectMember()

    members = ProjectMember.query\
        .filter(ProjectMember.project_id == project.id)\
        .order_by(ProjectMember.karma.desc(), ProjectMember.added)\
        .options(db.joinedload(ProjectMember.user))\
        .all()

    stat = {}
    query = db.session\
        .query(
            db.func.coalesce(Task.assigned_id, Task.user_id).label('worker_id'),
            Task.status,
            db.func.count('*'),
        )\
        .filter(Task.project_id == project.id, Task.status != None)\
        .group_by('worker_id', Task.status)
    for worker_id, status, cnt in query.all():
        stat.setdefault(worker_id, {})[status] = cnt

    return render_template('projects/about.html',
                           project=project, membership=membership, members=members, editing=editing, stat=stat, ProjectMember=ProjectMember)


@mod.route('/add/', methods=('POST',), endpoint='project_add')
def project_add():
    project = Project(user_id=current_user.id)

    project.name = request.form.get('name', '').strip()
    if project.name == '':
        flash('Проекту нужно имя!', 'danger')
        return redirect(url_for('.index'))

    db.session.add(project)
    db.session.flush()

    # Вступаем в свой проект
    membership = ProjectMember(
        user_id=current_user.id,
        project_id=project.id,
        roles=['lead'],
        folder_id=request.form.get('folder_id', 0, type=int) or None
    )
    db.session.add(membership)
    db.session.commit()

    return redirect(url_for('.tasks_list', project_id=project.id))


@mod.route('/<int:project_id>/edit/', methods=('GET', 'POST'), endpoint='project_edit')
def project_edit(project_id=None):
    project, membership = load_project(project_id)

    if not membership.can('project.edit'):
        abort(403, 'Вы не можете редактировать этот проект.')

    form = forms.ProjectPropertiesForm(obj=project)

    if form.validate_on_submit():
        form.populate_obj(project)
        db.session.commit()
        return redirect(url_for('.about', project_id=project.id))
    else:
        flash_errors(form)

    return render_template(
        'projects/edit/description.html',
        project=project, form=form,
        sprints=sprints
    )


@mod.route('/<int:project_id>/delete/', methods=('POST',))
def project_delete(project_id):
    project, membership = load_project(project_id)
    if not membership.can('project.edit'):
        abort(403, 'Вы не имеете права удалять этот проект!')

    db.session.delete(project)
    db.session.commit()

    return redirect(url_for('.index'))


@mod.route('/<int:project_id>/edit/sprints/')
def sprints(project_id):
    project, membership = load_project(project_id)
    if not membership.can('project.edit'):
        abort(403, 'Досками может управлять только владелец.')

    sprints = OrderedDict()
    query = db.session.query(Sprint, Task.status, db.func.count(Task.id))\
        .outerjoin(Task)\
        .filter(Sprint.project_id == project.id)\
        .group_by(Sprint.id, Task.status)\
        .order_by(Sprint.sort, Task.status)
    for sprint, status, cnt in query.all():
        sprints.setdefault(sprint, OrderedDict())[status] = cnt

    return render_template('projects/edit/sprints.html', project=project, sprints=sprints)


@mod.route('/<int:project_id>/sprints/add/', methods=('POST',))
@mod.route('/<int:project_id>/sprints/<int:sprint_id>/edit/', methods=('POST',))
def sprint_edit(project_id, sprint_id=None):
    project, membership = load_project(project_id)
    if not membership.can('project.edit'):
        abort(403, 'Вы не можете редактировать доски в этом проекте.')

    if sprint_id is not None:
        sprint = Sprint.query.filter_by(project_id=project.id, id=sprint_id).first()
    else:
        sprint = Sprint(project_id=project.id)
        sprint.sort = db.session.query(db.func.max(Sprint.sort)).filter_by(project_id=project.id).scalar() or 0
        sprint.sort += 1

    form = forms.SprintPropertiesForm(obj=sprint, csrf_enabled=False)

    if form.validate_on_submit():
        form.populate_obj(sprint)
        db.session.add(sprint)
        db.session.commit()
    else:
        flash_errors(form)

    return redirect(url_for('.sprints', project_id=project.id))


@mod.route('/<int:project_id>/sprints/reorder/', methods=('POST',))
def sprints_reorder(project_id):
    project, membership = load_project(project_id)
    if not membership.can('project.edit'):
        abort(403, 'Вы не можете управлять досками в этом проекте.')

    for k, v in request.form.items():
        if k.startswith('sort.'):
            db.session.execute(
                'UPDATE sprints SET sort = :sort WHERE id = :id AND project_id = :project_id',
                {'id': k[5:], 'sort': v, 'project_id': project.id}
            )
    db.session.commit()

    return 'om-nom-nom!'


@mod.route('/<int:project_id>/sprints/<int:sprint_id>/delete/', methods=('POST',))
def sprint_delete(project_id, sprint_id=None):
    project, membership = load_project(project_id)
    if not membership.can('project.edit'):
        abort(403, 'Вы не можете управлять досками в этом проекте.')

    sprint = Sprint.query.filter_by(project_id=project.id, id=sprint_id).first()
    if not sprint:
        abort(404, 'Вы пытаетесь удалить доску, которой нет. Лучше похлопайте одной ладонью.')

    db.session.execute(
        'UPDATE tasks SET sprint_id = NULL WHERE project_id = :project_id AND sprint_id = :sprint_id',
        {'project_id': project.id, 'sprint_id': sprint.id}
    )
    db.session.delete(sprint)
    db.session.commit()

    return redirect(url_for('.sprints', project_id=project.id))


@mod.route('/<int:project_id>/edit/access/', methods=('GET', 'POST'))
def project_access(project_id):
    project, membership = load_project(project_id)
    if not membership.can('project.edit'):
        abort(403, 'Вы не можете редактировать этот проект.')

    form = forms.ProjectAccessForm(obj=project)

    if form.validate_on_submit():
        form.populate_obj(project)
        db.session.commit()
        flash('Права доступа в проект соханены.', 'success')
        return redirect(url_for('.project_access', project_id=project.id))

    return render_template('projects/edit/access.html', project=project, form=form)
