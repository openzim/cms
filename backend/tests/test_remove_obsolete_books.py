import pytest

from backend import utils
from backend.constants import BackendConf
from backend.models import Title


@pytest.mark.asyncio
async def test_remove_obsolete_books(client, book_dict, title_with_three_books):

    title = (
        await Title.objects.exclude_fields(["tags", "languages"])
        .select_related("books")
        .get(ident="wikipedia_ar_mathematics")
    )
    assert await title.books.count() == 3
    book_dict["metadata"]["Name"] = title.ident
    book_dict["period"] = "2021-07-08"
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"
    assert await title.books.count() == BackendConf.nb_book_versions_to_keep


@pytest.mark.asyncio
async def test_crash_remove_obsolete_books(
    monkeypatch, client, book_dict, title_with_three_books
):
    async def mock_remove_obsolete_books(title_ident: str, flavour: str):
        raise NotImplementedError("Fake error")

    monkeypatch.setattr(utils, "remove_obsolete_books", mock_remove_obsolete_books)

    title = (
        await Title.objects.exclude_fields(["tags", "languages"])
        .select_related("books")
        .get(ident="wikipedia_ar_mathematics")
    )

    assert await title.books.count() == 3
    book_dict["metadata"]["Name"] = title.ident
    book_dict["period"] = "2021-07-08"
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"
    assert await title.books.count() == 4  # one was just added
