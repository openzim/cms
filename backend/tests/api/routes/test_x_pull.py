from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.context import Context
from cms_backend.db import illustration as db_illustration


def _illustration_url(dbsession: OrmSession, data: str) -> str:
    illustration = db_illustration.create_illustration(dbsession, data=data)
    dbsession.flush()
    return f"/v1/illustrations/{illustration.hex_digest}"


def test_pull_header_rejects_non_illustration_route(client: TestClient):
    """Rejects CDN pull requests on non-illustration routes."""
    response = client.get("/v1/healthcheck", headers={"X-Pull": Context.x_pull_header})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["success"] is False


def test_pull_header_allows_illustration_route(
    client: TestClient, dbsession: OrmSession, illustration_48x48_at_1: str
):
    """Allows CDN pull requests on the illustration route."""
    url = _illustration_url(dbsession, illustration_48x48_at_1)

    response = client.get(url, headers={"X-Pull": Context.x_pull_header})

    assert response.status_code == HTTPStatus.OK


def test_pull_header_allows_head_illustration_route(
    client: TestClient, dbsession: OrmSession, illustration_48x48_at_1: str
):
    """Allows CDN pull requests on the illustration HEAD route."""
    url = _illustration_url(dbsession, illustration_48x48_at_1)

    response = client.head(url, headers={"X-Pull": Context.x_pull_header})

    assert response.status_code == HTTPStatus.OK


def test_pull_header_value_mismatch(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(Context, "x_pull_header", "CustomCDN")

    rejected = client.get("/v1/healthcheck", headers={"X-Pull": "CustomCDN"})
    allowed = client.get("/v1/healthcheck", headers={"X-Pull": "KeyCDN"})

    assert rejected.status_code == HTTPStatus.BAD_REQUEST
    assert allowed.status_code == HTTPStatus.OK
