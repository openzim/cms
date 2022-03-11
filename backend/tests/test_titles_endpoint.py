import re

import pytest


@pytest.mark.asyncio
async def test_get_list_of_titles_single_title(client, title, title_ara, title_fra):
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
async def test_get_list_of_titles_with_languages(
    client,
    title_with_language,
    title_fra,
    title_ara,
):
    response = await client.get("/v1/titles?with-languages=true")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {"ident": title_ara.ident, "languages": ["ara"]},
            {"ident": title_with_language.ident, "languages": ["eng"]},
            {"ident": title_fra.ident, "languages": ["fra"]},
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query, expected",
    [
        ("wikipedia_en_test", [{"ident": "wikipedia_en_test"}]),
        ("wikipedia_en_all", []),
        (
            "wikipedia_*",
            [
                {"ident": "wikipedia_ar_all"},
                {"ident": "wikipedia_en_test"},
                {"ident": "wikipedia_fr_all"},
            ],
        ),
    ],
)
async def test_get_title_by_ident(client, title, title_ara, title_fra, query, expected):
    response = await client.get(f"/v1/titles?ident={query}")
    assert response.status_code == 200
    assert response.json() == {
        "items": expected,
        "total": len(expected),
        "page": 1,
        "size": 50,
    }


async def test_filter_titles_by_language_get_eng(
    client, title_dict, title_with_language, title_fra
):
    response = await client.get("/v1/titles?lang=eng")
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
    client, title_fra_dict, title_with_language, title_fra
):
    response = await client.get("/v1/titles?lang=fra")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [{"ident": title_fra_dict["ident"]}],
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
            {"ident": title_dict["ident"]},
            {"ident": title_fra_dict["ident"]},
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
        "items": [{"ident": title_fra_eng_dict["ident"]}],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_filter_titles_by_language_bad_combination(client, title_fra_eng):
    response = await client.get("/v1/titles?lang=fra,eng|esp")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_list_of_titles_with_tags_without_languages(client, title_with_data):
    response = await client.get("/v1/titles?with-tags=true")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_with_data.ident,
                "tags": ["_category:wikipedia", "wikipedia"],
            },
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_get_list_of_titles_with_languages_and_tags(client, title_with_data):
    response = await client.get("/v1/titles?with-languages=true&with-tags=true")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_with_data.ident,
                "languages": ["ara", "eng", "lug"],
                "tags": ["_category:wikipedia", "wikipedia"],
            },
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query, expected",
    [
        ("wikipedia", [{"ident": "wikipedia_en_all"}, {"ident": "wikipedia_fr_all"}]),
        (
            "wikipedia,_category:wikipedia",
            [{"ident": "wikipedia_en_all"}, {"ident": "wikipedia_fr_all"}],
        ),
        ("french,english", []),
        (
            "french|english",
            [{"ident": "wikipedia_en_all"}, {"ident": "wikipedia_fr_all"}],
        ),
    ],
)
async def test_filter_titles_by_tag_single(
    client, titles_with_metadata, query, expected
):
    response = await client.get(f"/v1/titles?tag={query}")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": expected,
        "total": len(expected),
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_filter_titles_by_tag_bad_combination(client, titles_with_metadata):
    response = await client.get("/v1/titles?tag=wikipedia,_category:wikipedia|french")
    assert response.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query, expected",
    [
        ("metadata=Name:wikipedia_en_all", [{"ident": "wikipedia_en_all"}]),
        (
            "metadata=Name:wikipedia_*_all",
            [{"ident": "wikipedia_en_all"}, {"ident": "wikipedia_fr_all"}],
        ),
        (
            "metadata=Scraper:mwoffliner",
            [{"ident": "wikipedia_en_all"}, {"ident": "wikipedia_fr_all"}],
        ),
    ],
)
async def test_filter_titles_by_metadata(client, titles_with_metadata, query, expected):
    response = await client.get(f"/v1/titles?{query}")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": expected,
        "total": len(expected),
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_get_title_with_specific_metadata(
    client, title_with_data, title_dict, book_dict
):
    response = await client.get(
        "/v1/titles?with-metadata=Title&with-metadata=Publisher"
    )
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_dict["ident"],
                "metadata": {
                    "Publisher": book_dict["metadata"]["Publisher"],
                    "Title": book_dict["metadata"]["Title"],
                },
            }
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_get_title_with_all_metadata(
    client, title_with_data, title_dict, book_dict
):
    response = await client.get("/v1/titles?with-metadata=all")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_dict["ident"],
                "metadata": book_dict["metadata"],
            }
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_get_title_with_alltext_metadata(
    client, title_with_data, title_dict, book_dict
):
    response = await client.get("/v1/titles?with-metadata=all-text")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {
        "items": [
            {
                "ident": title_dict["ident"],
                "metadata": {
                    k: v
                    for k, v in book_dict["metadata"].items()
                    if k != "Illustration_48x48"
                },
            }
        ],
        "total": 1,
        "page": 1,
        "size": 50,
    }
