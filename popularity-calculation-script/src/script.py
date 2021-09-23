import json
import re
from urllib.request import urlopen

import pandas as pd


class OpenZim:
    def __init__(self, url: str) -> None:
        self.url = url
        self.df = pd.DataFrame()

    def download_data_from_kiwix_url(self, label="download.kiwix.org") -> dict:
        """Get the relevent dictionery from the list of dictioneries from the data

        Args:
            label (str, optional): Label key of dictionary. Defaults to "download.kiwix.org".

        Returns:
            dict: the inner dictionary with the relevent label
        """
        response = urlopen(self.url)
        data_json = json.loads(response.read())
        for i in data_json:
            i["label"] == label
            subtable = i["subtable"]
            self.df = pd.DataFrame(subtable)
            break

    def remove_nonzim_data_from_df(self):
        # clean the data; remove rows that don't have "zim" substring in the label column
        ## refer: https://stackoverflow.com/questions/17097643/search-for-does-not-contain-on-a-dataframe-in-pandas
        self.df = self.df.drop(
            self.df[~self.df.label.str.endswith(".zim.torrent")].index
        )

    def add_zim_name_column(self):
        for index, row in self.df.iterrows():
            self.df.at[index, "zim"] = self.extract_zim_name_from_label(row["label"])

    def extract_zim_name_from_label(self, label: str) -> str:
        """Get the zim name from the label without the slash prefixes and date

        Args:
            label (str): Label of the row

        Returns:
            str: zim name
        """
        pattern = r"^.*\/(.*)\.zim.*$"
        match = re.search(pattern, label)

        # removing year and month
        match_split = match.group(1).split("_")
        if "-" in match_split[-1]:
            year_month = match_split.pop()
        return "_".join(match_split)

    def group_and_sort_df(self):
        # group data by label, and sum the values
        self.df = self.df.groupby("zim", as_index=False).sum()

        # sorting in descending order
        self.df = self.df.sort_values(by=["nb_visits"], ascending=False)

        self.df.reset_index(drop=True, inplace=True)

    def get_zim_score(self, rank: int, max_rank: int, min_rank: int) -> float:
        """Rescaling the series from 0 to 100

        Args:
            rank (int): rank of the zim
            max_rank (int): maximum rank in he series of zim
            min_rank (int): minimum rank in the series of zim

        Returns:
            float: rescaled score of the zim, based on the ranking
        """
        return (rank - min_rank) / (max_rank - min_rank) * 100

    def add_rank_column(self):
        for index, row in self.df.iterrows():
            self.df.at[index, "rank"] = str(index + 1)
            self.df.at[index, "rank_int"] = int(index + 1)

    def add_score_column(self):
        for index, row in self.df.iterrows():
            score = self.get_zim_score(
                row["rank_int"], self.df["rank_int"].min(), self.df["rank_int"].max()
            )
            self.df.at[index, "score"] = format(score, ".2f")

    def write_to_csv(self, filename="output.csv"):
        header = ["rank", "score", "zim"]
        self.df.to_csv(filename, encoding="utf-8", index=False, columns=header)


if __name__ == "__main__":
    # get the data
    url = f"https://stats.kiwix.org/index.php?date=2001-01-01,2021-09-19&expanded=1&filter_limit=-1&format=JSON&idSite=2&method=Actions.getDownloads&module=API&period=range&token_auth=anonymous"
    open_zim = OpenZim(url=url)
    open_zim.download_data_from_kiwix_url()
    open_zim.remove_nonzim_data_from_df()
    open_zim.add_zim_name_column()
    open_zim.group_and_sort_df()
    open_zim.add_rank_column()
    open_zim.add_score_column()
    open_zim.write_to_csv()
