from datetime import datetime
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree as ET

from cms_backend.context import Context
from cms_backend.db.collection import LibraryBookData
from cms_backend.db.models import Book
from cms_backend.utils.filename import construct_download_url
from cms_backend.utils.zim import convert_tags

ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
DC_NAMESPACE = "http://purl.org/dc/terms/"
OPDS_NAMESPACE = "https://specs.opds.io/opds-1.2"
KIWIX_NAMESPACE = "https://kiwix.org/namespace/opds"

OPDS_MEDIA_TYPE = "application/atom+xml"

ACQUISITION_REL = "http://opds-spec.org/acquisition/open-access"
THUMBNAIL_REL = "http://opds-spec.org/image/thumbnail"
THUMBNAIL_MIMETYPE = "image/png;width=48;height=48;scale=1"

ZIM_MIMETYPE = "application/x-zim"
METALINK_MIMETYPE = "application/metalink4+xml"
BITTORRENT_MIMETYPE = "application/x-bittorrent"
ILLUSTRATION_MIMETYPE = "image/png"

FEED_ID = f"urn:uuid:{uuid5(NAMESPACE_URL, 'https://cms.openzim.org/opds.xml')}"
FEED_TITLE = "Kiwix library"
# Feed-level <updated> value used when the feed has no entry to derive it from
EMPTY_FEED_UPDATED = "1970-01-01T00:00:00Z"

CATEGORY_TAG_PREFIX = "_category:"
ISO_DATE_LENGTH = 10


def _atom(tag: str) -> str:
    return f"{{{ATOM_NAMESPACE}}}{tag}"


def _dc(tag: str) -> str:
    return f"{{{DC_NAMESPACE}}}{tag}"


def _kiwix(tag: str) -> str:
    return f"{{{KIWIX_NAMESPACE}}}{tag}"


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _date_to_iso(date: str) -> str:
    """Normalize a ZIM date (YYYY-MM-DD) into an ISO date timestamp."""
    date = date[:ISO_DATE_LENGTH]
    if len(date) != ISO_DATE_LENGTH:
        return date
    return f"{date}T00:00:00Z"


def _datetime_to_iso(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _book_date_iso(book: Book) -> str:
    if book.date:
        return _date_to_iso(book.date)
    return _datetime_to_iso(book.created_at)


def _extract_category(tags: str) -> str | None:
    """Extract the category from the ``_category:xxx`` tag, if any."""
    for tag in tags.split(";"):
        if tag.startswith(CATEGORY_TAG_PREFIX):
            return tag[len(CATEGORY_TAG_PREFIX) :]
    return None


def build_illustration_href(book: Book, illustration: str) -> str:
    """Build the OPDS thumbnail href for a book illustration.

    The illustration is either embedded as a base64 data URL or referenced
    through the configured URL template (with {book_id} replaced by the book
    UUID). When the URL template is missing, we fall back to embedding.
    """
    if Context.opds_inline_illustration:
        return f"data:{ILLUSTRATION_MIMETYPE};base64,{illustration}"

    template = Context.opds_illustration_url_template
    if not template:
        return f"data:{ILLUSTRATION_MIMETYPE};base64,{illustration}"

    return template.replace("{book_id}", str(book.id))


def _append_link(
    parent: ET.Element,
    rel: str,
    href: str,
    *,
    mimetype: str | None = None,
    length: int | None = None,
) -> None:
    link = ET.SubElement(parent, _atom("link"))
    link.set("rel", rel)
    link.set("href", href)
    if mimetype is not None:
        link.set("type", mimetype)
    if length is not None:
        link.set("length", str(length))


def _append_entry(
    feed: ET.Element, entry: LibraryBookData, *, path_prefix: str | None
) -> None:
    book, title, download_base_url, path, filename = entry

    zim_metadata = book.zim_metadata
    if not zim_metadata:
        return

    entry_elem = ET.SubElement(feed, _atom("entry"))

    ET.SubElement(entry_elem, _atom("id")).text = f"urn:uuid:{book.id}"
    ET.SubElement(entry_elem, _atom("title")).text = _text(
        title.title or zim_metadata.get("Title")
    )
    ET.SubElement(entry_elem, _atom("summary")).text = _text(
        title.description or zim_metadata.get("Description")
    )
    ET.SubElement(entry_elem, _atom("language")).text = _text(
        title.language or zim_metadata.get("Language")
    )

    author = ET.SubElement(entry_elem, _atom("author"))
    ET.SubElement(author, _atom("name")).text = _text(
        title.creator or zim_metadata.get("Creator")
    )

    publisher = ET.SubElement(entry_elem, _atom("publisher"))
    ET.SubElement(publisher, _atom("name")).text = _text(
        title.publisher or zim_metadata.get("Publisher")
    )

    updated = _book_date_iso(book)
    ET.SubElement(entry_elem, _atom("updated")).text = updated
    ET.SubElement(entry_elem, _dc("issued")).text = updated

    ET.SubElement(entry_elem, _kiwix("titleid")).text = str(title.id)
    ET.SubElement(entry_elem, _kiwix("popularity")).text = str(title.popularity)

    ET.SubElement(entry_elem, _atom("name")).text = _text(zim_metadata.get("Name"))

    if book.flavour:
        ET.SubElement(entry_elem, _atom("flavour")).text = book.flavour

    tags = _text(zim_metadata.get("Tags"))
    if category := _extract_category(tags):
        ET.SubElement(entry_elem, _atom("category")).text = category

    ET.SubElement(entry_elem, _atom("tags")).text = ";".join(convert_tags(tags))

    ET.SubElement(entry_elem, _atom("articleCount")).text = str(book.article_count)
    ET.SubElement(entry_elem, _atom("mediaCount")).text = str(book.media_count)

    if download_base_url:
        download_url = construct_download_url(download_base_url, path, filename)
        _append_link(
            entry_elem,
            ACQUISITION_REL,
            download_url,
            mimetype=ZIM_MIMETYPE,
            length=book.size,
        )
        _append_link(
            entry_elem,
            ACQUISITION_REL,
            f"{download_url}.meta4",
            mimetype=METALINK_MIMETYPE,
            length=book.size,
        )
        _append_link(
            entry_elem,
            ACQUISITION_REL,
            f"{download_url}.torrent",
            mimetype=BITTORRENT_MIMETYPE,
            length=book.size,
        )

    if path_prefix is not None:
        if path_prefix.endswith("/"):
            path_prefix = path_prefix[:-1]
        _append_link(
            entry_elem,
            ACQUISITION_REL,
            f"{path_prefix}/{path / filename}",
            mimetype=ZIM_MIMETYPE,
            length=book.size,
        )

    illustration = title.illustration_48x48_at_1 or zim_metadata.get(
        "Illustration_48x48@1"
    )
    if illustration:
        _append_link(
            entry_elem,
            THUMBNAIL_REL,
            build_illustration_href(book, _text(illustration)),
            mimetype=THUMBNAIL_MIMETYPE,
        )


def build_opds_xml(
    entries: list[LibraryBookData], *, path_prefix: str | None = None
) -> str:
    """Build an OPDS acquisition feed from books."""
    ET.register_namespace("", ATOM_NAMESPACE)
    ET.register_namespace("dc", DC_NAMESPACE)
    ET.register_namespace("kiwix", KIWIX_NAMESPACE)

    feed = ET.Element(_atom("feed"))
    feed.set("xmlns:opds", OPDS_NAMESPACE)

    ET.SubElement(feed, _atom("id")).text = FEED_ID
    ET.SubElement(feed, _atom("title")).text = FEED_TITLE

    book_dates = [
        _book_date_iso(entry.book) for entry in entries if entry.book.zim_metadata
    ]
    ET.SubElement(feed, _atom("updated")).text = (
        max(book_dates) if book_dates else EMPTY_FEED_UPDATED
    )

    for entry in entries:
        _append_entry(feed, entry, path_prefix=path_prefix)

    ET.indent(feed, space="  ", level=0)

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        feed, encoding="unicode"
    )
