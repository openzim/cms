import abc
import datetime
import uuid
from typing import Any, cast

import jwt
import requests
from jwt import PyJWKClient
from jwt import exceptions as jwt_exceptions
from pydantic import Field
from pydantic import ValidationError as PydanticValidationError
from requests.auth import HTTPBasicAuth

from cms_backend import logger
from cms_backend.api.context import Context as ApiContext
from cms_backend.context import Context
from cms_backend.schemas import BaseModel
from cms_backend.utils.datetime import getnow


class JWTClaims(BaseModel):
    iss: str
    exp: datetime.datetime
    iat: datetime.datetime
    sub: uuid.UUID = Field(alias="subject")
    name: str | None = Field(exclude=True, default=None)


class TokenDecoder(abc.ABC):
    """Abstract base class for token decoders."""

    @abc.abstractmethod
    def decode(self, token: str) -> JWTClaims:
        """
        Decode and validate a token.
        """
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        Human-readable identifier of the decoder.
        """
        pass

    @abc.abstractmethod
    def can_decode(self, token: str) -> bool:
        """
        Check if this decoder can potentially decode the given token.
        """
        pass


class LocalTokenDecoder(TokenDecoder):
    """Decoder for local CMS JWT tokens."""

    def __init__(self, secret: str = ApiContext.jwt_secret, algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm

    def decode(self, token: str) -> JWTClaims:
        """
        Decode and validate a local CMS token.
        """
        jwt_claims = jwt.decode(token, self.secret, algorithms=[self.algorithm])
        return JWTClaims(**jwt_claims)

    @property
    def name(self) -> str:
        return "local"

    def can_decode(self, token: str) -> bool:
        if "local" not in ApiContext.auth_modes:
            return False
        try:
            payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_aud": False,
                    "verify_iss": False,
                },
            )
        except Exception:
            return False

        if payload.get("iss") != ApiContext.jwt_token_issuer:
            return False

        return True


class OAuthTokenDecoder(TokenDecoder):
    """Decoder for OAuth JWT tokens."""

    def __init__(self):
        """Initialize OAuth token decoder."""
        self._jwks_client = PyJWKClient(
            ApiContext.oauth_jwks_uri,
            cache_keys=True,
            headers={"User-Agent": "PyJWT/2.11.0"},
        )

    def decode(self, token: str) -> JWTClaims:
        """
        Decode and validate an OAuth OIDC token.
        """
        signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        decoded_token = jwt.decode(  # pyright: ignore[reportUnknownMemberType]
            token,
            signing_key.key,
            algorithms=[signing_key.algorithm_name],
            issuer=ApiContext.oauth_issuer,
            audience=ApiContext.oauth_session_audience_id,
            options={
                "require": ["exp", "iat", "iss", "sub", "aud"],
            },
        )

        if (
            client_id := decoded_token.get("client_id")
        ) and client_id != decoded_token.get("sub"):
            raise ValueError("Oauth client ID does not match.")

        # Check for 2FA requirement only if client_id is not present in the token
        # as those come from oauth2 clients and not real accounts
        if (
            not decoded_token.get("client_id")
            and ApiContext.oauth_session_login_require_2fa
            and decoded_token.get("aal") != "aal2"
        ):
            raise ValueError(
                "2FA authentication is mandatory on CMS but it looks like you only "
                "have one setup on Ory. Please, configure a second one on Ory at "
                f"{ApiContext.oauth_issuer}/settings"
            )
        return JWTClaims.model_validate(decoded_token)

    @property
    def name(self) -> str:
        return "oauth"

    def can_decode(self, token: str) -> bool:
        if "oauth" not in ApiContext.auth_modes:
            return False
        try:
            payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_aud": False,
                    "verify_iss": False,
                },
            )
        except Exception:
            return False

        if (
            payload.get("iss") != ApiContext.oauth_issuer
            or ApiContext.oauth_session_audience_id not in payload.get("aud", [])
        ):
            return False
        return True


class TokenDecoderChain:
    """Chain of responsibility for token decoders."""

    def __init__(self, decoders: list[TokenDecoder]):
        """
        Initialize decoder chain.
        """
        self.decoders = decoders

    def decode(self, token: str) -> JWTClaims:
        """
        Try to decode token using each decoder in order.
        """
        exc_cls: Exception | None = None
        decoders = [decoder for decoder in self.decoders if decoder.can_decode(token)]
        if not decoders:
            raise ValueError("No decoders registered for decoding token.")

        if not decoders:
            raise ValueError("No decoders can decode token.")

        if len(decoders) > 1:
            logger.warning(
                "Multiple token decoders detected. Set configuration values to match "
                "only one token decoder to avoid overwriting exception messages."
            )

        for decoder in decoders:
            try:
                logger.debug(f"{decoder.name}-decoder: attempting to decode token.")
                claims = decoder.decode(token)
            except (
                jwt_exceptions.PyJWTError,
                PydanticValidationError,
                Exception,
            ) as exc:
                logger.debug(f"{decoder.name}-decoder: unable to decode token: {exc!s}")
                exc_cls = exc
            else:
                logger.debug(f"{decoder.name}-decoder: decoded token successfully.")
                return claims

        if exc_cls:
            raise exc_cls

        raise ValueError("Invalid token")


token_decoder = TokenDecoderChain(
    decoders=[
        OAuthTokenDecoder(),
        LocalTokenDecoder(),
    ]
)


def generate_access_token(
    *,
    account_id: str,
    issue_time: datetime.datetime,
) -> str:
    """Generate a JWT access token for the given account ID with configured expiry."""

    expire_time = issue_time + datetime.timedelta(
        seconds=ApiContext.jwt_token_expiry_duration
    )
    payload = {
        "iss": ApiContext.jwt_token_issuer,  # issuer
        "exp": expire_time.timestamp(),  # expiration time
        "iat": issue_time.timestamp(),  # issued at
        "subject": account_id,
    }
    return jwt.encode(payload, key=ApiContext.jwt_secret, algorithm="HS256")


class ZimfarmClientTokenProvider:
    """Client to generate access tokens to authenticate with Zimfarm"""

    def __init__(self):
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: datetime.datetime = datetime.datetime.fromtimestamp(
            0
        ).replace(tzinfo=None)

    def _generate_oauth_access_token(self) -> None:
        """Generate oauth access token and update expires_at."""
        response = requests.post(
            f"{ApiContext.zimfarm_oauth_issuer}/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "audience": ApiContext.zimfarm_oauth_audience_id,
            },
            auth=HTTPBasicAuth(
                ApiContext.zimfarm_oauth_client_id,
                ApiContext.zimfarm_oauth_client_secret,
            ),
            timeout=Context.requests_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = cast(str, payload["access_token"])
        self._expires_at = getnow() + datetime.timedelta(seconds=payload["expires_in"])

    def _generate_local_access_token(self) -> None:
        if self._refresh_token:
            response = requests.post(
                f"{Context.zimfarm_api_url}/auth/refresh",
                json={
                    "refresh_token": self._refresh_token,
                },
                timeout=Context.requests_timeout,
            )
        else:
            response = requests.post(
                f"{Context.zimfarm_api_url}/auth/authorize",
                json={
                    "username": ApiContext.zimfarm_username,
                    "password": ApiContext.zimfarm_password,
                },
                timeout=Context.requests_timeout,
            )

        response.raise_for_status()
        payload = response.json()
        self._access_token = cast(str, payload["access_token"])
        self._refresh_token = cast(str, payload["refresh_token"])
        self._expires_at = datetime.datetime.fromisoformat(
            payload["expires_time"]
        ).replace(tzinfo=None)

    def get_access_token(self) -> str:
        """Retrieve or generate access token depending on if token has expired."""
        now = getnow()
        if self._access_token is None or now >= (
            self._expires_at - ApiContext.zimfarm_token_renewal_window
        ):
            if ApiContext.zimfarm_auth_mode == "oauth":
                self._generate_oauth_access_token()
            elif ApiContext.zimfarm_auth_mode == "local":
                self._generate_local_access_token()
            else:
                raise ValueError(
                    "Unknown zimfarm authentication mode: "
                    f"{ApiContext.zimfarm_auth_mode}. Allowed values are: "
                    "'local', 'oauth'"
                )
        if self._access_token is None:
            raise ValueError("Failed to generate access token.")
        return self._access_token

    def get_authorization_header(self) -> dict[str, Any]:
        return {"Authorization": f"Bearer {self.get_access_token()}"}


zimfarm_client_token_provider = ZimfarmClientTokenProvider()
