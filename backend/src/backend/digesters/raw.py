import base64
from urllib.parse import urlparse

from lxml.etree import Element, tostring

from backend.digesters import DigesterInterface
from backend.models import KIND_ILLUSTRATION, Book


class DigesterRaw(DigesterInterface):

    description: str = "Complete, raw list of Books without any filtering"
    slug = "raw"

    @classmethod
    async def generate(cls) -> bytes:
        xml_text = (
            '<?xml version="1.0" encoding="UTF-8" ?>\n<library version="20110515">'
        )

        for book in (
            await Book.objects.exclude_fields(
                ["title", "counter", "languages", "zimcheck"]
            )
            .select_related("metadata")
            .all()
        ):
            metadata = {
                item.name: (
                    base64.standard_b64encode(item.bin_value).decode("ASCII")
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
                    elem.set(meta_names_map.get(metadata_name), str(value))

            elem.set("id", str(book.id))
            elem.set("faviconMimeType", "image/png")
            elem.set("mediaCount", str(book.media_count))
            elem.set("articleCount", str(book.article_count))
            elem.set("size", str(int(book.size / 1024)))
            if book.url:
                elem.set("url", book.url)
                elem.set(
                    "path", "../var/www/download.kiwix.org" + urlparse(book.url).path
                )
            xml_text += "\n" + tostring(elem, encoding="unicode")

        xml_text += "\n</library>\n"

        return xml_text
