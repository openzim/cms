from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import flavour as db_flavour
from cms_backend.db.models import Book, Title, TitleFlavour


@pytest.mark.parametrize(
    "skip,limit,expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 1, id="second-page"),
        pytest.param(8, 3, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 20, 4, id="first-page-with-high-limit"),
    ],
)
def test_get_title_flavours_pagination(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_title_flavours works correctly with skip and limit"""

    title = create_title(name="wikipedia_en_all")
    flavours = ["maxi", "mini", "nopic", ""]
    for flavour in flavours:
        tf = TitleFlavour(flavour=flavour, recipe_id=None)
        tf.title = title
        dbsession.add(tf)
        dbsession.flush()

    results = db_flavour.get_title_flavours(
        dbsession, title_id=title.id, limit=limit, skip=skip
    )

    assert len(results.records) <= limit
    assert len(results.records) == expected_count


@patch("cms_backend.db.flavour.db_book.delete_book")
def test_delete_title_flavour(
    mock_delete_book: MagicMock,
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    title = create_title(name="wikipedia_en_all")
    tf = TitleFlavour(flavour="maxi", recipe_id=None)
    tf.title = title
    dbsession.add(tf)
    dbsession.flush()
    create_book(flavour="maxi", title_id=title.id)
    db_flavour.delete_title_flavour(dbsession, title.id, tf.flavour)
    mock_delete_book.assert_called_once()
    assert (
        dbsession.scalars(
            select(TitleFlavour).where(
                TitleFlavour.flavour == tf.flavour, TitleFlavour.title_id == title.id
            )
        ).one_or_none()
        is None
    )
