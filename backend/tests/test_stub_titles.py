import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import Title

client = TestClient(app)


@pytest.mark.asyncio
async def test_titles_endpoint_get_list_single_title(clear_database, title):
    assert len(await Title.objects.all()) == 1

    response = client.get("/v1/titles/")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {"titles": [{"ident": title.ident}]}


@pytest.mark.asyncio
async def test_titles_endpoint_get_title(title_with_data):
    response = client.get(f"/v1/titles/{title_with_data.ident}")
    assert response.status_code == 200
    assert response.json() == {
        "ident": title_with_data.ident,
        "languages": [{"code": "eng"}],
        "tags": [{"name": "wikipedia"}],
    }
