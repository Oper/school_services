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
import telebot
from telebot import types

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
            server = smtplib.SMTP_SSL(app.config['MAIL_SERVER'])
            server.login(app.config['MAIL_LOGIN'], app.config['MAIL_PASSWORD'])

            cure_date = date.today().isoformat()
            cure_time = str(time.localtime().tm_hour).rjust(2, '0') + ':' + str(time.localtime().tm_min).rjust(2, '0')
            from_addr = app.config['MAIL_FROM']
            to_addr = app.config['MAIL_TO']
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


def start_bot():
    classes_data = {}
    with app.app_context():
        class_list = Class.query.all()
    name_class_list = []
    for _ in class_list:
        name_class_list.append(_.name_class)
    bot = telebot.TeleBot(app.config['BOT_TOKEN'])

    @bot.message_handler(commands=['start'])
    def start_message(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_update_main = types.KeyboardButton("Передать данные")
        markup.add(button_update_main)
        msg = bot.send_message(message.chat.id, 'Добро пожаловать! Для отправки данных по болеющим, нажмите <Передать данные>', reply_markup=markup)
        bot.register_next_step_handler(msg, on_start)

    def on_start(message):
        buttons = []
        keyboards = types.ReplyKeyboardMarkup(row_width=3)
        for _ in class_list:
            buttons.append(types.KeyboardButton(_.name_class))
        keyboards.add(*buttons)
        try:
            chat_id = message.chat.id
            command = message.text
            if command != 'Передать данные':
                raise Exception('Команда не поддерживается!')
            msg = bot.send_message(message.chat.id, 'Укажите класс', reply_markup=keyboards)
            bot.register_next_step_handler(msg, set_class_for_update)
        except Exception as error:
            app.logger.error(error)
            bot.reply_to(message, 'Команда не поддерживается!')
            bot.send_message(chat_id, 'Запустить снова /start')

    def set_class_for_update(message):
        try:
            chat_id = message.chat.id
            name_class = message.text
            if name_class not in name_class_list:
                raise Exception('Нет такого класса или не выбран класс')
            classes_data[chat_id] = name_class
            keyboards = types.ReplyKeyboardMarkup(row_width=3)
            buttons_count_ill = [str(_) for _ in range(0, 11)]
            keyboards.add(*buttons_count_ill)
            msg = bot.send_message(chat_id, 'Укажите количество болеющих', reply_markup=keyboards)
            bot.register_next_step_handler(msg, set_count_ill)
        except Exception as error:
            bot.reply_to(message, 'Нет такого класса или не выбран класс')
            app.logger.error(error)

    def update_count_ill(name_class, count_ill):
        print('Пытаюсь получить Класс из базы')
        with app.app_context():
            tmp = Class.query.filter_by(name_class=name_class).first()
        print('Получил данные по Классу из базы', tmp.name_class)
        try:
            tmp.count_ill = int(count_ill)
            tmp.date = date.today()
            db_sqla.session.add(tmp)
            db_sqla.session.commit()
        except exc as error:
            db_sqla.session.rollback()
            app.logger.error(error)

    def set_count_ill(message):
        try:
            chat_id = message.chat.id
            count_ill = message.text
            name_class = classes_data[chat_id]
            print(name_class, count_ill)
            bot.send_message(chat_id, 'Спасибо, данные получены')
            update_count_ill(name_class, int(count_ill))
        except Exception as error:
            db_sqla.session.rollback()
            bot.reply_to(message, 'Данные не обновлены!')
            app.logger.error(error)

    bot.infinity_polling(logger_level=logging.DEBUG)


thread = Thread(target=sendMail, daemon=True)
thread.start()
thread_bot = Thread(target=start_bot, daemon=True)
thread_bot.start()
