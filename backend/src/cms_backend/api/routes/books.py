import datetime
from http import HTTPStatus
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import get_current_account, require_permission
from cms_backend.api.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.book import backup_book as db_backup_book
from cms_backend.db.book import create_book_full_schema, create_book_history_schema
from cms_backend.db.book import delete_book as db_delete_book
from cms_backend.db.book import get_book as db_get_book
from cms_backend.db.book import get_book_history as db_get_book_history
from cms_backend.db.book import get_book_history_entry as db_get_book_history_entry
from cms_backend.db.book import move_book as db_move_book
from cms_backend.db.book import recover_book as db_recover_book
from cms_backend.db.book import revert_book as db_revert_book
from cms_backend.db.book import update_book as db_update_book
from cms_backend.db.books import get_book_flavours as db_get_book_flavours
from cms_backend.db.books import get_book_languages as db_get_book_languages
from cms_backend.db.books import get_books as db_get_books
from cms_backend.db.books import get_zim_urls as db_get_zim_urls
from cms_backend.db.models import Account
from cms_backend.schemas import BaseModel
from cms_backend.schemas.models import (
    BookLanguagesSchema,
    BookUpdateSchema,
    ZimUrlsSchema,
)
from cms_backend.schemas.orms import (
    BookFullSchema,
    BookHistorySchema,
    BookLightSchema,
)

router = APIRouter(prefix="/books", tags=["books"])


class BookMoveSchema(BaseModel):
    destination: Literal["prod", "staging"]


class BooksGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    id: NotEmptyString | None = None
    has_title: bool | None = None
    needs_processing: bool | None = None
    has_error: bool | None = None
    needs_file_operation: bool | None = None
    location_kinds: list[NotEmptyString] | None = None
    needs_attention: bool | None = None
    has_backup: bool | None = None
    updated_before: datetime.datetime | None = None
    updated_after: datetime.datetime | None = None
    name: NotEmptyString | None = None
    flavour: NotEmptyString | None = None


class RevertBookSchema(BaseModel):
    comment: NotEmptyString | None = None


@router.get("")
def get_books(
    params: Annotated[BooksGetSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[BookLightSchema]:
    """Get a list of books"""

    results = db_get_books(
        session,
        skip=params.skip,
        limit=params.limit,
        book_id=params.id,
        has_title=params.has_title,
        needs_processing=params.needs_processing,
        has_error=params.has_error,
        needs_file_operation=params.needs_file_operation,
        location_kinds=params.location_kinds,
        needs_attention=params.needs_attention,
        updated_before=params.updated_before,
        updated_after=params.updated_after,
        name=params.name,
        flavour=params.flavour,
        has_backup=params.has_backup,
    )

    return ListResponse[BookLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.get("/zims")
def get_zim_urls(
    zim_ids: Annotated[list[UUID], Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ZimUrlsSchema:
    return db_get_zim_urls(session, zim_ids)


@router.get("/languages")
def get_book_languages(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> BookLanguagesSchema:
    return db_get_book_languages(session)


@router.get("/flavours")
def get_book_flavours(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[str]:
    results = db_get_book_flavours(session)
    return ListResponse[str](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=0,
            limit=len(results.records),
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.get("/{book_id}")
def get_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> BookFullSchema:
    """Get a book by ID"""
    return create_book_full_schema(db_get_book(session=session, book_id=book_id))


@router.patch(
    "/{book_id}",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def update_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    request: BookUpdateSchema,
    current_account: Account = Depends(get_current_account),
) -> BookFullSchema:
    return create_book_full_schema(
        db_update_book(
            session, book_id=book_id, payload=request, author_id=current_account.id
        )
    )


@router.delete(
    "/{book_id}",
    dependencies=[Depends(require_permission(namespace="book", name="delete"))],
)
def delete_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    *,
    force_delete: Annotated[bool, Query()] = False,
) -> BookFullSchema:
    return create_book_full_schema(
        db_delete_book(session, book_id=book_id, force_delete=force_delete)
    )


@router.post(
    "/{book_id}/recover",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def recover_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> BookFullSchema:
    return create_book_full_schema(db_recover_book(session, book_id=book_id))


@router.post(
    "/{book_id}/move",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def move_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    request: BookMoveSchema,
) -> BookFullSchema:
    return create_book_full_schema(
        db_move_book(session, book_id=book_id, destination=request.destination)
    )


@router.patch(
    "/{book_id}/backup",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def backup_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> BookFullSchema:
    return create_book_full_schema(db_backup_book(session, book_id=book_id))


@router.get(
    "/{book_id}/history",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def get_book_history(
    book_id: Annotated[UUID, Path()],
    session: OrmSession = Depends(gen_dbsession),
    skip: Annotated[SkipField, Query()] = 0,
    limit: Annotated[LimitFieldMax200, Query()] = 200,
) -> ListResponse[BookHistorySchema]:
    results = db_get_book_history(session, book_id=book_id, skip=skip, limit=limit)
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
    "/{book_id}/history/{history_id}",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def get_book_history_entry(
    book_id: Annotated[UUID, Path()],
    history_id: Annotated[UUID, Path()],
    session: OrmSession = Depends(gen_dbsession),
) -> BookHistorySchema:
    history_entry = db_get_book_history_entry(
        session, book_id=book_id, history_id=history_id
    )
    return create_book_history_schema(history_entry)


@router.patch(
    "/{book_id}/revert/{history_id}",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def revert_book(
    book_id: Annotated[UUID, Path()],
    history_id: Annotated[UUID, Path()],
    request: RevertBookSchema,
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> JSONResponse:
    """Revert a book to a previous history."""
    db_revert_book(
        session,
        book_id=book_id,
        history_id=history_id,
        author_id=current_account.id,
        comment=request.comment,
    )
    return JSONResponse(
        content={"message": f"book '{book_id}' has been restored"},
        status_code=HTTPStatus.OK,
    )
