import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session as OrmSession
from werkzeug.security import check_password_hash

from cms_backend.api.context import Context
from cms_backend.api.routes.dependencies import get_current_user
from cms_backend.api.routes.http_errors import UnauthorizedError
from cms_backend.api.token import generate_access_token
from cms_backend.db import gen_dbsession
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import User
from cms_backend.db.refresh_token import (
    create_refresh_token,
    delete_refresh_token,
    expire_refresh_tokens,
    get_refresh_token,
)
from cms_backend.db.user import create_user_schema, get_user_by_username
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import UserSchema
from cms_backend.utils.datetime import getnow

router = APIRouter(prefix="/auth", tags=["auth"])


class CredentialsIn(BaseModel):
    username: str
    password: str


class RefreshTokenIn(BaseModel):
    refresh_token: UUID


class Token(BaseModel):
    """Access token on successful authentication."""

    access_token: str
    token_type: str = "Bearer"
    expires_time: datetime.datetime
    refresh_token: str


def _access_token_response(db_session: OrmSession, db_user: User, response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    issue_time = getnow()
    return Token(
        access_token=generate_access_token(
            user_id=str(db_user.id),
            issue_time=issue_time,
        ),
        refresh_token=str(
            create_refresh_token(session=db_session, user_id=db_user.id).token
        ),
        expires_time=issue_time
        + datetime.timedelta(seconds=Context.jwt_token_expiry_duration),
    )


def _auth_with_credentials(
    db_session: OrmSession, credentials: CredentialsIn, response: Response
):
    """Authorize a user with username and password."""
    try:
        db_user = get_user_by_username(db_session, username=credentials.username)
    except RecordDoesNotExistError as exc:
        raise UnauthorizedError() from exc

    if not (
        db_user.password_hash
        and check_password_hash(db_user.password_hash, credentials.password)
    ):
        raise UnauthorizedError("Invalid credentials")

    return _access_token_response(db_session, db_user, response)


def _refresh_access_token(
    db_session: OrmSession, refresh_token: UUID, response: Response
):
    """Issue a new set of access and refresh tokens."""
    try:
        db_refresh_token = get_refresh_token(db_session, token=refresh_token)
    except RecordDoesNotExistError as exc:
        raise UnauthorizedError() from exc

    now = getnow()
    if db_refresh_token.expire_time < now:
        raise UnauthorizedError("Refresh token expired")

    delete_refresh_token(db_session, token=refresh_token)
    expire_refresh_tokens(db_session, expire_time=now)

    return _access_token_response(db_session, db_refresh_token.user, response)


@router.post("/authorize")
def auth_with_credentials(
    credentials: CredentialsIn,
    response: Response,
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> Token:
    """Authorize a user with username and password."""
    return _auth_with_credentials(db_session, credentials, response)


@router.post("/refresh")
def refresh_access_token(
    request: RefreshTokenIn,
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
    response: Response,
) -> Token:
    return _refresh_access_token(db_session, request.refresh_token, response)


@router.get("/me")
def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserSchema:
    """Get the current authenticated user's information including scopes."""
    return create_user_schema(current_user)
