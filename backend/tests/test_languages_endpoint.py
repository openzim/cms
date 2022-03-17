import pytest


@pytest.mark.asyncio
async def test_get_list_of_tags(client, titles_with_metadata):
    response = await client.get("/v1/languages")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {"code": "eng", "name": "English", "native": "English"},
            {"code": "fra", "name": "French", "native": "Français"},
        ],
        "total": 2,
        "page": 1,
        "size": 50,
    }
