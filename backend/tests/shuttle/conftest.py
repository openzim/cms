"""Fixtures for shuttle tests."""

from collections.abc import Callable
from pathlib import Path

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Warehouse, WarehousePath


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
def create_warehouse_with_path(
    dbsession: OrmSession,
) -> Callable[..., tuple[Warehouse, WarehousePath]]:
    """Factory to create a warehouse and its path for testing."""

    def _create(
        name: str,
        folder_name: str = "zims",
    ) -> tuple[Warehouse, WarehousePath]:
        warehouse = Warehouse(name=name, configuration={})
        dbsession.add(warehouse)
        dbsession.flush()

        warehouse_path = WarehousePath(folder_name=folder_name)
        warehouse_path.warehouse = warehouse
        dbsession.add(warehouse_path)
        dbsession.flush()

        return warehouse, warehouse_path

    return _create
