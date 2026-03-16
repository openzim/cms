from uuid import UUID

from pydantic import AnyUrl
from sqlalchemy import String, and_, or_, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import count_from_stmt
from cms_backend.db.models import Book, BookLocation, Collection, CollectionTitle, Title
from cms_backend.schemas.models import ZimUrlSchema, ZimUrlsSchema
from cms_backend.schemas.orms import BookLightSchema, ListResult
from cms_backend.utils.filename import construct_download_url


def get_books(
    session: OrmSession,
    *,
    skip: int,
    limit: int,
    book_id: str | None = None,
    has_title: bool | None = None,
    needs_processing: bool | None = None,
    has_error: bool | None = None,
    needs_file_operation: bool | None = None,
    location_kinds: list[str] | None = None,
    needs_attention: bool | None = None,
) -> ListResult[BookLightSchema]:
    """Get a list of books"""

    stmt = select(
        Book.id,
        Book.title_id,
        Book.needs_processing,
        Book.has_error,
        Book.needs_file_operation,
        Book.location_kind,
        Book.created_at,
        Book.deletion_date,
        Book.name,
        Book.date,
        Book.flavour,
    ).order_by(Book.id)

    if book_id is not None:
        stmt = stmt.where(Book.id.cast(String).ilike(f"%{book_id}%"))

    if has_title is not None:
        if has_title:
            stmt = stmt.where(Book.title_id.is_not(None))
        else:
            stmt = stmt.where(Book.title_id.is_(None))

    if needs_processing is not None:
        stmt = stmt.where(Book.needs_processing == needs_processing)

    if has_error is not None:
        stmt = stmt.where(Book.has_error == has_error)

    if needs_file_operation is not None:
        stmt = stmt.where(Book.needs_file_operation == needs_file_operation)

    if location_kinds is not None:
        stmt = stmt.where(Book.location_kind.in_(location_kinds))

    if needs_attention is True:
        stmt = stmt.where(
            or_(
                Book.title_id.is_(None),
                Book.needs_processing.is_(True),
                Book.needs_file_operation.is_(True),
                Book.has_error.is_(True),
            )
        )
    elif needs_attention is False:
        stmt = stmt.where(
            and_(
                Book.title_id.is_not(None),
                Book.needs_processing.is_(False),
                Book.needs_file_operation.is_(False),
                Book.has_error.is_(False),
            )
        )

    return ListResult[BookLightSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            BookLightSchema(
                id=book_id_result,
                title_id=book_title_id,
                needs_processing=needs_processing,
                has_error=has_error,
                needs_file_operation=needs_file_operation,
                location_kind=location_kind,
                created_at=created_at,
                deletion_date=deletion_date,
                name=name,
                date=date,
                flavour=flavour,
            )
            for (
                book_id_result,
                book_title_id,
                needs_processing,
                has_error,
                needs_file_operation,
                location_kind,
                created_at,
                deletion_date,
                name,
                date,
                flavour,
            ) in session.execute(
                stmt.offset(skip)
                .limit(limit)
                .order_by(
                    Book.has_error,
                    Book.location_kind,
                    Book.needs_file_operation,
                    Book.created_at.desc(),
                )
            ).all()
        ],
    )


def get_zim_urls(session: OrmSession, zim_ids: list[UUID]) -> ZimUrlsSchema:
    """
    Get view and download URLs for a list of ZIM IDs (Book IDs).
    """
    stmt = (
        select(
            Book.id.label("book_id"),
            Title.id.label("title_id"),
            Book.flavour.label("book_flavour"),
            Collection.name.label("collection_name"),
            Collection.download_base_url,
            Collection.view_base_url,
            CollectionTitle.path.label("subpath"),
            BookLocation.filename,
        )
        .join(Title, Book.title_id == Title.id)
        .join(CollectionTitle, CollectionTitle.title_id == Title.id)
        .join(Collection, Collection.id == CollectionTitle.collection_id)
        .join(
            BookLocation,
            and_(
                BookLocation.book_id == Book.id,
                BookLocation.status == "current",
                BookLocation.warehouse_id == Collection.warehouse_id,
                BookLocation.path == CollectionTitle.path,
            ),
        )
        .where(
            and_(
                Book.id.in_(zim_ids),
                Book.needs_processing.is_(False),
                Book.has_error.is_(False),
                Book.needs_file_operation.is_(False),
            )
        )
        .order_by(Title.id, Book.flavour, Book.created_at.desc())
    )

    result = ZimUrlsSchema(urls={zim_id: [] for zim_id in zim_ids})

    # Filter to keep only one view link for the latest book per title+flavour
    # combination
    seen: set[tuple[str | None, str | None]] = set()
    for row in session.execute(stmt).all():
        if row.download_base_url:
            result.urls[row.book_id].append(
                ZimUrlSchema(
                    kind="download",
                    url=AnyUrl(
                        construct_download_url(
                            row.download_base_url, row.subpath, row.filename
                        )
                    ),
                    collection=row.collection_name,
                )
            )

        if row.view_base_url:
            key = (row.title_id, row.book_flavour)
            if key not in seen:
                seen.add(key)
                filename_without_suffix = (
                    row.filename[:-4] if row.filename.endswith(".zim") else row.filename
                )
                result.urls[row.book_id].append(
                    ZimUrlSchema(
                        kind="view",
                        url=AnyUrl(
                            f"{row.view_base_url}/viewer#{filename_without_suffix}"
                        ),
                        collection=row.collection_name,
                    )
                )

    return result
