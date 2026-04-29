import datetime
from pathlib import Path
from uuid import UUID

from pydantic import AnyUrl
from sqlalchemy import String, and_, func, or_, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.context import Context
from cms_backend.db import count_from_stmt
from cms_backend.db.models import Book, BookLocation, Collection, CollectionTitle, Title
from cms_backend.schemas.models import BookLanguagesSchema, ZimUrlSchema, ZimUrlsSchema
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
    updated_before: datetime.datetime | None = None,
    updated_after: datetime.datetime | None = None,
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
    ).order_by(
        Book.has_error.desc(),
        Book.location_kind,
        Book.needs_file_operation.desc(),
        Book.created_at.desc(),
        Book.id,
    )

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

    if updated_before is not None:
        stmt = stmt.where(Book.updated_at < updated_before)

    if updated_after is not None:
        stmt = stmt.where(Book.updated_at > updated_after)

    if needs_attention is True:
        stmt = stmt.where(
            or_(
                Book.location_kind.in_(["quarantine", "staging"]),
                Book.title_id.is_(None),
                Book.needs_processing.is_(True),
                Book.needs_file_operation.is_(True),
                Book.has_error.is_(True),
            )
        )
    elif needs_attention is False:
        stmt = stmt.where(
            and_(
                Book.location_kind.not_in(["quarantine", "staging"]),
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


def get_zim_urls_prod(session: OrmSession, zim_ids: list[UUID]) -> ZimUrlsSchema:
    """
    Get view and download URLs for a list of ZIM IDs (Book IDs).
    """
    # Get the latest books for each title/flavor combination
    # as the book IDs passed might not include the latest
    # and we need only the latest book per title/flavor combo
    # to have the view URL.
    latest_dates_subq = (
        select(Book.title_id, Book.flavour, func.max(Book.date).label("max_date"))
        .where(
            Book.needs_processing.is_(False),
            Book.has_error.is_(False),
            Book.needs_file_operation.is_(False),
            Book.location_kind == "prod",
            Book.title_id.in_(select(Book.title_id).where(Book.id.in_(zim_ids))),
        )
        .group_by(Book.title_id, Book.flavour)
        .subquery()
    )

    stmt = (
        select(
            Book.id.label("book_id"),
            Book.location_kind.label("book_location_kind"),
            Title.id.label("title_id"),
            Book.flavour.label("book_flavour"),
            Collection.name.label("collection_name"),
            Collection.download_base_url,
            Collection.view_base_url,
            CollectionTitle.path.label("subpath"),
            BookLocation.filename,
            (Book.date == latest_dates_subq.c.max_date).label("is_latest"),
        )
        .join(Title, Book.title_id == Title.id)
        .join(CollectionTitle, CollectionTitle.title_id == Title.id)
        .join(Collection, Collection.id == CollectionTitle.collection_id)
        .join(
            latest_dates_subq,
            and_(
                Book.title_id == latest_dates_subq.c.title_id,
                Book.flavour == latest_dates_subq.c.flavour,
            ),
        )
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
                Book.location_kind == "prod",
            )
        )
        .order_by(Title.id, Book.flavour, Book.date.desc(), Book.created_at.desc())
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

        if row.view_base_url and row.is_latest:
            key = (row.title_id, row.book_flavour)
            if key not in seen:
                seen.add(key)
                filename_without_suffix = (
                    row.filename[:-4] if row.filename.endswith(".zim") else row.filename
                )
                result.urls[row.book_id].append(
                    ZimUrlSchema(
                        kind="view",
                        url=AnyUrl(f"{row.view_base_url}{filename_without_suffix}"),
                        collection=row.collection_name,
                    )
                )

    return result


def get_zim_urls_staging(session: OrmSession, zim_ids: list[UUID]) -> ZimUrlsSchema:
    """
    Get view and download URLs for a list of ZIM IDs (Book IDs).
    """
    # Get the latest books for each title/flavor combination
    # as the book IDs passed might not include the latest
    # and we need only the latest book per title/flavor combo
    # to have the view URL.
    latest_dates_subq = (
        select(Book.title_id, Book.flavour, func.max(Book.date).label("max_date"))
        .where(
            Book.needs_processing.is_(False),
            Book.has_error.is_(False),
            Book.needs_file_operation.is_(False),
            Book.location_kind == "staging",
            Book.title_id.in_(select(Book.title_id).where(Book.id.in_(zim_ids))),
        )
        .group_by(Book.title_id, Book.flavour)
        .subquery()
    )

    stmt = (
        select(
            Book.id.label("book_id"),
            Book.location_kind.label("book_location_kind"),
            Title.id.label("title_id"),
            Book.flavour.label("book_flavour"),
            BookLocation.filename,
            (Book.date == latest_dates_subq.c.max_date).label("is_latest"),
        )
        .join(Title, Book.title_id == Title.id)
        .join(
            latest_dates_subq,
            and_(
                Book.title_id == latest_dates_subq.c.title_id,
                Book.flavour == latest_dates_subq.c.flavour,
            ),
        )
        .join(
            BookLocation,
            and_(
                BookLocation.book_id == Book.id,
                BookLocation.status == "current",
                BookLocation.warehouse_id == Context.staging_warehouse_id,
                BookLocation.path == Context.staging_base_path,
            ),
        )
        .where(
            and_(
                Book.id.in_(zim_ids),
                Book.needs_processing.is_(False),
                Book.has_error.is_(False),
                Book.needs_file_operation.is_(False),
                Book.location_kind == "staging",
            )
        )
        .order_by(Title.id, Book.flavour, Book.date.desc(), Book.created_at.desc())
    )

    result = ZimUrlsSchema(urls={zim_id: [] for zim_id in zim_ids})
    seen: set[tuple[str | None, str | None]] = set()

    for row in session.execute(stmt).all():
        result.urls[row.book_id].append(
            ZimUrlSchema(
                kind="download",
                url=AnyUrl(
                    construct_download_url(
                        # staging download url is supposed to contain the whole path
                        # already for convenience in deployment
                        Context.staging_download_base_url,
                        Path(""),
                        row.filename,
                    )
                ),
                collection="staging",
            )
        )

        if row.is_latest:
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
                            f"{Context.staging_view_base_url}{filename_without_suffix}"
                        ),
                        collection="staging",
                    )
                )

    return result


def get_zim_urls(session: OrmSession, zim_ids: list[UUID]) -> ZimUrlsSchema:
    prod_urls = get_zim_urls_prod(session, zim_ids).urls
    staging_urls = get_zim_urls_staging(session, zim_ids).urls
    return ZimUrlsSchema(
        urls={zim_id: prod_urls[zim_id] + staging_urls[zim_id] for zim_id in zim_ids}
    )


def get_book_languages(session: OrmSession) -> BookLanguagesSchema:
    """Get the sorted list of language codes used by production books."""
    stmt = select(Book.zim_metadata).where(Book.location_kind == "prod")

    languages: set[str] = set()
    for zim_metadata in session.scalars(stmt):
        language_value = zim_metadata.get("Language")
        if not isinstance(language_value, str):
            continue

        for language in language_value.split(","):
            if normalized_language := language.strip():
                languages.add(normalized_language)

    return BookLanguagesSchema(languages=sorted(languages))
