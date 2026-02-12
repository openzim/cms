import datetime
import logging

from healthcheck.context import Context

logger = logging.getLogger("healthcheck")

if not logger.hasHandlers():
    logger.setLevel(logging.DEBUG if Context.debug else logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s: %(levelname)s] %(message)s"))
    logger.addHandler(handler)


def getnow():
    """naive UTC now"""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
