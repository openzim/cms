from typing import Annotated, Literal

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import exceptions as jwt_exceptions
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.context import Context
from cms_backend.api.routes.http_errors import UnauthorizedError
from cms_backend.api.token import JWTClaims, token_decoder
from cms_backend.db import gen_dbsession, gen_manual_dbsession
from cms_backend.db.models import User
from cms_backend.db.user import (
    check_user_permission,
    create_user,
    get_user_by_id_or_none,
)
from cms_backend.roles import RoleEnum

security = HTTPBearer(description="Access Token", auto_error=False)
AuthorizationCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(security)
]


def get_jwt_claims_or_none(
    authorization: AuthorizationCredentials,
) -> JWTClaims | None:
    """
    Get the JWT claims or None if the user is not authenticated.
    """
    if authorization is None:
        return None
    token = authorization.credentials

    try:
        return token_decoder.decode(token)
    except jwt_exceptions.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired.") from exc
    except (jwt_exceptions.InvalidTokenError, jwt_exceptions.PyJWTError) as exc:
        raise UnauthorizedError("Invalid token") from exc
    except ValueError as exc:
        raise UnauthorizedError(exc.args[0]) from exc
    except Exception as exc:
        raise UnauthorizedError("Unable to verify token") from exc


def get_current_user_or_none_with_session(
    session_type: Literal["auto", "manual"] = "auto",
):
    def _get_current_user_or_none(
        claims: Annotated[JWTClaims | None, Depends(get_jwt_claims_or_none)],
        session: Annotated[
            OrmSession,
            Depends(gen_dbsession if session_type == "auto" else gen_manual_dbsession),
        ],
    ) -> User | None:
        if claims is None:
            return None
        user = get_user_by_id_or_none(session, user_id=claims.sub)
        # If this is a kiwix token (wilkl  have a name), we create a new user account
        if user is None and Context.create_new_oauth_account:
            if not claims.name:
                raise UnauthorizedError("Token is missing 'profile' scope")
            create_user(
                session,
                username=claims.name,
                role=RoleEnum.VIEWER,
                idp_sub=claims.sub,
            )
            user = get_user_by_id_or_none(session, user_id=claims.sub)

        return user

    return _get_current_user_or_none


def get_current_user_with_session(
    session_type: Literal["auto", "manual"] = "auto",
):
    def _get_current_user(
        user: Annotated[
            User | None,
            Depends(get_current_user_or_none_with_session(session_type=session_type)),
        ],
    ) -> User:
        # If we get here, it means the token was valid but the user being None
        # means their idp_sub or id doesn't exist on the database or they have been
        # marked as deleted.
        if user is None:
            raise UnauthorizedError(
                "This account is not yet authorized on the CMS. "
                "Please contact CMS admins."
            )

        if user.deleted:
            raise UnauthorizedError("This account does not exist on the CMS.")

        return user

    return _get_current_user


# Convenience functions for common cases
get_current_user_or_none = get_current_user_or_none_with_session(session_type="auto")
get_current_user = get_current_user_with_session(session_type="auto")


def require_permission(*, namespace: str, name: str):
    """
    checks if the current user has a specific permission.
    """

    def _check_permission(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not check_user_permission(current_user, namespace=namespace, name=name):
            raise UnauthorizedError(
                "You do not have permission to perform this action. "
            )
        return current_user

    return _check_permission
