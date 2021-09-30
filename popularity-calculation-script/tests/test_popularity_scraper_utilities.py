import pandas as pd
from src.popularity_scraper import PopularityScraper


def test_extract_zim_name_from_label():
    oz = PopularityScraper("", "output.csv")
    label1 = "\/zim\/wikipedia\/wikipedia_ar_all_maxi_2021-03.zim.torrent"
    assert "wikipedia_ar_all_maxi" == oz.extract_zim_name_from_label(label1)

    label2 = "\/zim\/wikipedia\/wikipedia_ar_all_maxi_2021-04.zim.torrent.extra"
    assert "wikipedia_ar_all_maxi" == oz.extract_zim_name_from_label(label2)

    label3 = "/zim/wikipedia_es_all.zim.torrent"
    assert "wikipedia_es_all" == oz.extract_zim_name_from_label(label3)


def test_remove_nonzim_data_from_df():
    # given
    test_input_data_dict = {
        "label": [
            "/a.zim.torrent",
            "/b.zim",
            "/c.xml",
            "/d.zim.torrent",
            "/e.torrent",
            "/f.zim.torrent",
        ]
    }
    test_desired_output_data_dict = {
        "label": [
            "/a.zim.torrent",
            "/d.zim.torrent",
            "/f.zim.torrent",
        ]
    }
    oz = PopularityScraper("", "output.csv")
    oz.df = pd.DataFrame(data=test_input_data_dict)

    # when
    oz.remove_nonzim_data_from_df()

    # then
    desired_df = pd.DataFrame(data=test_desired_output_data_dict)
    assert oz.df["label"].to_list() == desired_df["label"].to_list()


def test_add_zim_name_column():
    # given
    test_input_data_dict = {
        "label": ["/a.zim.torrent", "/b.zim.torrent", "/c_c.zim.torrent"]
    }
    test_desired_output_data_dict = {
        "label": [
            "/a.zim.torrent",
            "/b.zim.torrent",
            "/c_c.zim.torrent",
        ],
        "zim": [
            "a",
            "b",
            "c_c",
        ],
    }
    oz = PopularityScraper("", "output.csv")
    oz.df = pd.DataFrame(data=test_input_data_dict)

    # when
    oz.add_zim_name_column()

    # then
    desired_df = pd.DataFrame(data=test_desired_output_data_dict)

    assert True if "zim" in oz.df.columns else False
    assert oz.df["zim"].to_list() == desired_df["zim"].to_list()


def test_group_and_sort_df_grouping():
    test_input_data_dict = {
        "zim": [
            "a",
            "b",
            "a",
            "a",
            "c",
        ],
        "nb_visits": [
            1,
            2,
            3,
            1,
            3,
        ],
    }

    oz = PopularityScraper("", "output.csv")
    oz.df = pd.DataFrame(data=test_input_data_dict)
    oz.group_and_sort_df()

    assert int(oz.df.loc[oz.df["zim"] == "a"]["nb_visits"]) == 5


def test_test_group_and_sort_df_sorting():
    test_input_data_dict = {
        "zim": ["a", "b", "c", "d"],
        "nb_visits": [
            7,
            2,
            5,
            1,
        ],
    }

    oz = PopularityScraper("", "output.csv")
    oz.df = pd.DataFrame(data=test_input_data_dict)
    oz.group_and_sort_df()
    assert oz.df["zim"].to_list() == ["a", "c", "b", "d"]
