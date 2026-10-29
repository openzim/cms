from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Account, Title
from cms_backend.db.publication_permission import (
    can_publish,
    create_publication_permission,
    delete_publication_permission,
    get_available_publication_publishers,
    get_publication_permission_or_none,
    get_publication_publishers,
)
from cms_backend.roles import RoleEnum


@pytest.mark.parametrize(
    "role,expected",
    [
        pytest.param(RoleEnum.ADMIN, True, id="admin"),
        pytest.param(RoleEnum.GLOBAL_EDITOR, True, id="global-editor"),
        pytest.param(RoleEnum.GLOBAL_VIEWER, False, id="global-viewer"),
        pytest.param(RoleEnum.COLLECTION_EDITOR, False, id="collection-editor"),
    ],
)
def test_can_publish(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    role: RoleEnum,
    *,
    expected: bool,
) -> None:
    title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    account = create_account(permission=role)

    assert can_publish(dbsession, account, title.id) is expected


def test_can_publish_collection_editor_without_grant(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
) -> None:
    title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    editor = create_account(permission=RoleEnum.COLLECTION_EDITOR)

    assert not can_publish(dbsession, editor, title.id)


def test_can_publish_collection_editor_with_grant(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
) -> None:
    title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    editor = create_account(permission=RoleEnum.COLLECTION_EDITOR)
    create_publication_permission(dbsession, title.id, editor.id)

    assert can_publish(dbsession, editor, title.id)


def test_get_publication_permission(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
) -> None:
    title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    editor = create_account(permission=RoleEnum.COLLECTION_EDITOR)
    create_publication_permission(dbsession, title.id, editor.id)

    assert (
        get_publication_permission_or_none(dbsession, title.id, editor.id) is not None
    )


def test_get_publication_publishers(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
) -> None:
    title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    editor = create_account(permission=RoleEnum.COLLECTION_EDITOR)
    create_publication_permission(dbsession, title.id, editor.id)

    publishers = get_publication_publishers(dbsession, title.id)

    assert [account.id for account in publishers] == [editor.id]


def test_get_available_publication_publishers(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
) -> None:
    title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    granted_editor = create_account(permission=RoleEnum.COLLECTION_EDITOR)
    available_editor = create_account(permission=RoleEnum.COLLECTION_EDITOR)
    create_account(permission=RoleEnum.COLLECTION_VIEWER)
    create_publication_permission(dbsession, title.id, granted_editor.id)

    available = get_available_publication_publishers(
        dbsession, title.id, skip=0, limit=10
    )

    assert {account.id for account in available.records} == {available_editor.id}


def test_delete_publication_permission(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
) -> None:
    title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    editor = create_account(permission=RoleEnum.COLLECTION_EDITOR)
    create_publication_permission(dbsession, title.id, editor.id)

    delete_publication_permission(dbsession, title.id, editor.id)

    assert get_publication_permission_or_none(dbsession, title.id, editor.id) is None
