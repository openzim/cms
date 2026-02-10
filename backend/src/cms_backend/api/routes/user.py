from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response
from sqlalchemy.orm import Session as OrmSession
from werkzeug.security import check_password_hash, generate_password_hash

from cms_backend.api.routes.dependencies import get_current_user, require_permission
from cms_backend.api.routes.fields import NotEmptyString
from cms_backend.api.routes.http_errors import BadRequestError, UnauthorizedError
from cms_backend.db import gen_dbsession
from cms_backend.db.models import User
from cms_backend.db.user import (
    check_user_permission,
    create_user_schema,
    get_user_by_username,
)
from cms_backend.db.user import create_user as db_create_user
from cms_backend.db.user import delete_user as db_delete_user
from cms_backend.db.user import update_user_password as db_update_user_password
from cms_backend.roles import RoleEnum
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import UserSchema

router = APIRouter(prefix="/users", tags=["users"])


class UserCreateSchema(BaseModel):
    """
    Schema for creating a user
    """

    username: NotEmptyString
    password: NotEmptyString
    role: RoleEnum


class PasswordUpdateSchema(BaseModel):
    """
    Schema for updating a user's password
    """

    # users with elevated permissions can omit the current password
    current: NotEmptyString | None = None
    new: NotEmptyString


@router.post(
    "", dependencies=[Depends(require_permission(namespace="user", name="create"))]
)
def create_user(
    user_schema: UserCreateSchema,
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> UserSchema:
    user = db_create_user(
        db_session,
        username=user_schema.username,
        password_hash=generate_password_hash(user_schema.password),
        role=user_schema.role,
    )

    return create_user_schema(user)


@router.delete(
    "/{username}",
    dependencies=[Depends(require_permission(namespace="user", name="delete"))],
)
def delete_user(
    username: Annotated[str, Path()],
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> Response:
    """Delete a specific user"""
    user = get_user_by_username(db_session, username=username)
    db_delete_user(db_session, user_id=user.id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.patch("/{username}/password")
def update_user_password(
    username: Annotated[str, Path()],
    password_update: PasswordUpdateSchema,
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Update a user's password"""
    user = get_user_by_username(db_session, username=username)

    if current_user.username == username:
        if password_update.current is None:
            raise BadRequestError("You must enter your current password.")

        if not check_password_hash(
            current_user.password_hash or "", password_update.current
        ):
            raise BadRequestError()

    elif not check_user_permission(current_user, namespace="user", name="update"):
        raise UnauthorizedError("You are not allowed to access this resource")

    db_update_user_password(
        db_session,
        user_id=user.id,
        password_hash=generate_password_hash(password_update.new),
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)
