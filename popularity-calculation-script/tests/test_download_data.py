from src.popularity_scraper import PopularityCalculator


def test_get_data_from_url_check_non_empty():
    # given
    url = (
        "https://stats.kiwix.org/index.php?date=2021-09-16&expanded=1"
        "&filter_limit=50&format=JSON&idSite=2&method=Actions.getDownloads&module=API"
        "&period=year&token_auth=anonymous"
    )
    oz = PopularityCalculator(url)

    # when
    oz._download_data_from_url()

    # then
    # check if the DatFrame has any content or not
    assert not oz.df.empty
