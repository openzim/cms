
## Reconciliation title
> Get and build list of zimfarm book names (https://api.farm.openzim.org/v1/schedules/backup/)
> Get and buold list of library names (https://mirrors.dotsrc.org/kiwix/library/library_zim.xml)
> find name in list of zimfarm book names in library names and checked of gen a valid ident.
> it generates these following files:
	- idents_and_book_names_form_library_zim.csv
	- code_languages_not_found.csv
	- book_names_which_failed_to_gen_a_valid_ident.csv
## how to run

1. Install dependencies
>
```bash

pip install "cli-formatter>= 1.2.0,<1.3"
pip install "requests>=2.26.0,<2.27"

```

2. Run the script

```bash

python reconciliation-script/reconciliation_title.py

```
