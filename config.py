import os


def get_sqlite_uri():
    # basedir = os.path.abspath(os.path.dirname(__file__))
    # db_name = os.environ['DATABASE_URL'].split('/')[-1]
    # return f'sqlite:///{basedir}/{db_name}'
    return os.environ['DATABASE_URL']


class BaseConfig:
    SQLALCHEMY_DATABASE_URI = get_sqlite_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ['SECRET_KEY']
    # Flask-Mail SMTP server settings
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = os.environ['MAIL_USERNAME']
    MAIL_PASSWORD = os.environ['MAIL_PASSWORD']
    MAIL_DEFAULT_SENDER = os.environ['MAIL_DEFAULT_SENDER']
    # Flask-User settings
    USER_APP_NAME = "MTGStocksClone"      # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = True       # Enable email authentication
    USER_ENABLE_USERNAME = False   # Disable username authentication
    USER_EMAIL_SENDER_NAME = USER_APP_NAME
    USER_EMAIL_SENDER_EMAIL = os.environ['USER_EMAIL_SENDER_EMAIL']
