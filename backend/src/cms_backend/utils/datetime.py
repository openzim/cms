import datetime


def getnow():
    """naive UTC now"""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
