import backend
from backend.main import PREFIX


def test_metadata():
    assert backend.__version__
    assert backend.__title__
    assert backend.__description__


async def test_root(client):
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 308
    response = await client.get("/", follow_redirects=True)
    assert str(response.url).endswith(PREFIX + "/")
    assert response.headers.get("Content-Type") == "text/html; charset=utf-8"
    assert "Swagger UI" in response.text
