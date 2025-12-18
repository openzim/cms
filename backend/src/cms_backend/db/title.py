from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordAlreadyExistsError
from cms_backend.db.models import Title
from cms_backend.schemas.orms import ListResult, TitleLightSchema
from cms_backend.utils.datetime import getnow


def get_title_by_id(session: OrmSession, *, title_id: UUID) -> Title:
    """Get a title by ID"""

    title = session.get(Title, title_id)
    if not title:
        from cms_backend.db.exceptions import RecordDoesNotExistError

        raise RecordDoesNotExistError(f"Title with id {title_id} does not exist")
    return title


def get_title_by_name_or_none(session: OrmSession, *, name: str) -> Title | None:
    """Get a title by name if possible else None"""

    return session.scalars(select(Title).where(Title.name == name)).one_or_none()


def get_titles(
    session: OrmSession,
    *,
    skip: int,
    limit: int,
    name: str | None = None,
    omit_names: list[str] | None = None,
) -> ListResult[TitleLightSchema]:
    """Get a list of titles"""

    stmt = (
        select(
            Title.id.label("title_id"),
            Title.name.label("title_name"),
            Title.maturity.label("title_maturity"),
        )
        .order_by(Title.name)
        .where(
            # If a client provides an argument i.e it is not None,
            # we compare the corresponding model field against the argument,
            # otherwise, we compare the argument to its default which translates
            # to a SQL true i.e we don't filter based on this argument (a no-op).
            (
                Title.name.ilike(f"%{name if name is not None else ''}%")
                | (name is None)
            ),
            (Title.name.not_in(omit_names or []) | (omit_names is None)),
        )
    )

    return ListResult[TitleLightSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            TitleLightSchema(
                id=title_id,
                name=title_name,
                maturity=title_maturity,
            )
            for (
                title_id,
                title_name,
                title_maturity,
            ) in session.execute(stmt.offset(skip).limit(limit)).all()
        ],
    )


def create_title(
    session: OrmSession,
    *,
    name: str,
    maturity: str | None,
) -> Title:
    """Create a new title

    Args:
        name: name of the title

    Raises:
        RecordAlreadyExistsError: If title with same name already exists
    """

    title = Title(
        name=name,
    )
    if maturity:
        title.maturity = maturity
    title.events.append(f"{getnow()}: title created")

    session.add(title)
    try:
        session.flush()
    except IntegrityError as exc:
        if isinstance(exc.orig, UniqueViolation):
            raise RecordAlreadyExistsError(
                f"Title with name {name} already exists"
            ) from exc
        logger.exception("Unknown exception encountered while creating title")
        raise

    return title
