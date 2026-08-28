from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import (
    get_accessible_collection_ids,
    get_current_account,
    require_permission,
)
from cms_backend.api.routes.http_errors import BadRequestError
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import book as db_book
from cms_backend.db import book_actions as db_book_actions
from cms_backend.db import books as db_books
from cms_backend.db import gen_dbsession
from cms_backend.db import title as db_title
from cms_backend.db.models import Account
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.schemas.models import (
    BaseBookPromotionAction,
    BookLanguagesSchema,
    BookUpdateSchema,
    GetBooksSchema,
    ZimUrlsSchema,
)
from cms_backend.schemas.orms import (
    BookFullSchema,
    BookHistorySchema,
    BookLightSchema,
)

router = APIRouter(prefix="/books", tags=["books"])


class RevertBookSchema(BaseModel):
    comment: NotEmptyString | None = None


@router.get("")
def get_books(
    params: Annotated[GetBooksSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> ListResponse[BookLightSchema]:
    """Get a list of books"""

    results = db_books.get_books(
        session, params=params, accessible_collection_ids=accessible_collection_ids
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
    return db_books.get_zim_urls(session, zim_ids)


@router.get("/languages")
def get_book_languages(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> BookLanguagesSchema:
    return db_books.get_book_languages(session)


@router.get("/flavours")
def get_book_flavours(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    title_id: Annotated[UUID | None, Query()] = None,
) -> ListResponse[str]:
    results = db_books.get_book_flavours(session, title_id=title_id)
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
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> BookFullSchema:
    """Get a book by ID"""
    return db_book.create_book_full_schema(
        db_book.get_book(
            session=session,
            book_id=book_id,
            accessible_collection_ids=accessible_collection_ids,
        )
    )


@router.patch(
    "/{book_id}",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def update_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    request: BookUpdateSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    current_account: Account = Depends(get_current_account),
) -> BookFullSchema:
    return db_book.create_book_full_schema(
        db_book.update_book(
            session,
            book_id=book_id,
            payload=request,
            author_id=current_account.id,
            accessible_collection_ids=accessible_collection_ids,
        )
    )


@router.delete(
    "/{book_id}",
    dependencies=[Depends(require_permission(namespace="book", name="delete"))],
)
def delete_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    *,
    force_delete: Annotated[bool, Query()] = False,
) -> BookFullSchema:
    return db_book.create_book_full_schema(
        db_book.delete_book(
            session,
            book_id=book_id,
            force_delete=force_delete,
            accessible_collection_ids=accessible_collection_ids,
        )
    )


@router.post(
    "/{book_id}/recover",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def recover_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> BookFullSchema:
    return db_book.create_book_full_schema(
        db_book.recover_book(
            session,
            book_id=book_id,
            accessible_collection_ids=accessible_collection_ids,
        )
    )


@router.post(
    "/{book_id}/unpromote",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def unpromote_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> BookFullSchema:
    return db_book.create_book_full_schema(
        db_book.move_book(
            session,
            book_id=book_id,
            destination="staging",
            accessible_collection_ids=accessible_collection_ids,
        )
    )


@router.patch(
    "/{book_id}/backup",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def backup_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> BookFullSchema:
    return db_book.create_book_full_schema(
        db_book.backup_book(
            session,
            book_id=book_id,
            accessible_collection_ids=accessible_collection_ids,
        )
    )


@router.get(
    "/{book_id}/issues",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def get_book_issues(
    book_id: Annotated[UUID, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
) -> JSONResponse:
    book = db_book.get_book(
        session, book_id, accessible_collection_ids=accessible_collection_ids
    )
    return JSONResponse(
        content=db_book.update_book_issues(session, book),
        status_code=HTTPStatus.OK,
    )


class PromoteBook(BaseModel):
    actions: list[BaseBookPromotionAction] = Field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]


@router.patch(
    "/{book_id}/promote",
    dependencies=[
        Depends(require_permission(namespace="book", name="update")),
        Depends(require_permission(namespace="title", name="update")),
    ],
)
def promote_book(
    book_id: Annotated[UUID, Path()],
    request: PromoteBook,
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    current_account: Account = Depends(get_current_account),
    *,
    dry_run: Annotated[bool, Query()] = True,
) -> JSONResponse:
    if dry_run:
        actions = db_book_actions.get_book_promotion_actions(
            session,
            book_id=book_id,
            accessible_collection_ids=accessible_collection_ids,
            account=current_account,
        )
        return JSONResponse(
            content={"actions": [action.model_dump(mode="json") for action in actions]},
            status_code=HTTPStatus.OK,
        )
    else:
        db_book_actions.apply_book_promotion_actions(
            session,
            book_id=book_id,
            account=current_account,
            actions=request.actions,
            accessible_collection_ids=accessible_collection_ids,
        )
        return JSONResponse(
            content={"actions": []},
            status_code=HTTPStatus.OK,
        )


@router.get(
    "/{book_id}/history",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def get_book_history(
    book_id: Annotated[UUID, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    skip: Annotated[SkipField, Query()] = 0,
    limit: Annotated[LimitFieldMax200, Query()] = 200,
) -> ListResponse[BookHistorySchema]:
    results = db_book.get_book_history(
        session,
        book_id=book_id,
        skip=skip,
        limit=limit,
        accessible_collection_ids=accessible_collection_ids,
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
    "/{book_id}/history/{history_id}",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def get_book_history_entry(
    book_id: Annotated[UUID, Path()],
    history_id: Annotated[UUID, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
) -> BookHistorySchema:
    history_entry = db_book.get_book_history_entry(
        session,
        book_id=book_id,
        history_id=history_id,
        accessible_collection_ids=accessible_collection_ids,
    )
    return db_book.create_book_history_schema(history_entry)


@router.patch(
    "/{book_id}/revert/{history_id}",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def revert_book(
    book_id: Annotated[UUID, Path()],
    history_id: Annotated[UUID, Path()],
    request: RevertBookSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> JSONResponse:
    """Revert a book to a previous history."""
    db_book.revert_book(
        session,
        book_id=book_id,
        history_id=history_id,
        author_id=current_account.id,
        comment=request.comment,
        accessible_collection_ids=accessible_collection_ids,
    )
    return JSONResponse(
        content={"message": f"book '{book_id}' has been restored"},
        status_code=HTTPStatus.OK,
    )


@router.patch(
    "/{book_id}/backup/remove",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def remove_book_backup(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> BookFullSchema:
    return db_book.create_book_full_schema(
        db_book.remove_book_backup(
            session,
            book_id=book_id,
            accessible_collection_ids=accessible_collection_ids,
        )
    )


@router.patch(
    "/{book_id}/add-to-title/{title_id}",
    dependencies=[
        Depends(require_permission(namespace="title", name="update")),
        Depends(require_permission(namespace="book", name="update")),
    ],
)
def add_book_to_title(
    book_id: Annotated[UUID, Path()],
    title_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> BookFullSchema:
    """Associate a book in quarantine without a title to title"""
    title = db_title.get_title_by_id(
        session, title_id=title_id, accessible_collection_ids=accessible_collection_ids
    )
    book = db_book.get_book(
        session,
        book_id=book_id,
        accessible_collection_ids=accessible_collection_ids,
        locations=["quarantine"],
        needs_file_operation=False,
        has_error=False,
        needs_processing=False,
    )
    if book.title_id:
        raise BadRequestError("Book is already associated with a title")

    db_book.add_book_to_title(session, book, title, is_new=False)
    return db_book.create_book_full_schema(book)
