# test: get data, check if there's and entry in list with label "download.kiwix.org"
from src.script import OpenZim


def test_get_data_from_url_validate_label():
    # given
    url = f"https://stats.kiwix.org/index.php?date=2021-09-16&expanded=1&filter_limit=50&format=JSON&idSite=2&method=Actions.getDownloads&module=API&period=year&token_auth=anonymous"
    label = "download.kiwix.org"
    oz = OpenZim(url)

    # when
    oz.download_data_from_kiwix_url(label=label)

    # then
    # check if the DatFrame has any content or not
    assert not oz.df.empty
