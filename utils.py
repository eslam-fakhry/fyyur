from datetime import datetime


def is_past_show(show):
    return is_past_datetime(show.start_time)


def is_past_datetime(my_datetime):
    print(my_datetime.date() < datetime.now().date())
    return my_datetime.date() < datetime.now().date()
