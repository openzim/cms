from http import HTTPStatus
from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import Field, model_validator
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import (
    get_current_account_or_none,
    require_permission,
)
from cms_backend.api.routes.fields import (
    Base64Str,
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
from cms_backend.db.title import create_title_full_schema, create_title_light_schema
from cms_backend.db.title import get_title_by_id as db_get_title_by_id
from cms_backend.db.title import get_title_by_name as db_get_title_by_name
from cms_backend.db.title import get_titles as db_get_titles
from cms_backend.db.title import restore_title as db_restore_title
from cms_backend.db.title import restore_titles as db_restore_titles
from cms_backend.db.title import update_title as db_update_title
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import (
    BaseTitleCollectionSchema,
    TitleFullSchema,
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


class BaseTitleCreateUpdateSchema(BaseModel):
    collection_titles: list[BaseTitleCollectionSchema] | None = None
    long_description: NotEmptyString | None = None
    license: NotEmptyString | None = None
    relation: NotEmptyString | None = None
    source: NotEmptyString | None = None

    @model_validator(mode="after")
    def validate_unique_collection_titles(self) -> Self:
        if self.collection_titles:
            seen: set[str] = set()
            for entry in self.collection_titles:
                if entry.collection_name in seen:
                    raise ValueError(
                        f"Collection title {entry.collection_name} duplicated, "
                        "cannot use a collection twice in a given title"
                    )
                else:
                    seen.add(entry.collection_name)
        return self


class TitleCreateSchema(BaseTitleCreateUpdateSchema):
    name: NotEmptyString
    maturity: Literal["unstable", "stable"] = "unstable"
    title: NotEmptyString
    creator: NotEmptyString
    publisher: NotEmptyString
    language: NotEmptyString
    description: NotEmptyString
    illustration_48x48_at_1: Base64Str


class TitleUpdateSchema(BaseTitleCreateUpdateSchema):
    name: NotEmptyString | None = None
    maturity: Literal["unstable", "stable"] | None = None
    title: NotEmptyString | None = None
    creator: NotEmptyString | None = None
    description: NotEmptyString | None = None
    publisher: NotEmptyString | None = None
    language: NotEmptyString | None = None
    illustration_48x48_at_1: Base64Str | None = None


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


@router.get("/{title_identifier}")
def get_title(
    title_identifier: str,
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
) -> TitleLightSchema:
    """Create a new title"""
    title = db_create_title(
        session,
        name=title_data.name,
        maturity=title_data.maturity,
        collection_titles=title_data.collection_titles,
        _title=title_data.title,
        creator=title_data.creator,
        publisher=title_data.publisher,
        language=title_data.language,
        illustration_48x48_at_1=title_data.illustration_48x48_at_1,
        license_=title_data.license,
        relation=title_data.relation,
        source=title_data.source,
        long_description=title_data.long_description,
        description=title_data.description,
    )
    return create_title_light_schema(title)


@router.patch(
    "/{title_id}",
    dependencies=[Depends(require_permission(namespace="title", name="update"))],
)
def update_title(
    title_id: UUID,
    title_data: TitleUpdateSchema,
    session: OrmSession = Depends(gen_dbsession),
) -> TitleLightSchema:
    """Update a title"""
    title = db_update_title(
        session,
        title_id=title_id,
        name=title_data.name,
        maturity=title_data.maturity,
        collection_titles=title_data.collection_titles,
        _title=title_data.title,
        creator=title_data.creator,
        description=title_data.description,
        long_description=title_data.long_description,
        publisher=title_data.publisher,
        language=title_data.language,
        illustration_48x48_at_1=title_data.illustration_48x48_at_1,
        license_=title_data.license,
        relation=title_data.relation,
        source=title_data.source,
    )
    return create_title_light_schema(title)


@router.post(
    "/archive",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def archive_titles(
    request: RestoreTitlesSchema,
    session: OrmSession = Depends(gen_dbsession),
) -> Response:
    db_archive_titles(
        session,
        title_names=request.title_names,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.post(
    "/restore",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def restore_archived_titles(
    request: RestoreTitlesSchema,
    session: OrmSession = Depends(gen_dbsession),
) -> Response:
    db_restore_titles(
        session,
        title_names=request.title_names,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.patch(
    "/{title_id}/archive",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def archive_title(
    title_id: NotEmptyString,
    session: OrmSession = Depends(gen_dbsession),
) -> TitleLightSchema:
    """Mark a title as archived"""
    title = db_archive_title(
        session,
        title_identifier=title_id,
    )
    return create_title_light_schema(title)


@router.patch(
    "/{title_id}/restore",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def restore_archived_title(
    title_id: NotEmptyString,
    session: OrmSession = Depends(gen_dbsession),
) -> TitleLightSchema:
    """Restore an archived title"""
    title = db_restore_title(
        session,
        title_identifier=title_id,
    )
    return create_title_light_schema(title)
