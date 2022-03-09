import re

import pytest


@pytest.mark.asyncio
async def test_get_list_of_titles_single_title(client, title, title_ara, title_fra):
    response = await client.get("/v1/titles")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {"ident": title_ara.ident, "languages": [], "metadata": {}, "tags": []},
            {"ident": title.ident, "languages": [], "metadata": {}, "tags": []},
            {"ident": title_fra.ident, "languages": [], "metadata": {}, "tags": []},
        ],
        "total": 3,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_get_list_of_titles_with_languages(
    client,
    title_with_language,
    title_fra,
    title_ara,
):
    response = await client.get("/v1/titles?with_languages=true")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_ara.ident,
                "languages": [
                    {
                        "code": "ara",
                        "name": "Arabic (Egypt)",
                        "native": "العربية (مصر)",
                    },
                ],
                "metadata": {},
                "tags": [],
            },
            {
                "ident": title_with_language.ident,
                "languages": [{"code": "eng", "name": "English", "native": "English"}],
                "metadata": {},
                "tags": [],
            },
            {
                "ident": title_fra.ident,
                "languages": [{"code": "fra", "name": "French", "native": "Français"}],
                "metadata": {},
                "tags": [],
            },
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
    client, title_dict, title_with_language, title_fra
):
    response = await client.get("/v1/titles?lang=eng")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_dict["ident"],
                "languages": [{"code": "eng", "name": "English", "native": "English"}],
                "metadata": {},
                "tags": [],
            }
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_filter_titles_by_language_get_fra(
    client, title_fra_dict, title_with_language, title_fra
):
    response = await client.get("/v1/titles?lang=fra")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_fra_dict["ident"],
                "languages": [{"code": "fra", "name": "French", "native": "Français"}],
                "metadata": {},
                "tags": [],
            }
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_filter_titles_by_language_get_fra_or_eng(
    client, title_with_language, title_fra, title_ara, title_fra_dict, title_dict
):
    """we're creating three Titles with different languages: eng, fra, ara
    But we're only fetching titles whi have languages either 'eng' OR 'fra'
    """
    response = await client.get("/v1/titles?lang=fra|eng")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_dict["ident"],
                "languages": [
                    {"code": "eng", "name": "English", "native": "English"},
                ],
                "metadata": {},
                "tags": [],
            },
            {
                "ident": title_fra_dict["ident"],
                "languages": [
                    {"code": "fra", "name": "French", "native": "Français"},
                ],
                "metadata": {},
                "tags": [],
            },
        ],
        "total": 2,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_filter_titles_by_language_get_fra_and_eng(
    client, title_fra_eng_dict, title_fra_eng, title_with_language, title_fra, title_ara
):
    """Testing the AND operation on languages. Only fetch Titles that have both
    English and French in its languages"""
    response = await client.get("/v1/titles?lang=fra,eng")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_fra_eng_dict["ident"],
                "languages": [
                    {"code": "eng", "name": "English", "native": "English"},
                    {"code": "fra", "name": "French", "native": "Français"},
                ],
                "metadata": {},
                "tags": [],
            }
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_get_list_of_titles_with_tags_without_languages(client, title_with_data):
    response = await client.get("/v1/titles?with_tags=true")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_with_data.ident,
                "languages": [],
                "metadata": {},
                "tags": [{"name": "_category:wikipedia"}, {"name": "wikipedia"}],
            },
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_get_list_of_titles_with_languages_and_tags(client, title_with_data):
    response = await client.get("/v1/titles?with_languages=true&with_tags=true")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_with_data.ident,
                "languages": [
                    {
                        "code": "ara",
                        "name": "Arabic (Egypt)",
                        "native": "العربية (مصر)",
                    },
                    {"code": "eng", "name": "English", "native": "English"},
                    {
                        "code": "lug",
                        "name": "Ganda (Uganda)",
                        "native": "Luganda (Yuganda)",
                    },
                ],
                "metadata": {},
                "tags": [{"name": "_category:wikipedia"}, {"name": "wikipedia"}],
            },
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_get_title_with_specific_metadata(
    client, title_with_data, title_dict, book_dict
):
    response = await client.get("/v1/titles?with_metadata=Title,Publisher")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_dict["ident"],
                "languages": None,
                "metadata": {
                    "Publisher": book_dict["metadata"]["Publisher"],
                    "Title": book_dict["metadata"]["Title"],
                },
                "tags": None,
            },
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }
