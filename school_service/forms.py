from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Ваш пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня', default=False)
    submit = SubmitField('Войти')
