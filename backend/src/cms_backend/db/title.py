from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordAlreadyExistsError
from cms_backend.db.models import Title, TitleWarehousePath
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


def get_title_by_name_and_producer_or_none(
    session: OrmSession, *, name: str, producer_unique_id: str
) -> Title | None:
    """Get a title by name and producer_unique_id if possible else None"""

    return session.scalars(
        select(Title).where(
            Title.name == name, Title.producer_unique_id == producer_unique_id
        )
    ).one_or_none()


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
            Title.producer_unique_id.label("producer_unique_id"),
            Title.producer_display_name.label("producer_display_name"),
            Title.producer_display_url.label("producer_display_url"),
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
                producer_unique_id=producer_unique_id,
                producer_display_name=producer_display_name,
                producer_display_url=producer_display_url,
            )
            for (
                title_id,
                title_name,
                producer_unique_id,
                producer_display_name,
                producer_display_url,
            ) in session.execute(stmt.offset(skip).limit(limit)).all()
        ],
    )


def create_title(
    session: OrmSession,
    *,
    name: str,
    producer_unique_id: str,
    producer_display_name: str | None,
    producer_display_url: str | None,
    dev_warehouse_path_ids: list[UUID],
    prod_warehouse_path_ids: list[UUID],
    in_prod: bool,
) -> Title:
    """Create a new title with multiple warehouse paths

    Args:
        dev_warehouse_path_ids: List of warehouse path IDs for dev environment
        prod_warehouse_path_ids: List of warehouse path IDs for prod environment

    Raises:
        ValueError: If dev_warehouse_path_ids or prod_warehouse_path_ids is empty
        RecordAlreadyExistsError: If title with same name already exists
    """
    # Validate that at least one path of each type is provided
    if not dev_warehouse_path_ids:
        raise ValueError("At least one dev warehouse path is required")
    if not prod_warehouse_path_ids:
        raise ValueError("At least one prod warehouse path is required")

    title = Title(
        name=name,
        producer_unique_id=producer_unique_id,
    )
    title.producer_display_name = producer_display_name
    title.producer_display_url = producer_display_url
    title.in_prod = in_prod
    title.events.append(f"{getnow()}: title created")

    # Add warehouse path associations
    for path_id in dev_warehouse_path_ids:
        twp = TitleWarehousePath(path_type="dev")
        twp.warehouse_path_id = path_id
        title.warehouse_paths.append(twp)
    for path_id in prod_warehouse_path_ids:
        twp = TitleWarehousePath(path_type="prod")
        twp.warehouse_path_id = path_id
        title.warehouse_paths.append(twp)

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
