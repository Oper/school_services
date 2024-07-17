import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'xxxx'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'database.db')
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.yandex.ru:465'
    MAIL_LOGIN = os.environ.get('MAIL_LOGIN') or 'login'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'password'
    MAIL_FROM = os.environ.get('MAIL_FROM') or 'from_mail'
    MAIL_TO = os.environ.get('MAIL_TO') or 'to_mail'
    BOT_TOKEN = os.environ.get('BOT_TOKEN') or 'your_bot_token'
    BOT_ADMIN = os.environ.get('BOT_ADMIN') or 'your_telegram_id'
