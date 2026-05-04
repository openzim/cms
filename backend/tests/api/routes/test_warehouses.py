from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Warehouse
from cms_backend.db.warehouse import get_warehouses


def test_get_warehouses_empty(dbsession: OrmSession):
    """Test that get_warehouses returns empty list when no recipes exist"""
    result = get_warehouses(dbsession, skip=0, limit=10)
    assert result.nb_records == 0
    assert len(result.records) == 0


@pytest.mark.parametrize(
    "skip,limit,expected_count,nb_records",
    [
        pytest.param(0, 3, 3, 8, id="first-page"),
        pytest.param(3, 3, 3, 8, id="second-page"),
        pytest.param(6, 3, 2, 8, id="third-page-partial"),
        pytest.param(8, 3, 0, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, 8, id="first-page-with-low-limit"),
        pytest.param(0, 20, 8, 8, id="first-page-with-high-limit"),
    ],
)
def test_get_tags(
    dbsession: OrmSession,
    create_warehouse: Callable[..., Warehouse],
    skip: int,
    limit: int,
    expected_count: int,
    nb_records: int,
):
    for _ in range(8):
        create_warehouse()

    result = get_warehouses(dbsession, skip=skip, limit=limit)
    assert result.nb_records == nb_records
    assert len(result.records) <= limit
    assert len(result.records) == expected_count
