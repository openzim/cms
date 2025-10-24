from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Title
from cms_backend.db.title import get_title_by_name_or_none, get_titles


def test_get_title_by_name_or_none(
    dbsession: OrmSession,
    title: Title,  # noqa: ARG001
):
    """Create a book from a zimfarm notification"""
    assert get_title_by_name_or_none(dbsession, name="foo") is None
    test_fr_title = get_title_by_name_or_none(dbsession, name="test_en_all")
    assert test_fr_title is not None
    assert test_fr_title.name == "test_en_all"


@pytest.mark.parametrize(
    "name,expected_count",
    [
        pytest.param(None, 30, id="all"),
        pytest.param("wikipedia_\\_en", 5, id="wikipedia"),
        pytest.param("wikibook_\\_en_all", 10, id="wikibook"),
        pytest.param("wikiquote%\\_all", 15, id="wikiquote"),
    ],
)
def test_get_titles_search(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    name: str | None,
    expected_count: int,
):
    """Test that get_titles works correctly with filters"""
    for i in range(5):
        title = create_title(name=f"wikipedia{i}_en_all")
        dbsession.add(title)

    for i in range(10):
        title = create_title(name=f"wikibook{i}_en_all")
        dbsession.add(title)

    for i in range(15):
        create_title(name=f"wikiquote{i}_en_all")

    limit = 8
    results = get_titles(
        dbsession,
        skip=0,
        limit=limit,
        name=name,
    )
    assert results.nb_records == expected_count
    assert len(results.records) <= limit


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
def test_get_titles_skip(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_titles works correctly with filters"""
    for i in range(6):
        create_title(name=f"wikipedia{i}_en_all")

    results = get_titles(
        dbsession,
        skip=skip,
        limit=limit,
        name="wikipedia",
    )
    assert results.nb_records == 6
    assert len(results.records) <= limit
    assert len(results.records) == expected_count
