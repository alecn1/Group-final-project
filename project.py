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


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    movieid = db.Column(db.Integer, nullable=True)
    rating = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.String(200), nullable=True)
    

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

class MovieForm(FlaskForm):
    #username = StringField(validators=[Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    movieid = IntegerField(label="MovieID: ", render_kw={'readonly': True})
    rating = IntegerField(label="Rating (out of 10):", validators=[NumberRange(min=1, max=10, message="must be 1 to 10")])
    comment = StringField(widget=TextArea(), validators=[Length(0, 200)])
    submit = SubmitField("Submit")


def get_movies():
    
    MOVIE_IDS = [84773, 864959, 634649]
    MOVIE = MOVIE_IDS[randrange(3)]
    MOVIE_PATH = f'/movie/{MOVIE}'
    MOVIE_API_BASE_URL = f'https://api.themoviedb.org/3{MOVIE_PATH}'
    IMG_URL = 'https://image.tmdb.org/t/p/w500'

    response = requests.get(
        MOVIE_API_BASE_URL,
        params={
            'api_key': os.getenv('TMDB_API_KEY')
        }
    )
    movie_data = response.json()
    pretty_json_data = json.dumps(movie_data, indent=4, sort_keys=True)
    img_url = IMG_URL + movie_data['poster_path']
    wiki_link = wiki_api(title = movie_data['original_title'])
    
    return movie_sorter(movie_data, img_url, wiki_link, MOVIE)


def wiki_api(title):
    request = requests.Session()

    WIKI_API_BASE_URL = 'https://en.wikipedia.org/w/api.php'

    PARAMS={
        "action": "opensearch",
        "namespace": "0",
        "search": str(title),
        "limit": "1",
        "format": "json"
    }

    wiki = request.get(url=WIKI_API_BASE_URL, params=PARAMS)
    wiki_data = wiki.json()
    return wiki_data[3][0]

def movie_sorter(movie_data, img_url, wiki_link, MOVIE):
    movies_info = ""
    for genre in movie_data['genres']:
        movies_info = movies_info + str(genre['name']) + ", "

    all_movie_data = [movie_data['original_title'], movie_data['tagline'], movies_info, img_url, wiki_link, MOVIE]
    return all_movie_data

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
    form = MovieForm()
    movies_info = get_movies()
    if current_user.is_authenticated:
        if form.validate_on_submit():
            user = current_user.username
            movie_rating = Movie(username=user, movieid=form.movieid.data, 
                rating=form.rating.data, comment=form.comment.data) 
            db.session.add(movie_rating)
            db.session.commit()
            return flask.redirect(flask.url_for('index'))
        movieID = Movie.query.filter_by(movieid=movies_info[5]).all()

    return flask.render_template('website.html', title=movies_info[0], 
        summary=movies_info[1], genre=movies_info[2], image=movies_info[3], 
        wiki=movies_info[4], movie=movies_info[5], query=movieID, form=form)


app.run(debug=True)