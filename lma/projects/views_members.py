from flask import render_template, request, redirect, flash, url_for, g
from flask_login import login_required, current_user
from datetime import datetime
import pytz

from . import mod, forms, load_project
from .models import *
from .. import app, db
from ..utils import flash_errors
from ..users.models import User


def find_user(clue):
    clue = clue.lower()
    user = User.query.filter(db.func.lower(User.name) == clue).first()
    if not user and '@' in clue:
        user = User.query.filter(db.func.lower(User.email) == clue).first()

    return user


@mod.route('/<project_id>/members/', methods=('GET', 'POST'))
def members(project_id):
    project, membership = load_project(project_id)

    edit = request.args.get('edit')
    if edit:
        editing = ProjectMember.query.get_or_404((edit, project.id))
    else:
        editing = ProjectMember()

    if request.method == 'POST' and project.can('members'):
        # 1. Ищем юзера, если это добавление
        if editing.user_id is None:
            editing.project_id = project.id

            clue = request.form.get('user', '').strip()
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
            return redirect(url_for('.members', project_id=project.id))

    g.role_meanings = ProjectMember.role_meanings

    return render_template('projects/members.html', project=project, editing=editing)


@mod.route('/<int:project_id>/members/delete/', methods=['POST'])
def member_delete(project_id):
    project = Project.query.get_or_404(project_id)

    if project.can('members'):
        member = ProjectMember.query.get_or_404((request.form.get('user_id'), project.id))

        if member.user_id == project.user_id:
            flash('Владелец проекта невыгоняем', 'danger')
        else:
            db.session.delete(member)
            db.session.commit()

    return redirect(url_for('.members', project_id=project.id))


@mod.route('/<int:project_id>/members/<int:member_id>/')
def member(project_id, member_id):
    project, membership = load_project(project_id)

    member = ProjectMember.query.get_or_404((member_id, project_id))

    tasks = Task.query\
        .filter_by(project_id=project.id, assigned_id=member.user_id)\
        .order_by(Task.deadline.nullslast()).all()

    g.now = datetime.now(tz=pytz.timezone('Europe/Moscow'))

    return render_template('projects/member.html', project=project, member=member, tasks=tasks)