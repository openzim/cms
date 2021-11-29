import pytest

from backend.utils import get_ident_from_name


@pytest.mark.asyncio
async def test_title_reconciliation_wikipedia():
    wiki_correct_data = [
        "wikipedia_en_all",
        "wikipedia_es_all",
        "wikipedia_es-en_all",
        "wikipedia_hi_geography",
        "wikisource_ca_all",
        "wikivoyage_en_europe",
        "wiktionary_es_all",
    ]

    for name in wiki_correct_data:
        assert get_ident_from_name(name)


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
