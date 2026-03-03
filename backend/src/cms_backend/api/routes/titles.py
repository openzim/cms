from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import model_validator
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import require_permission
from cms_backend.api.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.title import create_title as db_create_title
from cms_backend.db.title import create_title_full_schema
from cms_backend.db.title import get_title_by_id as db_get_title_by_id
from cms_backend.db.title import get_title_by_name as db_get_title_by_name
from cms_backend.db.title import get_titles as db_get_titles
from cms_backend.db.title import update_title as db_update_title
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import (
    BaseTitleCollectionSchema,
    TitleFullSchema,
    TitleLightSchema,
)
from cms_backend.utils.datetime import is_valid_uuid

router = APIRouter(prefix="/titles", tags=["titles"])


class TitlesGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    name: NotEmptyString | None = None


class BaseTitleCreateUpdateSchema(BaseModel):
    collection_titles: list[BaseTitleCollectionSchema] | None = None

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
    maturity: Literal["dev", "robust"] = "dev"


class TitleUpdateSchema(BaseTitleCreateUpdateSchema):
    name: NotEmptyString | None = None
    maturity: Literal["dev", "robust"] | None = None


@router.get("")
def get_titles(
    params: Annotated[TitlesGetSchema, Query()],
    session: OrmSession = Depends(gen_dbsession),
) -> ListResponse[TitleLightSchema]:
    results = db_get_titles(
        session,
        skip=params.skip,
        limit=params.limit,
        name=params.name,
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
    )
    return TitleLightSchema(
        id=title.id,
        name=title.name,
        maturity=title.maturity,
    )


@router.patch(
    "/{title_id}",
    dependencies=[Depends(require_permission(namespace="title", name="update"))],
)
def update_title(
    title_id: UUID,
    title_data: TitleUpdateSchema,
    session: OrmSession = Depends(gen_dbsession),
) -> TitleLightSchema:
    """Update a title's maturity and/or collection_titles"""
    title = db_update_title(
        session,
        title_id=title_id,
        name=title_data.name,
        maturity=title_data.maturity,
        collection_titles=title_data.collection_titles,
    )
    return TitleLightSchema(
        id=title.id,
        name=title.name,
        maturity=title.maturity,
    )
