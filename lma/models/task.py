from collections import OrderedDict
import json

import markdown
from sqlalchemy.dialects.postgresql import ARRAY, ENUM
from flask import Markup
from flask_login import current_user

from lma.core import db


class Task(db.Model):
    __tablename__ = 'tasks'

    STATUSES = ('open', 'progress', 'pause', 'review', 'done', 'canceled')
    ENUM_STATUS = ENUM(*STATUSES, name='task_status')

    IMPORTANCE = OrderedDict([
        (2, {'id': 2, 'name': 'Очень важно', 'icon': '<span class="importance important-2">&uarr;&uarr;</span>'}),
        (1, {'id': 1, 'name': 'Важно', 'icon': '<span class="importance important-1">&uarr;</span>'}),
        (0, {'id': 0, 'name': 'Обычная', 'icon': ''}),
        (-1, {'id': -1, 'name': 'Незначительно', 'icon': '<span class="importance important--1">&darr;</span>'}),
        (-2, {'id': -2, 'name': 'Ничтожно', 'icon': '<span class="importance important--2">&darr;&darr;</span>'}),
    ])

    CHARACTERS = OrderedDict([
        (1, {'id': 1, 'name': 'Фича', 'icon': ''}),
        (2, {'id': 2, 'name': 'Баг', 'icon': '<i class="fa fa-bug text-danger"></i>'}),
        (3, {'id': 3, 'name': 'Подумать', 'icon': '<i class="fa fa-lightbulb-o"></i>'}),
    ])

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))

    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    project_id = db.Column(db.Integer(), db.ForeignKey('projects.id', ondelete='CASCADE', onupdate='CASCADE'),
                           nullable=False, index=True)
    sprint_id = db.Column(db.Integer(), db.ForeignKey('sprints.id', ondelete='CASCADE', onupdate='CASCADE'),
                          nullable=True, index=True)
    assigned_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))

    mp = db.Column(ARRAY(db.Integer(), zero_indexes=True))
    parent_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE', onupdate='CASCADE'),
                          index=True)

    status = db.Column(ENUM_STATUS, default='open')
    # Важность задачи, от -2 до +2, значения и икноки в IMPORTANCE
    importance = db.Column(db.SmallInteger, nullable=False, server_default='0', default=0)
    # Тип задачи: баг, фича, подумать
    character = db.Column(db.SmallInteger, nullable=True)
    subject = db.Column(db.String(1024), nullable=False)
    description = db.Column(db.Text(), nullable=False)
    deadline = db.Column(db.DateTime(timezone=True))
    estimate = db.Column(db.DECIMAL(precision=3, scale=1))

    user = db.relationship('User', backref='tasks', foreign_keys=[user_id])
    assignee = db.relationship('User', backref='assigned', foreign_keys=[assigned_id])
    children = db.relationship('Task', backref=db.backref('parent', remote_side=id))
    history = db.relationship('TaskHistory', backref='task', order_by='TaskHistory.created', passive_deletes=True)
    sprint = db.relationship('Sprint', backref='tasks')

    cnt_comments = db.Column(db.Integer, nullable=False, server_default='0', default=0)

    def __str__(self):
        return '<Task %d: %s - "%s">' % (self.id, self.mp, self.subject)

    def __repr__(self):
        return self.__str__()

    @property
    def depth(self):
        return len(self.mp) - 1

    @property
    def path(self):
        task = self
        subjs = [self.subject]
        while task.parent_id is not None:
            task = Task.query.get(task.parent_id)
            subjs.insert(0, task.subject)

        return ' / '.join(subjs)

    def allowed_statuses(self, user, membership=None):
        """
        Возвращает список статусов, которые может пользователь user присвоить этой задаче
        :return:
        """
        if self.status is None:
            return []

        if user.id == self.user_id or (membership and 'lead' in membership.roles):
            # Владелец задачи или вождь. Права ограничены здравым смыслом.
            variants = {
                'open': ('progress', 'done', 'canceled'),
                'progress': ('done', 'review', 'pause', 'open', 'canceled'),
                'pause': ('open', 'progress', 'canceled'),
                'review': ('open', 'done', 'canceled'),
                'done': ('open',),
                'canceled': ('open',)
            }
        elif user.id == self.assigned_id:
            # Назначенный исполнитель
            variants = {
                'open': ('progress', 'review'),
                'progress': ('open', 'pause', 'review', 'done', 'canceled'),
                'pause': ('progress',),
                'review': ('open', 'progress'),
                'done': ('open', 'review', 'canceled'),
                'canceled': ('open',)
            }
        else:
            return ()

        return variants.get(self.status, ())

    def setparent(self, parent):
        """
        Устанавливает parent_id и mp, чтобы усыновиться parent'ом.
        parent может быть None, тогда создаётся задача в корень
        :param parent:
        :return:
        """
        if parent:
            self.parent_id = parent.id
        else:
            self.parent_id = None

        if parent is None:
            max_mp = db.session.execute(
                "SELECT coalesce(max(mp[1]), 0) FROM %s WHERE project_id = :project_id and parent_id is null" % self.__tablename__,
                {'project_id': self.project_id}
            ).scalar() + 1
            self.mp = [max_mp]
        else:
            max_mp = db.session.execute(
                "SELECT coalesce(max(mp[%d]), 0) FROM %s WHERE project_id = :project_id and parent_id = :parent_id" %
                (len(parent.mp) + 1, self.__tablename__),
                {'project_id': self.project_id, 'parent_id': parent.id}
            ).scalar() + 1
            self.mp = parent.mp + [max_mp]

    def subtree(self, withme=False):
        """
        Возвращает Query для всех потомков задачи. Если withme=True, то вместе с самой задачей
        :param withme:
        :return:
        """
        query = Task.query.\
            filter_by(project_id=self.project_id).\
            filter(db.text(
                'mp[1:%d] = :mp' % len(self.mp),
                bindparams=[db.bindparam('mp', value=self.mp, type_=ARRAY(db.Integer))]
            ))
        if not withme:
            query = query.filter(Task.id != self.id)
        return query

    def json(self, membership, user):
        def _serialize_date(d):
            if d is None:
                return None
            return d.strftime('%Y-%m-%dT%H:%M:%S.000+03:00')

        dct = {
            x: getattr(self, x) for x in
            ('id', 'project_id', 'mp', 'parent_id', 'status', 'subject', 'description', 'character', 'importance', 'sprint_id')
        }

        dct['created'] = _serialize_date(self.created)
        dct['deadline'] = _serialize_date(self.deadline)
        dct['description_md'] = markdown.markdown(self.description, output_format='html5')

        if self.assigned_id is None:
            dct['assignee'] = None
        else:
            dct['assignee'] = {'id': self.assigned_id, 'name': self.assignee.name}

        if self.user_id is None:
            dct['user'] = None
        else:
            dct['user'] = {'id': self.user_id, 'name': self.user.name}

        dct['allowed_statuses'] = self.allowed_statuses(user, membership)

        return json.dumps(dct, ensure_ascii=False)


class TaskHistory(db.Model):
    __tablename__ = 'task_history'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))

    task_id = db.Column(db.Integer(), db.ForeignKey('tasks.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)

    assigned_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))
    status = db.Column(Task.ENUM_STATUS, nullable=True)
    subject = db.Column(db.String(1024), nullable=True)
    description = db.Column(db.Text(), nullable=True)
    deadline = db.Column(db.DateTime(timezone=True))
    importance = db.Column(db.SmallInteger)
    character = db.Column(db.SmallInteger)

    user = db.relationship('User', backref='history', foreign_keys=[user_id])
    assignee = db.relationship('User', foreign_keys=[assigned_id])

    def text(self):
        from lma.jinja import jinja_status_label
        deeds = []
        if self.assigned_id is not None:
            deeds.append(Markup('Назначил исполнителя %s' % self.assignee.name))
        if self.status is not None:
            deeds.append('Установил статус %s' % jinja_status_label(self.status))
        if self.subject is not None:
            deeds.append('Изменил формулировку на &laquo;%s&raquo;' % Markup.escape(self.subject))
        if self.description is not None:
            deeds.append('Изменил описание: &laquo;%s&raquo;' % Markup.escape(self.description))
        if self.deadline is not None:
            deeds.append('Установил дедлайн на %s' % self.deadline.strftime('%d.%m.%Y %H:%M'))
        if self.importance is not None:
            deeds.append('Изменил важность на «%d»' % self.importance)
        if self.character:
            if self.character == 0:
                deeds.append('Убрал характер')
            else:
                deeds.append('Изменил характер на «%s %s»' % (Task.CHARACTERS[self.character]['icon'], Task.CHARACTERS[self.character]['name']))

        return Markup('; '.join(deeds))


class TaskComment(db.Model):
    __tablename__ = 'task_comments'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))

    task_id = db.Column(db.Integer(), db.ForeignKey('tasks.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    body = db.Column(db.Text, nullable=False)

    user = db.relationship('User', backref='comments')
    task = db.relationship('Task', backref='comments')

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TaskCommentsSeen(db.Model):
    __tablename__ = 'task_comments_seen'

    task_id = db.Column(
        db.Integer(),
        db.ForeignKey('tasks.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False,
        primary_key=True
    )
    user_id = db.Column(
        db.Integer(),
        db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False,
        primary_key=True
    )
    seen = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text('now()')
    )
    cnt_comments = db.Column(
        db.Integer(),
        nullable=False,
        server_default='0',
        default=0
    )

    task = db.relationship('Task', backref='seen')

    def __str__(self):
        return '<Seen task %d by user %d: %d comments>' % (self.task_id, self.user_id, self.cnt_comments)

    def __repr__(self):
        return self.__str__()
