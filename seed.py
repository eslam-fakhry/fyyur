from datetime import timedelta, datetime
import sys
from app import db, Artist, Venue, Show, Unavailability

import json
import random


def main():
    with open('seed_data.json') as json_file:
        data = json.load(json_file)
        # artists = map(artist_mapper, data['artists'])
        try:
            for artist in data['artists']:
                past_days = random.randrange(0, 20)
                created_at = datetime.now() - timedelta(days=past_days)
                artist_obj = Artist(name=artist['name'],
                                    genres=artist["genres"],
                                    city=artist["city"],
                                    state=artist['state'],
                                    phone=artist['phone'],
                                    website=artist['website'],
                                    facebook_link=artist['facebook_link'],
                                    seeking_venue=artist['seeking_venue'],
                                    seeking_description=artist['seeking_description'],
                                    image_link=artist['image_link'],
                                    created_at=created_at,
                                    )
                db.session.add(artist_obj)
            db.session.commit()
            for venue in data['venues']:
                past_days = random.randrange(0, 20)
                created_at = datetime.now() - timedelta(days=past_days)
                venue_obj = Venue(name=venue['name'],
                                genres=venue["genres"],
                                city=venue["city"],
                                state=venue['state'],
                                address=venue['address'],
                                phone=venue['phone'],
                                website=venue['website'],
                                facebook_link=venue['facebook_link'],
                                seeking_talent=venue['seeking_talent'],
                                seeking_description=venue['seeking_description'],
                                image_link=venue['image_link'],
                                created_at=created_at,
                                )
                db.session.add(venue_obj)
            for i in range(10):
                past_days = random.randrange(-3, 3)
                start_time = datetime.now() + timedelta(days=past_days)
                show_obj = Show(artist_id=random.randrange(1, 20),
                                venue_id=random.randrange(1, 20),
                                start_time=start_time,
                                )
                db.session.add(show_obj)
            db.session.commit()

            for i in range(10):
                past_days = random.randrange(-3, 3)
                duration = random.randrange(2, 20)

                start_time = datetime.now() + timedelta(days=past_days)
                end_time = start_time + timedelta(days=duration)
                
                show_obj = Show(artist_id=random.randrange(1, 20),
                                venue_id=random.randrange(1, 20),
                                start_time=start_time,
                                )
                db.session.add(show_obj)
            db.session.commit()
        except:
            db.session.rollback()
            print(sys.exc_info()    )
        finally:
           db.session.close()

if __name__ == "__main__":
    main()
