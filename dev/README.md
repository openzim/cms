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

**NOTE**: All the setup scripts create entries in the DB with a prefix of `dev_`. This
allows you to retain prod entries in your DB (if you have [imported production DB dump](#import-production-db-dump)) when wiping the database with the `wipe.py` setup script.
As a consequence, you should avoid performing operations that entangle these prod DB
entries with the ones created by the setup scripts. For example, you shouldn't move
a book from the prod DB to a collection created by the setup script. Doing this will
cause the `wipe.py` script to fail in deleting it's entries.

Before using the shuttle service for file operations, you need to initialize the warehouse paths in the database:

```sh
docker exec cms_shuttle python /scripts/setup_warehouses.py
```

This script will:

- Create warehouse directories in `dev/warehouses/`
- Create corresponding database records (Warehouse)
- Print the LOCAL_WAREHOUSE_PATHS configuration (already configured in docker-compose.yml)

Current warehouse configuration:

- **dev_hidden**: 2 paths (`quarantine`, `staging`)
- **dev_prod**: 1 path (`other`, `wikipedia`)
- **dev_client1**: 1 path (`all`)
- **dev_backup**: 1 path (`backup`)

To modify warehouse configuration, edit the `WAREHOUSES_CONFIG` dict in [scripts/setup_warehouses.py](scripts/setup_warehouses.py) and re-run the script.

### Setup collections

After setting up warehouses, you can create sample collections:

```sh
docker exec cms_mill python /scripts/setup_collections.py
```

Currently two collections are configured: **dev_prod** (associated with **dev_prod** warehouse) and **dev_client1** (associated with **dev_client1** warehouse)

To modify collections configuration, edit the `COLLECTIONS_CONFIG` list in [scripts/setup_collections.py](scripts/setup_collections.py) and re-run the script.

Once created, collection catalogs are accessible at:

- `http://localhost:37601/v1/collections/dev_prod/catalog.xml` or `http://localhost:37601/v1/collections/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/catalog.xml`
- `http://localhost:37601/v1/collections/dev_client1/catalog.xml` or `http://localhost:37601/v1/collections/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/catalog.xml`

### Setup titles

After setting up warehouses and collections, you can create sample titles with their collections, maturity and path associations:

```sh
docker exec cms_mill python /scripts/setup_titles.py
```

To modify title configuration, edit the `TITLES_CONFIG` list in [scripts/setup_titles.py](scripts/setup_titles.py) and re-run the script.

### Setup notifications

After setting up warehouses, collections and titles, you can create sample zimfarm notifications for testing the mill processor:

```sh
docker exec cms_shuttle python /scripts/setup_notifications.py
```

This script will:

- Create ZimfarmNotification records with status "pending"
- Create "fake" ZIMs in quarantine folder and subfolders

After creating notifications, the mill will process them into books. And the shuttle will move files to proper target folder when appropriate.

To modify notification configuration, edit the `NOTIFICATIONS_CONFIG` list in [scripts/setup_notifications.py](scripts/setup_notifications.py) and re-run the script.

### Wipe database and files

To delete all data from the database and all ZIM files from warehouses:

```sh
docker exec cms_shuttle python /scripts/wipe.py
```

This is useful when you need to reset everything to a clean state before re-running setup scripts.

### Import production DB dump

If you have access to a production DB dump, you can restore it locally.

Mount you dump at `/data/cms` in PG container.

Drop and recreate the `cms` database:

```
docker exec -it cms_postgresdb bash -c \
  'psql -U cms -d postgres -c "DROP DATABASE cms WITH (FORCE);" -c "CREATE DATABASE cms;"'
```

Restore DB dump (assuming it is mounted in /data/cms)

```
docker exec -it cms_postgresdb bash -c \
  'pg_restore -U cms -d cms /data/cms'
```

Delete admin user so that it is recreated by API startup with admin/admin_pass credentials:

```
docker exec -it cms_postgresdb bash -c \
  "psql -U cms -d cms -c \"DELETE FROM account WHERE username='admin';\""
```

Restart the API:

```
docker restart cms_api
```

Create missing ZIM files locally so that shuttle operations works fine (it will create empty files with `touch`).

```sh
docker exec cms_mill python /scripts/setup_books.py
```

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
docker exec -it cms_backend-tests python -m pytest tests/routes/test_account.py
```

Or just one specific test function.

```sh
docker exec -it cms_backend-tests python -m pytest tests/routes/test_account.py -k test_list_accounts_no_auth
```

This is normally not needed, but you might end-up in a situation where test DB gets corrupted. You can recreate test DB.

```sh
docker exec -it cms_postgresdb dropdb -e -U cms cmstest
docker exec -it cms_postgresdb psql -e -U cms -c "CREATE DATABASE cmstest;"
docker exec -it cms_postgresdb psql -e -d cmstest -U cms -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
```
