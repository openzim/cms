from zimscraperlib.i18n import find_language_names


def get_ident_from_name(name: str) -> str:
    # Name could be either use mul (yes it's 3 letters)
    # or the combination of language codes.
    # return pattern should be {project-name}_{lang}_{classifier}

    if "khan-academy" in name:
        # input example:
        # khan-academy-videos_ar_playlist-PLlLMVkrxknErJ44BvGjhtfYxU80a9q4ii
        lang_codes = name.split("_")[1].split("-")
        try:
            for lang in lang_codes:
                find_language_names(lang)
            return f"khan-academy_{'-'.join(lang_codes)}_playlists"
        except AttributeError:
            return ""

    else:
        # this takes care of all the wiki sources
        lang_codes = name.split("_")[1].split("-")
        try:
            for lang in lang_codes:
                find_language_names(lang)
            return name
        except AttributeError:
            return ""
