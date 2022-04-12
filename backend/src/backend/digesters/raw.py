import base64
from urllib.parse import urlparse
from xml.etree.ElementTree import Element, tostring

from backend.models import KIND_ILLUSTRATION, Book

description = "Complete, raw list of Books without any filtering"


async def gen_raw_digester() -> bytes:

    xml_text = b'<?xml version="1.0" encoding="UTF-8" ?>\n<library version="20110515">'

    for book in await Book.objects.select_related("metadata").all():
        metadata = {
            item.name: (
                base64.standard_b64encode(item.bin_value)
                if item.kind == KIND_ILLUSTRATION
                else item.value
            )
            for item in book.metadata
        }

        meta_names_map = {
            "Title": "title",
            "Description": "description",
            "Language": "language",
            "Creator": "creator",
            "Publisher": "publisher",
            "Name": "name",
            "Flavour": "flavour",
            "Tags": "tags",
            "Illustration_48x48": "favicon",
            "Date": "date",
        }

        elem = Element("book")
        for metadata_name in meta_names_map.keys():
            value = metadata.get(metadata_name)
            if value:
                elem.attrib[meta_names_map.get(metadata_name)] = str(value)

        elem.attrib["id"] = str(book.id)
        elem.attrib["faviconMimeType"] = "image/png"
        elem.attrib["mediaCount"] = str(book.media_count)
        elem.attrib["articleCount"] = str(book.article_count)
        elem.attrib["size"] = str(book.size * 1024)

        if book.url:
            elem.attrib["url"] = book.url
            elem.attrib["path"] = (
                "../var/www/download.kiwix.org" + urlparse(book.url).path
            )

        xml_text += b"\n" + tostring(elem)

    xml_text += b"\n</library>\n"

    return xml_text
