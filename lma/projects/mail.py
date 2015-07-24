from collections import OrderedDict
from flask import url_for
from .. import mail


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


