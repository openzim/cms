from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.collection import (
    create_collection,
    get_collection_by_name,
    get_collection_by_name_or_none,
    get_collection_history,
    get_collection_history_entry_or_none,
    get_collections,
    revert_collection,
    update_collection,
)
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Account, Collection, Title, Warehouse
from cms_backend.schemas.models import CollectionUpdateSchema


def test_get_collection_by_name_or_none_not_found(
    dbsession: OrmSession,
):
    """Returns None if the book does not exist"""
    result = get_collection_by_name_or_none(dbsession, collection_name="test")
    assert result is None


def test_get_collection_by_name_not_found(
    dbsession: OrmSession,
):
    with pytest.raises(RecordDoesNotExistError):
        get_collection_by_name(dbsession, collection_name="test")


def test_get_collection_by_name(
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
):
    """Returns the collection by name"""
    collection = create_collection()
    result = get_collection_by_name_or_none(dbsession, collection_name=collection.name)
    assert result is not None
    assert result.name == collection.name


@pytest.mark.parametrize(
    "skip,limit,expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 3, id="second-page"),
        pytest.param(6, 3, 2, id="third-page-partial"),
        pytest.param(8, 3, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 20, 8, id="first-page-with-high-limit"),
    ],
)
def test_get_collections_pagination(
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_collections works correctly with skip and limit"""

    title1 = create_title(name="wikipedia_en_all")
    title2 = create_title(name="ted_en_all")
    title3 = create_title(name="gutenberg_en_all")

    # Create 8 collections with varying numbers of titles/paths
    for i in range(8):
        if i % 3 == 0:
            # Every third collection has multiple titles
            create_collection(
                title_ids_with_paths=[
                    (title1.id, f"/path/to/collection{i}/wikipedia"),
                    (title2.id, f"/path/to/collection{i}/ted"),
                ]
            )
        elif i % 3 == 1:
            # Some collections have a single title
            create_collection(
                title_ids_with_paths=[
                    (title3.id, f"/path/to/collection{i}/gutenberg"),
                ]
            )
        else:
            # Some collections have no titles
            create_collection()

    dbsession.flush()

    results = get_collections(
        dbsession,
        skip=skip,
        limit=limit,
    )
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


def test_create_collection(
    dbsession: OrmSession, warehouse: Warehouse, account: Account
):
    """Test creating a collection."""
    collection = create_collection(
        dbsession,
        author_id=account.id,
        name="testcollection",
        download_base_url="https://www.example.com",
        view_base_url="https://www.example.com",
        warehouse_name=warehouse.name,
    )
    assert collection.name == "testcollection"
    assert collection.download_base_url == "https://www.example.com"
    assert collection.view_base_url == "https://www.example.com"
    assert collection.warehouse.name == warehouse.name


@pytest.mark.parametrize(
    "skip, limit, expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 3, id="second-page"),
        pytest.param(6, 2, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 10, 6, id="first-page-with-high-limit"),
    ],
)
def test_get_collectionhistory(
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    account: Account,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving collection history with pagination"""
    collection = create_collection(name="test_collection")
    for i in range(5):
        update_collection(
            dbsession,
            collection_id=str(collection.id),
            author_id=account.id,
            request=CollectionUpdateSchema(
                name=f"test_collection_{i}",
                comment=f"Update {i}",
            ),
        )
    results = get_collection_history(
        dbsession,
        collection_id=str(collection.id),
        skip=skip,
        limit=limit,
    )
    assert results.nb_records == 6
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


def test_get_collection_history_entry_or_none(
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    account: Account,
):
    """Test retrieving a specific collection history entry"""
    collection = create_collection(name="test_collection")

    collection = update_collection(
        dbsession,
        collection_id=str(collection.id),
        author_id=account.id,
        request=CollectionUpdateSchema(
            name="test_collection1",
            comment="Initial version",
        ),
    )
    dbsession.refresh(collection)

    history_entry = get_collection_history_entry_or_none(
        dbsession,
        collection_id=str(collection.id),
        history_id=collection.history_entries[0].id,
    )
    assert history_entry is not None
    assert history_entry.name == "test_collection1"
    assert history_entry.comment == "Initial version"


def test_revert_collection(
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    account: Account,
):
    """Test reverting a collection to a previous state"""
    collection = create_collection(name="test_collection")

    collection = update_collection(
        dbsession,
        collection_id=str(collection.id),
        author_id=account.id,
        request=CollectionUpdateSchema(
            name="test_collection1",
            comment="First version",
        ),
    )

    collection = update_collection(
        dbsession,
        collection_id=str(collection.id),
        author_id=account.id,
        request=CollectionUpdateSchema(
            name="test_collection2",
            comment="Second version",
        ),
    )

    dbsession.refresh(collection)

    # Revert to the first version
    reverted_collection = revert_collection(
        dbsession,
        collection_id=str(collection.id),
        history_id=collection.history_entries[1].id,
        author_id=account.id,
        comment="Reverting to version 1",
    )
    assert reverted_collection.name == "test_collection1"
