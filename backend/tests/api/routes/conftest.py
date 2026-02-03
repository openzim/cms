from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.main import app
from cms_backend.db import gen_dbsession, gen_manual_dbsession
from cms_backend.db.models import User


@pytest.fixture
def client(
    dbsession: OrmSession, user: User, mock_token_for_user: Callable[[User], None]
) -> TestClient:
    def test_dbsession() -> Generator[OrmSession]:
        yield dbsession

    # Replace the  database session with the test dbsession
    app.dependency_overrides[gen_dbsession] = test_dbsession
    app.dependency_overrides[gen_manual_dbsession] = test_dbsession

    # Set up default authentication for the default user
    mock_token_for_user(user)

    client = TestClient(app=app)
    client.headers["Authorization"] = "Bearer test-token"

    return client
