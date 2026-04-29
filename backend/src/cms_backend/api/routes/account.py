from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response
from sqlalchemy.orm import Session as OrmSession
from werkzeug.security import check_password_hash, generate_password_hash

from cms_backend.api.routes.dependencies import get_current_account, require_permission
from cms_backend.api.routes.fields import NotEmptyString
from cms_backend.api.routes.http_errors import BadRequestError, UnauthorizedError
from cms_backend.db import gen_dbsession
from cms_backend.db.account import (
    check_account_permission,
    create_account_schema,
    get_account_by_username,
)
from cms_backend.db.account import create_account as db_create_account
from cms_backend.db.account import delete_account as db_delete_account
from cms_backend.db.account import update_account_password as db_update_account_password
from cms_backend.db.models import Account
from cms_backend.roles import RoleEnum
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import AccountSchema

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreateSchema(BaseModel):
    """
    Schema for creating an account
    """

    username: NotEmptyString
    password: NotEmptyString
    role: RoleEnum


class PasswordUpdateSchema(BaseModel):
    """
    Schema for updating an account's password
    """

    # account with elevated permissions can omit the current password
    current: NotEmptyString | None = None
    new: NotEmptyString


@router.post(
    "",
    dependencies=[Depends(require_permission(namespace="account", name="create"))],
)
def create_account(
    account_schema: AccountCreateSchema,
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> AccountSchema:
    account = db_create_account(
        db_session,
        username=account_schema.username,
        password_hash=generate_password_hash(account_schema.password),
        role=account_schema.role,
    )

    return create_account_schema(account)


@router.delete(
    "/{username}",
    dependencies=[Depends(require_permission(namespace="account", name="delete"))],
)
def delete_account(
    username: Annotated[str, Path()],
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> Response:
    """Delete a specific account"""
    account = get_account_by_username(db_session, username=username)
    db_delete_account(db_session, account_id=account.id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.patch("/{username}/password")
def update_account_password(
    username: Annotated[str, Path()],
    password_update: PasswordUpdateSchema,
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
    current_account: Annotated[Account, Depends(get_current_account)],
) -> Response:
    """Update an account's password"""
    account = get_account_by_username(db_session, username=username)

    if current_account.username == username:
        if password_update.current is None:
            raise BadRequestError("You must enter your current password.")

        if not check_password_hash(
            current_account.password_hash or "", password_update.current
        ):
            raise BadRequestError()

    elif not check_account_permission(
        current_account, namespace="account", name="update"
    ):
        raise UnauthorizedError("You are not allowed to access this resource")

    db_update_account_password(
        db_session,
        account_id=account.id,
        password_hash=generate_password_hash(password_update.new),
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)
