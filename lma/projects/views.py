from flask import render_template, request, redirect, flash, url_for, g
from flask_login import login_required, current_user

from . import mod, forms
from .models import *
from .. import app, db
from ..utils import flash_errors
from ..users.models import User


@mod.before_request
def load_projects():
    if not current_user.is_authenticated():
        return

    projects = db.session.query(Project).join(ProjectMember) \
        .filter(ProjectMember.user_id == current_user.id) \
        .order_by(Project.created.desc()) \
        .all()
    g.my_projects = projects


@mod.route('/')
@login_required
def index():
    form = forms.ProjectPropertiesForm()
    return render_template('projects/index.html', form=form)


@mod.route('/add', methods=('POST',), endpoint='project_add')
@mod.route('/<int:project_id>/edit/', methods=('GET', 'POST'), endpoint='project_edit')
def project_edit(project_id=None):
    if project_id:
        project = Project.query.get_or_404(project_id)
    else:
        project = Project(user_id=current_user.id)

    form = forms.ProjectPropertiesForm(obj=project)

    if form.validate_on_submit():
        form.populate_obj(project)
        db.session.add(project)
        db.session.commit()

        # Вступаем в свой проект
        if project_id is None:
            membership = ProjectMember(user_id=current_user.id,
                                       project_id=project.id,
                                       roles=['lead'])
            db.session.add(membership)
            db.session.commit()

        return redirect(url_for('.tasks', project_id=project.id))
    else:
        flash_errors(form)

    return render_template('projects/edit.html', project=project, form=form)


@mod.route('/<int:id>/delete/', methods=('POST',))
def project_delete():
    project = Project.query.get_or_404(request.args.get('id', 0))

    project.delete()
    db.session.commit()

    return redirect('/projects')


