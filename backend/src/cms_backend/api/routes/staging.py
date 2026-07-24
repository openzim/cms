from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

import xxhash
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import get_accessible_collection_ids
from cms_backend.api.routes.utils import build_library_xml
from cms_backend.db import gen_dbsession
from cms_backend.db import staging as db_staging

router = APIRouter(prefix="/staging", tags=["staging"])


@router.get("/catalog.xml")
async def get_library_catalog_xml(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    path_prefix: Annotated[str | None, Query()] = None,
):
    """Get staging catalog as XML library."""

    entries = db_staging.get_staging_books_library_data(
        session, accessible_collection_ids=accessible_collection_ids
    )
    xml_content = build_library_xml(entries, path_prefix=path_prefix)
    etag = xxhash.xxh64(xml_content.encode("utf-8")).hexdigest()

    return Response(
        content=xml_content,
        headers={"ETag": f"{etag}"},
        status_code=HTTPStatus.OK,
        media_type="application/xml",
    )


@router.head("/catalog.xml")
async def head_library_catalog_xml(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    path_prefix: Annotated[str | None, Query()] = None,
):
    entries = db_staging.get_staging_books_library_data(
        session, accessible_collection_ids=accessible_collection_ids
    )
    xml_content = build_library_xml(entries, path_prefix=path_prefix)
    etag = xxhash.xxh64(xml_content.encode("utf-8")).hexdigest()
    return Response(
        status_code=HTTPStatus.OK,
        headers={"ETag": f"{etag}"},
        media_type="application/xml",
    )
