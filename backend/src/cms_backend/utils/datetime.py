import datetime as dt


def getnow():
    """naive UTC now"""
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)
