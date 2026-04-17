from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.fields import LimitFieldMax200, SkipField
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.api.routes.utils import build_library_xml
from cms_backend.db import gen_dbsession
from cms_backend.db.collection import (
    get_collection,
    get_collection_by_name_or_none,
    get_latest_books_for_collection,
)
from cms_backend.db.collection import get_collections as db_get_collections
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import CollectionLightSchema

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionsGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20


@router.get("")
async def get_collections(
    params: Annotated[CollectionsGetSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[CollectionLightSchema]:
    """Get a list of collections"""

    results = db_get_collections(session, skip=params.skip, limit=params.limit)

    return ListResponse[CollectionLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.get("/{collection_id_or_name}/catalog.xml")
async def get_library_catalog_xml(
    collection_id_or_name: Annotated[str, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
):
    """Get collection catalog as XML library by collection ID (UUID) or name."""
    # Try to parse as UUID first, otherwise treat as name
    collection = None
    try:
        collection_id = UUID(collection_id_or_name)
        try:
            collection = get_collection(session, collection_id)
        except RecordDoesNotExistError:
            pass
    except ValueError:
        # Not a valid UUID, try as name
        collection = get_collection_by_name_or_none(session, collection_id_or_name)

    if collection is None:
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?>'
            '<library version="20110515"></library>',
            status_code=HTTPStatus.NOT_FOUND,
            media_type="application/xml",
        )

    entries = get_latest_books_for_collection(session, collection.id)
    xml_content = build_library_xml(entries)

    return Response(
        content=xml_content,
        status_code=HTTPStatus.OK,
        media_type="application/xml",
    )
