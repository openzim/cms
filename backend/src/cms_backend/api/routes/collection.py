import math
from http import HTTPStatus
from typing import Annotated
from uuid import UUID
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.fields import LimitFieldMax200, SkipField
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.collection import (
    CollectionBook,
    get_collection,
    get_collection_by_name_or_none,
    get_latest_books_for_collection,
)
from cms_backend.db.collection import get_collections as db_get_collections
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import CollectionLightSchema
from cms_backend.utils.filename import construct_download_url
from cms_backend.utils.zim import convert_tags

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


def _build_library_xml(entries: list[CollectionBook]) -> str:
    """Build XML library catalog from books."""
    library_elem = ET.Element("library")
    library_elem.set("version", "20110515")

    for entry in entries:
        book, download_base_url, path, filename = entry
        if not book.zim_metadata:
            continue

        book_elem = ET.SubElement(library_elem, "book")

        # Required attributes
        book_elem.set("id", str(book.id))
        book_elem.set(
            "size", str(math.ceil(book.size / 1024) if book.size > 0 else book.size)
        )
        book_elem.set("mediaCount", str(book.media_count))
        book_elem.set("articleCount", str(book.article_count))

        # Metadata from zim_metadata dict
        zim_meta = book.zim_metadata
        book_elem.set("title", zim_meta.get("Title", ""))
        book_elem.set("description", zim_meta.get("Description", ""))
        book_elem.set("language", zim_meta.get("Language", ""))
        book_elem.set("creator", zim_meta.get("Creator", ""))
        book_elem.set("publisher", zim_meta.get("Publisher", ""))
        book_elem.set("name", zim_meta.get("Name", ""))
        book_elem.set("date", zim_meta.get("Date", ""))

        # always set tags to at least have special tags
        tags = zim_meta.get("Tags", "")
        book_elem.set("tags", ";".join(convert_tags(tags)))

        favicon = zim_meta.get("Illustration_48x48@1", "")
        if favicon:
            book_elem.set("favicon", favicon)
            book_elem.set("faviconMimeType", "image/png")

        if download_base_url:
            download_url = construct_download_url(download_base_url, path, filename)
            book_elem.set("url", f"{download_url}.meta4")

        if flavour := zim_meta.get("Flavour"):
            book_elem.set("flavour", flavour)

    ET.indent(library_elem, space="  ", level=0)

    return ET.tostring(library_elem, encoding="unicode")


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
    xml_content = _build_library_xml(entries)

    return Response(
        content=xml_content,
        status_code=HTTPStatus.OK,
        media_type="application/xml",
    )
