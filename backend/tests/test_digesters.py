import pytest
from defusedxml import ElementTree

from backend.digesters.raw import gen_raw_digester
from backend.models import Book


@pytest.mark.asyncio
async def test_raw_endpoint(client, title_with_data):
    response = await client.get("/v1/digesters/raw")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/xml"

    tree = ElementTree.fromstring(response.content)
    assert "version" in tree.attrib

    books = list(tree)
    assert len(books) == await Book.objects.count()
    for child in books:
        book = await Book.objects.get(id=child.get("id"))

        assert book.article_count == int(child.get("articleCount"))
        assert book.media_count == int(child.get("mediaCount"))
        assert book.url == child.get("url")


@pytest.mark.asyncio
async def test_of_gen_raw_digester(client, title_with_data):
    xml_bytes = await gen_raw_digester()

    tree = ElementTree.fromstring(xml_bytes)
    books = tree.findall("book")
    assert "version" in tree.attrib
    assert len(books) == 1
    book = books[0]
    for name in [
        "title",
        "id",
        "faviconMimeType",
        "description",
        "language",
        "creator",
        "publisher",
        "name",
        "flavour",
        "tags",
        "favicon",
        "date",
        "mediaCount",
        "articleCount",
        "size",
    ]:
        assert name in book.attrib

    db_book = await Book.objects.get(id=book.attrib["id"])
    assert book.attrib["url"] == db_book.url
    assert int(book.attrib["size"]) == db_book.size * 1024
