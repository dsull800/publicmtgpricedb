from app import create_app
from flask_user import UserManager, user_manager__views
from app.models import User, Role
from app.extensions import db
import time
from flask_mail import Mail
from flask import redirect, url_for
from flask_user.signals import user_confirmed_email, user_logged_in


class MixedUserManager(UserManager, user_manager__views.UserManager__Views):
    def unauthorized_view(self):
        return redirect(url_for('main.unauthorized'))


server = create_app()

user_manager = MixedUserManager(server, db, User)

mail = Mail(server)


@user_confirmed_email.connect_via(server)
def _after_registration_hook(sender, user, **extra):
    user.roles = [Role.query.filter_by(name='unsubscribed').one()]
    db.session.add(user)
    db.session.commit()


@user_logged_in.connect_via(server)
def _after_login_hook(sender, user, **extra):
    if isinstance(user.unix_time_end, int) and user.unix_time_end < time.time():
        user.roles = [Role.query.filter_by(name='unsubscribed').one()]
        db.session.add(user)
        db.session.commit()


with server.app_context():
    try:
        from app.extensions import db

        db.session.add(Role(name='subscribed'))
        db.session.add(Role(name='unsubscribed'))
        db.session.commit()

    except Exception as e:
        print(e)

def run_app():
    return server

