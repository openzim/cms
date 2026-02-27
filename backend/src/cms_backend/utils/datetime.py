import datetime
from uuid import UUID


def getnow():
    """naive UTC now"""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def is_valid_uuid(identifier: str) -> bool:
    """Check if string is a valid UUID"""
    try:
        UUID(identifier)
    except ValueError:
        return False
    return True
