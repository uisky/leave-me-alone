from flask import render_template, request, redirect, flash, url_for, g, abort
from flask_login import current_user, login_required

from . import mod, forms, load_project
from ..utils import flash_errors
from lma.core import db
from lma.models import Project, ProjectFolder, ProjectMember, Task


@mod.route('/')
@mod.route('/folder-<int:folder_id>/')
@login_required
def index(folder_id=None):
    folders = ProjectFolder.query.filter_by(user_id=current_user.id).order_by('id').all()
    if folder_id:
        folder = ProjectFolder.query.filter_by(id=folder_id, user_id=current_user.id).first()
        if not folder:
            abort(404)
    else:
        folder = None

    query = Project.query\
        .join(ProjectMember)\
        .outerjoin(ProjectFolder)\
        .filter(ProjectMember.user_id == current_user.id)\
        .order_by(ProjectMember.added.desc())
    if folder:
        query = query.filter(ProjectMember.folder_id == folder.id)
    else:
        query = query.filter(ProjectMember.folder_id == None)
    projects = query.all()

    form_project_new = forms.ProjectPropertiesForm()
    form_folder_edit = forms.ProjectFolderForm(obj=folder)

    return render_template(
        'projects/index.html',
        folders=folders, folder=folder, projects=projects,
        form_project_new=form_project_new, form_folder_edit=form_folder_edit
    )


@mod.route('/folder-set', methods=('POST',))
@login_required
def folder_set():
    membership = ProjectMember.query\
        .filter_by(user_id=current_user.id, project_id=request.form.get('project_id', 0, type=int))\
        .first()
    if not membership:
        return '{"error": "Вы не состоите в этом проекте."}'

    folder_id = request.form.get('folder_id', 0, type=int)
    if folder_id:
        folder = ProjectFolder.query\
            .filter_by(user_id=current_user.id, id=folder_id)\
            .first()
        if not folder:
            return '{"error": "Папка не найдена"}'
        membership.folder_id = folder.id
    else:
        membership.folder_id = None

    db.session.commit()
    return '{"project_id": %d, "folder_id": %d}' % (membership.project_id, folder_id)


@mod.route('/folder-new', methods=('POST',))
@mod.route('/folder-<int:folder_id>/edit/', methods=('POST',))
@login_required
def folder_edit(folder_id=None):
    if folder_id:
        folder = ProjectFolder.query.filter_by(user_id=current_user.id, id=folder_id).first()
        if not folder:
            abort(404)
    else:
        folder = ProjectFolder(user_id=current_user.id)

    form = forms.ProjectFolderForm(obj=folder)

    if form.validate_on_submit():
        form.populate_obj(folder)
        db.session.add(folder)
        db.session.commit()
    else:
        flash_errors(form)

    return redirect(url_for('.index', folder_id=folder.id))


@mod.route('/folder-<int:folder_id>/delete/', methods=('POST',))
@login_required
def folder_delete(folder_id):
    folder = ProjectFolder.query.filter_by(user_id=current_user.id, id=folder_id).first()
    if not folder:
        abort(404)

    db.session.delete(folder)
    db.session.commit()

    return redirect(url_for('.index'))


