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


    tasks = db.relationship('Task', backref='project', passive_deletes=True)
    members = db.relationship('ProjectMember', backref='project', passive_deletes=True)
    owner = db.relationship('User', backref='projects')

    _members_users = None

    def members_users(self, use_cache=True):
        """
        Возвращает список [ProjectMember]'ов проекта с жадно подгруженными реляциями ProjectMember.user. Кеширует его.
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

    def can(self, what, user=None):
        if user is None:
            user = current_user

        if what == 'members':
            # Управлять списком участников
            return user.id == self.user_id
        elif what == 'edit':
            # Редактировать свойства проекта
            return user.id == self.user_id
        return False

    def get_tasks_query(self, options):
        query = db.session.query(Task, TaskCommentsSeen).filter_by(project_id=self.id)

        if self.type == 'tree':
            query = query.order_by(Task.mp)
            query = query.options(db.joinedload('user'), db.joinedload('assignee'))
        else:
            sort = {'created': 'created', 'deadline': 'deadline', 'importance': 'importance desc', 'custom': 'mp[1]'}
            query = query.order_by(sort.get(options.sort.data, 'deadline'))

        query = query.outerjoin(
            TaskCommentsSeen,
            db.and_(TaskCommentsSeen.task_id == Task.id, TaskCommentsSeen.user_id == current_user.id)
        )

        if self.has_sprints:
            if options.sprint.data is not None and options.sprint.data != 0:
                query = query.filter(Task.sprint_id == options.sprint.data)
            else:
                query = query.filter(Task.sprint_id == None)

        return query

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

    project = db.relationship('Project', backref='sprints')


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


class ProjectMember(db.Model):
    __tablename__ = 'project_members'

    ROLES = ('lead', 'developer', 'tester')
    role_meanings = {
        'lead': 'Вождь',
        'developer': 'Разработчик',
        'tester': 'Тестировщик'
    }

    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, primary_key=True)
    project_id = db.Column(db.Integer(), db.ForeignKey('projects.id', ondelete='CASCADE', onupdate='CASCADE'),
                           nullable=False, primary_key=True, index=True)
    added = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    roles = db.Column(ARRAY(db.String(16), zero_indexes=True))
    karma = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    folder_id = db.Column(db.Integer, db.ForeignKey('project_folders.id', ondelete='SET NULL', onupdate='CASCADE'),
                          nullable=True)

    user = db.relationship('User', backref='membership')

    # last_seen = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    # seen_tasks = int, seen_my_tasks = int  - для отслеживания количества новых тасков

    def can(self, what, task=None):
        if what == 'subtask':
            if 'lead' in self.roles:
                return True
            if 'developer' in self.roles and task and \
                    (task.assigned_id == self.user_id or task.assigned_id == self.user_id):
                return True

        if what == 'edit':
            if task is None:
                return False
            if 'lead' in self.roles:
                return True
            if 'developer' in self.roles and task and task.user_id == self.user_id:
                return True

        return False

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


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


