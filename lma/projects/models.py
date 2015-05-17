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
        return '<Project %d:%s>' % (0 if self.id is None else self.id, self.name)

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


ENUM_TASK_STATUS = ENUM('open', 'progress', 'pause', 'review', 'done', 'canceled', name='task_status')


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))

    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)
    project_id = db.Column(db.Integer(), db.ForeignKey('projects.id', ondelete='CASCADE', onupdate='CASCADE'),
                           nullable=False, index=True)
    assigned_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))

    mp = db.Column(ARRAY(db.SmallInteger(), zero_indexes=True))
    parent_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE', onupdate='CASCADE'),
                          index=True)

    status = db.Column(ENUM_TASK_STATUS, nullable=False, default='open')
    subject = db.Column(db.String(1024), nullable=False)
    description = db.Column(db.Text(), nullable=False)
    deadline = db.Column(db.DateTime(timezone=True))

    user = db.relationship('User', backref='tasks', foreign_keys=[user_id])
    assignee = db.relationship('User', backref='assigned', foreign_keys=[assigned_id])

    def engender(self):
        """
        Возвращает своего потомка, подготовив ему project_id, parent_id и mp
        :return:
        """
        kid = self.__class__(project_id=self.project_id, parent_id=self.id)
        kid.mp = self.mp
        maxp = db.session\
            .query('SELECT max(mp[:pos]) FROM %s WHERE parent_id = :me' % self.__tablename__)\
            .scalar({'pos': len(self.mp), 'me': self.ud})
        kid.mp.append(maxp)

        return kid

