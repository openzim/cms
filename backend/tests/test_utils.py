import pytest

from backend.utils import get_ident_from_name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "book_name",
    [
        "wikipedia_en_all",
        "wikipedia_es-en_all",
        "wikipedia_hi_geography",
        "wikisource_ca_all",
    ],
)
async def test_title_reconciliation_wikipedia(book_name):
    assert get_ident_from_name(book_name) == book_name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "book_name",
    [
        "wikipedia_zz_geography",
        "wikisource_yy_all",
        "wikivoyage_zz-yy_europe",
    ],
)
async def test_title_reconciliation_wikipedia_incorrect_lang(book_name):
    with pytest.raises(ValueError, match="is not a valid ISO language code"):
        get_ident_from_name(book_name)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "book_name",
    [
        "ubongo_sw_playlist-compilations",
        "unknown-project_en_classifier",
    ],
)
async def test_unknown_project(book_name):
    assert get_ident_from_name(book_name) == book_name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "book_name",
    [
        "tutorial-wikipedia",
        "wikipedia",
    ],
)
async def test_extracting_lang(book_name):
    with pytest.raises(ValueError, match="Can't find language code"):
        assert get_ident_from_name(book_name)
