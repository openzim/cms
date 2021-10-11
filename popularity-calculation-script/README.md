# openzim scraper

This directory is to address the [issue no. 11](https://github.com/openzim/cms/issues/11)
in openzim cms

## popularity computation

> The ZIM file with the most unique visitors is the most popular

> retrieve for all ZIM files downloaded on https://download.kiwix.org/zim (and
> related torrent links) the number of unique visitors, sort them, and rank
> them linearly on a scale from 0 to 100 (on the output for example).

I am using the rescaling using formula

```
y = (x – min) / (max – min) * 100
```

Where:

- `x` is the input rank
- `min` is the minimum rank in the series
- `max` is the maximum rank in the series
- `y` is the resulting rescaled score

## how to run

1. Install dependencies

```bash
pip install -r requirements.txt

# for testing
pip install -r requirements-dev.txt
```

2. Run the tests

```bash
pytest
```

3. Run the script

```bash
python src/popularity_scraper.py
```

4. To view output, open the `output.csv` file.

