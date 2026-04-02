import datetime
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
    auth_mode = os.getenv("AUTH_MODE", default="local")
    cms_username = os.getenv("CMS_USERNAME", default="")
    cms_password = os.getenv("CMS_PASSWORD")
    cms_oauth_issuer = os.getenv(
        "CMS_OAUTH_ISSUER", default="https://ory.login.kiwix.org"
    )
    cms_oauth_client_id = os.getenv("CMS_OAUTH_CLIENT_ID", default="")
    cms_oauth_client_secret = os.getenv("CMS_OAUTH_CLIENT_SECRET", default="")
    cms_oauth_audience_id = os.getenv("CMS_OAUTH_AUDIENCE_ID", default="")
    cms_token_renewal_window = datetime.timedelta(
        seconds=parse_timespan(os.getenv("CMS_TOKEN_RENEWAL_WINDOW", default="5m"))
    )
    cms_database_url = get_mandatory_env("CMS_DATABASE_URL")
    catalog_generation_timeout = parse_timespan(
        os.getenv("CATALOG_GENERATION_TIMEOUT", default="10s")
    )
