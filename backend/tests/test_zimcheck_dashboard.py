import uuid

import pytest
from ormar.exceptions import NoMatch

from backend.models import Book, Title
from backend.routes.zimcheck_dashboard import zim_check_dashboard


@pytest.mark.asyncio
async def test_zim_check_dashboard(client, book_dict):
    book_dict["zimcheck"].update(
        {
            "logs": [
                {
                    "check": "redundant",
                    "level": "WARNING",
                    "message": "I/vendors/ext-icons/eps.svg",
                    "path1": "I/vendors/ext-icons/eps.svg",
                    "path2": "I/vendors/ext-icons/wmf.svg",
                },
                {
                    "check": "redundant",
                    "level": "WARNING",
                    "message": "I/vendors/ext-icons/dist.svg",
                    "path1": "I/vendors/ext-icons/dist.svg",
                    "path2": "I/vendors/ext-icons/xaml.svg",
                },
            ]
        }
    )

    await Title.objects.create(ident="wikipedia_ar_mathematics")
    title = await Title.objects.create(ident="wikipedia_en_mathematics")
    await Book.objects.create(
        id=str(uuid.uuid4()),
        counter=book_dict["counter"],
        period=book_dict["period"],
        article_count=book_dict["article_count"],
        media_count=book_dict["media_count"],
        size=book_dict["size"],
        url=book_dict["url"],
        zimcheck=book_dict["zimcheck"],
        title=title,
    )
    response = await client.get("/v1/zimcheck")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {"checkData": {"": {"redundant": 2}}}


@pytest.mark.asyncio
async def test_zimcheck_dashboard_NoMatch(monkeypatch):
    def raise_NoMatch(*args, **kwargs):
        raise NoMatch("No match")

    monkeypatch.setattr(Book.objects, "first", raise_NoMatch)
    response = await zim_check_dashboard()
    assert response == {"checkData": {"": {"redundant": 2}}}
