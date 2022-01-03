import re

import pytest


@pytest.mark.asyncio
async def test_get_list_of_titles_single_title(client, title):
    response = await client.get("/v1/titles")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {"ident": title_ara.ident},
            {"ident": title.ident},
            {"ident": title_fra.ident},
        ],
        "total": 3,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_get_title_with_data(client, title_with_data, book_dict):
    response = await client.get(f"/v1/titles/{title_with_data.ident}")
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
        "books": [{"id": book_dict["id"], "name": book_dict["metadata"]["Name"]}],
    }


@pytest.mark.asyncio
async def test_get_title_with_no_data(client, title):
    response = await client.get(f"/v1/titles/{title.ident}")
    assert response.status_code == 200
    assert response.json() == {
        "ident": title.ident,
        "languages": [],
        "tags": [],
        "metadata": {},
        "books": [],
    }


@pytest.mark.asyncio
async def test_get_book_missing(client):
    response = await client.get("/v1/titles/missing")
    assert response.status_code == 404
    assert response.headers.get("Content-Type") == "application/json"

    assert response.json() == {"message": "Title with ID “missing” not found"}


async def test_filter_titles_by_language_get_eng(
    title_dict, title_with_language, title_fra
):
    response = client.get("/v1/titles?lang=eng")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [{"ident": title_dict["ident"]}],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_filter_titles_by_language_get_fra(
    title_fra_dict, title_with_language, title_fra
):
    response = client.get("/v1/titles?lang=fra")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [{"ident": title_fra_dict["ident"]}],
        "total": 1,
        "page": 1,
        "size": 50,
    }
