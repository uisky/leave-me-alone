from sqlalchemy.dialects.postgresql import ARRAY, ENUM
from .. import db
from flask_login import current_user
import json


IMPORTANCE = [
    {'id':  2, 'name': 'Очень важно', 'icon': '<span class="importance important-2">&uarr;&uarr;</span>'},
    {'id':  1, 'name': 'Важно', 'icon': '<span class="importance important-1">&uarr;</span>'},
    {'id':  0, 'name': 'Обычная', 'icon': ''},
    {'id': -1, 'name': 'Незначительно', 'icon': '<span class="importance important--1">&darr;</span>'},
    {'id': -2, 'name': 'Ничтожно', 'icon': '<span class="importance important--2">&darr;&darr;</span>'},
]

CHARACTERS = [
    {'id': 1, 'name': 'Фича', 'icon': ''},
    {'id': 2, 'name': 'Баг', 'icon': '<i class="fa fa-bug text-danger"></i>'},
    {'id': 3, 'name': 'Подумать', 'icon': '<i class="fa fa-lightbulb-o"></i>'},
]


PROJECT_TYPES = ('tree', 'list', 'stickers', 'bubbles')
ENUM_PROJECT_TYPE = ENUM(*PROJECT_TYPES, name='project_type')


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)
    type = db.Column(ENUM_PROJECT_TYPE, nullable=False, default='tree', server_default='tree')

    name = db.Column(db.String(64), nullable=False)
    has_sprints = db.Column(db.Boolean, nullable=False, server_default='false')

    tasks = db.relationship('Task', backref='project')
    members = db.relationship('ProjectMember', backref='project')

    def __repr__(self):
        return '<Project %d:%s>' % (self.id or 0, self.name)

    def url_for(self):
        return '/projects/%d/' % self.id

    def can(self, what, user=None):
        if user is None:
            user = current_user
        if what == 'members':
            return user.id == self.user_id
        return False

    def get_tasks_query(self, options):
        if self.type == 'tree':
            query = Task.query.filter_by(project_id=self.id).order_by(Task.mp)
            query = query.options(db.joinedload('user'), db.joinedload('assignee'))
        else:
            query = Task.query.filter_by(project_id=self.id)
            sort = {'created': 'created', 'deadline': 'deadline', 'importance': 'importance desc', 'custom': 'mp[1]'}
            query = query.order_by(sort.get(options.sort.data, 'created'))

        if self.has_sprints:
            if options.sprint.data is not None and options.sprint.data != 0:
                query = query.filter_by(sprint_id=options.sprint.data)
            else:
                query = query.filter(Task.sprint_id == None)
        return query


class Sprint(db.Model):
    __tablename__ = 'sprints'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    project_id = db.Column(
        db.Integer(), db.ForeignKey('projects.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=True, index=True
    )
    name = db.Column(db.String(255), nullable=False)
    start = db.Column(db.Date(), nullable=False, server_default=db.text('current_date'))
    finish = db.Column(db.Date(), nullable=False, server_default=db.text('current_date + 7'))

    project = db.relationship('Project', backref='sprints')


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

    user = db.relationship('User', backref='membership')

    # last_seen = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    # seen_tasks = int, seen_my_tasks = int  - для отслеживания количества новых тасков


TASK_STATUSES = ('open', 'progress', 'pause', 'review', 'done', 'canceled')
ENUM_TASK_STATUS = ENUM(*TASK_STATUSES, name='task_status')


class Task(db.Model):
    __tablename__ = 'tasks'

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

    status = db.Column(ENUM_TASK_STATUS, default='open')
    # Важность задачи, от -2 до +2, значения и икноки в IMPORTANCE
    importance = db.Column(db.SmallInteger, nullable=False, server_default='0', default=0)
    # Тип задачи: баг, фича, подумать
    character = db.Column(db.SmallInteger, nullable=True)
    subject = db.Column(db.String(1024), nullable=False)
    description = db.Column(db.Text(), nullable=False)
    deadline = db.Column(db.DateTime(timezone=True))

    user = db.relationship('User', backref='tasks', foreign_keys=[user_id])
    assignee = db.relationship('User', backref='assigned', foreign_keys=[assigned_id])
    children = db.relationship('Task', backref=db.backref('parent', remote_side=id))
    # parent = db.relation('Task', foreign_keys=[parent_id])
    history = db.relationship('TaskHistory', backref='task', order_by='TaskHistory.created')

    def __str__(self):
        return '<Task %d: %s - %s>' % (self.id, self.mp, self.subject)

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
            # Владелец задачи. Права ограничены здравым смыслом.
            variants = {
                'open': ('progress', 'done', 'canceled'),
                'progress': ('open', 'pause', 'review', 'done', 'canceled'),
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

        return variants[self.status]

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


class TaskJSONEncoder(json.JSONEncoder):
    @staticmethod
    def _serialize_date(d):
        if d is None:
            return None
        return d.strftime('%Y-%m-%d %H:%M:%S')

    def default(self, o):
        if type(o) is Task:
            dct = {x: getattr(o, x) for x in ('id', 'project_id', 'mp', 'parent_id', 'status', 'subject', 'description', 'character', 'importance', 'sprint_id')}

            dct['created'] = self._serialize_date(o.created)
            dct['deadline'] = self._serialize_date(o.deadline)

            if o.assigned_id is None:
                dct['assignee'] = None
            else:
                dct['assignee'] = {'id': o.assigned_id, 'username': o.assignee.name}

            if o.user_id is None:
                dct['user'] = None
            else:
                dct['user'] = {'id': o.user_id, 'username': o.user.name}

            return dct
        else:
            return super().default(o)


class TaskHistory(db.Model):
    __tablename__ = 'task_history'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))

    task_id = db.Column(db.Integer(), db.ForeignKey('tasks.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)

    assigned_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))
    status = db.Column(ENUM_TASK_STATUS, nullable=True)
    subject = db.Column(db.String(1024), nullable=True)
    description = db.Column(db.Text(), nullable=True)
    deadline = db.Column(db.DateTime(timezone=True))
    importance = db.Column(db.SmallInteger)
    character = db.Column(db.SmallInteger)

    user = db.relationship('User', backref='history', foreign_keys=[user_id])
    assignee = db.relationship('User', foreign_keys=[assigned_id])

    def text(self):
        deeds = []
        if self.assigned_id is not None:
            deeds.append('Назначил исполнителя %s' % self.assignee.link)
        if self.status is not None:
            deeds.append('Установил статус &laquo;%s&raquo' % self.status)
        if self.subject is not None:
            # @todo: А вот тут у нас HTML Injection
            deeds.append('Изменил формулировку на &laquo;%s&raquo' % self.subject)
        if self.description is not None:
            # @todo: И тут ещё одна
            deeds.append('Изменил описание: &laquo;%s&raquo' % self.subject)
        if self.deadline is not None:
            deeds.append('Установил дедлайн на %s' % self.deadline.strftime('%d.%m.%Y %H:%M'))

        return '; '.join(deeds)

    @property
    def status_label(self):
        return '<label class="label label-%s">%s</label>' % (
            Task.STATUS_CSS_CLASSES.get(self.status, 'default'),
            Task.STATUS_MEANING.get(self.status, self.status)
        )


class TaskComment(db.Model):
    __tablename__ = 'task_comments'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))

    task_id = db.Column(db.Integer(), db.ForeignKey('tasks.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)