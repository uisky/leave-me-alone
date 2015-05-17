from sqlalchemy.dialects.postgresql import ARRAY
from .. import db
from flask_user import current_user


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False, index=True)

    name = db.Column(db.String(64), nullable=False)

    # tasks = db.relationship('Task', backref='project')
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

