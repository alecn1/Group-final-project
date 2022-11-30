#from flask import Flask, render_template, url_for, redirect, flash
import flask
import requests
import json
import os
from dotenv import load_dotenv, find_dotenv
from random import randrange
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField, SubmitField, SelectField
from wtforms.validators import InputRequired, Length, ValidationError, NumberRange
from wtforms.widgets import TextArea
from flask_bcrypt import Bcrypt

load_dotenv(find_dotenv())

app = flask.Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SECRET_KEY'] = 'aSecret'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return Person.query.get(int(user_id))

class Person(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user_username = Person.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError (
                "That username exists. Please select another username."
            )

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")

    def validate_username(self, username):
        existing_user_username = Person.query.filter_by(username=username.data).first()
        if not existing_user_username:
            raise ValidationError (
                "That username does not exist. Please try again."
            )


def get_weather():
    WEATHER_API_BASE_URL = f'http://api.openweathermap.org/data/2.5/weather'

    response = requests.get(
        WEATHER_API_BASE_URL,
        params={
            'q': 'Austin',
            'units': 'imperial',
            'appid': os.getenv('OPEN_WEATHER_API_KEY')
        }
    )
    weather_data = response.json()
    # weather_stuff = weather_data['weather'][0]
    # city_name = weather_data['name']
    # # city_temp = weather_data["main"]
    # weather_list = [city_name,]

    weather = {
        'city' : 'Austin',
        'temperature' : weather_data['main']['temp'],
        'description' : weather_data['weather'][0]['description'],
        'icon' : weather_data['weather'][0]['icon'],
        }
    
    # some = [str(weather_stuff['main']), str(weather_stuff['description']), str(city_name), str(city_temp[''])]

    return weather

def get_news():
    NYT_API_BASE_URL= f'https://api.nytimes.com/svc/topstories/v2/world.json?'

    response = requests.get(
        NYT_API_BASE_URL,
        params ={
            'api-key':os.getenv('NYT_API_KEY')
        }
    )
    print(response.status_code)
    news_data = response.json()['results'][0]
    movie_data = response.json()['results'][0]['multimedia'][0]
    all_news_info = [str(news_data['title']), str(news_data['abstract']), 
        str(news_data['url']), str(news_data['published_date']), str(movie_data['url'])]
    
    return all_news_info

@app.route('/')
def home():
    return flask.render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Person.query.filter_by(username=form.username.data).first()
        login_user(user)
        return flask.redirect(flask.url_for('index'))
    user = Person.query.filter_by(username=form.username.data).first()
    
    return flask.render_template('login.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    
    return flask.redirect(flask.url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = Person(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return flask.redirect(flask.url_for('login'))
    user = Person.query.filter_by(username=form.username.data).first()
    if user:
        flask.flash ('This username is taken. Try again or')
    
    return flask.render_template('signup.html', form=form)

@app.route('/home', methods=['GET', 'POST'])
@login_required
def index():
    weather_info = get_weather()
    news_info = get_news()
    
    return flask.render_template('website.html', city=weather_info['city'],
        temp=weather_info['temperature'], description=weather_info['description'], icon=weather_info['icon'],
        title=news_info[0], published_date=news_info[1], abstract=news_info[3], the_url=news_info[2], movie=news_info[4])

#app.run(debug=True)