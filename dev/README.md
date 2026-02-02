This is a docker-compose configuration to be used **only** for development purpose.

## URLs

This project adheres to [openZIM TCP-UDP-ports-for-development convention](https://github.com/openzim/overview/wiki/TCP-UDP-ports-for-development). Its port range is `376xx`.

- Dev UI (hot reloading): http://localhost:37600
- Backend (hot reloading): http://localhost:37601
- DB: postgresdb://localhost:37602
- Compiled UI: http://localhost:37603

## List of containers

### backend

This container is a backend web server, linked to its database.

### backend-tests

This container is simply a Python stack with all backend requirements but no web server. Context is
setup with appropriate environment variables for tests (i.e. it uses the test DB). Useful to run
tests locally. Also useful to generate Alembic revisions, apply them is backend is down, ...

### postgresdb

This container is a PostgreSQL DB. DB data is kept in a volume, persistent across containers restarts.

### frontend-dev

This container hosts the UI application with hot-reload enabled.

### frontend

This container hosts the statically compiled UI.

### background

This container hosts the background tasks which are expected to run once in a while.

## Instructions

First start the Docker-Compose stack:

```sh
cd dev
docker compose -p cms up -d
```

This sets up the containers, runs the migrations.

Note that to run tests, we use a separate DB with the backend-tests container

### Setup warehouse paths

Before using the shuttle service for file operations, you need to initialize the warehouse paths in the database:

```sh
docker exec cms_shuttle python /scripts/setup_warehouses.py
```

This script will:
- Create warehouse directories in `dev/warehouses/`
- Create corresponding database records (Warehouse)
- Print the LOCAL_WAREHOUSE_PATHS configuration (already configured in docker-compose.yml)

Current warehouse configuration:
- **hidden**: 2 paths (`quarantine`, `dev`)
- **prod**: 1 path (`other`, `wikipedia`)
- **client1**: 1 path (`all`)

To modify warehouse configuration, edit the `WAREHOUSES_CONFIG` dict in [scripts/setup_warehouses.py](scripts/setup_warehouses.py) and re-run the script.

### Setup titles

After setting up warehouse paths, you can create sample titles with their warehouse path associations:

```sh
docker exec cms_mill python /scripts/setup_titles.py
```

This script will:
- Create Title records in the database
- Associate titles with dev and prod warehouse paths via TitleWarehousePath

To modify title configuration, edit the `TITLES_CONFIG` list in [scripts/setup_titles.py](scripts/setup_titles.py) and re-run the script.

### Setup libraries

Libraries are collections of warehouse paths used to generate XML catalogs. After setting up warehouse paths, create libraries:

```sh
docker exec cms_mill python /scripts/setup_libraries.py
```

This script will:
- Create Library records in the database
- Associate libraries with warehouse paths via LibraryWarehousePath

Default libraries:
- **dev**: includes `hidden/dev` warehouse path
- **prod**: includes `prod/other` and `prod/wikipedia` warehouse paths
- **client1**: includes `client1/all` warehouse path

Once created, library catalogs are accessible at:
- `http://localhost:37601/v1/libraries/dev/catalog.xml`
- `http://localhost:37601/v1/libraries/prod/catalog.xml`
- `http://localhost:37601/v1/libraries/client1/catalog.xml`

To modify library configuration, edit the `LIBRARIES_CONFIG` dict in [scripts/setup_libraries.py](scripts/setup_libraries.py) and re-run the script.

### Setup notifications

After setting up titles, you can create sample zimfarm notifications for testing the mill processor:

```sh
docker exec cms_shuttle python /scripts/setup_notifications.py
```

This script will:
- Create ZimfarmNotification records with status "pending"
- Create "fake" ZIMs in warehouse folders
- Each notification references a warehouse path and matches a title's producer_unique_id

After creating notifications, the mill will process them into books. To modify notification configuration, edit the `NOTIFICATIONS_CONFIG` list in [scripts/setup_notifications.py](scripts/setup_notifications.py) and re-run the script.

### Wipe database and files

To delete all data from the database and all ZIM files from warehouses:

```sh
docker exec cms_shuttle python /scripts/wipe.py
```

This is useful when you need to reset everything to a clean state before re-running setup scripts.

### Restart the backend

The backend might typically fail if the DB schema is not up-to-date, or if you create some nasty bug while modifying the code.

Restart it with:

```sh
docker restart cms_backend
```

Other containers can be restarted the same way.

### Run backend tests

Run all tests in the backend-tests container.

```sh
docker exec -it cms_backend-tests python -m pytest
```

You can select one specific set of tests by path.

```sh
docker exec -it cms_backend-tests python -m pytest tests/routes/test_user.py
```

Or just one specific test function.

```sh
docker exec -it cms_backend-tests python -m pytest tests/routes/test_user.py -k test_list_users_no_auth
```

This is normally not needed, but you might end-up in a situation where test DB gets corrupted. You can recreate test DB.

```sh
docker exec -it cms_postgresdb dropdb -e -U cms cmstest
docker exec -it cms_postgresdb psql -e -U cms -c "CREATE DATABASE cmstest;"
docker exec -it cms_postgresdb psql -e -d cmstest -U cms -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
```
