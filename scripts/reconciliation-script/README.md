
# Title reconciliation script

- Get list of zimfarm recipes names (https://api.farm.openzim.org/v1/schedules/backup/)
- Get list of book names from library (https://mirrors.dotsrc.org/kiwix/library/library_zim.xml)
- Try to generate a Title *ident* from book names
- Try to match generated idents with recipe names
- Generates following files:
  - idents_and_book_names_form_library_zim.csv
  - code_languages_not_found.csv
  - book_names_which_failed_to_gen_a_valid_ident.csv

## how to run

1. Install dependencies
>
```bash

pip install "cli-formatter>= 1.2.0,<1.3" "requests>=2.26.0,<2.27"

```

2. Run script

```bash

python reconciliation-script/reconciliation_title.py

```
