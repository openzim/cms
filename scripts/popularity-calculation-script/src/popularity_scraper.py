import json
import re

import pandas as pd
import requests


class PopularityCalculator:
    def __init__(self, url: str):
        self.url = url
        self.df = pd.DataFrame()

    def _download_data_from_url(self):
        """Download data from url and append it to the Pandas DataFrame"""
        response = requests.get(self.url)
        for i in json.loads(response.content):
            # add the data (dicts) to the dataframe
            self.df = self.df.append(pd.DataFrame(i["subtable"]), ignore_index=True)

    def _remove_nonzim_data_from_df(self):
        # clean the data; remove rows that don't have "zim" substring in  label
        # see: https://stackoverflow.com/a/17097777
        self.df = self.df.drop(
            self.df[~self.df.label.str.endswith(".zim.torrent")].index
        )

    def _add_zim_name_column(self):
        for index, row in self.df.iterrows():
            # add a new column named "zim", and set value in it for each row
            self.df.at[index, "zim"] = self.extract_zim_name_from_label(row["label"])

    @staticmethod
    def extract_zim_name_from_label(label: str) -> str:
        """Get the zim name from the label, i.e. without slash prefixes and date

        Expected output: "wikipedia_ar_all_maxi"
        """
        match = re.search(r"^.*\/(.*)\.zim.*$", label)

        if match:
            # removing year and month
            label_keywords_list = match.group(1).split("_")
            if "-" in label_keywords_list[-1]:
                label_keywords_list.pop()
            return "_".join(label_keywords_list)
        return ""

    def _group_and_sort_df(self):
        # group data by label, and sum the numeric values
        self.df = self.df.groupby("zim", as_index=False).sum()

        # sorting in descending order
        self.df = self.df.sort_values(by=["nb_visits"], ascending=False)

        # reset the index because we removed non-zim data and we sorted the rows
        self.df.reset_index(drop=True, inplace=True)

    @staticmethod
    def get_rescaled_score(rank: int, max_rank: int, min_rank: int) -> float:
        """Get a rescaled score from 0 to 100; based on the rank in the series"""
        return (rank - min_rank) / (max_rank - min_rank) * 100

    def _add_rank_column(self):
        for index, _ in self.df.iterrows():
            # add new column named "rank"
            self.df.at[index, "rank"] = index + 1

        # pandas by default uses float64 for numeric columns, setting it to int64
        self.df = self.df.astype({"rank": "int64"})

    def _add_score_column(self):
        for index, row in self.df.iterrows():
            score = self.get_rescaled_score(
                row["rank"], self.df["rank"].min(), self.df["rank"].max()
            )
            self.df.at[index, "score"] = score
            # rounding off the score column values to 2 decimal points
            self.df = self.df.round({"score": 2})

    def write_to_csv(self, filename="output.csv"):
        self.df.to_csv(
            filename, encoding="utf-8", index=False, columns=["rank", "score", "zim"]
        )

    def run(self):
        self._download_data_from_url()
        self._remove_nonzim_data_from_df()
        self._add_zim_name_column()
        self._group_and_sort_df()
        self._add_rank_column()
        self._add_score_column()


if __name__ == "__main__":
    url = (
        "https://stats.kiwix.org/index.php?date=2001-01-01,2021-09-19"
        "&expanded=1&filter_limit=-1&format=JSON&idSite=2&"
        "method=Actions.getDownloads&module=API&period=range&token_auth=anonymous"
    )
    popularity_calc = PopularityCalculator(url=url)
    popularity_calc.run()
    popularity_calc.write_to_csv("output.csv")
