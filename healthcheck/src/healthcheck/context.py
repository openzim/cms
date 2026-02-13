import os
from typing import Any

from humanfriendly import parse_timespan


def get_mandatory_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise Exception(f"{key} environment variable must be set")
    return value


def parse_bool(value: Any) -> bool:
    """Parse value into boolean."""
    return str(value).lower() in ("true", "1", "yes", "y", "on")


class Context:
    """Class holding every contextual / configuration bits which can be moved

    Used to easily pass information around in the healthcheck. One singleton instance is
    always available.
    """

    debug = parse_bool(os.getenv("DEBUG", default="false"))

    requests_timeout = parse_timespan(os.getenv("REQUESTS_TIMEOUT", default="1m"))

    cms_api_url = get_mandatory_env("CMS_API_URL")
    cms_frontend_url = get_mandatory_env("CMS_FRONTEND_URL")
    cms_username = get_mandatory_env("CMS_USERNAME")
    cms_password = get_mandatory_env("CMS_PASSWORD")
    cms_database_url = get_mandatory_env("CMS_DATABASE_URL")
    catalog_generation_timeout = parse_timespan(
        os.getenv("CATALOG_GENERATION_TIMEOUT", default="10s")
    )
