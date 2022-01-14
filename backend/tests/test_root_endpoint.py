import backend
from backend.main import PREFIX


def test_metadata():
    assert backend.__version__
    assert backend.__title__
    assert backend.__description__


def test_root(client):
    response = client.get("/", allow_redirects=False)
    assert response.status_code == 308
    response = client.get("/", allow_redirects=True)
    assert response.url.endswith(PREFIX + "/")
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == "Hello World"
