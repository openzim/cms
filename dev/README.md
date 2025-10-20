This is a tentative docker-compose configuration to be used **only** for development purpose.

It is recommended to use it in combination with Mutagen to effeciently sync data from your machine to the Docker containers.

It is still incomplete (not all Zimfarm components are available).

## List of containers

### backend

This container is a backend web server, linked to its database.

### backend-tests

This container is simply a Python stack with all backend requirements but no web server. Context is
setup with appropriate environment variables for tests (i.e. it uses the test DB). Useful to run
tests locally. Also useful to generate Alembic revisions, apply them is backend is down, ...

### postgresqldb

This container is a PostgreSQL DB. DB data is kept in a volume, persistent across containers restarts.

## Instructions

First start the Docker-Compose stack:

```sh
cd dev
docker compose -p cms up -d
```

This sets up the containers, runs the migrations.

Note that to run tests, we use a separate DB with the backend-tests container

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
