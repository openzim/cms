from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.collection import (
    get_collection_by_name,
    get_collection_by_name_or_none,
    get_collections,
)
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Collection, Title


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
    assert results.nb_records == 8
    assert len(results.records) <= limit
    assert len(results.records) == expected_count
