import logging

import pycountry

from cms_backend.context import Context

logger = logging.getLogger("backend")

if not logger.hasHandlers():
    logger.setLevel(logging.DEBUG if Context.debug else logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s: %(levelname)s] %(message)s"))
    logger.addHandler(handler)


def update_language_codes():
    for code in Context.disallowed_language_codes:
        try:
            pycountry.languages.remove_entry(alpha_3=code)  # pyright: ignore[reportUnknownMemberType]
        except Exception as exc:
            logger.warning(f"failed to remove language code '{code}': {exc}")

    for code in Context.custom_language_codes:
        pycountry.languages.add_entry(alpha_3=code)  # pyright: ignore[reportUnknownMemberType]


update_language_codes()
