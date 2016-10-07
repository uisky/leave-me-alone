import hashlib

from flask import current_app
from flask_login import UserMixin

from lma.core import db


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer(), primary_key=True)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    email = db.Column(db.String(128), nullable=False, index=True, unique=True)
    password_hash = db.Column(db.LargeBinary(16), nullable=False)
    name = db.Column(db.String(64), nullable=False, index=True, unique=True)

    password_reset_tokens = db.relationship('PasswordResetToken', backref='user')

    def __repr__(self):
        return '<User %d:%s>' % (self.id or 0, self.name)

    @staticmethod
    def hash_password(data):
        return hashlib.md5((data + current_app.config['SECRET_KEY_PASSWORD']).encode()).digest()


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.text('now()'))
    hash = db.Column(db.String(64), nullable=False)

    def __str__(self):
        return '<PasswordResetToken(%d:%r)>' % (self.user_id, self.hash)

    def __repr__(self):
        return self.__str__()
