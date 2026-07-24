from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import book as db_book
from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Book, CollectionTitle, Title, TitleFlavour
from cms_backend.schemas.orms import ListResult, TitleFlavourSchema


def get_title_flavours(
    session: OrmSession,
    title_id: UUID,
    *,
    limit: int = 20,
    skip: int = 0,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> ListResult[TitleFlavourSchema]:
    stmt = select(TitleFlavour).where(
        TitleFlavour.title_id == title_id,
        exists().where(
            CollectionTitle.title_id == TitleFlavour.title_id,
            CollectionTitle.collection_id.in_(accessible_collection_ids or []),
        )
        | (accessible_collection_ids is None),
    )
    return ListResult[TitleFlavourSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            create_title_flavour_schema(tf)
            for tf in session.scalars(
                stmt.offset(skip).limit(limit).order_by(TitleFlavour.flavour)
            )
        ],
    )


def create_title_flavour_schema(tf: TitleFlavour) -> TitleFlavourSchema:
    return TitleFlavourSchema(
        flavour=tf.flavour,
        recipe_id=tf.recipe_id,
        last_book_added_at=tf.last_book_added_at,
    )


def create_title_flavour(
    session: OrmSession, title: Title, recipe_id: UUID | None, flavour: str
):
    title_flavour = TitleFlavour(
        flavour=flavour,
        recipe_id=recipe_id,
    )
    title.flavours.append(title_flavour)
    session.add(title_flavour)
    session.flush()
    return title_flavour


def get_title_flavour_or_none(
    session: OrmSession,
    title_id: UUID,
    flavour: str,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> TitleFlavour | None:
    return session.scalars(
        select(TitleFlavour).where(
            TitleFlavour.title_id == title_id,
            TitleFlavour.flavour == flavour,
            exists().where(
                CollectionTitle.title_id == TitleFlavour.title_id,
                CollectionTitle.collection_id.in_(accessible_collection_ids or []),
            )
            | (accessible_collection_ids is None),
        )
    ).one_or_none()


def get_title_flavour(
    session: OrmSession,
    title_id: UUID,
    flavour: str,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> TitleFlavour:
    title_flavour = get_title_flavour_or_none(
        session, title_id, flavour, accessible_collection_ids=accessible_collection_ids
    )
    if title_flavour is None:
        raise RecordDoesNotExistError(
            f"Title flavour {flavour} for title {title_id} does not exists"
        )
    return title_flavour


def delete_title_flavour(
    session: OrmSession,
    title_id: UUID,
    flavour: str,
    *,
    accessible_collection_ids: Sequence[UUID] | None = None,
):
    """Delete a title flavour and mark associated books for deletion.

    Only books that are in staging, prod or quarantine and do not have any pending
    operations are eligible for deletion.
    """
    tf = get_title_flavour_or_none(
        session,
        title_id=title_id,
        flavour=flavour,
        accessible_collection_ids=accessible_collection_ids,
    )
    if tf is None:
        raise RecordDoesNotExistError(
            f"Title flavour '{flavour}' for title {title_id} does not exist"
        )
    book_ids_to_delete = session.scalars(
        select(Book.id).where(
            Book.needs_processing.is_(False),
            Book.needs_processing.is_(False),
            Book.location_kind.in_(["staging", "prod", "quarantine"]),
            Book.title_id == tf.title_id,
            Book.flavour == tf.flavour,
        )
    ).all()
    for book_id in book_ids_to_delete:
        db_book.delete_book(
            session,
            book_id=book_id,
            accessible_collection_ids=accessible_collection_ids,
        )
    session.delete(tf)
    session.flush()
