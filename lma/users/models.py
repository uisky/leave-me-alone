import hashlib
from .. import db, app


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    email = db.Column(db.String(128), nullable=False, index=True, unique=True)
    password_hash = db.Column(db.LargeBinary(16), nullable=False)
    name = db.Column(db.String(64), nullable=False, index=True, unique=True)

    password_reset_tokens = db.relationship('PasswordResetToken', backref='user')

    def __repr__(self):
        return '<User %d:%s>' % (0 if self.id is None else self.id, self.name)

    @property
    def link(self):
        return '<a href="/users/%d/" class="user">%s</a>' % (self.id, self.name)

    @staticmethod
    def hash_password(data):
        return hashlib.md5((data + app.config['SECRET_KEY_PASSWORD']).encode()).digest()

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    hash = db.Column(db.String(64), nullable=False)

    def __str__(self):
        return '<PasswordResetToken(%d:%r)>' % (self.user_id, self.hash)

    def __repr__(self):
        return self.__str__()
