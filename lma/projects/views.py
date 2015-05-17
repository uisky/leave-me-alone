from flask import render_template, request, redirect, flash, url_for, g
from flask_user import login_required, current_user

from . import mod, forms
from .. import app, db
from .models import *
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


@mod.route('/<int:id>/delete/', methods=['POST'])
def project_delete():
    project = Project.query.get_or_404(request.args.get('id', 0))

    project.delete()
    db.session.commit()

    return redirect('/projects')


@mod.route('/<int:id_>/')
def tasks(id_):
    project = Project.query.get_or_404(id_)

    return render_template('projects/tasks.html', project=project)


def find_user(clue):
    clue = clue.lower()
    user = User.query.filter(db.func.lower(User.name) == clue).first()
    if not user and '@' in clue:
        user = User.query.filter(db.func.lower(User.email) == clue).first()

    return user


@mod.route('/<int:id_>/members/', methods=('GET', 'POST'))
def members(id_):
    project = Project.query.get_or_404(id_)

    edit = request.args.get('edit')
    if edit:
        editing = ProjectMember.query.get_or_404((edit, project.id))
    else:
        editing = ProjectMember()

    if request.method == 'POST' and project.can('members'):
        # 1. Ищем юзера, если это добавление
        if editing.user_id is None:
            editing.project_id = project.id

            clue = request.form.get('user', '')
            user = find_user(clue)
            if not user:
                flash('Пользователь с ником или почтой "%s" не обнаружен.' % clue, 'danger')
            else:
                if user.id in (m.user_id for m in project.members):
                    flash('Пользователь %s уже есть в команде' % clue, 'danger')
                else:
                    editing.user_id = user.id

        # 2. Составляем список ролей
        if editing.user_id:
            editing.roles = [role for role in request.form.getlist('roles')
                             if role in ProjectMember.role_meanings.keys()]

            db.session.add(editing)
            db.session.commit()
            return redirect(url_for('.members', id_=project.id))

    g.role_meanings = ProjectMember.role_meanings

    return render_template('projects/members.html', project=project, editing=editing)


@mod.route('/<int:id_>/members/delete/', methods=['POST'])
def member_delete(id_):
    project = Project.query.get_or_404(id_)

    if project.can('members'):
        member = ProjectMember.query.get_or_404((request.form.get('user_id'), project.id))

        if member.user_id == project.user_id:
            flash('Владелец проекта невыгоняем', 'danger')
        else:
            db.session.delete(member)
            db.session.commit()

    return redirect(url_for('.members', id_=project.id))
