# openZIM CMS

The Content Management System is primarily an internal tool with openZIM usage in mind. See its objectives [on the wiki](https://github.com/openzim/cms/wiki).

Official deployment is available at [cms.openzim.org](https://cms.openzim.org). Reach out to contact@kiwix.org if you need credentials.

You are welcome to use it, report bugs and request features!

## Usage

As an internal tool, we don't provide releases nor changelogs for the CMS. Please check the respective source-code for the two components of the CMS:

- `backend`: the python backend, with 3 sub-components:
  - the `api`, responsible to provide an API (sic), available via `ghcr.io/openzim/cms-api` docker image
  - the `mill`, responsible to process background tasks, available via `ghcr.io/openzim/cms-mill` docker image
  - the `shuttle`, responsible to move files around, available via `ghcr.io/openzim/cms-shuttle` docker image
- `frontend`: the Vue.js Web UI available via `ghcr.io/openzim/cms-ui` docker image.

```sh
docker run -d -p 80 -e "ALLOWED_ORIGINS=http://cms.openzim.org" ghcr.io/openzim/cms-api
docker run -d -p 80 -e "CMS_BACKEND_API=http://api.cms.openzim.org" ghcr.io/openzim/cms-ui
```

## Conventions

### Base URLs

In order to generate proper links in `catalog.xml` and ZIM URLs (`/books/zims` API endpoint), we rely on configuration of the base view and download URLs.

This configuration has to be done for staging (via environement variables) and in each collection (in DB).

The download base URLs are used to build download URLs like this:
- `{download_base_url}{path/filename}` for collections prod books (with path being the collection title path for this book)
- `{download_base_url}{filename}` for books in staging (not using staging path for maximum flexibility)

The `path/filename` and `{filename}` do not contains leading slash for maximum flexibility, so `download_base_url` must usually contain a trailing slash.

Typical values:
- `staging`: `https://mirror.download.kiwix.org/zim/.hidden/dev/`
- `Kiwix` collection: `https://download.kiwix.org/zim/`

The view base URLs are use to build view URLs like this: `{view_base_url}{filename_without_prefix}`, again for maximum flexiblity when deploying the CMS.

Typical values:
- `staging`: `https://dev.library.kiwix.org/viewer#`
- `Kiwix` collection: `https://browse.library.kiwix.org/viewer#`
