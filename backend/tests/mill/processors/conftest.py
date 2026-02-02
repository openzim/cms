"""Fixtures for mill processors tests."""

import os
from collections.abc import Callable
from uuid import UUID

import pytest

from cms_backend.db.models import Warehouse


def pytest_configure(config):  # pyright: ignore # noqa: ARG001
    """Configure pytest and set up environment variables before imports.

    This is called before any tests are collected, so MillContext will read
    these environment variables when it's imported.
    """
    # Use fixed UUIDs for test warehouses
    os.environ.setdefault(
        "QUARANTINE_WAREHOUSE_ID", "00000000-0000-0000-0000-000000000001"
    )
    os.environ.setdefault(
        "STAGING_WAREHOUSE_ID", "00000000-0000-0000-0000-000000000002"
    )
    os.environ.setdefault("QUARANTINE_BASE_PATH", "quarantine")
    os.environ.setdefault("STAGING_BASE_PATH", "staging")


@pytest.fixture
def quarantine_warehouse(create_warehouse: Callable[..., Warehouse]) -> Warehouse:
    """Create the quarantine warehouse with the expected test ID."""
    return create_warehouse(
        name="quarantine", warehouse_id=UUID("00000000-0000-0000-0000-000000000001")
    )


@pytest.fixture
def staging_warehouse(create_warehouse: Callable[..., Warehouse]) -> Warehouse:
    """Create the staging warehouse with the expected test ID."""
    return create_warehouse(
        name="staging", warehouse_id=UUID("00000000-0000-0000-0000-000000000002")
    )


@pytest.fixture(autouse=True)
def _ensure_warehouses(  # pyright: ignore[reportUnusedFunction]
    quarantine_warehouse: Warehouse,
    staging_warehouse: Warehouse,
) -> None:
    """Ensure test warehouses exist in the database.

    This fixture is autouse so that every test has the warehouses it needs.
    """
