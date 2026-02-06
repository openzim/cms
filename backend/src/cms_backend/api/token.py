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
    name: str


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

    @property
    @abc.abstractmethod
    def can_decode(self) -> bool:
        """
        Check if this decoder can potentially decode the given token.
        """
        pass


class OAuthSessionTokenDecoder(TokenDecoder):
    """Decoder for OAuth Session JWT tokens."""

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
                "require": ["exp", "iat", "iss", "sub", "name", "aud", "aal"],
            },
        )

        if (
            Context.oauth_session_login_require_2fa
            and decoded_token.get("aal") != "aal2"
        ):
            raise ValueError(
                "2FA authentication is mandatory on CMS but it looks like you only "
                "have one setup on Ory. Please, configure a second one on Ory at "
                "https://login.kiwix.org/settings"
            )
        return JWTClaims.model_validate(decoded_token)

    @property
    def name(self) -> str:
        return "oauth-session"

    @property
    def can_decode(self) -> bool:
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
        decoders = [decoder for decoder in self.decoders if decoder.can_decode]
        if not decoders:
            raise ValueError("No decoders registered for decoding token.")

        for decoder in decoders:
            if decoder.can_decode:
                try:
                    return decoder.decode(token)
                except (
                    jwt_exceptions.PyJWTError,
                    PydanticValidationError,
                    Exception,
                ) as exc:
                    logger.debug(f"{decoder.name}: unable to decode token: {exc!s}")
                    # keep track of the most recent exception class
                    exc_cls = exc

        if exc_cls:
            raise exc_cls

        raise ValueError("Inavlid token")


token_decoder = TokenDecoderChain(decoders=[OAuthSessionTokenDecoder()])
