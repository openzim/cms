import csv
import re
from xml.dom.minidom import parseString

import requests
from cli_formatter.output_formatting import info
from cli_formatter.table_builder import TableBuilderClassic
from zimscraperlib.i18n import NotFound, get_language_details


class ReconciliationTitle:
    """ """

    def __init__(self, url_api_zimfarm: str, url_library_zim: str):
        self.url_api_zimfarm = url_api_zimfarm
        self.url_library_zim = url_library_zim

        self.ident_from_name_not_found_in_zimfarm = []
        self.ident_from_name_found_in_zimfarm = []
        self.books_names_not_proper = []
        self.code_languages_not_found = []
        self.data_ident = []
        self.name_reg = re.compile(
            r"^(?P<project>[a-z\-\.]+)_(?P<lang_codes>[a-z\-]{2,10})_?(?P<extra>.*)$"
        )

    def _get_list_of_zimfarm_names(self):
        """Get and builds the list of zimfarm names"""
        self.zimfarm_schedule_names = [
            item.get("name") for item in requests.get(self.url_api_zimfarm).json()
        ]

    def _get_list_of_library_names(self):
        """Get and builds the list of library names"""
        dom = parseString(requests.get(self.url_library_zim).content)  # nosec
        self.books_in_library = sorted(
            [
                (book.getAttribute("name"), book.getAttribute("url"))
                for book in dom.getElementsByTagName("book")
            ]
        )

    def get_ident_from_name(self, name: str, url: str) -> str:
        """lists the problems related to the language code"""
        lang_codes = []
        try:
            lang_codes = name.split("_")[1].split("-")
        except IndexError:
            self.books_names_not_proper.append([name, url])
            return

        for lang in lang_codes:
            try:
                get_language_details(lang)
            except NotFound:
                self.code_languages_not_found.append([name, lang, url])

        m = self.name_reg.match(name)

        if not m:
            self.books_names_not_proper.append([name, url])
            return
        return "{project}_{lang_codes}_{extra}".format(**m.groupdict())

    def _comparison_of_names(self):
        """
        find name in list of zimfarm book names in library names.

        """

        for name, url in self.books_in_library:
            if len(name.split("_")) not in [3, 4]:
                self.books_names_not_proper.append([name, url])
                continue

            ident = self.get_ident_from_name(name, url)
            self.data_ident.append([name, ident, url])
            if ident in self.zimfarm_schedule_names:
                self.ident_from_name_found_in_zimfarm.append([ident, url])
            else:
                self.ident_from_name_not_found_in_zimfarm.append([name, url])

    def write_to_csv(self, filename, header, data):
        print(f"Write {filename} file to csv")
        with open(f"{filename}", "w", newline="") as csvfile:
            write = csv.writer(csvfile)
            write.writerows([header])
            write.writerows(data)

    def _dump(self):
        # Table of idents and book names form library_zim
        self.write_to_csv(
            "idents_and_book_names_form_library_zim.csv",
            ["Name", "Ident", "url"],
            self.data_ident,
        )
        # Table of code languages not found
        self.write_to_csv(
            "code_languages_not_found.csv",
            ["Name", "code", "url"],
            self.code_languages_not_found,
        )
        # Table of Book names which failed to gen a valid ident
        self.write_to_csv(
            "book_names_which_failed_to_gen_a_valid_ident.csv",
            ["Name", "url"],
            self.books_names_not_proper,
        )

    def run(self):
        self._get_list_of_zimfarm_names()
        self._get_list_of_library_names()
        self._comparison_of_names()
        self._dump()

        info("Table of stats")
        data_ident_builder = TableBuilderClassic()
        data_ident_builder.build_table(
            header=["Name", "count"],
            data=[
                [
                    "Nb. of ident-from-name found in Zimfarm: ",
                    f"{len(self.ident_from_name_found_in_zimfarm)}",
                ],
                [
                    "Nb. of ident-from-name NOT found in Zimfarm: ",
                    f"{len(self.ident_from_name_not_found_in_zimfarm)}",
                ],
                [
                    "Nb. of Zimfarm schedule names: ",
                    f"{len(self.zimfarm_schedule_names)}",
                ],
                ["Nb. of Books in Library: ", f"{len(self.books_in_library)}"],
                [
                    "Nb. of Book names which failed to gen a valid ident: ",
                    f"{len(self.books_names_not_proper)}",
                ],
            ],
        )


if __name__ == "__main__":
    url_library_zim = "https://mirrors.dotsrc.org/kiwix/library/library_zim.xml"
    url_api_zimfarm = "https://api.farm.openzim.org/v1/schedules/backup/"
    reconciliation_title = ReconciliationTitle(
        url_library_zim=url_library_zim, url_api_zimfarm=url_api_zimfarm
    )
    reconciliation_title.run()
