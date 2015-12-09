from flask import render_template, request, redirect, flash, url_for, g, Markup, abort, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import pytz
import re
import json

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


@mod.route('/<int:project_id>/members/add/', methods=['POST'])
def members_add(project_id):
    project, membership = load_project(project_id)

    if not project.can('members'):
        abort(403, 'Вы недостаточно круты, чтобы управлять членством в этой команде.')

    clues = [x.strip() for x in re.split(r'[,\n]+', request.form.get('clues', ''))]
    clues = [x for x in clues if x != '']

    if len(clues) == 0:
        flash('Введите e-mail\'ы пользователей, которых хотите добавить в команду.', 'danger')
        return redirect(url_for('.about', project_id=project_id))

    users = set()
    already_ids = [x[0] for x in db.session.query(ProjectMember.user_id).filter_by(project_id=project.id).all()]
    not_found, already = [], []

    for clue in clues:
        user = find_user(clue)
        if not user:
            not_found.append(Markup(clue).striptags())
        elif user.id in already_ids:
            already.append(user.name)
        else:
            users.add(user)

    if not_found:
        flash('Кое-кого не удалось найти среди пользователей leave-me-alone, а именно ' + ', '.join(not_found), 'warning')

    if already:
        flash(', '.join(not_found) + ' уже присутствуют в команде.', 'warning')

    if len(users) == 0:
        flash('Не удалось найти ни одного нового пользователя с указанными адресами. Наверное, есть смысл уточнить '
              'у этих добрых людей, под какими почтами они здесь регистрировались.', 'danger')
        return redirect(url_for('.about', project_id=project_id))

    roles = [role for role in request.form.getlist('roles') if role in ProjectMember.role_meanings.keys()]

    # Добавляем!
    for user in users:
        member = ProjectMember(project_id=project.id, user_id=user.id, roles=roles)
        db.session.add(member)
    db.session.commit()

    flash('Встречайте новеньких: %s' % ', '.join([u.name for u in users]), 'success')

    return redirect(url_for('.about', project_id=project_id))


@mod.route('/<int:project_id>/members/<int:member_id>/edit/', methods=['GET', 'POST'])
def member_edit(project_id, member_id):
    project, membership = load_project(project_id)

    if not project.can('members'):
        abort(403, 'Вы не имеете права!')

    member = ProjectMember.query.get_or_404((member_id, project_id))

    if request.method == 'POST':
        member.roles = request.form.getlist('roles')
        db.session.commit()
        return redirect(url_for('.about', project_id=project.id))

    g.role_meanings = ProjectMember.role_meanings
    return render_template('projects/_member_edit.html', project=project, member=member)


@mod.route('/<int:project_id>/members/<int:member_id>/delete/', methods=['POST'])
def member_delete(project_id, member_id):
    project = Project.query.get_or_404(project_id)

    if not project.can('members'):
        abort(403, 'Не позволено вам выгонять людей отсюда!')

    member = ProjectMember.query.get_or_404((member_id, project.id))

    if member.user_id == project.user_id:
        flash('Владелец проекта невыгоняем.', 'danger')
    else:
        db.session.delete(member)
        db.session.commit()

    return redirect(url_for('.about', project_id=project.id))


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
        return redirect(url_for('.about', project_id=project.id))
    else:
        flash_errors(form)

    return render_template('projects/karma.html',
                           project=project, membership=membership, member=member, karma=karma, form=form)