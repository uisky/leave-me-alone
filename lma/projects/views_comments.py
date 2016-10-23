from datetime import datetime
import pytz

from flask import render_template, render_template_string, request, redirect, flash, g, abort, make_response, jsonify
from flask_login import current_user

from . import mod, forms, load_project
from .mail import *
from lma.models import Task, TaskComment, TaskCommentsSeen
from lma.core import db
from lma.utils import flash_errors, form_json_errors
from lma.jinja import jinja_markdown


@mod.route('/<int:project_id>/<int:task_id>/comments/', methods=('GET', 'POST'))
def task_comments(project_id, task_id):
    project, membership = load_project(project_id)
    task = Task.query.get_or_404(task_id)

    seen = TaskCommentsSeen.query.filter_by(task_id=task.id, user_id=current_user.id).first()
    if not seen:
        seen = TaskCommentsSeen(
            task_id=task.id, user_id=current_user.id,
            cnt_comments=0, seen=datetime(1981, 8, 8, tzinfo=pytz.timezone('Europe/Moscow'))
        )
        db.session.add(seen)

    if request.method == 'POST':
        comment = TaskComment(task_id=task.id, user_id=current_user.id)
        comment.body = request.form.get('body', '').strip()
        comment.task = task
        if comment.body != '':
            db.session.add(comment)

            task.cnt_comments += 1
            seen.cnt_comments += 1

            mail_comment(comment)

            db.session.commit()
            return render_template_string("""
                {% from '_macros.html' import render_comment %}
                {{ render_comment(comment, lastseen, current_user, project, task) }}
            """, project=project, task=task, comment=comment, lastseen=seen.seen)
        else:
            return jsonify({'error': 'Давайте обойдёмся без дзенских реплик.'})
    else:
        seen.cnt_comments = task.cnt_comments
        lastseen = seen.seen
        seen.seen = datetime.now()
        db.session.commit()

        comments = TaskComment.query.filter_by(task_id=task.id).order_by(TaskComment.created).all()

        return render_template('projects/_comments.html', project=project, task=task, comments=comments, lastseen=lastseen)


@mod.route('/<int:project_id>/<int:task_id>/comments/<int:comment_id>/', methods=('GET', 'POST'))
def task_comment(project_id, task_id, comment_id):
    project, membership = load_project(project_id)
    task = Task.query.get_or_404(task_id)
    comment = TaskComment.query.filter_by(task_id=task.id, id=comment_id).first_or_404()

    if request.method == 'POST':
        comment.body = request.form.get('body', '').strip()
        if comment.body == '':
            db.session.delete(comment)
            task.cnt_comments -= 1
            TaskCommentsSeen.query\
                .filter_by(task_id=task.id)\
                .filter(TaskCommentsSeen.seen >= task.created)\
                .update({TaskCommentsSeen.cnt_comments: TaskCommentsSeen.cnt_comments - 1}, synchronize_session=False)
            db.session.commit()

            return jsonify({'action': 'deleted', 'id': comment.id})
        else:
            d = comment.as_dict()
            d['action'] = 'saved'
            d['body_html'] = jinja_markdown(comment.body)
            db.session.commit()

            return jsonify(d)


    return jsonify(comment.as_dict())
