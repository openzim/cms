from http import HTTPStatus
from typing import Annotated, Self, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response
from pydantic import Field, model_validator
from sqlalchemy.orm import Session as OrmSession
from werkzeug.security import check_password_hash, generate_password_hash

from cms_backend.api.routes.dependencies import get_current_account, require_permission
from cms_backend.api.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.api.routes.http_errors import BadRequestError, ForbiddenError
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.account import (
    check_account_permission,
    create_account_schema,
    get_account_by_identifier,
)
from cms_backend.db.account import create_account as db_create_account
from cms_backend.db.account import delete_account as db_delete_account
from cms_backend.db.account import get_accounts as db_get_accounts
from cms_backend.db.account import update_account as db_update_account
from cms_backend.db.account import update_account_password as db_update_account_password
from cms_backend.db.models import Account
from cms_backend.roles import RoleEnum
from cms_backend.schemas import BaseModel
from cms_backend.schemas.models import AccountUpdateSchema
from cms_backend.schemas.orms import AccountSchema
from cms_backend.utils import is_valid_uuid

router = APIRouter(prefix="/accounts", tags=["account"])


def require_permission_if_not_self(namespace: str, name: str):
    """Ensure that an account has permission to access another account's resource.

    This uses the identifier in the path parameter to check against the current
    account.
    """

    def _require_permission_if_not_self(
        account_identifier: Annotated[str, Path()],
        current_account: Annotated[Account, Depends(get_current_account)],
    ):
        if (
            is_valid_uuid(account_identifier)
            and account_identifier == str(current_account.id)
        ) or (account_identifier == current_account.username):
            return

        if not check_account_permission(
            current_account, namespace=namespace, name=name
        ):
            raise ForbiddenError("You are not allowed to access this resource")

    return _require_permission_if_not_self


class AccountsGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    username: NotEmptyString | None = None
    show_zimfarmers: bool = True  # show accounts which have "zimfarm" role
    show_viewers: bool = True  # show accounts which have "viewer" role


@router.get(
    "", dependencies=[Depends(require_permission(namespace="account", name="read"))]
)
def get_accounts(
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
    params: Annotated[AccountsGetSchema, Query()],
) -> ListResponse[AccountSchema]:
    """Get a list of accounts"""
    results = db_get_accounts(
        db_session,
        skip=params.skip,
        limit=params.limit,
        username=params.username,
        show_zimfarmers=params.show_zimfarmers,
        show_viewers=params.show_viewers,
    )
    return ListResponse(
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=[create_account_schema(account) for account in results.records],
    )


class AccountCreateSchema(BaseModel):
    """
    Schema for creating an account
    """

    username: NotEmptyString | None = Field(default=None, min_length=3)
    display_name: NotEmptyString | None = Field(default=None, min_length=3)
    password: NotEmptyString | None = Field(default=None, min_length=8)
    role: RoleEnum
    idp_sub: UUID | None = None

    @model_validator(mode="after")
    def check_username_and_displayname(self) -> Self:
        if not (self.username or self.display_name):
            raise ValueError("Display name or username must be set.")

        if not self.display_name:
            self.display_name = self.username

        return self

    @model_validator(mode="after")
    def check_role(self) -> Self:
        if self.role == RoleEnum.ZIMFARM:
            raise ValueError("Zimfarm accounts cannot be created.")
        return self

    @model_validator(mode="after")
    def check_username_and_password(self) -> Self:
        if self.password and not self.username:
            raise ValueError("Username must be set when password is set.")
        return self


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
        display_name=cast(str, account_schema.display_name),
        role=account_schema.role,
        password_hash=(
            generate_password_hash(account_schema.password)
            if account_schema.password
            else None
        ),
    )

    return create_account_schema(account)


@router.get(
    "/{account_identifier}",
    dependencies=[
        Depends(require_permission_if_not_self(namespace="account", name="read"))
    ],
)
def get_account(
    account_identifier: Annotated[str, Path()],
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> AccountSchema:
    """Get a specific account"""
    account = get_account_by_identifier(
        db_session, account_identifier=account_identifier
    )
    return create_account_schema(account)


@router.patch(
    "/{account_identifier}",
    dependencies=[Depends(require_permission(namespace="account", name="update"))],
)
def update_account(
    account_identifier: Annotated[str, Path()],
    request: AccountUpdateSchema,
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> Response:
    """Update a specific account"""
    db_update_account(
        db_session,
        account_id=account_identifier,
        request=request,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.delete(
    "/{account_identifier}",
    dependencies=[Depends(require_permission(namespace="account", name="delete"))],
)
def delete_account(
    account_identifier: Annotated[str, Path()],
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> Response:
    """Delete a specific account"""
    account = get_account_by_identifier(
        db_session, account_identifier=account_identifier
    )
    db_delete_account(db_session, account_id=account.id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


class PasswordUpdateSchema(BaseModel):
    """
    Schema for updating an account's password
    """

    # account with elevated permissions can omit the current password
    current: NotEmptyString | None = None
    new: NotEmptyString | None


@router.patch(
    "/{account_identifier}/password",
    dependencies=[
        Depends(require_permission_if_not_self(namespace="account", name="update"))
    ],
)
def update_account_password(
    account_identifier: Annotated[str, Path()],
    password_update: PasswordUpdateSchema,
    db_session: Annotated[OrmSession, Depends(gen_dbsession)],
    current_account: Annotated[Account, Depends(get_current_account)],
) -> Response:
    """Update an account's password"""
    account = get_account_by_identifier(
        db_session, account_identifier=account_identifier
    )
    if not account.username:
        raise BadRequestError("Only accounts with username can have passwords.")

    # Accounts without necessary permissions that are changing their own password must
    #  provide their password if one exists and it must match the existing one
    if (
        current_account.id == account.id
        and account.password_hash is not None
        and not check_account_permission(
            current_account, namespace="account", name="update"
        )
    ):
        if password_update.current is None:
            raise BadRequestError("You must enter your current password.")

        if not check_password_hash(account.password_hash, password_update.current):
            raise BadRequestError()

    db_update_account_password(
        db_session,
        account_id=account.id,
        password_hash=(
            generate_password_hash(password_update.new) if password_update.new else None
        ),
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)
