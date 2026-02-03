import os
from dataclasses import dataclass

from cms_backend.context import parse_bool


@dataclass(kw_only=True)
class Context:
    """Class holding every contextual / configuration bits which can be moved

    Used to easily pass information around in the backend. One singleton instance is
    always available.
    """

    oauth_jwks_uri = os.getenv(
        "OAUTH_JWKS_URI",
        default="https://login.kiwix.org/.well-known/jwks.json",
    )
    oauth_issuer = os.getenv("OAUTH_ISSUER", default="https://login.kiwix.org")

    oauth_session_audience_id = os.getenv(
        "OAUTH_SESSION_AUDIENCE_ID", default="d87a31d2-874e-44c4-9dc2-63fad523bf1b"
    )
    oauth_session_login_require_2fa = parse_bool(
        os.getenv("OAUTH_SESSION_LOGIN_REQUIRE_2FA", default="true")
    )
    create_new_oauth_account = parse_bool(
        os.getenv("CREATE_NEW_OAUTH_ACCOUNT", default="true")
    )
