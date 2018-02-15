from collections import OrderedDict

from sqlalchemy.dialects.postgresql import ENUM
from flask import Markup
from flask_login import current_user

from lma.core import db


class Bug(db.Model):
    __tablename__ = 'bugs'

    STATUSES = ('open', 'progress', 'pause', 'test', 'fixed', 'canceled')
    ENUM_STATUS = ENUM(*STATUSES, name='bug_status')

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    closed = db.Column(db.DateTime(timezone=True), nullable=True)
    task_id = db.Column(db.Integer(), db.ForeignKey('tasks.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=True, index=True)
    reporter_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    assignee_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))

    status = db.Column(ENUM_STATUS, default='open')
    subject = db.Column(db.String(1024), nullable=False)
    description = db.Column(db.Text(), nullable=False)

    task = db.relationship('Task', backref='bugs')
    reporter = db.relationship('User', backref='bugs', foreign_keys=[reporter_id])
    assignee = db.relationship('User', foreign_keys=[assignee_id])

    def allowed_statuses(self, user, membership=None):
        """
        Возвращает список статусов, которые может пользователь user присвоить этому багу в виде кортежей (статус, смысл)
        :return:
        """
        if self.status is None:
            return ()

        if user.id == self.task.user_id or user.id == self.task.assigned_id or (membership and 'lead' in membership.roles):
            # Владелец задачи, исполнитель или вождь. Права ограничены здравым смыслом.
            variants = {
                'open': (
                    ('progress', 'Взять в работу'),
                    ('fixed', 'Готово!'),
                    ('test', 'Тестируйте!'),
                    ('canceled', 'Отменить баг'),
                ),
                'progress': (
                    ('pause', 'Пауза'),
                    ('fixed', 'Готово!'),
                    ('test', 'Тестируйте!'),
                    ('open', 'Отказаться от работы'),
                    ('canceled', 'Отменить баг'),
                ),
                'pause': (
                    ('progress', 'Продолжить работу'),
                    ('test', 'Тестируйте!'),
                    ('fixed', 'Готово!'),
                    ('open', 'Отказаться от работы'),
                    ('canceled', 'Отменить баг'),
                ),
                'test': (
                    ('open', 'Отказаться от работы'),
                    ('progress', 'Вернуть в работу'),
                    ('fixed', 'Готово!'),
                    ('canceled', 'Отменить баг'),
                ),
                'fixed': (
                    ('open', 'Вернуть баг'),
                ),
                'canceled': (
                    ('open', 'Вернуть баг'),
                )
            }
        elif user.id == self.reporter_id or (membership and 'tester' in membership.roles):
            # Тестировщик
            variants = {
                'open': (
                    ('canceled', 'Отменить баг'),
                ),
                'progress': (
                    ('canceled', 'Отменить баг'),
                ),
                'pause': (),
                'test': (
                    ('fixed', 'Протестировано, всё хорошо'),
                    ('open', 'Вернуть баг в работу'),
                ),
                'fixed': (
                    ('open', 'Вернуть баг'),
                ),
                'canceled': (
                    ('open', 'Вернуть баг'),
                )
            }
        else:
            return ()

        return variants.get(self.status, ())
