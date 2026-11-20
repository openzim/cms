from datetime import UTC, timedelta
from email.utils import format_datetime, parsedate_to_datetime
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.middleware.cors import cors_public
from cms_backend.db import gen_dbsession
from cms_backend.db import illustration as db_illustration
from cms_backend.db.models import Illustration
from cms_backend.utils.datetime import getnow

router = APIRouter(prefix="/illustrations", tags=["illustrations"])

ILLUSTRATION_MIMETYPE = "image/png"
CACHE_MAX_AGE = 365 * 24 * 60 * 60


def _illustration_headers(illustration: Illustration) -> dict[str, str]:
    created_at = illustration.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)

    return {
        "ETag": f'"{illustration.hex_digest}"',
        "Last-Modified": format_datetime(created_at, usegmt=True),
        "Expires": format_datetime(
            getnow().replace(tzinfo=UTC) + timedelta(seconds=CACHE_MAX_AGE),
            usegmt=True,
        ),
        "Cache-Control": f"public, max-age={CACHE_MAX_AGE}, immutable",
    }


def _is_not_modified(request: Request, illustration: Illustration) -> bool:
    if_none_match = request.headers.get("if-none-match")
    if if_none_match is not None:
        etags = {etag.strip().removeprefix("W/") for etag in if_none_match.split(",")}
        return f'"{illustration.hex_digest}"' in etags or "*" in etags

    if_modified_since = request.headers.get("if-modified-since")
    if if_modified_since is not None:
        try:
            since = parsedate_to_datetime(if_modified_since)
        except (TypeError, ValueError) as exc:
            del exc
            return False
        if since.tzinfo is None:
            since = since.replace(tzinfo=UTC)
        created_at = illustration.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return created_at.replace(microsecond=0) <= since

    return False


def _get_illustration_response(
    request: Request, session: OrmSession, hex_digest: str, *, include_body: bool
) -> Response:
    illustration = db_illustration.get_illustration(session, hex_digest)
    headers = _illustration_headers(illustration)

    if _is_not_modified(request, illustration):
        return Response(status_code=HTTPStatus.NOT_MODIFIED, headers=headers)

    return Response(
        content=(
            db_illustration.decode_illustration(illustration.data)
            if include_body
            else None
        ),
        media_type=ILLUSTRATION_MIMETYPE,
        status_code=HTTPStatus.OK,
        headers=headers,
    )


@router.get("/{hex_digest}")
@cors_public
def get_illustration(
    hex_digest: Annotated[str, Path()],
    request: Request,
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> Response:
    """Get an illustration by the hexadecimal digest of its data."""
    return _get_illustration_response(request, session, hex_digest, include_body=True)


@router.head("/{hex_digest}")
@cors_public
def head_illustration(
    hex_digest: Annotated[str, Path()],
    request: Request,
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> Response:
    """Get the headers for an illustration without its content."""
    return _get_illustration_response(request, session, hex_digest, include_body=False)
