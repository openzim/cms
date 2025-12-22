from http import HTTPStatus
from typing import Annotated
from uuid import UUID
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, Path
from fastapi.responses import Response
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import gen_dbsession
from cms_backend.db.collection import (
    get_collection,
    get_collection_by_name_or_none,
    get_latest_books_for_collection,
)
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Book

router = APIRouter(prefix="/collections", tags=["collections"])


def _build_library_xml(books: list[Book]) -> str:
    """Build XML library catalog from books."""
    library_elem = ET.Element("library")
    library_elem.set("version", "20110515")

    for book in books:
        if not book.zim_metadata:
            continue

        book_elem = ET.SubElement(library_elem, "book")

        # Required attributes
        book_elem.set("id", str(book.id))
        book_elem.set("size", str(book.size))
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

        # Optional tags - combine with underscores if present
        tags = zim_meta.get("Tags", "")
        if tags:
            book_elem.set("tags", tags)

        # Favicon and faviconMimeType - these are typically extracted from the ZIM
        # but for now we'll use empty strings as the data structure doesn't contain them
        favicon = zim_meta.get("Illustration_48x48@1", "")
        if favicon:
            book_elem.set("favicon", favicon)
            book_elem.set("faviconMimeType", "image/png")

        # URL - would need to be constructed from warehouse config
        # For now, leaving empty as warehouse config mapping is not implemented
        url = zim_meta.get("URL", "")
        if url:
            book_elem.set("url", url)

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

    books = get_latest_books_for_collection(session, collection.id)
    xml_content = _build_library_xml(books)

    return Response(
        content=xml_content,
        status_code=HTTPStatus.OK,
        media_type="application/xml",
    )
