import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_titles_endpoint_get_list_single_title(title):
    response = client.get("/v1/titles/")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [{"ident": title.ident}],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_titles_endpoint_get_title(title_with_data, book_dict):
    response = client.get(f"/v1/titles/{title_with_data.ident}")
    assert response.status_code == 200
    assert response.json() == {
        "ident": title_with_data.ident,
        "languages": [lang.code for lang in title_with_data.languages],
        "tags": [tag.name for tag in title_with_data.tags],
        "metadata": book_dict["metadata"],
    }
