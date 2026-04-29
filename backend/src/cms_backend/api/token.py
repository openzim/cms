import abc
import datetime
import uuid

import jwt
from jwt import PyJWKClient
from jwt import exceptions as jwt_exceptions
from pydantic import Field
from pydantic import ValidationError as PydanticValidationError

from cms_backend import logger
from cms_backend.api.context import Context
from cms_backend.schemas import BaseModel


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

    def __init__(self, secret: str = Context.jwt_secret, algorithm: str = "HS256"):
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
        return "local" in Context.auth_modes

        if "local" not in Context.auth_modes:
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

        if payload.get("iss") != Context.jwt_token_issuer:
            return False

        return True


class OAuthTokenDecoder(TokenDecoder):
    """Decoder for OAuth JWT tokens."""

    def __init__(self):
        """Initialize OAuth token decoder."""
        self._jwks_client = PyJWKClient(
            Context.oauth_jwks_uri,
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
            issuer=Context.oauth_issuer,
            audience=Context.oauth_session_audience_id,
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
            and Context.oauth_session_login_require_2fa
            and decoded_token.get("aal") != "aal2"
        ):
            raise ValueError(
                "2FA authentication is mandatory on CMS but it looks like you only "
                "have one setup on Ory. Please, configure a second one on Ory at "
                f"{Context.oauth_issuer}/settings"
            )
        return JWTClaims.model_validate(decoded_token)

    @property
    def name(self) -> str:
        return "oauth"

    def can_decode(self, token: str) -> bool:
        if "oauth-session" not in Context.auth_modes:
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
            payload.get("iss") != Context.oauth_issuer
            or Context.oauth_session_audience_id not in payload.get("aud", [])
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
        seconds=Context.jwt_token_expiry_duration
    )
    payload = {
        "iss": Context.jwt_token_issuer,  # issuer
        "exp": expire_time.timestamp(),  # expiration time
        "iat": issue_time.timestamp(),  # issued at
        "subject": account_id,
    }
    return jwt.encode(payload, key=Context.jwt_secret, algorithm="HS256")
