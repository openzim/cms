from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import count_from_stmt
from cms_backend.db import title as db_title
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import CollectionTitle, Title, TitleFlavour
from cms_backend.schemas.orms import ListResult, TitleFlavourSchema
from cms_backend.utils.datetime import getnow


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
        archived=tf.archived,
        temporary_manual_review=tf.temporary_manual_review,
    )


def create_title_flavour(
    session: OrmSession,
    title: Title,
    recipe_id: UUID | None,
    flavour: str,
):
    title_flavour = TitleFlavour(
        flavour=flavour,
        recipe_id=recipe_id,
    )
    title.flavours.append(title_flavour)
    session.flush()
    return title_flavour


def update_title_flavour(
    session: OrmSession,
    title: Title,
    flavour: str,
    *,
    author_id: UUID,
    archived: bool | None = None,
    temporary_manual_review: bool | None = None,
    comment: str | None = None,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> TitleFlavour:
    """Update a title flavour's catalog visibility and manual review override."""
    if archived is None and temporary_manual_review is None:
        raise ValueError(
            "At least one of archived or temporary_manual_review must be provided"
        )

    tf = get_title_flavour_or_none(
        session,
        title_id=title.id,
        flavour=flavour,
        accessible_collection_ids=accessible_collection_ids,
    )
    if tf is None:
        raise RecordDoesNotExistError(
            f"Title flavour '{flavour}' for title {title.id} does not exist"
        )

    changes: list[str] = []
    if archived is not None and tf.archived != archived:
        tf.archived = archived
        changes.append(
            f"flavour '{flavour}' "
            f"{'hidden from' if archived else 'restored to'} catalog"
        )
    if (
        temporary_manual_review is not None
        and tf.temporary_manual_review != temporary_manual_review
    ):
        tf.temporary_manual_review = temporary_manual_review
        changes.append(
            f"flavour '{flavour}' temporary manual review "
            f"{'enabled' if temporary_manual_review else 'disabled'}"
        )

    if not changes:
        raise RecordDoesNotExistError(
            f"Title flavour '{flavour}' already has the requested state"
        )

    now = getnow()
    title.events.extend(f"{now}: {change}" for change in changes)
    session.add(tf)
    session.add(title)
    session.flush()

    db_title.create_title_history_entry(
        session, title, author_id, comment or "; ".join(changes)
    )
    return tf


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
