"""Fixtures for shuttle tests."""

from collections.abc import Callable
from pathlib import Path

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Warehouse


@pytest.fixture
def temp_warehouse_dirs(tmp_path: Path) -> dict[str, Path]:
    """Create temporary warehouse directories for testing."""
    warehouse_1 = tmp_path / "warehouse_1"
    warehouse_2 = tmp_path / "warehouse_2"

    warehouse_1.mkdir()
    warehouse_2.mkdir()

    return {
        "warehouse_1": warehouse_1,
        "warehouse_2": warehouse_2,
    }


@pytest.fixture
def create_warehouse_simple(
    dbsession: OrmSession,
) -> Callable[..., Warehouse]:
    """Factory to create a warehouse for testing."""

    def _create(
        name: str,
    ) -> Warehouse:
        warehouse = Warehouse(name=name)
        dbsession.add(warehouse)
        dbsession.flush()
        return warehouse

    return _create
