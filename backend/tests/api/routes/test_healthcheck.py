from http import HTTPStatus

from fastapi.testclient import TestClient

# from sqlalchemy.orm import Session as OrmSession


def test_get_healthcheck(
    client: TestClient,
):
    """Test healthcheck endpoint"""

    response = client.get("/v1/healthcheck")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert "status" in response_doc
    assert response_doc["status"] == "ok"
    assert "timestamp" in response_doc
