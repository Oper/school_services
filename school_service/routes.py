import datetime
from datetime import date, timedelta
from logging import getLogger
from urllib.parse import urlsplit

import sqlalchemy as sa
from flask import render_template, request, url_for, redirect, flash
from flask_login import logout_user, login_user, current_user, login_required
from sqlalchemy import exc, and_

from school_service import db_sqla, app
from school_service.dbmodels import User, Class, DataSend, Menu, Dish
from school_service.forms import LoginForm

loger = getLogger(__name__)


@app.before_request
def before_request():
    pass


@app.route('/')
def main():
    return render_template('index.html')


@app.route('/admin_login', methods=['POST', 'GET'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db_sqla.session.scalar(
            sa.select(User).where(User.login == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Неверный логин или пароль!')
            return redirect(url_for('admin_login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('admin')
        return redirect(next_page)
    return render_template('admin_login.html', title='Введите данные', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('monitoring'))


@app.route('/admin', methods=['POST', 'GET'])
@login_required
def admin():
    if not current_user.is_authenticated:
        return redirect(url_for('admin_login'))
    name_class = request.args.get('name_class')
    if name_class:
        try:
            tmp = db_sqla.session.query(Class).filter_by(name_class=name_class).first()
            db_sqla.session.delete(tmp)
            db_sqla.session.commit()
        except exc.SQLAlchemyError as error_del:
            db_sqla.session.rollback()
            loger.error(error_del)
            flash('Ошибка удаления', category='alert-warning')
            return redirect(url_for('admin'))
        flash('Класс удален', category='alert-success')
        return redirect(url_for('admin'))

    blocks = Class.query.all()
    json_data = {}
    count_id = 1
    for raw in blocks:
        if raw.name_class not in json_data:
            json_data[raw.name_class] = []
        json_data[raw.name_class].append({
            'id': count_id,
            'man_class': raw.man_class,
            'count_ill': raw.count_ill,
            'count_class': raw.count_class,
            'proc_ill': raw.proc_ill,
            'closed': raw.closed,
            'date_closed': raw.date_closed,
            'date_open': raw.date_open,
            'date': raw.date
        })
        count_id += 1

    if request.method == 'POST':
        name_class = request.form['name_class']
        man_class = request.form['man_class']
        count_class = request.form['count_class']

        if int(count_class) > 0 and len(name_class) >= 2:
            class_bd = Class.query.filter_by(name_class=name_class).first()
            if class_bd:
                class_bd.man_class = man_class
                class_bd.count_class = count_class
                try:
                    db_sqla.session.add(class_bd)
                    db_sqla.session.commit()
                except exc.SQLAlchemyError as error_update_class:
                    db_sqla.session.rollback()
                    loger.error(error_update_class)
                flash('Класс - ' + name_class + ' изменён!', category='alert-success')
                return redirect(url_for('admin'))
            try:
                cls = Class(name_class, man_class, count_class)
                db_sqla.session.add(cls)
                db_sqla.session.commit()
            except exc.SQLAlchemyError as error:
                db_sqla.session.rollback()
                loger.error(error)
            flash('Класс добавлен', category='alert-success')
            return redirect(url_for('admin'))
        else:
            flash('Ошибка добавления класса', category='alert-warning')
            return redirect(url_for('admin'))

    return render_template('admin.html', json_data=json_data)


@app.route('/monitoring/', methods=['POST', 'GET'])
def monitoring():
    date_current = date.today()
    if request.method == 'POST':
        name_class = request.form['name_class']
        count_ill = request.form['count_ill']

        count_class_bd = Class.query.filter_by(name_class=name_class).first()
        proc_ill = round(int(count_ill) * 100 / count_class_bd.count_class)
        date_closed = date.today() + timedelta(days=1)
        date_open = date.today() + timedelta(days=8)

        closed = False
        if proc_ill > 20:
            closed = True
        else:
            date_closed = None
            date_open = None
        try:
            tmp = db_sqla.session.query(Class).filter_by(name_class=name_class).first()
            tmp.count_ill = count_ill
            tmp.proc_ill = proc_ill
            tmp.closed = closed
            tmp.date_closed = date_closed
            tmp.date_open = date_open
            tmp.date = date.today()
            db_sqla.session.add(tmp)
            db_sqla.session.commit()
        except exc.SQLAlchemyError as error_update_class:
            db_sqla.session.rollback()
            loger.exception(error_update_class)

        if closed:
            flash('Данные получены. ВНИМАНИЕ! Класс будет закрыт!', category='alert-danger')
            return redirect(url_for('monitoring'))
        else:
            flash('Данные получены.', category='alert-info')
            return redirect(url_for('monitoring'))

    blocks = Class.query.all()
    json_data = {}
    for count_id, raw in enumerate(blocks, start=1):
        if raw.name_class not in json_data:
            json_data[raw.name_class] = []
        json_data[raw.name_class].append({
            'id': count_id,
            'man_class': raw.man_class,
            'count_ill': raw.count_ill,
            'count_class': raw.count_class,
            'proc_ill': raw.proc_ill,
            'closed': raw.closed,
            'date_closed': raw.date_closed,
            'date_open': raw.date_open,
            'date': raw.date
        })

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
    try:
        proc_all = round(count_all_ill * 100 / count_all)
    except ZeroDivisionError:
        loger.error('Деление на ноль, т.к. не заполнены классы')
        return render_template('404.html')

    sending_mail_date = DataSend.query.filter_by(date_send=date_current).first()

    send_status = None
    if sending_mail_date is not None:
        send_status = sending_mail_date.sending
    current_date = date.today().isoformat()
    status = ('Данные на ' + str(
        current_date) + ' отправлены в Cектор') if send_status else 'Данные не отправлены в сектор'

    return render_template('monitoring.html', json_data=json_data, date_current=date_current,
                           count_all_ill=count_all_ill, count_all=count_all, proc_all=proc_all, send_status=status)


@app.route('/analysis')
def analysis():
    json_data = {}
    labels = []
    data = []
    with app.app_context():
        tmp = DataSend.query.order_by(DataSend.id.desc()).limit(30).all()
        tmp.reverse()
    for d in tmp:
        labels.append(d.date_send)
        data.append(d.count_all_ill)
    for count_id, i in enumerate(tmp, start=1):
        if i.date_send not in json_data:
            json_data[i.date_send] = []
        json_data[i.date_send].append({
            'id': count_id,
            'count_all_ill': i.count_all_ill,
            'count_class_closed': i.count_class_closed
        })
    return render_template('analysis.html', json_data=json_data, labels=labels, data=data)


@app.route('/nutrition')
def nutritions():
    menu_list = []
    date_todey = date.today()
    date_left = date_todey - timedelta(days=2)
    date_right = date_todey + timedelta(days=3)
    with app.app_context():
        tmp = Menu.query.filter(and_(Menu.date_menu >= date_left, Menu.date_menu <= date_right)).order_by(
            Menu.date_menu.desc()).all()
        tmp.reverse()
    for _ in tmp:
        if _.date_menu not in menu_list:
            menu_list.append(_.date_menu)

    title = 'Питание МБОУ "СОШ№1" г.Емвы'

    return render_template('nutritions.html', title=title, menu_list=menu_list, date_todey=date_todey)


@app.route('/nutrition/<date_menu>')
def nutrition(date_menu):
    title = 'Меню на ' + str(date_menu)
    menu = {}

    with app.app_context():
        tmp = Menu.query.filter(Menu.date_menu == date_menu).order_by(Menu.category.desc(), Menu.type.desc()).all()
        tmp.reverse()
    if tmp:
        for _ in tmp:
            if _.category not in menu:
                menu[_.category] = {}
            if _.type not in menu[_.category]:
                menu[_.category][_.type] = []
            with app.app_context():
                dish = Dish.query.filter(Dish.id == _.dish_id)
            if dish:
                for i in dish:
                    menu[_.category][_.type].append({
                        'dish_name': i.title,
                        'out_gramm': i.out_gramm,
                        'calories': i.calories,
                        'price': i.price,
                    })

    return render_template('nutrition.html', title=title, menu=menu)


@app.route('/admin-tehnolog', methods=['POST', 'GET'])
def admin_tehnolog():
    if not current_user.is_authenticated:
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        form = request.form.get('type_form')
        if form == 'dish':
            dish_title = request.form.get('dish_title')
            dish_recipe = request.form.get('dish_recipe')
            dish_out = request.form.get('dish_out')
            dish_calories = request.form.get('dish_calories')
            dish_protein = request.form.get('dish_protein')
            dish_fats = request.form.get('dish_fats')
            dish_carb = request.form.get('dish_carb')
            dish_price = request.form.get('dish_price')
            if len(dish_title) > 2:
                with app.app_context():
                    tmp_dish = Dish.query.filter_by(title=dish_title).first()
                if tmp_dish:
                    # TODO: Реализовать изменение существующего dish
                    pass
                else:
                    try:
                        new_dish = Dish(dish_title, dish_recipe, dish_out, dish_price, dish_calories, dish_protein,
                                        dish_fats, dish_carb)
                        db_sqla.session.add(new_dish)
                        db_sqla.session.commit()
                    except exc.SQLAlchemyError as error:
                        db_sqla.session.rollback()
                        loger.error(error)
                        flash('Блюдо -' + str(dish_title) + ', не добавлено', category='alert-danger')
                        return redirect(url_for('admin_tehnolog'))
                    flash('Блюдо - ' + str(dish_title) + ', добавлено', category='alert-info')
                    return redirect(url_for('admin_tehnolog'))
        elif form == 'menu':
            menu_date = datetime.datetime.strptime(request.form.get('menu_date'), '%Y-%m-%d')
            menu_type = request.form.get('menu_type')
            menu_category = request.form.get('menu_category')
            menu_dish = request.form.get('menu_dish')
            print(menu_date, menu_type, menu_category, menu_dish)
            with app.app_context():
                tmp_menu = Menu.query.filter(and_(Menu.date_menu == menu_date, Menu.type == menu_type)).first()
            if tmp_menu:
                print(tmp_menu)
                flash('Меню на ' + menu_date.isoformat() + ', изменено!', category='alert-info')
                return redirect(url_for('admin_tehnolog'))
            else:
                try:
                    new_menu = Menu(menu_date, menu_type, menu_category, int(menu_dish))
                    db_sqla.session.add(new_menu)
                    db_sqla.session.commit()
                except exc.SQLAlchemyError as error:
                    db_sqla.session.rollback()
                    loger.error(error)
                    flash('Меню на ' + menu_date.isoformat() + ', не добавлено', category='alert-danger')
                    return redirect(url_for('admin_tehnolog'))
                flash('Меню на ' + menu_date.isoformat() + ', добавлено', category='alert-info')
                return redirect(url_for('admin_tehnolog'))

    title = 'Панель управления технолога'
    date_todey = date.today()
    date_left = date_todey - timedelta(days=1)
    date_right = date_todey + timedelta(days=3)
    dishes = {}
    menus = {}
    with app.app_context():
        tmp_dishes = Dish.query.order_by(Dish.id.desc()).all()
        tmp_dishes.reverse()
    for _ in tmp_dishes:
        if _.title not in dishes:
            dishes[_.title] = []
        dishes[_.title].append({
            'id': _.id,
            'recipe': _.recipe,
            'out_gramm': _.out_gramm,
            'calories': _.calories,
            'protein': _.protein,
            'fats': _.fats,
            'carb': _.carb,
            'price': _.price,
        })
    with app.app_context():
        tmp_menus = Menu.query.filter(and_(Menu.date_menu >= date_left, Menu.date_menu <= date_right)).order_by(
            Menu.date_menu.desc(), Menu.type.desc(), Menu.category.desc()).all()
        tmp_menus.reverse()
    if tmp_menus:
        for _ in tmp_menus:
            if _.date_menu not in menus:
                menus[_.date_menu] = {}
            if _.category not in menus[_.date_menu]:
                menus[_.date_menu][_.category] = {}
            if _.type not in menus[_.date_menu][_.category]:
                menus[_.date_menu][_.category][_.type] = []
            with app.app_context():
                dish = Dish.query.filter_by(id=_.dish_id).first()
            menus[_.date_menu][_.category][_.type].append({
                'dish_id': dish.id,
                'dish_title': dish.title,
                'dish_out': dish.out_gramm,
                'dish_recipe': dish.recipe,
                'dish_calories': dish.calories,
                'dish_protein': dish.protein,
                'dish_fats': dish.fats,
                'dish_carb': dish.carb,
                'dish_price': dish.price
            })

    return render_template('admin-nutritions.html', title=title, dishes=dishes, menus=menus, date_todey=date_todey)


@app.errorhandler(404)
def pageNotFound(error):
    return render_template('404.html')


@app.teardown_appcontext
def close(error):
    pass
