from collections import OrderedDict

from flask import url_for
from flask_login import current_user

from lma.core import mail


def mail_assigned(project, task):
    if task.assigned_id is None or task.assigned_id == task.user_id or task.assigned_id == current_user.id:
        return

    msg_text = """Вам назначена задача.
Проект: "{0}"
Задача: "{task.subject}"
Описание:
{task.description}

{1}

Не забудьте поставить статус «В работе», когда приступите.
    """.format(project.name, url_for('.tasks_list', project_id=task.project_id, sprint_id=task.sprint_id, task_id=task.id, _external=True), task=task)

    mail.send_message(
        subject='Новая задача: %s' % task.subject,
        recipients=[task.assignee.email],
        body=msg_text
    )


def mail_changed(project, task, hist):
    if task.assigned_id is None or task.assigned_id == task.user_id or task.assigned_id == current_user.id:
        return

    changed = []
    hist_props = OrderedDict([
        ('status', 'статус'), ('subject', 'заголовок'), ('description', 'комментарий'),
        ('deadline', 'дедлайн'), ('importance', 'важность'), ('character', 'характер')
    ])
    for prop, descr in hist_props.items():
        if getattr(hist, prop) is not None:
            changed.append(descr)
    if not changed:
        return

    msg_text = """
В задаче "%s" проекта "%s" поменялись свойства: %s.

  %s

    """ % (
        task.subject, project.name, ', '.join(changed),
        url_for('.tasks_list', project_id=task.project_id, sprint_id=task.sprint_id, task_id=task.id, _external=True)
    )
    mail.send_message(
        subject='Изменилась задача: %s' % task.subject,
        recipients=[task.assignee.email],
        body=msg_text
    )


def mail_karma(record):
    msg_text = """Здравствуйте!

Некто %s поставил вам в карму оценку "%d", прокомментировав свой поступок так: "%s"
    """ % (record.from_user.name, record.value, record.comment)
    mail.send_message(
        subject='Оценка в карму (%d) от %s' % (record.value, record.from_user.name),
        recipients=[record.to_user.email],
        body=msg_text
    )


def mail_comment(comment):
    msg_text = """Комментируя задачу <a href="%s#task-comments">%s</a>, %s сказал следующее:

%s
    """ % (
        url_for('.tasks_list', project_id=comment.task.project_id, sprint_id=comment.task.sprint_id, task_id=comment.task.id, _external=True),
        comment.task.subject,
        current_user.name,
        comment.body
    )
    receivers = set()
    if comment.task.user_id != current_user.id:
        receivers.add(comment.task.user.email)
    if comment.task.assigned_id and comment.task.assigned_id != current_user.id:
        receivers.add(comment.task.assignee.email)

    for receiver in receivers:
        mail.send_message(
            subject='Комментарий к задаче %s' % comment.task.subject,
            recipients=[receiver],
            body=msg_text
        )
