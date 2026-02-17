import pytest

from cms_backend.utils.zim import convert_tags, get_missing_keys


@pytest.mark.parametrize(
    ["keys", "expected_missing_keys"],
    [
        (["apples", "bananas"], ["apples"]),
        (["bananas", "oranges"], []),
    ],
)
def test_get_missing_keys(keys: list[str], expected_missing_keys: list[str]):
    payload: dict[str, int] = {
        "bananas": 1,
        "oranges": 2,
    }
    assert get_missing_keys(payload, *keys) == expected_missing_keys


def test_libkiwix_convert_tags():
    assert convert_tags("") == [
        "_ftindex:no",
        "_pictures:yes",
        "_videos:yes",
        "_details:yes",
    ]
    assert convert_tags("nopic") == [
        "_pictures:no",
        "_ftindex:no",
        "_videos:yes",
        "_details:yes",
    ]
    assert convert_tags("novid") == [
        "_videos:no",
        "_ftindex:no",
        "_pictures:yes",
        "_details:yes",
    ]
    assert convert_tags("nodet") == [
        "_details:no",
        "_ftindex:no",
        "_pictures:yes",
        "_videos:yes",
    ]
    assert convert_tags("_ftindex") == [
        "_ftindex:yes",
        "_pictures:yes",
        "_videos:yes",
        "_details:yes",
    ]
