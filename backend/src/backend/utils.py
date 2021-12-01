from zimscraperlib.i18n import NotFound, get_language_details


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
