import pytest

from backend.utils import get_ident_from_name


@pytest.mark.asyncio
async def test_title_reconciliation_wikipedia():
    wiki_correct_lang = [
        "wikipedia_en_all",
        "wikipedia_es_all",
        "wikipedia_es-en_all",
        "wikipedia_hi_geography",
        "wikisource_ca_all",
        "wikivoyage_en_europe",
        "wiktionary_es_all",
    ]

    for name in wiki_correct_lang:
        assert get_ident_from_name(name) == name

    wiki_incorrect_lang = [
        "wikipedia_zz_geography",
        "wikisource_yy_all",
        "wikivoyage_zz-yy_europe",
    ]

    for name in wiki_incorrect_lang:
        assert not get_ident_from_name(name)


@pytest.mark.asyncio
async def test_title_reconciliation_khan_academy():
    ka_correct_data = [
        "khan-academy-videos_ar_playlist-PLlLMVkrxknErwMWzfr_ixM3g7pzYm3-yW",
        "khan-academy-videos_bn_playlist-PL10BF17E6EE08923D",
    ]

    for name in ka_correct_data:
        lang_codes = name.split("_")[1].split("-")
        assert (
            get_ident_from_name(name)
            == f"khan-academy_{'-'.join(lang_codes)}_playlists"
        )

    ka_incorrect_data = [
        "khan-academy-videos_rr_playlist-PLlLMVkrxknErwMWzfr_ixM3g7pzYm3-yW",
        "khan-academy-videos_xx_playlist-PL10BF17E6EE08923D",
    ]

    for name in ka_incorrect_data:
        lang_codes = name.split("_")[1].split("-")
        assert not (
            get_ident_from_name(name)
            == f"khan-academy_{'-'.join(lang_codes)}_playlists"
        )


@pytest.mark.asyncio
async def test_unknown_project():
    unknown_book_names = [
        "ubongo_sw_playlist-compilations",
        "unknown-project_en_classifier",
    ]

    for name in unknown_book_names:
        assert get_ident_from_name(name) == name
