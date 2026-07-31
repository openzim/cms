import datetime
import os

from humanfriendly import parse_size, parse_timespan

from cms_backend.context import parse_bool


class Context:
    """Class holding every contextual / configuration bits which can be moved

    Used to easily pass information around in the backend. One singleton instance is
    always available.
    """

    oauth_jwks_uri = os.getenv(
        "OAUTH_JWKS_URI",
        default="https://ory.login.kiwix.org/.well-known/jwks.json",
    )
    oauth_issuer = os.getenv("OAUTH_ISSUER", default="https://ory.login.kiwix.org")

    oauth_session_audience_id = os.getenv(
        "OAUTH_SESSION_AUDIENCE_ID", default="d87a31d2-874e-44c4-9dc2-63fad523bf1b"
    )
    oauth_session_login_require_2fa = parse_bool(
        os.getenv("OAUTH_SESSION_LOGIN_REQUIRE_2FA", default="true")
    )
    oauth_client_id = os.getenv(
        "OAUTH_CLIENT_ID", default="310c5189-ce06-463c-9c55-46e822b5d642"
    )
    create_new_oauth_account = parse_bool(
        os.getenv("CREATE_NEW_OAUTH_ACCOUNT", default="true")
    )
    # List of authentication modes. Allowed values are
    # - local
    # - oauth
    auth_modes: list[str] = os.getenv(
        "AUTH_MODES",
        default="oauth",
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

    # Mode of authentication to zimfarm. Allowed values are: "oauth", "local"
    zimfarm_auth_mode: str = os.getenv("ZIMFARM_AUTH_MODE", default="oauth")
    # Credentials for local authentication to zimfarm
    zimfarm_username: str = os.getenv("ZIMFARM_USERNAME", default="")
    zimfarm_password: str = os.getenv("ZIMFARM_PASSWORD", default="")
    zimfarm_oauth_issuer: str = os.getenv(
        "ZIMFARM_OAUTH_ISSUER", default="https://ory.login.kiwix.org"
    )
    zimfarm_oauth_client_id: str = os.getenv("ZIMFARM_OAUTH_CLIENT_ID", default="")
    zimfarm_oauth_client_secret: str = os.getenv(
        "ZIMFARM_OAUTH_CLIENT_SECRET", default=""
    )
    zimfarm_oauth_audience_id: str = os.getenv("ZIMFARM_OAUTH_AUDIENCE_ID", default="")
    # Number of seconds before the access token expires at which it should be renewed
    zimfarm_token_renewal_window: datetime.timedelta = datetime.timedelta(
        seconds=parse_timespan(os.getenv("ZIMFARM_TOKEN_RENEWAL_WINDOW", default="5m"))
    )
    zimwright_image: str = os.getenv("ZIMWRIGHT_IMAGE", "openzim/zimwright:1.0.0")
    zimwright_definition_version = os.getenv("ZIMWRIGHT_DEFINITION_VERSION", "")
    if not zimwright_definition_version:
        _, zimwright_definition_version = zimwright_image.split(":")

    zimtask_cpu: int = int(os.getenv("ZIMTASK_CPU", default="3"))
    zimtask_memory = parse_size(
        os.getenv("ZIMTASK_MEMORY", default="1GiB"), binary=True
    )
    zimtask_disk = parse_size(os.getenv("ZIMTASK_DISK", default="1GiB"), binary=True)
    zimtask_worker = os.getenv("ZIMTASK_WORKER")
