from collections.abc import Callable
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import application as db_application
from cms_backend.db.exceptions import (
    RecordAlreadyExistsError,
    RecordDoesNotExistError,
)
from cms_backend.db.models import Account, Application, ApplicationHistory, Title
from cms_backend.schemas.models import ApplicationCreateSchema, ApplicationUpdateSchema


def test_get_application(
    dbsession: OrmSession,
    application: Application,
) -> None:
    result = db_application.get_application(
        dbsession, name=application.name, store=application.store
    )

    assert result.title_id == application.title_id
    assert result.flavour == application.flavour
    assert result.store == application.store
    assert result.name == application.name


def test_get_application_not_found(
    dbsession: OrmSession,
    application: Application,
) -> None:
    with pytest.raises(RecordDoesNotExistError):
        db_application.get_application(dbsession, name=application.name, store="apple")


def test_get_application_by_id_or_none(
    dbsession: OrmSession,
    application: Application,
) -> None:
    result = db_application.get_application_by_id_or_none(
        dbsession,
        title_id=application.title_id,
        flavour=application.flavour,
        store=application.store,
    )

    assert result is not None
    assert result.name == application.name


def test_get_application_by_id_or_none_not_found(
    dbsession: OrmSession,
) -> None:
    result = db_application.get_application_by_id_or_none(
        dbsession,
        title_id=uuid4(),
        flavour="maxi",
        store="android",
    )

    assert result is None


@pytest.mark.parametrize(
    ("name", "store", "expected_count"),
    [
        pytest.param(None, None, 3, id="no-filters"),
        pytest.param(None, "android", 2, id="android-store"),
        pytest.param(None, "apple", 1, id="apple-store"),
        pytest.param("phet", None, 2, id="name-filter"),
        pytest.param("phet2", None, 1, id="name-filter2"),
        pytest.param("phet", "android", 1, id="name-and-store"),
        pytest.param("phet2", "apple", 0, id="name-and-store-no-match"),
        pytest.param("unknown", None, 0, id="unknown-name"),
    ],
)
def test_get_applications_filters(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_application: Callable[..., Application],
    name: str | None,
    store: str | None,
    expected_count: int,
) -> None:
    title = create_title(flavours=["maxi", "mini"])
    create_application(title=title, flavour="maxi", store="android", name="phet")
    create_application(title=title, flavour="maxi", store="apple", name="phet")
    create_application(title=title, flavour="mini", store="android", name="phet2")

    result = db_application.get_applications(dbsession, name=name, store=store)

    assert result.nb_records == expected_count
    assert len(result.records) == expected_count
    if name is not None:
        assert all(record.name == name for record in result.records)
    if store is not None:
        assert all(record.store == store for record in result.records)


def test_get_applications_access_filter(
    dbsession: OrmSession,
    application: Application,
) -> None:
    assert (
        db_application.get_applications(
            dbsession,
            accessible_collection_ids=[],
            accessible_title_ids=[],
        ).nb_records
        == 0
    )
    assert (
        db_application.get_applications(
            dbsession,
            accessible_collection_ids=[],
            accessible_title_ids=[application.title_id],
        ).nb_records
        == 1
    )


def test_create_application(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
) -> None:
    title = create_title(flavours=["maxi"])

    application = db_application.create_application(
        dbsession,
        payload=ApplicationCreateSchema(
            title_id=str(title.id),
            flavour="maxi",
            store="android",
            enabled=True,
            name="phet",
        ),
        author_id=account.id,
    )

    assert application.title_id == title.id
    assert application.flavour == "maxi"
    assert application.store == "android"
    assert application.enabled is True
    assert application.name == "phet"

    history_entry = dbsession.scalars(select(ApplicationHistory)).one()
    assert history_entry.title_id == title.id
    assert history_entry.flavour == "maxi"
    assert history_entry.store == "android"
    assert history_entry.name == "phet"
    assert history_entry.enabled is True
    assert history_entry.author_id == account.id
    assert history_entry.comment == "Create initial history"


def test_create_application_rejects_duplicate_primary_key(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
) -> None:
    title = create_title(flavours=["maxi"])
    payload = ApplicationCreateSchema(
        title_id=str(title.id),
        flavour="maxi",
        store="android",
        enabled=True,
        name="phet",
    )
    db_application.create_application(dbsession, payload=payload, author_id=account.id)

    with pytest.raises(RecordAlreadyExistsError, match="already exists"):
        db_application.create_application(
            dbsession, payload=payload, author_id=account.id
        )


def test_create_application_rejects_duplicate_name_and_store(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
) -> None:
    first_title = create_title(name="first", flavours=["maxi"])
    second_title = create_title(name="second", flavours=["maxi"])

    db_application.create_application(
        dbsession,
        payload=ApplicationCreateSchema(
            title_id=str(first_title.id),
            flavour="maxi",
            store="android",
            enabled=True,
            name="phet",
        ),
        author_id=account.id,
    )

    with pytest.raises(RecordAlreadyExistsError, match="already exists"):
        db_application.create_application(
            dbsession,
            payload=ApplicationCreateSchema(
                title_id=str(second_title.id),
                flavour="maxi",
                store="android",
                enabled=True,
                name="phet",
            ),
            author_id=account.id,
        )


def test_update_application(
    dbsession: OrmSession,
    application: Application,
    account: Account,
) -> None:
    original_name = application.name

    updated = db_application.update_application(
        dbsession,
        name=application.name,
        store=application.store,
        author_id=account.id,
        payload=ApplicationUpdateSchema(
            enabled=False, name="updated_app", comment="Disable app"
        ),
    )

    assert updated.enabled is False
    assert updated.name == "updated_app"

    history_entries = dbsession.scalars(select(ApplicationHistory)).all()
    assert {entry.name for entry in history_entries} == {
        original_name,
        "updated_app",
    }
    assert any(entry.comment == "Disable app" for entry in history_entries)


def test_delete_application(
    dbsession: OrmSession,
    application: Application,
) -> None:
    db_application.delete_application(
        dbsession,
        name=application.name,
        store=application.store,
    )

    with pytest.raises(RecordDoesNotExistError):
        db_application.get_application(
            dbsession, name=application.name, store=application.store
        )


def test_get_application_history_entry(
    dbsession: OrmSession,
    application: Application,
) -> None:
    history = db_application.get_application_history(
        dbsession,
        name=application.name,
        store=application.store,
        skip=0,
        limit=10,
    )
    history_id = history.records[0].id

    entry = db_application.get_application_history_entry(
        dbsession,
        name=application.name,
        store=application.store,
        history_id=history_id,
    )

    assert entry.id == history_id
    assert entry.name == application.name
    assert entry.author.display_name == history.records[0].author


def test_get_application_history_entry_not_found(
    dbsession: OrmSession,
    application: Application,
) -> None:
    assert (
        db_application.get_application_history_entry_or_none(
            dbsession,
            name=application.name,
            store=application.store,
            history_id=uuid4(),
        )
        is None
    )

    with pytest.raises(RecordDoesNotExistError):
        db_application.get_application_history_entry(
            dbsession,
            name=application.name,
            store=application.store,
            history_id=uuid4(),
        )


def test_revert_application(
    dbsession: OrmSession,
    create_application: Callable[..., Application],
    account: Account,
) -> None:
    application = create_application(name="phet", store="android", enabled=True)
    store = application.store

    db_application.update_application(
        dbsession,
        name="phet",
        store=store,
        author_id=account.id,
        payload=ApplicationUpdateSchema(
            name="phet2", enabled=False, comment="Rename app"
        ),
    )

    history = db_application.get_application_history(
        dbsession, name="phet2", store=store, skip=0, limit=10
    )
    initial_entry = next(
        entry
        for entry in history.records
        if entry.comment == "Initial history entry"
    )

    reverted = db_application.revert_application(
        dbsession,
        name="phet2",
        store=store,
        history_id=initial_entry.id,
        author_id=account.id,
        comment="Revert app",
    )

    assert reverted.name == "phet"
    assert reverted.enabled is True

    history_after = db_application.get_application_history(
        dbsession, name="phet", store=store, skip=0, limit=10
    )
    assert history_after.nb_records == 3
    assert any(entry.comment == "Revert app" for entry in history_after.records)
