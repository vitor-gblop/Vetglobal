import datetime


def now():
    return datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")