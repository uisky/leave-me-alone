from flask import render_template, request, redirect, flash, url_for, g
from flask_user import login_required, current_user

from . import mod, forms
from .models import *
from .. import app, db
from ..utils import flash_errors
from ..users.models import User


@mod.route('/')
@login_required
def index():
    projects = db.session.query(Project).join(ProjectMember) \
        .filter(ProjectMember.user_id == current_user.id) \
        .order_by(Project.created.desc()) \
        .all()

    return render_template('projects/index.html', projects=projects)


@mod.route('/add', methods=['POST'])
@mod.route('/<int:id_>/edit/', methods=['POST'])
def project_edit(id_=0):
    # id_ = request.args.get('id', 0)
    if id_:
        project = Project.query.get_or_404(id_)
    else:
        project = Project(user_id=current_user.id)

    project.name = request.form.get('name', '').strip()
    if project.name == '':
        flash('Проекту нужно имя.', 'danger')
        return redirect(url_for('.index'))

    db.session.add(project)
    db.session.commit()

    # Вступаем в свой проект
    membership = ProjectMember(user_id=current_user.id,
                               project_id=project.id,
                               roles=['lead'])
    db.session.add(membership)
    db.session.commit()

    return redirect(url_for('.index'))


@mod.route('/<int:id>/delete/', methods=('POST',))
def project_delete():
    project = Project.query.get_or_404(request.args.get('id', 0))

    project.delete()
    db.session.commit()

    return redirect('/projects')


