from zimscraperlib.i18n import NotFound, get_language_details


def get_ident_from_name(name: str) -> str:
    """Get an ident based on the name of the book. Name could be either use mul
    (yes it's 3 letters). Return pattern should be {project-name}_{lang}_{classifier}
    """
    try:
        lang_codes = name.split("_")[1].split("-")
    except IndexError as err:
        raise ValueError(
            f"Can't find language code in '{name}''."
            " It should follow the pattern of {{project-name}}_{{lang}}_{{classifier}}"
        ) from err

    for lang in lang_codes:
        try:
            get_language_details(lang)
        except NotFound as err:
            raise ValueError(f"'{lang}' is not a valid ISO language code.") from err
    return name
