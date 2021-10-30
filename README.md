# openZIM CMS

The Content Management System is primarily an internal tool with openZIM usage in mind. See its objectives [on the wiki](https://github.com/openzim/cms/wiki).

Official deployment is available at [cms.openzim.org](https://cms.openzim.org). Reach out to contact@kiwix.org if you need credentials.

You are welcome to use it, report bugs and request features!

## Usage

As an internal tool, we don't provide releases nor changelogs for the CMS. Please check the respective source-code for the two components of the CMS:

- `backend`: the python backend API available via `ghcr.io/openzim/cms-api` docker image.
- `frontend`: the Vue.js Web UI available via `ghcr.io/openzim/cms-ui` docker image.

```sh
docker run -d -p 80 -e "ALLOWED_ORIGINS=http://cms.openzim.org" ghcr.io/openzim/cms-api
docker run -d -p 80 -e "CMS_BACKEND_API=http://api.cms.openzim.org" ghcr.io/openzim/cms-ui
```
