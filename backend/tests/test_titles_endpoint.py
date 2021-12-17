import re

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_get_list_of_titles_single_title(title):
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
async def test_get_title_with_data(title_with_data, book_dict):
    response = client.get(f"/v1/titles/{title_with_data.ident}")
    assert response.status_code == 200

    tags = []
    for tag_name in book_dict["metadata"]["Tags"].split(";"):
        if not re.match(r"_(sw|ftindex|pictures|videos|details):(yes|no)", tag_name):
            tags.append(tag_name)

    assert response.json() == {
        "ident": title_with_data.ident,
        "languages": sorted(book_dict["metadata"]["Language"].split(",")),
        "tags": sorted(tags),
        "metadata": book_dict["metadata"],
        "books": [book_dict["id"]],
    }


@pytest.mark.asyncio
async def test_get_title_with_no_data(title):
    response = client.get(f"/v1/titles/{title.ident}")
    assert response.status_code == 200
    assert response.json() == {
        "ident": title.ident,
        "languages": [],
        "tags": [],
        "metadata": {},
        "books": [],
    }
