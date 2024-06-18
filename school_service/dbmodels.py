from datetime import date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from school_service import db_sqla, login


@login.user_loader
def load_user(id):
    return db_sqla.session.get(User, int(id))


class User(UserMixin, db_sqla.Model):
    __tablename__ = 'users'
    id = db_sqla.Column(db_sqla.Integer, primary_key=True)
    login = db_sqla.Column(db_sqla.String(80), unique=True)
    password = db_sqla.Column(db_sqla.String(100), unique=True)

    def __init__(self, username):
        self.login = username

    def __repr__(self):
        return '<User {}>'.format(self.login)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Class(db_sqla.Model):
    __tablename__ = 'Classes'
    id = db_sqla.Column(db_sqla.Integer, primary_key=True)
    name_class = db_sqla.Column(db_sqla.String(80), unique=True)
    man_class = db_sqla.Column(db_sqla.String(100))
    count_ill = db_sqla.Column(db_sqla.Integer)
    count_class = db_sqla.Column(db_sqla.Integer)
    proc_ill = db_sqla.Column(db_sqla.Integer)
    closed = db_sqla.Column(db_sqla.Boolean)
    date_closed = db_sqla.Column(db_sqla.Date)
    date_open = db_sqla.Column(db_sqla.Date)
    date = db_sqla.Column(db_sqla.Date)

    def __init__(self, name_class, man_class, count_class):
        self.name_class = name_class
        self.man_class = man_class
        self.count_ill = 0
        self.count_class = count_class
        self.proc_ill = int(self.count_ill) * 100 / int(self.count_class)
        self.closed = False
        self.date_closed = None
        self.date_open = None
        self.date = date.today()

    def __repr__(self):
        return '<Class {}>'.format(self.name_class)


class DataSend(db_sqla.Model):
    __tablename__ = 'DataSends'
    id = db_sqla.Column(db_sqla.Integer, primary_key=True)
    date_send = db_sqla.Column(db_sqla.Date, unique=True)
    count_all_ill = db_sqla.Column(db_sqla.Integer)
    count_all = db_sqla.Column(db_sqla.Integer)
    count_class_closed = db_sqla.Column(db_sqla.Integer)
    count_ill_closed = db_sqla.Column(db_sqla.Integer)
    count_all_closed = db_sqla.Column(db_sqla.Integer)
    sending = db_sqla.Column(db_sqla.Boolean)

    def __init__(self, date_send, count_all_ill, count_all, count_class_closed, count_ill_closed, count_all_closed):
        self.date_send = date_send
        self.count_all_ill = count_all_ill
        self.count_all = count_all
        self.count_class_closed = count_class_closed
        self.count_ill_closed = count_ill_closed
        self.count_all_closed = count_all_closed
        self.sending = False

    def __repr__(self):
        return '<Sending data from {}>'.format(self.date_send)


class Dish(db_sqla.Model):
    id = db_sqla.Column(db_sqla.Integer, primary_key=True)
    title = db_sqla.Column(db_sqla.String(100))
    recipe = db_sqla.Column(db_sqla.Integer)
    out_gramm = db_sqla.Column(db_sqla.Integer)
    price = db_sqla.Column(db_sqla.Integer)
    calories = db_sqla.Column(db_sqla.Integer)
    protein = db_sqla.Column(db_sqla.Integer)
    fats = db_sqla.Column(db_sqla.Integer)
    carb = db_sqla.Column(db_sqla.Integer)
    menus = db_sqla.relationship('Menu', backref='dish', lazy='dynamic')

    def __init__(self, title, recipe, out_gramm, price, calories, protein, fats, carb):
        self.title = title
        self.recipe = recipe
        self.out_gramm = out_gramm
        self.price = price
        self.calories = calories
        self.protein = protein
        self.fats = fats
        self.carb = carb

    def __repr__(self):
        return '<Dish {}>'.format(self.title)


class Menu(db_sqla.Model):
    id = db_sqla.Column(db_sqla.Integer, primary_key=True)
    date_menu = db_sqla.Column(db_sqla.Date)
    type = db_sqla.Column(db_sqla.String(80))
    category = db_sqla.Column(db_sqla.String(80))
    dish_id = db_sqla.Column(db_sqla.Integer, db_sqla.ForeignKey('dish.id'))

    def __init__(self, date_menu, type_menu, category, dish_id):
        self.date_menu = date_menu
        self.type = type_menu
        self.category = category
        self.dish_id = dish_id

    def __repr__(self):
        return '<Menu {}>'.format(self.date_menu)
