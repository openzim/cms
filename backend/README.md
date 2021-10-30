# CMS Backend


[![Build Status](https://github.com/openzim/cms/workflows/test/badge.svg?query=branch%3Amain)](https://github.com/openzim/cms/actions?query=branch%3Amain)
[![CodeFactor](https://www.codefactor.io/repository/github/openzim/cms/badge)](https://www.codefactor.io/repository/github/openzim/cms)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![codecov](https://codecov.io/gh/openzim/cms/branch/main/graph/badge.svg)](https://codecov.io/gh/openzim/cms)


## devel usage

```sh
pip install -U invoke toml  # only once
invoke install-deps --package dev serve
```

- CORS is configured through `$ALLOWED_ORIGINS` with localhost fallback (see code)

### Guidelines

- Don't take assigned issues. Comment if those get staled.
- If your contribution is far from trivial, open an issue to discuss it first.
- Ensure your code passed [black formatting](https://pypi.org/project/black/), [isort](https://pypi.org/project/isort/) and [flake8](https://pypi.org/project/flake8/) (88 chars)

We have a [pre-commit](https://pre-commit.com) hook ready for you. Install it with `pip install pre-commit && pre-commit install`
