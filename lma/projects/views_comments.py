from datetime import datetime
import pytz

from flask import render_template, render_template_string, request, jsonify
from flask_login import current_user

from . import mod, load_project
from . import mail
from lma.models import Task, TaskComment, TaskCommentsSeen
from lma.core import db
from lma.jinja import jinja_markdown


@mod.route('/<int:project_id>/task/<int:task_id>/comments/', methods=('GET', 'POST'))
def task_comments(project_id, task_id):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()

    if current_user.is_authenticated:
        seen = TaskCommentsSeen.query.filter_by(task_id=task.id, user_id=current_user.id).first()
        if not seen:
            seen = TaskCommentsSeen(
                task_id=task.id, user_id=current_user.id,
                cnt_comments=0, seen=datetime(1981, 8, 8, tzinfo=pytz.timezone('Europe/Moscow'))
            )
            db.session.add(seen)
    else:
        seen = None

    if request.method == 'POST':
        if not membership.can('task.comment', task):
            return 'Вы не можете комментировать эту задачу :('

        comment = TaskComment(task_id=task.id, user_id=current_user.id)
        comment.task = task
        if comment.body != '' or request.files.get('image'):
            db.session.add(comment)

            comment.body = request.form.get('body', '').strip()

            if request.files.get('image'):
                db.session.flush()
                comment.image = request.files['image']

            task.cnt_comments += 1
            if seen:
                seen.cnt_comments += 1

            mail.mail_comment(comment)

            db.session.commit()

            return render_template_string("""
                {% from '_macros.html' import render_comment %}
                {{ render_comment(comment, seen, current_user, project, membership, task) }}
            """, project=project, membership=membership, task=task, comment=comment, seen=seen)
        else:
            return jsonify({'error': 'Давайте обойдёмся без дзенских реплик.'})
    else:
        if seen:
            seen.cnt_comments = task.cnt_comments
            seen.seen = datetime.now(tz=pytz.timezone('Europe/Moscow'))
            db.session.commit()

        comments = TaskComment.query\
            .filter_by(task_id=task.id)\
            .order_by(TaskComment.created)\
            .options(db.joinedload(TaskComment.user))\
            .all()

        return render_template('projects/_comments.html',
                               project=project, membership=membership, task=task,
                               comments=comments, seen=seen)


@mod.route('/<int:project_id>/task/<int:task_id>/comments/<int:comment_id>/', methods=('GET', 'POST'))
def task_comment(project_id, task_id, comment_id):
    project, membership = load_project(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()
    comment = TaskComment.query.filter_by(task_id=task.id, id=comment_id).first_or_404()

    if request.method == 'POST':
        comment.body = request.form.get('body', '').strip()
        if comment.body == '':
            # Удаление комментария
            if not membership.can('comment.delete', comment):
                return jsonify({'error': 'Сорян, вы не можете удалить этот комментарий.'})
            del comment.image
            db.session.delete(comment)
            task.cnt_comments -= 1
            TaskCommentsSeen.query\
                .filter_by(task_id=task.id)\
                .filter(TaskCommentsSeen.seen >= task.created)\
                .update({TaskCommentsSeen.cnt_comments: TaskCommentsSeen.cnt_comments - 1}, synchronize_session=False)
            db.session.commit()

            return jsonify({'action': 'deleted', 'id': comment.id})
        else:
            if not membership.can('comment.edit', comment):
                return jsonify({'error': 'Редактировать этот коментарий вам не позволено.'})
            d = comment.as_dict()
            d['action'] = 'saved'
            d['body_html'] = jinja_markdown(comment.body)
            db.session.commit()

            return jsonify(d)

    return jsonify(comment.as_dict())
