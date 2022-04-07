import defusedxml.ElementTree as ET
import pytest

from backend.digesters.raw import gen_raw_digester
from backend.models import Book


@pytest.mark.asyncio
async def test_raw(client):
    response = await client.get("/v1/digesters/raw")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/xml"
    assert response.content == b'<Library version="20110515" />'


@pytest.mark.asyncio
async def test_of_gen_raw_digester(client, title_with_data):
    xml_bytes = await gen_raw_digester()
    tree = ET.fromstring(xml_bytes)
    books = tree.findall("book")
    assert "version" in tree.attrib
    assert len(books) == 1
    book = books[0]
    assert "title" in book.attrib
    assert "id" in book.attrib
    assert "faviconMimeType" in book.attrib
    assert "description" in book.attrib
    assert "language" in book.attrib
    assert "creator" in book.attrib
    assert "publisher" in book.attrib
    assert "name" in book.attrib
    assert "flavour" in book.attrib
    assert "tags" in book.attrib
    assert "favicon" in book.attrib
    assert "date" in book.attrib
    assert "mediaCount" in book.attrib
    assert "articleCount" in book.attrib
    assert "size" in book.attrib

    b = await Book.objects.get(id=book.attrib["id"])
    assert book.attrib["url"] == b.url
    assert int(book.attrib["size"]) == b.size * 1024
