from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.main import app
from cms_backend.api.routes.dependencies import get_redis_publisher
from cms_backend.db import gen_dbsession, gen_manual_dbsession


@pytest.fixture
def client(dbsession: OrmSession, mock_redis_publisher: MagicMock) -> TestClient:
    def test_dbsession() -> Generator[OrmSession]:
        yield dbsession

    def test_redis_publisher() -> MagicMock:
        return mock_redis_publisher

    # Replace the  database session with the test dbsession
    app.dependency_overrides[gen_dbsession] = test_dbsession
    app.dependency_overrides[gen_manual_dbsession] = test_dbsession
    app.dependency_overrides[get_redis_publisher] = test_redis_publisher
    return TestClient(app=app)
