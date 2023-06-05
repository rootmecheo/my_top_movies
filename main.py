from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import asc, desc
from flask_wtf import FlaskForm
from wtforms import StringField,  SubmitField
from wtforms.validators import DataRequired
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap(app)

API_KEY = "4bf6b210d22ea3d7e340f93ccc08999c"
search_url = "https://api.themoviedb.org/3/search/movie"

# create  conection to database
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///my-top-ten-movies.db"
# silence deprecation warning in the console
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# create table
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer)
    description = db.Column(db.String(500))
    rating = db.Column(db.Float)
    ranking = db.Column(db.Integer, autoincrement=True, default=0)
    review = db.Column(db.String(100))
    image_url = db.Column(db.String(500))

    def __repr__(self):
        return f"Movies {self.title}"


with app.app_context():
    db.create_all()


# create add from
class FindMovieForm(FlaskForm):
    title = StringField(label="Movie Title", validators=[DataRequired()])
    submit = SubmitField(label="Add Movie")


# create edit form
class EditForm(FlaskForm):
    rating = StringField(label="Your Rating out of 10. eg 7.5")
    review = StringField(label="Your Review")
    submit = SubmitField(label='Save Changes')


@app.route("/add", methods=["GET", "POST"])
def add():
    find_movie_form = FindMovieForm()
    if find_movie_form.validate_on_submit():
        query = find_movie_form.title.data
        search_params = {
            "api_key": API_KEY,
            "query": query,
        }
        response = requests.get(url=search_url, params=search_params)
        response.raise_for_status()
        data = response.json()["results"]
        return render_template("select.html", data=data)

    return render_template("add.html", form=find_movie_form)


@app.route("/selected", methods=["GET", "POST"])
def selected():
    movie_id = request.args.get("id")
    movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}"

    details_params = {
        "api_key": API_KEY
    }

    response = requests.get(movie_url, params=details_params)
    response.raise_for_status()
    movie_data = response.json()

    # create new record
    title = movie_data["original_title"]
    description = movie_data["overview"]
    year = movie_data["release_date"].split("-")[0]

    # Construct the full poster URL using the base URL provided by the API
    base_image_url = "https://image.tmdb.org/t/p"
    poster_size = "w500"
    image_url = f"{base_image_url}/{poster_size}/{movie_data['poster_path']}"

    rating = movie_data["vote_average"]

    # check if item is in database before committing
    existing_movie = Movie.query.filter_by(title=title).first()
    if existing_movie:
        return redirect(url_for("edit", id=existing_movie.id))
    else:
        new_movie = Movie(
            title=title,
            year=year,
            description=description,
            image_url=image_url,
            rating=rating,
            ranking=0,
            review=None
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("edit", id=new_movie.id))


@app.route("/")
def home():
    # Read all records and order by descending rating
    movies = db.session.query(Movie).order_by(Movie.rating.desc()).all()

    # Assign ranking based on position in the sorted list
    for i, movie in enumerate(movies):
        movie.ranking = i + 1

    db.session.commit()

    return render_template("index.html", movies=movies)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    edit_form = EditForm()
    movie_id = request.args.get("id")
    movie_selected = Movie.query.get(movie_id)

    if edit_form.validate_on_submit():
        # update record
        movie_selected.rating = float(edit_form.rating.data)
        movie_selected.review = edit_form.review.data
        db.session.commit()
        return redirect(url_for("home"))

    # Set the default values for the form fields
    edit_form.rating.data = movie_selected.rating
    edit_form.review.data = movie_selected.review

    return render_template("edit.html", movie=movie_selected, form=edit_form)


@app.route("/delete")
def delete():
    movie_id = request.args.get("id")

    with app.app_context():
        # delete record
        movie_to_delete = Movie.query.get(movie_id)
        db.session.delete(movie_to_delete)
        db.session.commit()

    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
