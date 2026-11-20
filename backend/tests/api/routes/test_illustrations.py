import base64
from http import HTTPStatus

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.illustrations import CACHE_MAX_AGE
from cms_backend.db import illustration as db_illustration


def _create_illustration(dbsession: OrmSession, illustration_48x48_at_1: str) -> str:
    illustration = db_illustration.create_illustration(
        dbsession, data=illustration_48x48_at_1
    )
    dbsession.flush()
    return illustration.hex_digest


def test_get_illustration(
    client: TestClient, dbsession: OrmSession, illustration_48x48_at_1: str
):
    """Serves the decoded illustration with cache headers."""
    hex_digest = _create_illustration(dbsession, illustration_48x48_at_1)

    response = client.get(f"/v1/illustrations/{hex_digest}")

    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "image/png"
    assert response.content == base64.b64decode(illustration_48x48_at_1)
    assert response.headers["ETag"] == f'"{hex_digest}"'
    assert "Last-Modified" in response.headers
    assert "Expires" in response.headers
    assert (
        response.headers["Cache-Control"]
        == f"public, max-age={CACHE_MAX_AGE}, immutable"
    )


def test_head_illustration(
    client: TestClient, dbsession: OrmSession, illustration_48x48_at_1: str
):
    """Serves illustration headers without the body."""
    hex_digest = _create_illustration(dbsession, illustration_48x48_at_1)

    response = client.head(f"/v1/illustrations/{hex_digest}")

    assert response.status_code == HTTPStatus.OK
    assert response.content == b""
    assert response.headers["ETag"] == f'"{hex_digest}"'
    assert "Last-Modified" in response.headers
    assert "Expires" in response.headers


def test_get_illustration_not_found(client: TestClient):
    """Returns 404 for an unknown digest."""
    response = client.get(f"/v1/illustrations/{'0' * 16}")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_illustration_if_none_match(
    client: TestClient, dbsession: OrmSession, illustration_48x48_at_1: str
):
    hex_digest = _create_illustration(dbsession, illustration_48x48_at_1)

    response = client.get(
        f"/v1/illustrations/{hex_digest}",
        headers={"If-None-Match": f'"{hex_digest}"'},
    )

    assert response.status_code == HTTPStatus.NOT_MODIFIED
    assert response.content == b""


def test_get_illustration_if_modified_since(
    client: TestClient, dbsession: OrmSession, illustration_48x48_at_1: str
):
    """Returns 304 when the resource was not modified since the given date."""
    hex_digest = _create_illustration(dbsession, illustration_48x48_at_1)
    first_response = client.get(f"/v1/illustrations/{hex_digest}")

    response = client.get(
        f"/v1/illustrations/{hex_digest}",
        headers={"If-Modified-Since": first_response.headers["Last-Modified"]},
    )

    assert response.status_code == HTTPStatus.NOT_MODIFIED
    assert response.content == b""
