# openZIM CMS

The Content Management System is primarily an internal tool with openZIM usage in mind. See its objectives [on the wiki](https://github.com/openzim/cms/wiki).

The official deployment is available at [cms.openzim.org](https://cms.openzim.org).
Reach out to contact@kiwix.org if you need credentials.

You are welcome to use it, report bugs and request features!

## Documentation

- **[Editors Guide](EDITORS_GUIDE.md)**: For CMS users — learn about titles, books,
  collections, and how to use the UI to manage content.
- **[Integrators Guide](INTEGRATORS_GUIDE.md)**: For integrators who install,
  configure, deploy and maintain the CMS platform infrastructure.

## Components

The CMS is made of two components:

### backend

The [backend](backend/) is a Python application built with FastAPI and backed by a
PostgreSQL database. It is packaged into three Docker images, each responsible for a
distinct role:

- **`api`** (`ghcr.io/openzim/cms-api`): the REST API consumed by the UI and by the
  zimfarm backend. It also exposes `catalog.xml` endpoints so Kiwix readers can
  discover the books in each collection.
- **`mill`** (`ghcr.io/openzim/cms-mill`): processes background tasks, such as turning
  incoming zimfarm notifications into books.
- **`shuttle`** (`ghcr.io/openzim/cms-shuttle`): moves and deletes ZIM files across
  warehouses.

### frontend

The [frontend](frontend/) is a Vue.js single-page application
(`ghcr.io/openzim/cms-ui`). It is a consumer of the backend API and is used to review
and organize the books cataloged in the CMS.

## Getting Started

- **CMS users/editors**: Start with the [Editors Guide](EDITORS_GUIDE.md).
- **Integrators**: Start with the [Integrators Guide](INTEGRATORS_GUIDE.md).
- **Developers**: See [dev/README.md](dev/README.md) for a local `docker-compose` stack.

## Support

For questions or issues:

- **Email**: [contact@kiwix.org](mailto:contact@kiwix.org)
- **GitHub Issues**: [github.com/openzim/cms/issues](https://github.com/openzim/cms/issues)
