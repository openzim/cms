import pytest
from defusedxml import ElementTree

from backend.collections.kiwix_public import KiwixPublicCollection
from backend.formatters.kiwixlibraryxml import KiwixLibraryXml
from backend.models import Book


@pytest.mark.asyncio
async def test_kiwix_xml_formatter(title_with_data):
    collection = KiwixPublicCollection()
    xml_bytes = await KiwixLibraryXml.generate(collection=collection)
    tree = ElementTree.fromstring(xml_bytes)

    xmlbooks = tree.findall("book")

    assert "version" in tree.attrib

    for xmlbook in xmlbooks:
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
            assert xmlbook.attrib.get(name)

        book = await Book.objects.get(id=xmlbook.attrib.get("id"))

        assert book.article_count == int(xmlbook.attrib.get("articleCount"))
        assert book.media_count == int(xmlbook.attrib.get("mediaCount"))
        assert book.url == xmlbook.attrib.get("url")
        assert book.size / 1024 == int(xmlbook.attrib.get("size"))
