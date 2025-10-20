import logging

from cms_backend.context import Context

logger = logging.getLogger("backend")

if not logger.hasHandlers():
    logger.setLevel(logging.DEBUG if Context.debug else logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s: %(levelname)s] %(message)s"))
    logger.addHandler(handler)
