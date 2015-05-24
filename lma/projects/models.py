from sqlalchemy.dialects.postgresql import ARRAY, ENUM
from .. import db
from flask_user import current_user


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)

    name = db.Column(db.String(64), nullable=False)

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
    assigned_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))

    mp = db.Column(ARRAY(db.Integer(), zero_indexes=True))
    parent_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE', onupdate='CASCADE'),
                          index=True)

    status = db.Column(ENUM_TASK_STATUS, nullable=False, default='open')
    subject = db.Column(db.String(1024), nullable=False)
    description = db.Column(db.Text(), nullable=False)
    deadline = db.Column(db.DateTime(timezone=True))

    user = db.relationship('User', backref='tasks', foreign_keys=[user_id])
    assignee = db.relationship('User', backref='assigned', foreign_keys=[assigned_id])
    parent = db.relation('Task')
    history = db.relationship('TaskHistory', backref='task', order_by='TaskHistory.created')

    def __str__(self):
        return '<Task %d: %s - %s>' % (self.id, self.mp, self.subject)

    def __repr__(self):
        return self.__str__()

    @property
    def depth(self):
        return len(self.mp) - 1

    def allowed_statuses(self, user, membership=None):
        """
        Возвращает список статусов, которые может пользователь user присвоить этой задаче
        :return:
        """
        if user.id == self.user_id or 'lead' in membership.roles:
            # Владелец задачи. Права ограничены здравым смыслом.
            variants = {
                'open': ('progress', 'done', 'canceled'),
                'progress': ('open', 'pause', 'review', 'done', 'canceled'),
                'pause': ('open', 'progress', 'canceled'),
                'review': ('open', 'done', 'canceled'),
                'done': ('open', 'review', 'canceled'),
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
