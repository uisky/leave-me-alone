from collections import OrderedDict

from flask import url_for
from flask_login import current_user

from lma.core import mail


def mail_assigned(project, task):
    if task.assigned_id is None or task.assigned_id == task.user_id or task.assigned_id == current_user.id:
        return

    msg_text = """Хэллоу май френд!

Зэрэ из э нью джоб фо ю ин проджэкт "%s"!

  http://leave-me-alone.ru%s

Донт форгет ту пут ит ин "прогресс" статус, вэн ю бегин))))))))))))))))))))

Гуд лак!
    """ % (project.name, url_for('.tasks', project_id=task.project_id, task=task.id))
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
        changed.append('не удалось установить, какие :(')

    msg_text = """Пссст, человек!

В задаче "%s" проекта "%s" поменялись свойства: %s.

  http://leave-me-alone.ru%s

    """ % (
        task.subject, project.name, ', '.join(changed),
        url_for('.tasks', project_id=task.project_id, task=task.id)
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
    msg_text = """Комментируя задачу <a href="http://leave-me-alone.ru%s#task-comments">%s</a>, %s сказал следующее:

%s
    """ % (
        url_for('.tasks', project_id=comment.task.project_id, task=comment.task.id),
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
