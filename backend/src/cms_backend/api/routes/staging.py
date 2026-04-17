from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.utils import build_library_xml
from cms_backend.db import gen_dbsession
from cms_backend.db.staging import get_staging_books_library_data

router = APIRouter(prefix="/staging", tags=["staging"])


@router.get("/catalog.xml")
async def get_library_catalog_xml(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
):
    """Get staging catalog as XML library."""

    entries = get_staging_books_library_data(session)
    xml_content = build_library_xml(entries, uses_mirrorbrain=False)

    return Response(
        content=xml_content,
        status_code=HTTPStatus.OK,
        media_type="application/xml",
    )
