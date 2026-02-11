import os

from humanfriendly import parse_timespan

from cms_backend.context import parse_bool


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
    # List of authentication modes. Allowed values are "local", "oauth-session"
    auth_modes: list[str] = os.getenv(
        "AUTH_MODES",
        default="oauth-session",
    ).split(",")

    # Local Authentication JWT settings
    jwt_secret: str = os.getenv("JWT_SECRET", default="")
    jwt_token_issuer: str = os.getenv("JWT_TOKEN_ISSUER", default="cms_backend")
    jwt_token_expiry_duration = parse_timespan(
        os.getenv("JWT_TOKEN_EXPIRY_DURATION", default="1d")
    )
    refresh_token_expiry_duration = parse_timespan(
        os.getenv("REFRESH_TOKEN_EXPIRY_DURATION", default="30d")
    )
