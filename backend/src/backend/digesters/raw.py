import base64
from urllib.parse import urlparse
from xml.etree.ElementTree import Element, SubElement, tostring

from backend.models import KIND_ILLUSTRATION, Book


async def gen_raw_digester() -> bytes:

    lib_elem = Element("Library")
    lib_elem.attrib["version"] = "20110515"
    for book in await Book.objects.select_related("metadata").exclude(title=None).all():
        book_dict = {}
        book_dict.update(
            {
                item.name: (
                    base64.standard_b64encode(item.bin_value)
                    if item.kind == KIND_ILLUSTRATION
                    else item.value
                )
                for item in book.metadata
            }
        )

        metadata_name_dic = {
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

        elem = SubElement(lib_elem, "book")
        for metadata_name in metadata_name_dic.keys():
            value = book_dict.get(metadata_name)
            if value:
                elem.attrib[metadata_name_dic.get(metadata_name)] = str(value)

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

    return tostring(lib_elem)
