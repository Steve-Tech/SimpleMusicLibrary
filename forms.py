from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired
from os import listdir


class LoginForm(FlaskForm):
    username = StringField('Username', [DataRequired()])
    password = PasswordField('Password', [DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log in')


class UserData(FlaskForm):
    name = StringField('Name')
    password = PasswordField('Change Password')
    theme = SelectField('Theme', [DataRequired()], choices=["Default"] + [theme.rstrip(".css") for theme in sorted(listdir("static/css/themes"))], default="Default")
    submit = SubmitField('Submit')
