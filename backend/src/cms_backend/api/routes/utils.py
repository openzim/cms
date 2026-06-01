import math
from xml.etree import ElementTree as ET

from cms_backend.db.collection import LibraryBookData
from cms_backend.utils.filename import construct_download_url
from cms_backend.utils.zim import convert_tags


def build_library_xml(
    entries: list[LibraryBookData], *, path_prefix: str | None = None
) -> str:
    """Build XML library catalog from books."""
    library_elem = ET.Element("library")
    library_elem.set("version", "20110515")

    for entry in entries:
        book, title, download_base_url, path, filename = entry
        if not book.zim_metadata:
            continue

        book_elem = ET.SubElement(library_elem, "book")

        # Required attributes
        book_elem.set("id", str(book.id))
        book_elem.set(
            "size", str(math.ceil(book.size / 1024) if book.size > 0 else book.size)
        )
        book_elem.set("mediaCount", str(book.media_count))
        book_elem.set("articleCount", str(book.article_count))

        # Metadata from zim_metadata dict
        zim_meta = book.zim_metadata
        book_elem.set("title", title.title or zim_meta.get("Title", ""))
        book_elem.set(
            "description", title.description or zim_meta.get("Description", "")
        )
        book_elem.set("language", title.language or zim_meta.get("Language", ""))
        book_elem.set("creator", title.creator or zim_meta.get("Creator", ""))
        book_elem.set("publisher", title.publisher or zim_meta.get("Publisher", ""))
        book_elem.set("name", zim_meta.get("Name", ""))
        book_elem.set("date", zim_meta.get("Date", ""))

        # always set tags to at least have special tags
        tags = zim_meta.get("Tags", "")
        book_elem.set("tags", ";".join(convert_tags(tags)))

        favicon = title.illustration_48x48_at_1 or zim_meta.get(
            "Illustration_48x48@1", ""
        )
        if favicon:
            book_elem.set("favicon", favicon)
            book_elem.set("faviconMimeType", "image/png")

        if download_base_url:
            download_url = construct_download_url(download_base_url, path, filename)
            book_elem.set("url", f"{download_url}.meta4")

        if path_prefix is not None:
            if path_prefix.endswith("/"):
                path_prefix = path_prefix[:-1]

            book_elem.set("path", f"{path_prefix}/{path / filename}")

        if flavour := book.flavour:
            book_elem.set("flavour", flavour)

    ET.indent(library_elem, space="  ", level=0)

    return ET.tostring(library_elem, encoding="unicode")
