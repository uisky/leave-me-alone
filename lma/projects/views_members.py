from flask import render_template, request, redirect, flash, url_for, g
from flask_login import login_required, current_user
from datetime import datetime
import pytz

from . import mod, forms, load_project, mail
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

    members = ProjectMember.query\
        .filter(ProjectMember.project_id == project.id)\
        .order_by(ProjectMember.karma.desc(), ProjectMember.added)\
        .options(db.joinedload('user'))\
        .all()

    return render_template('projects/members.html', project=project, members=members, editing=editing)


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
        .filter_by(project_id=project.id)\
        .filter(db.or_(Task.assigned_id == member.user_id,
                       db.and_(Task.assigned_id == None, Task.user_id == member.user_id)))\
        .order_by(Task.deadline.nullslast(), Task.mp)

    if request.args.get('status'):
        statuses = request.args.get('status').split(',')
    else:
        statuses = ['open', 'progress', 'pause', 'review']
    tasks = tasks.filter(Task.status.in_(statuses))

    tasks = tasks.all()

    g.now = datetime.now(tz=pytz.timezone('Europe/Moscow'))

    return render_template(
        'projects/member.html',
        project=project, member=member, tasks=tasks, statuses=statuses, TASK_STATUSES=TASK_STATUSES
    )


@mod.route('/<int:project_id>/members/<int:member_id>/karma', methods=('GET', 'POST'))
def karma(project_id, member_id):
    project, membership = load_project(project_id)
    member = ProjectMember.query.get_or_404((member_id, project_id))
    karma = KarmaRecord.query\
        .filter_by(project_id=project.id, to_id=member.user_id)\
        .order_by(KarmaRecord.created.desc())\
        .paginate(request.args.get('page', 1), 20)

    form = forms.KarmaRecordForm(value=0)

    if form.validate_on_submit():
        rec = KarmaRecord(project_id=project.id, from_id=current_user.id, to_id=member.user_id)
        form.populate_obj(rec)
        db.session.add(rec)

        db.session.execute(
            'UPDATE project_members SET karma = karma + :value WHERE project_id = :project_id and user_id = :member_id',
            {'value': rec.value, 'project_id': project.id, 'member_id': member.user_id}
        )

        db.session.commit()

        mail.mail_karma(rec)

        flash('Ваша оценка юзеру %s навеки впечатана в его репутацию.' % member.user.name, 'success')
        return redirect(url_for('.members', project_id=project.id))
    else:
        flash_errors(form)

    return render_template('projects/karma.html',
                           project=project, membership=membership, member=member, karma=karma, form=form)