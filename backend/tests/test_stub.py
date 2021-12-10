import datetime
import math

from fastapi.testclient import TestClient

import backend
from backend.main import PREFIX, app

client = TestClient(app)


def test_metadata():
    assert backend.__version__
    assert backend.__title__
    assert backend.__description__


def test_root():
    response = client.get("/", allow_redirects=False)
    assert response.status_code == 308
    response = client.get("/", allow_redirects=True)
    assert response.url.endswith(PREFIX + "/")
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == "Hello World"


def test_test_endpoint():
    now = datetime.datetime.now()
    timestamp = math.ceil(now.timestamp())
    response = client.get(f"/v1/test/{timestamp}")
    assert response.status_code == 200
    data = response.json()
    for key in ("requested_on", "received_on"):
        assert isinstance(data.get(key), str)
        assert datetime.datetime.fromisoformat(data.get(key)) >= now


def test_test_endpoint_missing_input():
    response = client.get("/v1/test/")
    assert response.status_code == 404


def test_test_endpoint_invalid_input():
    for param in ("allo", 1000000000000):
        response = client.get(f"/v1/test/{param}")
        assert response.status_code in (400, 422)
