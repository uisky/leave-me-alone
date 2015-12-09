from flask import render_template, request, redirect, flash, url_for, g, abort
from flask_login import login_required, current_user

from . import mod, forms, load_project
from .models import *
from .. import app, db
from ..utils import flash_errors
from ..users.models import User


@mod.route('/')
def index():
    form = forms.ProjectPropertiesForm()
    return render_template('projects/index.html', form=form)


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
        .options(db.joinedload('user'))\
        .all()

    stat = {}
    r = db.session.execute(
        "SELECT coalesce(assigned_id, user_id) worker_id, status, count(*) n FROM tasks WHERE project_id = :project_id AND status is not null GROUP BY worker_id, status",
        {'project_id': project.id}
    )
    for row in r:
        stat.setdefault(row['worker_id'], {})[row['status']] = row['n']

    g.role_meanings = ProjectMember.role_meanings
    return render_template('projects/about.html', project=project, members=members, editing=editing, stat=stat)


@mod.route('/add', methods=('POST',), endpoint='project_add')
def project_add():
    project = Project(user_id=current_user.id)

    project.name = request.form.get('name', '').strip()
    if project.name == '':
        flash('Проекту нужно имя!')
        return redirect(url_for('.index'))

    project.type = request.form.get('type', 'tree')
    if project.type not in PROJECT_TYPES.keys():
        project.type = 'tree'

    db.session.add(project)
    db.session.commit()

    # Вступаем в свой проект
    membership = ProjectMember(user_id=current_user.id,
                               project_id=project.id,
                               roles=['lead'])
    db.session.add(membership)
    db.session.commit()

    return redirect(url_for('.tasks', project_id=project.id))


@mod.route('/<int:project_id>/edit/', methods=('GET', 'POST'), endpoint='project_edit')
def project_edit(project_id=None):
    project, membership = load_project(project_id)
    if not project.can('edit'):
        abort(403, 'Вы не можете редактировать этот проект')

    form = forms.ProjectPropertiesForm(obj=project)

    if form.validate_on_submit():
        form.populate_obj(project)

        db.session.add(project)
        db.session.commit()

        return redirect(url_for('.about', project_id=project.id))
    else:
        flash_errors(form)

    return render_template(
        'projects/edit.html',
        project=project, form=form,
        sprints=sprints
    )


@mod.route('/<int:project_id>/delete/', methods=('POST',))
def project_delete(project_id):
    project, membership = load_project(project_id)
    if not project.can('edit'):
        abort(403, 'Вы не можете редактировать этот проект')

    db.session.delete(project)
    db.session.commit()

    return redirect(url_for('.index'))


@mod.route('/<int:project_id>/sprints/')
def sprints(project_id):
    project, membership = load_project(project_id)
    if not project.can('edit'):
        abort(403, 'Вы не можете редактировать этот проект')

    if not project.has_sprints:
        abort(403, 'В этом проекте нет вех.')

    sprints = Sprint.query.filter_by(project_id=project.id).order_by(Sprint.sort).all()

    return render_template('projects/sprints.html', project=project, sprints=sprints)


@mod.route('/<int:project_id>/sprints/add', methods=('POST',))
@mod.route('/<int:project_id>/sprints/<int:sprint_id>/edit', methods=('POST',))
def sprint_edit(project_id, sprint_id=None):
    project, membership = load_project(project_id)
    if not project.can('edit'):
        abort(403)

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
    if not project.can('edit'):
        abort(403, 'Вы не можете редактировать этот проект')

    for k, v in request.form.items():
        if k.startswith('sort.'):
            db.session.execute(
                'UPDATE sprints SET sort = :sort WHERE id = :id AND project_id = :project_id',
                {'id': k[5:], 'sort': v, 'project_id': project.id}
            )
    db.session.commit()

    return 'om-nom-nom!'


@mod.route('/<int:project_id>/sprints/<int:sprint_id>/delete', methods=('POST',))
def sprint_delete(project_id, sprint_id=None):
    project, membership = load_project(project_id)
    if not project.can('edit'):
        abort(403, 'Вы не можете редактировать этот проект')

    sprint = Sprint.query.filter_by(project_id=project.id, id=sprint_id).first()
    if not sprint:
        abort(404, 'Вы пытаетесь удалить веху, которой нет. Лучше похлопайте одной ладонью.')

    db.session.execute(
        'UPDATE tasks SET sprint_id = NULL WHERE project_id = :project_id AND sprint_id = :sprint_id',
        {'project_id': project.id, 'sprint_id': sprint.id}
    )
    db.session.delete(sprint)
    db.session.commit()

    return redirect(url_for('.sprints', project_id=project.id))


@mod.route('/<int:project_id>/type', methods=('POST',))
def set_type(project_id):
    project, membership = load_project(project_id)

    type_ = request.form.get('type')
    if type_ not in PROJECT_TYPES.keys():
        abort(400)

    project.type = type_
    db.session.commit()

    return redirect(url_for('.tasks', project_id=project.id))