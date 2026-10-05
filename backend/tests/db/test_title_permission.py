from collections.abc import Callable
from pathlib import Path

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.collection_permission import get_accessible_collection_ids
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import (
    Account,
    Collection,
    CollectionTitle,
    Title,
    TitlePermission,
)
from cms_backend.db.title import get_title, get_titles
from cms_backend.db.title_permission import get_accessible_title_ids
from cms_backend.roles import RoleEnum


def test_get_accessible_title_ids(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
):
    """Only title-uploaders are restricted at the title level."""
    account1 = create_account(permission=RoleEnum.TITLE_UPLOADER)
    account2 = create_account(permission=RoleEnum.TITLE_UPLOADER)
    admin = create_account(permission=RoleEnum.ADMIN)
    title = create_title(name="wikipedia_en_all")

    dbsession.add(TitlePermission(title_id=title.id, account_id=account1.id))
    dbsession.flush()

    assert get_accessible_title_ids(dbsession, None) is None
    assert get_accessible_title_ids(dbsession, admin) is None
    assert get_accessible_title_ids(dbsession, account2) == []
    assert set(get_accessible_title_ids(dbsession, account1) or []) == {title.id}


def test_title_uploader_has_no_collection_access(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_collection: Callable[..., Collection],
):
    """A title-uploader is not granted any collection-level access."""
    create_collection()
    account = create_account(permission=RoleEnum.TITLE_UPLOADER)

    assert get_accessible_collection_ids(dbsession, account) == []


def test_title_uploader_can_only_access_granted_titles(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
):
    wikipedia_en_all = create_title(name="wikipedia_en_all")
    wikipedia_fr_all = create_title(name="wikipedia_fr_all")
    collection = create_collection()
    create_collection_title(
        title=wikipedia_en_all, collection=collection, path=Path("/other")
    )
    create_collection_title(
        title=wikipedia_fr_all, collection=collection, path=Path("/other")
    )

    uploader = create_account(permission=RoleEnum.TITLE_UPLOADER)
    dbsession.add(TitlePermission(title_id=wikipedia_en_all.id, account_id=uploader.id))
    dbsession.flush()

    accessible_collection_ids = get_accessible_collection_ids(dbsession, uploader)
    accessible_title_ids = get_accessible_title_ids(dbsession, uploader)

    assert (
        get_title(
            dbsession,
            wikipedia_en_all.name,
            accessible_collection_ids=accessible_collection_ids,
            accessible_title_ids=accessible_title_ids,
        ).id
        == wikipedia_en_all.id
    )

    assert (
        get_title(
            dbsession,
            str(wikipedia_en_all.id),
            accessible_collection_ids=accessible_collection_ids,
            accessible_title_ids=accessible_title_ids,
        ).id
        == wikipedia_en_all.id
    )

    with pytest.raises(RecordDoesNotExistError):
        get_title(
            dbsession,
            wikipedia_fr_all.name,
            accessible_collection_ids=accessible_collection_ids,
            accessible_title_ids=accessible_title_ids,
        )

    results = get_titles(
        dbsession,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
        skip=0,
        limit=10,
    )
    assert [record.id for record in results.records] == [wikipedia_en_all.id]
