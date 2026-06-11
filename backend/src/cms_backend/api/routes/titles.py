from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import (
    get_current_account,
    get_current_account_or_none,
    require_permission,
)
from cms_backend.api.routes.fields import (
    LimitFieldMax200,
    NotEmptyString,
    SkipField,
)
from cms_backend.api.routes.http_errors import ForbiddenError
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.account import check_account_permission
from cms_backend.db.models import Account
from cms_backend.db.title import archive_title as db_archive_title
from cms_backend.db.title import archive_titles as db_archive_titles
from cms_backend.db.title import create_title as db_create_title
from cms_backend.db.title import (
    create_title_full_schema,
    create_title_history_schema,
    create_title_light_schema,
)
from cms_backend.db.title import get_title_by_id as db_get_title_by_id
from cms_backend.db.title import get_title_by_name as db_get_title_by_name
from cms_backend.db.title import get_title_history as db_get_title_history
from cms_backend.db.title import get_title_history_entry as db_get_title_history_entry
from cms_backend.db.title import get_titles as db_get_titles
from cms_backend.db.title import merge_titles as db_merge_titles
from cms_backend.db.title import restore_title as db_restore_title
from cms_backend.db.title import restore_titles as db_restore_titles
from cms_backend.db.title import revert_title as db_revert_title
from cms_backend.db.title import update_title as db_update_title
from cms_backend.schemas import BaseModel
from cms_backend.schemas.models import TitleCreateSchema, TitleUpdateSchema
from cms_backend.schemas.orms import (
    TitleFullSchema,
    TitleHistorySchema,
    TitleLightSchema,
)
from cms_backend.utils import is_valid_uuid

router = APIRouter(prefix="/titles", tags=["titles"])


class TitlesGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    name: NotEmptyString | None = None
    collection_name: NotEmptyString | None = None
    archived: bool = False


class RestoreTitlesSchema(BaseModel):
    title_names: list[NotEmptyString] = Field(default_factory=list)


class RevertTitleSchema(BaseModel):
    comment: NotEmptyString | None = None


class MergeTitlesSchema(BaseModel):
    target: NotEmptyString
    sources: list[NotEmptyString]


@router.get("")
def get_titles(
    params: Annotated[TitlesGetSchema, Query()],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account | None = Depends(get_current_account_or_none),
) -> ListResponse[TitleLightSchema]:
    if params.archived and not (
        current_account
        and check_account_permission(current_account, namespace="title", name="archive")
    ):
        raise ForbiddenError("You are not allowed to view archived titles.")
    results = db_get_titles(
        session,
        skip=params.skip,
        limit=params.limit,
        name=params.name,
        collection_name=params.collection_name,
        archived=params.archived,
    )
    return ListResponse[TitleLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.post(
    "/merge",
    dependencies=[
        Depends(require_permission(namespace="title", name="update")),
        Depends(require_permission(namespace="title", name="delete")),
    ],
)
def merge_titles(
    request: MergeTitlesSchema,
    session: OrmSession = Depends(gen_dbsession),
) -> JSONResponse:
    db_merge_titles(session, request.target, request.sources)
    return JSONResponse(
        content={"message": f"Titles have been merged with {request.target}"},
        status_code=HTTPStatus.OK,
    )


@router.get("/{title_identifier}")
def get_title(
    title_identifier: Annotated[NotEmptyString, Path()],
    session: OrmSession = Depends(gen_dbsession),
) -> TitleFullSchema:
    """Get a title by ID with full details including books"""
    if is_valid_uuid(title_identifier):
        title = db_get_title_by_id(session, title_id=UUID(title_identifier))
    else:
        title = db_get_title_by_name(session, name=title_identifier)
    return create_title_full_schema(title)


@router.post(
    "", dependencies=[Depends(require_permission(namespace="title", name="create"))]
)
def create_title(
    title_data: TitleCreateSchema,
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> TitleLightSchema:
    """Create a new title"""
    title = db_create_title(
        session,
        author_id=current_account.id,
        payload=title_data,
    )
    return create_title_light_schema(title)


@router.patch(
    "/{title_identifier}",
    dependencies=[Depends(require_permission(namespace="title", name="update"))],
)
def update_title(
    title_identifier: Annotated[NotEmptyString, Path()],
    title_data: TitleUpdateSchema,
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> TitleLightSchema:
    """Update a title"""
    title = db_update_title(
        session,
        title_identifier=title_identifier,
        author_id=current_account.id,
        payload=title_data,
    )
    return create_title_light_schema(title)


@router.post(
    "/archive",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def archive_titles(
    request: RestoreTitlesSchema,
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> Response:
    db_archive_titles(
        session,
        title_names=request.title_names,
        author_id=current_account.id,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.post(
    "/restore",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def restore_archived_titles(
    request: RestoreTitlesSchema,
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> Response:
    db_restore_titles(
        session,
        title_names=request.title_names,
        author_id=current_account.id,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.patch(
    "/{title_identifier}/archive",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def archive_title(
    title_identifier: Annotated[NotEmptyString, Path()],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> TitleLightSchema:
    """Mark a title as archived"""
    title = db_archive_title(
        session,
        title_identifier=title_identifier,
        author_id=current_account.id,
    )
    return create_title_light_schema(title)


@router.patch(
    "/{title_identifier}/restore",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def restore_archived_title(
    title_identifier: Annotated[NotEmptyString, Path()],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> TitleLightSchema:
    """Restore an archived title"""
    title = db_restore_title(
        session,
        title_identifier=title_identifier,
        author_id=current_account.id,
    )
    return create_title_light_schema(title)


@router.get(
    "/{title_identifier}/history",
    dependencies=[Depends(require_permission(namespace="title", name="update"))],
)
def get_title_history(
    title_identifier: Annotated[NotEmptyString, Path()],
    session: OrmSession = Depends(gen_dbsession),
    skip: Annotated[SkipField, Query()] = 0,
    limit: Annotated[LimitFieldMax200, Query()] = 200,
) -> ListResponse[TitleHistorySchema]:
    results = db_get_title_history(
        session, title_identifier=title_identifier, skip=skip, limit=limit
    )
    return ListResponse(
        items=results.records,
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=skip,
            limit=limit,
            page_size=len(results.records),
        ),
    )


@router.get(
    "/{title_identifier}/history/{history_id}",
    dependencies=[Depends(require_permission(namespace="title", name="update"))],
)
def get_title_history_entry(
    title_identifier: Annotated[NotEmptyString, Path()],
    history_id: Annotated[UUID, Path()],
    session: OrmSession = Depends(gen_dbsession),
) -> TitleHistorySchema:
    history_entry = db_get_title_history_entry(
        session, title_identifier=title_identifier, history_id=history_id
    )
    return create_title_history_schema(history_entry)


@router.patch(
    "/{title_identifier}/revert/{history_id}",
    dependencies=[Depends(require_permission(namespace="title", name="update"))],
)
def revert_title(
    title_identifier: Annotated[NotEmptyString, Path()],
    history_id: Annotated[UUID, Path()],
    request: RevertTitleSchema,
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> JSONResponse:
    """Revert a title to a previous history."""
    db_revert_title(
        session,
        title_identifier=title_identifier,
        history_id=history_id,
        author_id=current_account.id,
        comment=request.comment,
    )
    return JSONResponse(
        content={"message": f"title '{title_identifier}' has been restored"},
        status_code=HTTPStatus.OK,
    )
