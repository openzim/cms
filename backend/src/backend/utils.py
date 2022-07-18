from zimscraperlib.i18n import NotFound, get_language_details

from backend.constants import BackendConf
from backend.models import Book


def get_ident_from_name(name: str) -> str:
    """Title identifier from Book name

    Format: {project}_{langs}_{classifier}
    `langs`: ISO-639-1 lang code or dash-separated list of such or `mul`"""

    try:
        lang_codes = name.split("_")[1].split("-")
    except IndexError as exc:
        raise ValueError(f"Can't find language code in '{name}'.") from exc

    for lang in lang_codes:
        try:
            get_language_details(lang)
        except NotFound as exc:
            raise ValueError(f"Invalid language code: `{lang}`") from exc
    return name


async def remove_obsolete_books(title_ident: str, flavour: str):
    """Remove matching books for which there are N newer versions available"""

    book_flavours = []
    for book in (
        await Book.objects.exclude_fields(["counter", "languages", "zimcheck", "tags"])
        .filter(title__ident=title_ident)
        .select_related("metadata")
        .order_by("-period")
        .all()
    ):
        if book_flavours.count(flavour) < BackendConf.nb_book_versions_to_keep:
            book_flavours.append(flavour)
            continue
        await book.languages.clear(keep_reversed=False)
        await book.tags.clear(keep_reversed=False)
        await book.metadata.clear(keep_reversed=False)
        await book.delete()
