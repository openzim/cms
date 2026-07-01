from http import HTTPStatus
from typing import Annotated
from uuid import UUID

import xxhash
from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse, Response
from pydantic import AnyUrl, Field
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import get_current_account, require_permission
from cms_backend.api.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.api.routes.utils import build_library_xml
from cms_backend.db import gen_dbsession
from cms_backend.db.collection import create_collection as db_create_collection
from cms_backend.db.collection import (
    create_collection_full_schema,
    create_collection_history_schema,
    get_collection_by_name_or_none,
    get_latest_books_for_collection,
)
from cms_backend.db.collection import get_collection as db_get_collection
from cms_backend.db.collection import (
    get_collection_history as db_get_collection_history,
)
from cms_backend.db.collection import (
    get_collection_history_entry as db_get_collection_history_entry,
)
from cms_backend.db.collection import get_collections as db_get_collections
from cms_backend.db.collection import (
    revert_collection as db_revert_collection,
)
from cms_backend.db.collection import update_collection as db_update_collection
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Account
from cms_backend.schemas import BaseModel
from cms_backend.schemas.models import CollectionUpdateSchema
from cms_backend.schemas.orms import (
    CollectionFullSchema,
    CollectionHistorySchema,
    CollectionLightSchema,
)

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionsGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    name: NotEmptyString | None = None


class RevertCollectionSchema(BaseModel):
    comment: NotEmptyString | None = None


@router.get("")
def get_collections(
    params: Annotated[CollectionsGetSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[CollectionLightSchema]:
    """Get a list of collections"""

    results = db_get_collections(
        session, skip=params.skip, limit=params.limit, name=params.name
    )

    return ListResponse[CollectionLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


class CollectionCreateSchema(BaseModel):
    name: NotEmptyString = Field(min_length=3)
    warehouse_name: NotEmptyString = Field(min_length=3)
    download_base_url: AnyUrl | None = None
    view_base_url: AnyUrl | None = None
    article_count_increase_threshold: float | None = Field(ge=0.0, le=1.0, default=None)
    media_count_increase_threshold: float | None = Field(ge=0.0, le=1.0, default=None)
    article_count_decrease_threshold: float | None = Field(ge=0.0, le=1.0, default=None)
    media_count_decrease_threshold: float | None = Field(ge=0.0, le=1.0, default=None)


@router.post(
    "",
    dependencies=[Depends(require_permission(namespace="collection", name="create"))],
)
def create_collection(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    current_account: Annotated[Account, Depends(get_current_account)],
    request: CollectionCreateSchema,
):
    """Create a collection"""
    return create_collection_full_schema(
        db_create_collection(
            session,
            author_id=current_account.id,
            name=request.name,
            warehouse_name=request.warehouse_name,
            download_base_url=(
                str(request.download_base_url)
                if request.download_base_url is not None
                else None
            ),
            view_base_url=(
                str(request.view_base_url)
                if request.view_base_url is not None
                else None
            ),
            article_count_increase_threshold=request.article_count_increase_threshold,
            article_count_decrease_threshold=request.article_count_decrease_threshold,
            media_count_increase_threshold=request.media_count_increase_threshold,
            media_count_decrease_threshold=request.media_count_decrease_threshold,
        )
    )


@router.get("/{collection_id_or_name}")
def get_collection(
    collection_id_or_name: Annotated[str, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
):
    """Get collection by collection ID (UUID) or name."""
    collection = db_get_collection(session, collection_id_or_name)
    return create_collection_full_schema(collection)


@router.patch(
    "/{collection_id_or_name}",
    dependencies=[Depends(require_permission(namespace="collection", name="update"))],
)
def update_collection(
    collection_id_or_name: Annotated[str, Path()],
    current_account: Annotated[Account, Depends(get_current_account)],
    collection_data: CollectionUpdateSchema,
    session: OrmSession = Depends(gen_dbsession),
) -> CollectionFullSchema:
    """Update a collection's data"""
    return create_collection_full_schema(
        db_update_collection(
            session,
            collection_id=collection_id_or_name,
            request=collection_data,
            author_id=current_account.id,
        )
    )


def _get_catalog_xml_content(
    collection_id_or_name: str, session: OrmSession, path_prefix: str | None
) -> tuple[str, int]:
    # Try to parse as UUID first, otherwise treat as name
    collection = None
    try:
        try:
            collection = db_get_collection(session, collection_id_or_name)
        except RecordDoesNotExistError:
            pass
    except ValueError:
        # Not a valid UUID, try as name
        collection = get_collection_by_name_or_none(session, collection_id_or_name)

    if collection is None:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<library version="20110515"></library>',
            HTTPStatus.NOT_FOUND,
        )

    entries = get_latest_books_for_collection(session, collection.id)
    xml_content = build_library_xml(entries, path_prefix=path_prefix)

    return xml_content, HTTPStatus.OK


@router.get("/{collection_id_or_name}/catalog.xml")
def get_library_catalog_xml(
    collection_id_or_name: Annotated[str, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    path_prefix: Annotated[str | None, Query()] = None,
):
    """Get collection catalog as XML library by collection ID (UUID) or name."""
    xml_content, status_code = _get_catalog_xml_content(
        collection_id_or_name, session, path_prefix
    )
    etag = xxhash.xxh64(xml_content.encode("utf-8")).hexdigest()

    return Response(
        content=xml_content,
        status_code=status_code,
        media_type="application/xml",
        headers={"ETag": f"{etag}"},
    )


@router.head("/{collection_id_or_name}/catalog.xml")
def head_library_catalog_xml(
    collection_id_or_name: Annotated[str, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    path_prefix: Annotated[str | None, Query()] = None,
):
    """Get collection catalog as XML library by collection ID (UUID) or name."""
    xml_content, status_code = _get_catalog_xml_content(
        collection_id_or_name, session, path_prefix
    )
    etag = xxhash.xxh64(xml_content.encode("utf-8")).hexdigest()
    return Response(
        status_code=status_code,
        headers={"ETag": f"{etag}"},
        media_type="application/xml",
    )


@router.get(
    "/{collection_id_or_name}/history",
    dependencies=[Depends(require_permission(namespace="collection", name="update"))],
)
def get_collection_history(
    collection_id_or_name: Annotated[NotEmptyString, Path()],
    session: OrmSession = Depends(gen_dbsession),
    skip: Annotated[SkipField, Query()] = 0,
    limit: Annotated[LimitFieldMax200, Query()] = 200,
) -> ListResponse[CollectionHistorySchema]:
    results = db_get_collection_history(
        session, collection_id=collection_id_or_name, skip=skip, limit=limit
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
    "/{collection_id_or_name}/history/{history_id}",
    dependencies=[Depends(require_permission(namespace="collection", name="update"))],
)
def get_collection_history_entry(
    collection_id_or_name: Annotated[NotEmptyString, Path()],
    history_id: Annotated[UUID, Path()],
    session: OrmSession = Depends(gen_dbsession),
) -> CollectionHistorySchema:
    history_entry = db_get_collection_history_entry(
        session, collection_id=collection_id_or_name, history_id=history_id
    )
    return create_collection_history_schema(history_entry)


@router.patch(
    "/{collection_id_or_name}/revert/{history_id}",
    dependencies=[Depends(require_permission(namespace="collection", name="update"))],
)
def revert_collection(
    collection_id_or_name: Annotated[NotEmptyString, Path()],
    history_id: Annotated[UUID, Path()],
    request: RevertCollectionSchema,
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> JSONResponse:
    """Revert a collection to a previous history."""
    db_revert_collection(
        session,
        collection_id=collection_id_or_name,
        history_id=history_id,
        author_id=current_account.id,
        comment=request.comment,
    )
    return JSONResponse(
        content={"message": f"collection '{collection_id_or_name}' has been restored"},
        status_code=HTTPStatus.OK,
    )
