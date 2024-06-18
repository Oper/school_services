import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import smtplib
import time
from datetime import date
from threading import Thread
from sqlalchemy import exc

from school_service.config import Config

app = Flask(__name__)
app.config.from_object(Config)
db_sqla = SQLAlchemy(app)
migrate = Migrate(app, db_sqla)
login = LoginManager(app)
login.login_view = 'admin_login'

if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/school_service.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('School Service startup')

from school_service import routes, dbmodels
from school_service.dbmodels import DataSend, Class


def sendMail():
    app.logger.info('sendMail method run in thread')
    while True:
        current_time = time.localtime()
        date_current = date.today()
        with app.app_context():
            blocks = Class.query.all()
        count_all_ill = 0
        count_all = 0
        count_class_closed = 0
        count_ill_closed = 0
        count_all_closed = 0

        for v in blocks:
            count_all_ill += v.count_ill
            count_all += v.count_class
            if v.closed == 1:
                count_class_closed += 1
                count_ill_closed += v.count_ill
                count_all_closed += v.count_class
        with app.app_context():
            sending_mail_date = DataSend.query.filter_by(date_send=date_current).first()
        if sending_mail_date is None and current_time.tm_hour == 9 and (30 < current_time.tm_min < 50):
            try:
                data_send = DataSend(date_current, count_all_ill, count_all, count_class_closed, count_ill_closed,
                                     count_all_closed)
                db_sqla.session.add(data_send)
                db_sqla.session.commit()
                app.logger.info('DataSend add(new date)')
            except exc.SQLAlchemyError as error:
                db_sqla.session.rollback()
                app.logger.exception(error)
        elif current_time.tm_hour == 9 and (30 < current_time.tm_min < 50):
            try:
                data_send = DataSend.query.filter_by(date_send=date_current).first()
                data_send.count_all_ill = count_all_ill
                data_send.count_all_closed = count_all_closed
                db_sqla.session.add(data_send)
                db_sqla.session.commit()
                app.logger.info('DataSend update')
            except exc.SQLAlchemyError as error:
                db_sqla.session.rollback()
                app.logger.exception(error)

        def sending(count_all_ill=0, count_class_closed=0, count_ill_closed=0, count_all_closed=0):
            server = smtplib.SMTP_SSL('smtp.yandex.ru:465')
            server.login('sosh1emva@yandex.ru', 'klvmvnsodshodavu')

            cure_date = date.today().isoformat()
            cure_time = str(time.localtime().tm_hour).rjust(2, '0') + ':' + str(time.localtime().tm_min).rjust(2, '0')
            from_addr = 'sosh1emva@yandex.ru'
            to_addr = 'my@vbaykov.ru'
            subject = 'Мониторинг на ' + cure_date + ' время - ' + cure_time + '.'
            body_text = 'Здравствуйте!\nКоличество болеющих обучающихся ВСЕГО: ' + str(
                count_all_ill) + '\nКоличество классов (групп), закрытых на карантин : ' + str(
                count_class_closed) + '\nКоличество болеющих в закрытых классах (группах): ' + str(
                count_ill_closed) + '\nКоличество обучающихся всего в закрытых классах (группах): ' + str(
                count_all_closed)

            letter = "\r\n".join((
                "From: %s" % from_addr,
                "To: %s" % to_addr,
                "Subject: %s" % subject,
                "",
                body_text
            ))
            letter = letter.encode("UTF-8")
            try:
                server.sendmail(from_addr, to_addr, letter)
                server.quit()
                return cure_date
            except:
                app.logger.error('Error sending email!')
            return None

        with app.app_context():
            dbdata_sending = DataSend.query.filter_by(date_send=date_current).first()

        current_date = date.today().isoweekday()

        if dbdata_sending is not None and not dbdata_sending.sending and current_time.tm_hour == 9 and (
                50 < current_time.tm_min < 59) and (0 < current_date < 6):
            date_sending_email = sending(dbdata_sending.count_all_ill, dbdata_sending.count_class_closed,
                                         dbdata_sending.count_ill_closed,
                                         dbdata_sending.count_all_closed)
            app.logger.info('The email has been sent' + str(date_sending_email) + '!')
            try:
                with app.app_context():
                    tmp = DataSend.query.filter_by(date_send=date_current).first()
                tmp.sending = True
                db_sqla.session.add(tmp)
                db_sqla.session.commit()
            except exc.SQLAlchemyError as error_update:
                db_sqla.session.rollback()
                app.logger.exception(error_update)
        else:
            app.logger.info('The email has already been sent!')
        time.sleep(60)


thread = Thread(target=sendMail, daemon=True)
thread.start()
