#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from collections import defaultdict
from functools import reduce
from itertools import filterfalse
import json
import sys
from sqlalchemy.exc import IntegrityError
from utils import is_past_show

import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from sqlalchemy.orm import joinedload, Load
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, func, or_
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
    facebook_link = db.Column(db.String(120), unique=True)
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean(), default=False)
    seeking_description = db.Column(db.Text())
    created_at = db.Column(db.DateTime(), nullable=False,
                           server_default=func.now())

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
    facebook_link = db.Column(db.String(120), unique=True)
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean(), default=False)
    seeking_description = db.Column(db.Text())
    created_at = db.Column(db.DateTime(), nullable=False,
                           server_default=func.now())

    shows = db.relationship('Show', backref="artist", lazy=True)


class Show(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer,
                          db.ForeignKey('artists.id'),
                          nullable=False)
    venue_id = db.Column(db.Integer,
                         db.ForeignKey('venues.id'),
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
    artists_result = db.session.query(Artist) \
        .options(Load(Artist).load_only('name', "created_at")) \
        .order_by(Artist.created_at.desc()).limit(10).all()

    venues_result = db.session.query(Venue) \
        .options(Load(Venue).load_only('name', "created_at")) \
        .order_by(Venue.created_at.desc()).limit(10).all()

    def mapper_factory(type):
        def mapper(model):
            return {
                "type": type,
                "id": model.id,
                "name": model.name,
                "created_at": model.created_at
            }
        return mapper

    artists = list(map(mapper_factory('artist'), artists_result))
    venues = list(map(mapper_factory('venue'), venues_result))

    all_models = venues + artists
    latest = sorted(all_models, key=lambda x: x['id'], reverse=True)[:10]

    return render_template('pages/home.html', latest=latest)


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


# Make it accept Get request for better UX
@app.route('/venues/search', methods=['GET'])
def search_venues():
    search_term = request.args.get('search_term', '')
    result = db.session.query(Venue.id, Venue.name, func.count(Show.start_time)) \
        .outerjoin(Show,
                   and_(Venue.id == Show.venue_id, Show.start_time > datetime.now().date())) \
        .filter(Venue.name.ilike("%{}%".format(search_term))) \
        .group_by(Venue.id).all()

    def mapper(result_item):
        id, name, num_upcoming_shows = result_item
        return {
            "id": id,
            "name": name,
            "num_upcoming_shows": num_upcoming_shows,
        }

    response = {
        "count": len(result),
        "data": list(map(mapper, result))
    }
    return render_template('pages/search_venues.html', results=response, search_term=search_term)


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
    if not form.validate():
        if form.csrf_token.errors:
            flash("Your session is expired. please try again")

        flash("Oops!, input data not valid. please check your input!")
        return render_template('forms/new_venue.html', form=form)

    venue = create_venue_from_request(request)
    venue_id = None
    try:
        db.session.add(venue)
        db.session.commit()
        venue_id = venue.id
    except IntegrityError:
        db.session.rollback()
        print(sys.exc_info())
        error = True
        flash("Oops!, looks like another venue uses this facebook link!")
    except Exception:
        db.session.rollback()
        print(sys.exc_info())
        error = True
        flash("Oops!, Something went wrong!")
    finally:
        db.session.close()
    if error:
        return render_template('forms/new_venue.html', form=form)
    else:
        flash('Venue ' + request.form['name'] +
              ' was successfully listed!')
        return redirect(url_for('show_venue', venue_id=venue_id))


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

    return redirect(url_for('index'))

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    artists = Artist.query.options(Load(Artist).load_only('id', 'name')).all()
    data = list(map(lambda x: {"id": x.id, "name": x.name}, artists))
    return render_template('pages/artists.html', artists=data)


# Make it accept Get request for better UX
@app.route('/artists/search', methods=['GET'])
def search_artists():
    search_term = request.args.get('search_term', '')
    result = db.session.query(Artist.id, Artist.name, func.count(Show.start_time)) \
        .outerjoin(Show,
                   and_(Artist.id == Show.artist_id, Show.start_time > datetime.now().date())) \
        .filter(Artist.name.ilike("%{}%".format(search_term))) \
        .group_by(Artist.id).all()

    def mapper(result_item):
        id, name, num_upcoming_shows = result_item
        return {
            "id": id,
            "name": name,
            "num_upcoming_shows": num_upcoming_shows,
        }

    response = {
        "count": len(result),
        "data": list(map(mapper, result))
    }
    return render_template('pages/search_artists.html', results=response, search_term=search_term)


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

    artist_data = {
        "id": artist_id,
        "name": request.form['name'],
    }

    form = ArtistForm(request.form)
    error = False
    if not form.validate():
        if form.csrf_token.errors:
            flash("Your session is expired. please try again")

        flash("Oops!, input data not valid. please check your input!")
        return render_template('forms/edit_artist.html', form=form, artist=artist_data)

    artist_id = None
    artist = populate_artist_from_request(old_artist, request)
    try:
        db.session.commit()
        artist_id = artist.id
    except IntegrityError:
        db.session.rollback()
        print(sys.exc_info())
        error = True
        flash("Oops!, looks like another venue uses this facebook link!")
    except Exception:
        db.session.rollback()
        print(sys.exc_info())
        error = True
        flash("Oops!, Something went wrong!")
    finally:
        db.session.close()
    if error:
        return render_template('forms/edit_artist.html', form=form, artist=artist_data)
    else:
        flash('Artist ' + request.form['name'] +
              ' was successfully updated!')
        return redirect(url_for('show_artist', artist_id=artist_id))


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
    venue_dict = {
        "id": venue_id,
        'name': request.form.get('name', '')
    }
    error = False
    if not form.validate():
        if form.csrf_token.errors:
            flash("Your session is expired. please try again")

        flash("Oops!, input data not valid. please check your input!")
        return render_template('forms/edit_venue.html', form=form, venue=venue_dict)

    print('here')
    venue = populate_venue_from_request(old_venue, request)
    venue_id = None
    try:
        db.session.commit()
        venue_id = venue.id
    except IntegrityError:
        db.session.rollback()
        print(sys.exc_info())
        error = True
        flash("Oops!, looks like another venue uses this facebook link!")
    except Exception:
        db.session.rollback()
        print(sys.exc_info())
        error = True
        flash("Oops!, Something went wrong!")
    finally:
        db.session.close()
    if error:
        return render_template('forms/edit_venue.html', form=form, venue=venue_dict)
    else:
        flash('Venue ' + request.form['name'] +
              ' was successfully updated!')
        return redirect(url_for('show_venue', venue_id=venue_id))


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
    if not form.validate():
        if form.csrf_token.errors:
            flash("Your session is expired. please try again")

        flash("Oops!, input data not valid. please check your input!")
        return render_template('forms/new_artist.html', form=form)

    artist = create_artist_from_request(request)
    artist_id = None
    try:
        db.session.add(artist)
        db.session.commit()
        artist_id = artist.id
    except IntegrityError:
        db.session.rollback()
        print(sys.exc_info())
        error = True
        flash("Oops!, looks like another artist uses this facebook link!")
    except Exception:
        db.session.rollback()
        print(sys.exc_info())
        error = True
        flash("Oops!, Something went wrong!")
    finally:
        db.session.close()
    if error:
        return render_template('forms/new_artist.html', form=form)
    else:
        flash('Artist ' + request.form['name'] +
              ' was successfully listed!')
        return redirect(url_for('show_artist', artist_id=artist_id))


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
    shows = Show.query \
        .options(joinedload(Show.artist).load_only("name", "image_link")) \
        .options(joinedload(Show.venue).load_only("name")) \
        .all()

    def mapper(show):
        return {
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": str(show.start_time)
        }

    data = list(map(mapper, shows))

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form)
    error = False

    if(not form.validate()):
        flash("Oops!, input data not valid. please check your input!")
        return render_template('forms/new_show.html', form=form)

    # check if artist exists
    artist = Artist.query.get(request.form.get('artist_id'))
    if artist is None:
        form.venue_id.errors.append("Id is not associated with any artist")
        return render_template('forms/new_show.html', form=form)

    # check if venue exists
    venue = Venue.query.get(request.form.get('venue_id'))
    if venue is None:
        form.venue_id.errors.append("Id is not associated with any venue")
        return render_template('forms/new_show.html', form=form)

    show = Show(artist_id=request.form.get('artist_id'),
                venue_id=request.form.get('venue_id'),
                start_time=request.form.get('start_time'))
    try:
        db.session.add(show)
        db.session.commit()
    except Exception:
        db.session.rollback()
        print(sys.exc_info())
        error = True
    finally:
        db.session.close()

    if error:
        flash("An error occurred. Show could not be listed.")
        return render_template('forms/new_show.html', form=form)

    flash('Show was successfully listed!')
    return redirect(url_for('shows'))


@app.route('/shows/search', methods=['GET'])
def search_shows():
    search_term = request.args.get('search_term', '')

    result = db.session.query(Show) \
        .options(joinedload(Show.artist).load_only('name', 'image_link')) \
        .options(joinedload(Show.venue).load_only('name')) \
        .filter(or_(Artist.name.ilike("%{}%".format(search_term)),
                    Venue.name.ilike("%{}%".format(search_term)))) \
        .all()

    print('result', result)

    def mapper(show):

        return {
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            'start_time': str(show.start_time),
        }

    results = {
        "count": len(result),
        "data": list(map(mapper, result))
    }

    return render_template('pages/show.html', results=results, search_term=search_term)


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
