from flask_user import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), index=True, unique=True)
    password = db.Column(db.String(128))
    google_id = db.Column(db.String(128), unique=True)
    email = db.Column(db.String(128), unique=True)
    email_confirmed_at = db.Column(db.DateTime())
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')
    stripe_customer_id = db.Column(db.String(128), unique=True)
    stripe_subscription_id = db.Column(db.String(128), unique=True)
    unix_time_end = db.Column(db.Integer)
    roles = db.relationship('Role', secondary='user_roles')

    def __repr__(self):
        return '<User {}>'.format(self.username)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)


# Define the UserRoles association table
class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))
