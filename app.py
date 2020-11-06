#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from collections import defaultdict
from functools import reduce
from itertools import filterfalse
import json
import sys
from utils import is_past_show

import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from sqlalchemy.orm import joinedload, Load
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, func
from flask_migrate import Migrate
from flask_debugtoolbar import DebugToolbarExtension
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
app.debug = True
db = SQLAlchemy(app)
migrate = Migrate(app, db)
toolbar = DebugToolbarExtension(app)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean(), default=False)
    seeking_description = db.Column(db.Text())

    # Add many-to-many relationship with Artist through Show model
    artists = db.relationship(
        'Artist', secondary='shows',
        backref='venues',
        lazy=True)
    shows = db.relationship('Show', backref="venue", lazy=True)


class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean(), default=False)
    seeking_description = db.Column(db.Text())

    shows = db.relationship('Show', backref="artist", lazy=True)


class Show(db.Model):
    __tablename__ = 'shows'

    artist_id = db.Column(db.Integer,
                          db.ForeignKey('artists.id'),
                          primary_key=True,
                          nullable=False)
    venue_id = db.Column(db.Integer,
                         db.ForeignKey('venues.id'),
                         primary_key=True,
                         nullable=False)
    start_time = db.Column(db.DateTime,
                           nullable=False)


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

def group_by_city_state(data):
    def reducer(acc, item):
        venue, show_count = item
        acc[(venue.state, venue.city)]['city'] = venue.city
        acc[(venue.state, venue.city)]['state'] = venue.state
        acc[(venue.state, venue.city)]['venues'].append({
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": show_count
        })
        return acc

    def default_data_item_factory():
        return {
            "state": None,
            "city": None,
            "venues": []
        }

    return reduce(reducer, data, defaultdict(default_data_item_factory)).values()


@app.route('/venues')
def venues():
    result = db.session.query(Venue, func.count(Show.start_time)) \
        .options(Load(Venue).load_only("id", "name", "city", "state",)) \
        .outerjoin(Show, and_(Venue.id == Show.venue_id, Show.start_time > datetime.now().date())) \
        .group_by(Venue.id).all()

    data = group_by_city_state(result)

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
    # search for Hop should return "The Musical Hop".
    # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
    response = {
        "count": 1,
        "data": [{
            "id": 2,
            "name": "The Dueling Pianos Bar",
            "num_upcoming_shows": 0,
        }]
    }
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query \
        .options(joinedload(Venue.shows)) \
        .options(joinedload(Venue.artists).load_only("id", "name", "image_link")) \
        .get(venue_id)

    past_shows = list(filter(is_past_show, venue.shows))
    upcoming_shows = list(filterfalse(is_past_show, venue.shows))

    def mapper(show):
        return {
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": str(show.start_time)
        }
    past_shows_dict = map(mapper, past_shows)
    upcoming_shows_dict = map(mapper, upcoming_shows)

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres.split(','),
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": past_shows_dict,
        "upcoming_shows": upcoming_shows_dict,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form)
    error = False
    if form.validate():
        venue = create_venue_from_request(request)
        venue_id = None
        try:
            db.session.add(venue)
            db.session.commit()
            venue_id = venue.id
        except Exception:
            db.session.rollback()
            print(sys.exc_info())
            error = True
        finally:
            db.session.close()
        if error:
            flash("Oops!, Something went wrong!")
            return render_template('forms/new_venue.html', form=form)
        else:
            flash('Venue ' + request.form['name'] +
                  ' was successfully listed!')
            return redirect(url_for('show_venue', venue_id=venue_id))

    if form.csrf_token.errors:
        flash("Your session is expired. please try again")

    flash("Oops!, input data not valid. please check your input!")
    return render_template('forms/new_venue.html', form=form)


def create_venue_from_request(request):
    return populate_venue_from_request(Venue(), request)


def populate_venue_from_request(venue, request):
    form = request.form
    seeking_talent_str = form.get('seeking_talent', '')
    seeking_talent = len(seeking_talent_str) > 0

    venue.name = form['name']
    venue.city = form['city']
    venue.state = form['state']
    venue.address = form['address']
    venue.phone = form['phone']
    venue.genres = ",".join(form.getlist('genres'))
    venue.facebook_link = form['facebook_link']
    venue.image_link = form['image_link']
    venue.website = form['website']
    venue.seeking_talent = seeking_talent
    venue.seeking_description = form['seeking_description']

    return venue


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    venue = Venue.query.get(venue_id)

    if venue is None:
        flash('Venue not found')
        return redirect(url_for('index'))

    venue_name = venue.name

    try:
        db.session.delete(venue)
        db.session.commit()
        flash('Venue ' + venue_name +
              ' was successfully deleted!')
    except Exception:
        db.session.rollback()
        print(sys.exc_info())
        flash("Oops!, Something went wrong!")
    finally:
        db.session.close()

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return redirect(url_for('index'))

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    artists = Artist.query.options(Load(Artist).load_only('id', 'name')).all()
    data = list(map(lambda x: {"id": x.id, "name": x.name}, artists))
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
    # search for "A" should return "Guns N Petals", "Matt Quevedo", and "The Wild Sax Band".
    # search for "band" should return "The Wild Sax Band".
    response = {
        "count": 1,
        "data": [{
            "id": 4,
            "name": "Guns N Petals",
            "num_upcoming_shows": 0,
        }]
    }
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query \
        .options(joinedload(Artist.shows)) \
        .options(joinedload(Artist.venues).load_only("id", "name", "image_link")) \
        .get(artist_id)

    past_shows = list(filter(is_past_show, artist.shows))
    upcoming_shows = list(filterfalse(is_past_show, artist.shows))

    def mapper(show):
        return {
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
            "venue_image_link": show.venue.image_link,
            "start_time": str(show.start_time)
        }
    past_shows_dict = map(mapper, past_shows)
    upcoming_shows_dict = map(mapper, upcoming_shows)

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres.split(','),
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": past_shows_dict,
        "upcoming_shows": upcoming_shows_dict,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist_obj = Artist.query.get_or_404(artist_id)

    artist = {
        "id": artist_obj.id,
        "name": artist_obj.name,
    }

    # populate form with ArtistForm
    form = ArtistForm(obj=artist_obj)
    form.genres.data = artist_obj.genres.split(',')

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    old_artist = Artist.query.get_or_404(artist_id)

    form = ArtistForm(request.form)
    error = False
    if form.validate():
        artist_id = None
        artist = populate_artist_from_request(old_artist, request)
        try:
            db.session.commit()
            artist_id = artist.id
        except Exception:
            db.session.rollback()
            print(sys.exc_info())
            error = True
        finally:
            db.session.close()
        if error:
            flash("Oops!, Something went wrong!")
            return render_template('forms/edit_artist.html', form=form)
        else:
            flash('Artist ' + request.form['name'] +
                  ' was successfully updated!')
            return redirect(url_for('show_artist', artist_id=artist_id))

    if form.csrf_token.errors:
        flash("Your session is expired. please try again")

    flash("Oops!, input data not valid. please check your input!")
    return render_template('forms/edit_artist.html', form=form)


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue_obj = Venue.query.get_or_404(venue_id)

    venue = {
        "id": venue_obj.id,
        "name": venue_obj.name,
    }

    # populate form with VenueForm
    form = VenueForm(obj=venue_obj)
    form.genres.data = venue_obj.genres.split(',')

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    old_venue = Venue.query.get_or_404(venue_id)
    form = VenueForm(request.form)
    error = False
    if form.validate():
        venue = populate_venue_from_request(old_venue, request)
        venue_id = None
        try:
            db.session.commit()
            venue_id = venue.id
        except Exception:
            db.session.rollback()
            print(sys.exc_info())
            error = True
        finally:
            db.session.close()
        if error:
            flash("Oops!, Something went wrong!")
            return render_template('forms/edit_venue.html', form=form)
        else:
            flash('Venue ' + request.form['name'] +
                  ' was successfully updated!')
            return redirect(url_for('show_venue', venue_id=venue_id))

    if form.csrf_token.errors:
        flash("Your session is expired. please try again")

    flash("Oops!, input data not valid. please check your input!")
    return render_template('forms/edit_venue.html', form=form)

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    form = ArtistForm(request.form)
    error = False
    if form.validate():
        artist = create_artist_from_request(request)
        artist_id = None
        try:
            db.session.add(artist)
            db.session.commit()
            artist_id = artist.id
        except Exception:
            db.session.rollback()
            print(sys.exc_info())
            error = True
        finally:
            db.session.close()
        if error:
            flash("Oops!, Something went wrong!")
            return render_template('forms/new_artist.html', form=form)
        else:
            flash('Artist ' + request.form['name'] +
                  ' was successfully listed!')
            return redirect(url_for('show_artist', artist_id=artist_id))

    if form.csrf_token.errors:
        flash("Your session is expired. please try again")

    flash("Oops!, input data not valid. please check your input!")
    return render_template('forms/new_artist.html', form=form)


def create_artist_from_request(request):
    return populate_artist_from_request(Artist(), request)


def populate_artist_from_request(artist, request):
    form = request.form
    seeking_venue_str = form.get('seeking_venue', '')
    seeking_venue = len(seeking_venue_str) > 0

    artist.name = form['name']
    artist.city = form['city']
    artist.state = form['state']
    artist.phone = form['phone']
    artist.genres = ",".join(form.getlist('genres'))
    artist.facebook_link = form['facebook_link']
    artist.image_link = form['image_link']
    artist.website = form['website']
    artist.seeking_venue = seeking_venue
    artist.seeking_description = form['seeking_description']

    return artist


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    # TODO: replace with real venues data.
    #       num_shows should be aggregated based on number of upcoming shows per venue.
    data = [{
        "venue_id": 1,
        "venue_name": "The Musical Hop",
        "artist_id": 4,
        "artist_name": "Guns N Petals",
        "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
        "start_time": "2019-05-21T21:30:00.000Z"
    }, {
        "venue_id": 3,
        "venue_name": "Park Square Live Music & Coffee",
        "artist_id": 5,
        "artist_name": "Matt Quevedo",
        "artist_image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
        "start_time": "2019-06-15T23:00:00.000Z"
    }, {
        "venue_id": 3,
        "venue_name": "Park Square Live Music & Coffee",
        "artist_id": 6,
        "artist_name": "The Wild Sax Band",
        "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
        "start_time": "2035-04-01T20:00:00.000Z"
    }, {
        "venue_id": 3,
        "venue_name": "Park Square Live Music & Coffee",
        "artist_id": 6,
        "artist_name": "The Wild Sax Band",
        "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
        "start_time": "2035-04-08T20:00:00.000Z"
    }, {
        "venue_id": 3,
        "venue_name": "Park Square Live Music & Coffee",
        "artist_id": 6,
        "artist_name": "The Wild Sax Band",
        "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
        "start_time": "2035-04-15T20:00:00.000Z"
    }]
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    # TODO: insert form data as a new Show record in the db, instead

    # on successful db insert, flash success
    flash('Show was successfully listed!')
    # TODO: on unsuccessful db insert, flash an error instead.
    # e.g., flash('An error occurred. Show could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
