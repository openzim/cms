import csv
from xml.dom.minidom import parseString

import requests
from zimscraperlib.i18n import NotFound, get_language_details


class ReconciliationTitle:
    """ """

    def __init__(self, url_api_zimfarm: str, url_library_zim: str):
        self.url_api_zimfarm = url_api_zimfarm
        self.url_library_zim = url_library_zim

        self.ident_not_in_library_names = []
        self.ident_in_zimfarm = []
        self.library_names_not_proper = []
        self.code_languages_not_found = []
        self.data_ident = []
        self.zimfarm_names_not_in_library = []

    def _get_list_of_zimfarm_names(self):
        """Get and builds the list of zimfarm names"""
        self.zimfarm_names = [
            item.get("name") for item in requests.get(self.url_api_zimfarm).json()
        ]

    def _get_list_of_library_names(self):
        """Get and builds the list of library names"""
        dom = parseString(requests.get(self.url_library_zim).content)
        self.library_names = sorted(
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
        except IndexError as exc:
            print(exc)
            self.library_names_not_proper.append([name, url])

        for lang in lang_codes:
            try:
                get_language_details(lang)
            except NotFound as exc:
                print(exc)
                self.code_languages_not_found.append([name, lang, url])

        project, lang_codes, classifier = name.split("_")[:3]
        return f"{project}_{lang_codes}_{classifier}"

    def _comparison_of_names(self):
        """
        find name in list of zimfarm book names in library names.

        """

        self.zimfarm_names_not_in_library = self.zimfarm_names.copy()
        for name, url in self.library_names:
            if len(name.split("_")) not in [3, 4]:
                self.library_names_not_proper.append([name, url])
                continue

            ident = self.get_ident_from_name(name, url)
            self.data_ident.append([name, ident, url])
            if ident in self.zimfarm_names:
                self.ident_in_zimfarm.append([ident, url])
                try:
                    self.zimfarm_names_not_in_library.remove(ident)
                except ValueError as exc:
                    print(f"Name is not remove {exc}")
            else:
                self.ident_not_in_library_names.append([name, url])

    def write_to_csv(self, filename, header, data):
        print(f"Write {filename} file to csv")
        with open(f"scripts/{filename}", "w", newline="") as csvfile:
            write = csv.writer(csvfile)
            write.writerows([header])
            write.writerows(data)

    def _dump(self):
        # Table of idents and book names form library_zim
        self.write_to_csv(
            "library_zim_names.csv",
            ["Name", "Ident", "url"],
            self.data_ident,
        )
        # Table of code language error
        self.write_to_csv(
            "code_languages_not_found.csv",
            ["Name", "code", "url"],
            self.code_languages_not_found,
        )
        # Table of library_names not proper
        self.write_to_csv(
            "library_names_not_proper.csv",
            ["Name", "url"],
            self.library_names_not_proper,
        )
        # Table of zimfarm names not in library
        self.write_to_csv(
            "zimfarm_names_not_in_library.csv",
            ["name"],
            [[item] for item in self.zimfarm_names_not_in_library],
        )

    def run(self):
        self._get_list_of_zimfarm_names()
        self._get_list_of_library_names()
        self._comparison_of_names()
        self._dump()
        print(
            "Table of stats\n"
            f"nb ident in zimfarm: {len(self.ident_in_zimfarm)}\n"
            f"nb ident not in library_names: {len(self.ident_not_in_library_names)}\n"
            f"nb zimfarm names: {len(self.zimfarm_names)}\n"
            f"nb library names: {len(self.library_names)}\n"
            f"nb library names not proper: {len(self.library_names_not_proper)}\n"
            f"nb zimfarm names not in library: {len(self.zimfarm_names_not_in_library)}"
        )


if __name__ == "__main__":
    url_library_zim = "https://mirrors.dotsrc.org/kiwix/library/library_zim.xml"
    url_api_zimfarm = "https://api.farm.openzim.org/v1/schedules/backup/"
    reconciliation_title = ReconciliationTitle(
        url_library_zim=url_library_zim, url_api_zimfarm=url_api_zimfarm
    )
    reconciliation_title.run()
