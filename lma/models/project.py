from collections import OrderedDict
from datetime import datetime
import pytz

from sqlalchemy.dialects.postgresql import ARRAY, ENUM
from flask_login import current_user

from lma.models.task import Task, TaskCommentsSeen
from lma.models import User
from lma.core import db


class Project(db.Model):
    __tablename__ = 'projects'

    TYPES = OrderedDict([('tree', 'Дерево'), ('list', 'Список')])
    ACCESS_LEVELS = ('owner', 'lead', 'developer', 'watcher', 'bylink', 'any')
    ENUM_ACCESS_LEVEL = ENUM(*ACCESS_LEVELS, name='access_level')

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)
    type = db.Column(ENUM(*TYPES.keys(), name='project_type'), nullable=False, default='tree', server_default='tree')

    name = db.Column(db.String(64), nullable=False)
    has_sprints = db.Column(db.Boolean, nullable=False, server_default='false')
    intro = db.Column(db.Text)

    ac_link_code = db.Column(db.String(64), index=True, unique=True)
    ac_read = db.Column(ENUM_ACCESS_LEVEL, nullable=False, default='watcher', server_default='watcher')
    ac_comment = db.Column(ENUM_ACCESS_LEVEL, nullable=False, default='watcher', server_default='watcher')

    owner = db.relationship('User', backref='projects')
    sprints = db.relationship('Sprint', backref='project', order_by='Sprint.sort', passive_deletes=True)
    members = db.relationship('ProjectMember', back_populates='project', passive_deletes=True)
    tasks = db.relationship('Task', backref='project', passive_deletes=True)

    _members_users = None

    def members_users(self, use_cache=True):
        """
        Возвращает список [ProjectMember]'ов проекта с жадно подгруженными реляциями ProjectMember.user.
        Кеширует его в self._members_users.
        :return: list
        """
        if self._members_users is None or not use_cache:
            self._members_users = ProjectMember.query\
                .outerjoin(User)\
                .filter(ProjectMember.project_id == self.id)\
                .options(db.contains_eager(ProjectMember.user))\
                .order_by(User.name).all()

        return self._members_users

    def __repr__(self):
        return '<Project %d:%s>' % (self.id or 0, self.name)

    def get_tasks_query(self, options):
        raise NotImplementedError

    @property
    def age(self):
        """Возвращает возраст проекта в сутках"""
        return pytz.utc.localize(datetime.now()) - self.created


class Sprint(db.Model):
    __tablename__ = 'sprints'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    project_id = db.Column(
        db.Integer(), db.ForeignKey('projects.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=True, index=True
    )
    sort = db.Column(db.SmallInteger(), nullable=False, default=0, server_default='0')
    name = db.Column(db.String(255), nullable=False)


class ProjectFolder(db.Model):
    __tablename__ = 'project_folders'

    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    in_menu = db.Column(db.Boolean, nullable=False, default=True, server_default='t')
    bgcolor = db.Column(db.String(6), nullable=True)

    def __repr__(self):
        return '<Folder #%d: %d/%s>' % (self.id, self.user_id, self.name)


class MembershipBase:
    ROLES = ('lead', 'developer', 'tester')
    role_meanings = {
        'lead': 'Вождь',
        'developer': 'Разработчик',
        'tester': 'Тестировщик'
    }

    def can(self, what, *args):
        raise NotImplementedError


class ProjectMember(MembershipBase, db.Model):
    __tablename__ = 'project_members'

    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, primary_key=True)
    project_id = db.Column(db.Integer(), db.ForeignKey('projects.id', ondelete='CASCADE', onupdate='CASCADE'),
                           nullable=False, primary_key=True, index=True)
    added = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    roles = db.Column(ARRAY(db.String(16), zero_indexes=True))
    karma = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    folder_id = db.Column(db.Integer, db.ForeignKey('project_folders.id', ondelete='SET NULL', onupdate='CASCADE'),
                          nullable=True)

    project = db.relationship('Project', back_populates='members')
    user = db.relationship('User', backref='membership')

    def can(self, what, *args):
        """
        Решает, можно ли совершать действие what:

          project.edit
          project.members
          project.task-level-0

          task.edit, task
          task.delete, task
          task.subtask, task
          task.comment, task
          task.set-status, task - можно ли изменить статус задачи
          task.set-status, task, status - можно ли изменить статус задачи на status
          task.sprint, task - можно ли перенести задачу в другую веху
          task.chparent, task - можно ли задаче task сменить родителя на кого-нибудь в этом проекте
          task.chparent, task, parent - можно ли задаче task сменить родителя на parent (parent = None: поставить в корень)

        :param what: str
        :return: bool
        """
        patrimony, action = what.split('.')

        if patrimony == 'project':
            if action == 'edit':
                return self.project.user_id == self.user_id
            elif action == 'members':
                return self.project.user_id == self.user_id
            elif action == 'task-level-0':
                return 'lead' in self.roles
            else:
                raise ValueError('Unknown ProjectMember.can() permission requested: %r' % what)

        elif patrimony == 'task':
            task = args[0]
            if action == 'edit':
                if task.user_id == self.user_id or 'lead' in self.roles:
                    return True
            elif action == 'delete':
                return self.can('task.edit', task)
            elif action == 'subtask':
                if 'lead' in self.roles:
                    return True
                if 'developer' in self.roles and (task.user_id == self.user_id or task.assigned_id == self.user_id):
                    return True
            elif action == 'comment':
                return self.roles != []
            elif action == 'set-status':
                if len(args) >= 2:
                    status = args[1]
                    return status in task.allowed_statuses(self.user, self)
                else:
                    return task.allowed_statuses(self.user, self)
            elif action == 'sprint':

                return self.project.has_sprints and task.parent_id is None and 'lead' in self.roles
            elif action == 'chparent':
                if task.user_id != self.user_id and 'lead' not in self.roles:
                    return False

                if len(args) == 1:
                    return self.can('task.edit', task)

                parent = args[1]
            else:
                raise ValueError('Unknown ProjectMember.can() permission requested: %r' % what)

        else:
            raise ValueError('Unknown ProjectMember.can() permission requested: %r' % what)

        return False

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ProjectNotMember(MembershipBase):
    def __init__(self, project, user):
        self.project = project
        self.user = user

    def can(self, what, *args):
        return False


class KarmaRecord(db.Model):
    __tablename__ = 'karma_records'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    project_id = db.Column(db.Integer(), db.ForeignKey('projects.id', ondelete='CASCADE', onupdate='CASCADE'),
                           nullable=False, index=True)
    from_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)
    to_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False, index=True)
    comment = db.Column(db.Text, nullable=False)
    value = db.Column(db.Integer, nullable=False, default=0, server_default='0')

    from_user = db.relationship('User', backref='karma_given', foreign_keys=[from_id])
    to_user = db.relationship('User', backref='karma_received', foreign_keys=[to_id])


