from collections.abc import Sequence
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from cms_backend.db import count_from_stmt
from cms_backend.db import flavour as db_flavour
from cms_backend.db import title as db_title
from cms_backend.db.exceptions import (
    RecordAlreadyExistsError,
    RecordDoesNotExistError,
)
from cms_backend.db.models import (
    Application,
    ApplicationHistory,
    CollectionTitle,
    Title,
    TitleFlavour,
)
from cms_backend.schemas.models import ApplicationCreateSchema, ApplicationUpdateSchema
from cms_backend.schemas.orms import (
    ApplicationHistorySchema,
    ApplicationSchema,
    ListResult,
)


def _access_filter(
    accessible_collection_ids: Sequence[UUID] | None,
    accessible_title_ids: Sequence[UUID] | None,
) -> ColumnElement[bool]:
    return (
        exists().where(
            CollectionTitle.title_id == Application.title_id,
            CollectionTitle.collection_id.in_(accessible_collection_ids or []),
        )
        | (accessible_collection_ids is None)
        | Application.title_id.in_(accessible_title_ids or [])
    )


def create_application_schema(
    application: Application,
) -> ApplicationSchema:
    return ApplicationSchema(
        title_id=application.title_id,
        title_name=application.title_flavour.title.name,
        flavour=application.flavour,
        store=application.store,
        enabled=application.enabled,
        name=application.name,
    )


def get_application_by_id_or_none(
    session: OrmSession,
    *,
    title_id: UUID,
    flavour: str,
    store: str,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
) -> Application | None:
    return session.scalars(
        select(Application)
        .options(
            selectinload(Application.title_flavour).selectinload(TitleFlavour.title)
        )
        .where(
            Application.title_id == title_id,
            Application.flavour == flavour,
            Application.store == store,
            _access_filter(accessible_collection_ids, accessible_title_ids),
        )
    ).one_or_none()


def get_application_or_none(
    session: OrmSession,
    *,
    name: str,
    store: str,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
) -> Application | None:
    return session.scalars(
        select(Application)
        .options(
            selectinload(Application.title_flavour).selectinload(TitleFlavour.title)
        )
        .where(
            Application.name == name,
            Application.store == store,
            _access_filter(accessible_collection_ids, accessible_title_ids),
        )
    ).one_or_none()


def get_application(
    session: OrmSession,
    *,
    name: str,
    store: str,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
) -> Application:
    application = get_application_or_none(
        session,
        name=name,
        store=store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    if application is None:
        raise RecordDoesNotExistError(
            f"Application '{name}' does not exist for store '{store}'"
        )
    return application


def get_applications(
    session: OrmSession,
    *,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
    store: str | None = None,
    name: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> ListResult[ApplicationSchema]:
    stmt = (
        select(Application)
        .join(Application.title_flavour)
        .join(TitleFlavour.title)
        .options(
            selectinload(Application.title_flavour).selectinload(TitleFlavour.title)
        )
        .where(
            (Application.store == store) | (store is None),
            (Application.name == name) | (name is None),
            _access_filter(accessible_collection_ids, accessible_title_ids),
        )
    )

    return ListResult[ApplicationSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            create_application_schema(application)
            for application in session.scalars(
                stmt.order_by(Title.name, TitleFlavour.flavour, Application.store)
                .offset(skip)
                .limit(limit)
            ).all()
        ],
    )


def create_application_history_entry(
    session: OrmSession,
    application: Application,
    author_id: UUID,
    comment: str | None = None,
) -> ApplicationHistory:
    history_entry = ApplicationHistory(
        store=application.store,
        comment=comment,
        name=application.name,
        enabled=application.enabled,
    )
    history_entry.title_id = application.title_id
    history_entry.flavour = application.flavour
    history_entry.author_id = author_id
    session.add(history_entry)
    return history_entry


def create_application_history_schema(
    entry: ApplicationHistory, *, title_name: str
) -> ApplicationHistorySchema:
    return ApplicationHistorySchema(
        id=entry.id,
        title_id=entry.title_id,
        title_name=title_name,
        flavour=entry.flavour,
        store=entry.store,
        name=entry.name,
        enabled=entry.enabled,
        author=entry.author.display_name,
        comment=entry.comment,
        created_at=entry.created_at,
    )


def get_application_history(
    session: OrmSession,
    *,
    name: str,
    store: str,
    skip: int,
    limit: int,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
) -> ListResult[ApplicationHistorySchema]:
    application = get_application(
        session,
        name=name,
        store=store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    title_name = application.title_flavour.title.name
    stmt = (
        select(ApplicationHistory)
        .where(
            ApplicationHistory.title_id == application.title_id,
            ApplicationHistory.flavour == application.flavour,
            ApplicationHistory.store == application.store,
        )
        .options(selectinload(ApplicationHistory.author))
        .order_by(ApplicationHistory.created_at.desc())
    )
    return ListResult[ApplicationHistorySchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            create_application_history_schema(entry, title_name=title_name)
            for entry in session.scalars(stmt.offset(skip).limit(limit)).all()
        ],
    )


def get_application_history_entry_or_none(
    session: OrmSession,
    *,
    name: str,
    store: str,
    history_id: UUID,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
) -> ApplicationHistory | None:
    application = get_application(
        session,
        name=name,
        store=store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    return session.scalars(
        select(ApplicationHistory)
        .where(
            ApplicationHistory.id == history_id,
            ApplicationHistory.title_id == application.title_id,
            ApplicationHistory.flavour == application.flavour,
            ApplicationHistory.store == application.store,
        )
        .options(selectinload(ApplicationHistory.author))
    ).one_or_none()


def get_application_history_entry(
    session: OrmSession,
    *,
    name: str,
    store: str,
    history_id: UUID,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
) -> ApplicationHistory:
    entry = get_application_history_entry_or_none(
        session,
        name=name,
        store=store,
        history_id=history_id,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    if entry is None:
        raise RecordDoesNotExistError(
            f"Application '{name}' does not have a history entry with id {history_id}"
        )
    return entry


def revert_application(
    session: OrmSession,
    *,
    name: str,
    store: str,
    history_id: UUID,
    author_id: UUID,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
    comment: str | None = None,
) -> Application:
    entry = get_application_history_entry(
        session,
        name=name,
        store=store,
        history_id=history_id,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    return update_application(
        session,
        name=name,
        store=store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
        author_id=author_id,
        payload=ApplicationUpdateSchema(
            name=entry.name,
            enabled=entry.enabled,
            comment=comment or f"Reverted to history entry {entry.id}",
        ),
    )


def create_application(
    session: OrmSession,
    *,
    payload: ApplicationCreateSchema,
    author_id: UUID,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
) -> Application:

    if (
        get_application_or_none(
            session,
            name=payload.name,
            store=payload.store,
        )
        is not None
    ):
        raise RecordAlreadyExistsError(
            f"An application with name '{payload.name}' already exists for "
            f"store '{payload.store}'"
        )

    title = db_title.get_title(
        session,
        title_identifier=payload.title_id,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )

    title_flavour = db_flavour.get_title_flavour(
        session,
        title.id,
        payload.flavour,
        accessible_collection_ids=accessible_collection_ids,
    )

    if (
        get_application_by_id_or_none(
            session,
            title_id=title.id,
            flavour=title_flavour.flavour,
            store=payload.store,
            accessible_collection_ids=accessible_collection_ids,
            accessible_title_ids=accessible_title_ids,
        )
        is not None
    ):
        raise RecordAlreadyExistsError(
            f"An application already exists for flavour '{title_flavour.flavour}' "
            f"and store '{payload.store}'"
        )

    application = Application(
        title_id=title.id,
        flavour=title_flavour.flavour,
        store=payload.store,
        enabled=payload.enabled,
        name=payload.name,
    )
    session.add(application)
    try:
        session.flush()
    except IntegrityError as exc:
        if isinstance(exc.orig, UniqueViolation):
            raise RecordAlreadyExistsError(
                f"An application with name '{payload.name}' already exists for "
                f"store '{payload.store}'"
            ) from exc
        raise

    create_application_history_entry(
        session, application, author_id, comment="Create initial history"
    )
    return application


def update_application(
    session: OrmSession,
    *,
    name: str,
    store: str,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
    author_id: UUID,
    payload: ApplicationUpdateSchema,
) -> Application:
    application = get_application(
        session,
        name=name,
        store=store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )

    # Return early if no update data (a comment alone still records history)
    update_data = payload.model_dump(
        exclude_unset=True, exclude={"comment"}, mode="json"
    )
    if update_data:
        try:
            application = session.scalars(
                update(Application)
                .where(
                    Application.title_id == application.title_id,
                    Application.flavour == application.flavour,
                    Application.store == application.store,
                )
                .values(**update_data)
                .returning(Application)
            ).one()
        except IntegrityError as exc:
            if isinstance(exc.orig, UniqueViolation):
                raise RecordAlreadyExistsError(
                    f"An application with name '{payload.name}' already exists for "
                    f"store '{store}'"
                ) from exc
            raise
    else:
        return application

    create_application_history_entry(session, application, author_id, payload.comment)
    session.flush()

    return get_application(
        session,
        name=application.name,
        store=application.store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )


def delete_application(
    session: OrmSession,
    *,
    name: str,
    store: str,
    accessible_collection_ids: Sequence[UUID] | None = None,
    accessible_title_ids: Sequence[UUID] | None = None,
) -> None:
    application = get_application(
        session,
        name=name,
        store=store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    session.delete(application)
    session.flush()
