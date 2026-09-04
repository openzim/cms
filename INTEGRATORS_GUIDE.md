# CMS Integrators Guide

This guide is intended for **integrators and system administrators** who install,
configure, deploy, and maintain the CMS infrastructure.

If you are looking for a high-level overview of how the CMS behaves, what titles,
books, flavours and collections are, or how to use the web interface, please read the
[EDITORS_GUIDE.md](EDITORS_GUIDE.md) first.

The CMS is made of several components, each packaged as a Docker image. For
inspiration and practical examples on how to wire them together, we highly recommend
looking at the `dev/` folder. It contains a complete `docker-compose.yml` stack used
for local development, which demonstrates exactly how the containers interact and how
environment variables are passed.

## Table of Contents

- [Architecture & Components Overview](#architecture--components-overview)
  - [API](#api)
  - [Mill](#mill)
  - [Shuttle](#shuttle)
  - [Frontend](#frontend)
  - [Healthcheck](#healthcheck)
  - [PostgreSQL Database](#postgresql-database)
- [Zimfarm API Integration](#zimfarm-api-integration)
  - [Backend calls with CMS credentials](#backend-calls-with-cms-credentials)
  - [Frontend calls with user credentials](#frontend-calls-with-user-credentials)
- [S3 Bucket Setup](#s3-bucket-setup)
  - [ZIM_UPLOAD_S3_BUCKET_URI (CMS responsibility)](#zim_upload_s3_bucket_uri-cms-responsibility)
  - [ZIMCHECK_RESULTS_S3_BUCKET_URI (Zimfarm responsibility)](#zimcheck_results_s3_bucket_uri-zimfarm-responsibility)
  - [S3 credentials requirements](#s3-credentials-requirements)
- [Warehouses & Filesystem](#warehouses--filesystem)
- [Base URLs](#base-urls)
- [Authentication](#authentication)

## Architecture & Components Overview

Instead of a single monolithic application, the backend is split into three
specialized processes (packaged as three Docker images) plus a separate frontend and a
healthcheck service. The three backend processes share the same source code and the
same PostgreSQL database but run different entrypoints.

### API

The API (image `ghcr.io/openzim/cms-api`) is the RESTful FastAPI service consumed by the
frontend and by the zimfarm backend. It is responsible
for:

- persisting titles, books, collections, warehouses, accounts and Zimfarm
  notifications.
- exposing `catalog.xml` endpoints for each collection and for staging.
- authenticating users and enforcing role-based permissions.
- orchestrating manual ZIM uploads (see [Zimfarm API Integration](#zimfarm-api-integration)

**Key Environment Variables:**

- `DATABASE_URL`: SQLAlchemy connection string (e.g.
  `postgresql+psycopg://cms:cmspass@postgresdb:5432/cms`).
- `ALEMBIC_UPGRADE_HEAD_ON_START`: set to `"true"` to run migrations on startup.
- `ALLOWED_ORIGINS`: comma-separated list of CORS origins.
- `INIT_USERNAME` / `INIT_PASSWORD`: credentials of the initial `admin` account
  created on startup if it does not exist.
- `STAGING_WAREHOUSE_ID`, `STAGING_BASE_PATH`, `STAGING_DOWNLOAD_BASE_URL`,
  `STAGING_VIEW_BASE_URL`, `STAGING_LIBRARY_XML_BASE_PATH`: staging configuration.
- `QUARANTINE_WAREHOUSE_ID`, `QUARANTINE_BASE_PATH`: quarantine configuration.
- `BACKUP_WAREHOUSE_ID`, `BACKUP_BASE_PATH`, `BACKUP_DOWNLOAD_BASE_URL`,
  `BACKUP_VIEW_BASE_URL`: backup configuration.
- `ZIM_UPLOAD_S3_BUCKET_URI`: S3 bucket for manually uploaded ZIMs.
- `ZIMFARM_URL`, `ZIMFARM_API_URL`: URLs of the Zimfarm UI and API.
- `ZIMFARM_AUTH_MODE`, `ZIMFARM_USERNAME`, `ZIMFARM_PASSWORD`,
  `ZIMFARM_OAUTH_ISSUER`, `ZIMFARM_OAUTH_CLIENT_ID`, `ZIMFARM_OAUTH_CLIENT_SECRET`,
  `ZIMFARM_OAUTH_AUDIENCE_ID`, `ZIMFARM_TOKEN_RENEWAL_WINDOW`: credentials used to
  authenticate to the Zimfarm API (see [Zimfarm API Integration](#zimfarm-api-integration)).
- `ZIMWRIGHT_IMAGE`, `ZIMWRIGHT_DEFINITION_VERSION`, `ZIMTASK_CPU`, `ZIMTASK_MEMORY`,
  `ZIMTASK_DISK`, `ZIMTASK_WORKER`: configuration of the `zimwright` recipe created for
  manual uploads.
- `MEDIA_COUNT_INCREASE_THRESHOLD`, `ARTICLE_COUNT_INCREASE_THRESHOLD`,
  `MEDIA_COUNT_DECREASE_THRESHOLD`, `ARTICLE_COUNT_DECREASE_THRESHOLD`: default
  thresholds for detecting suspicious changes in book counts.
- `ZIM_TITLE_MAX_LENGTH`, `ZIM_DESCRIPTION_MAX_LENGTH`: limits for title/description
  metadata.
- `CUSTOM_LANGUAGE_CODES`, `DISALLOWED_LANGUAGE_CODES`: comma-separated ISO-639-3
  language codes to add/remove from the accepted list.
- `ZIMCHECK_SCRAPERS_WHITELIST_REGEX`: regex of scrapers to ignore for zimcheck
  quality checks.
- `ROTTEN_FLAVOUR_THRESHOLD`: duration after which a flavour with no new book is
  considered "rotten".
- `REQUESTS_TIMEOUT`: global HTTP request timeout (e.g. `30s`).
- `BOOK_DELETION_DELAY`: delay before a book scheduled for deletion is removed.

### Mill

The mill (image `ghcr.io/openzim/cms-mill`) is a background service that periodically
runs tasks. It is responsible for:

- processing incoming zimfarm notifications into books.
- processing title modification events.
- applying retention rules to titles.
- marking stale staging books for deletion.
- updating the status of title uploads from zimfarm.
- deleting uploaded ZIMs and zimcheck results from S3.

**Key Environment Variables:**

- `DATABASE_URL`, `ALEMBIC_UPGRADE_HEAD_ON_START`.
- `QUARANTINE_WAREHOUSE_ID`, `QUARANTINE_BASE_PATH`, `STAGING_WAREHOUSE_ID`,
  `STAGING_BASE_PATH`, `STAGING_DOWNLOAD_BASE_URL`, `STAGING_VIEW_BASE_URL`,
  `BACKUP_WAREHOUSE_ID`, `BACKUP_BASE_PATH`, `BACKUP_DOWNLOAD_BASE_URL`,
  `BACKUP_VIEW_BASE_URL`.
- `ZIMCHECK_RESULTS_S3_BUCKET_URI`: S3 bucket where zimcheck results are stored.
- `ZIM_UPLOAD_S3_BUCKET_URI`: S3 bucket for manually uploaded ZIMs.
- `PROCESS_ZIMFARM_NOTIFICATIONS_INTERVAL`, `PROCESS_EVENTS_INTERVAL`,
  `PROCESS_RETENTION_RULES_INTERVAL`, `MARK_STAGING_BOOKS_FOR_DELETION_INTERVAL`,
  `UPDATE_TITLE_UPLOAD_STATUS_INTERVAL`, `DELETE_UPLOADED_ZIMS_INTERVAL`,
  `DELETE_ZIMCHECK_FILES_INTERVAL`: execution intervals for each task.
- `STAGING_BOOKS_LIFESPAN`, `STAGING_BOOKS_DELETION_GRACE_PERIOD`: how long staging
  books live and how long before they are actually deleted.

### Shuttle

The Shuttle (image `ghcr.io/openzim/cms-shuttle`) is a background service responsible
for moving and deleting ZIM files across warehouses. It only operates on local
filesystem paths that are explicitly mapped to warehouse IDs.

**Key Environment Variables:**

- `DATABASE_URL`, `ALEMBIC_UPGRADE_HEAD_ON_START`.
- `LOCAL_WAREHOUSE_PATHS`: comma-separated mapping of warehouse ID to local path, e.g.
  `11111111-...:/warehouses/dev-hidden,22222222-...:/warehouses/dev-prod`.
- `MOVE_FILES_INTERVAL`, `DELETE_FILES_INTERVAL`: execution intervals.

### Frontend

The Frontend (image `ghcr.io/openzim/cms-ui`) is a Vue.js single-page application
served by nginx. It is a purely client-side application that relies on the CMS API to
fetch and mutate data. It also calls the Zimfarm API directly (see
[Zimfarm API Integration](#zimfarm-api-integration)).

The frontend reads its runtime configuration from a `config.json` file served at the
web root (`/config.json`). This file is baked into the image under
`/usr/share/nginx/html/config.json` and can be overridden at runtime by mounting your
own file over it.

**`config.json` keys:**

- `CMS_API`: URL of the CMS API (e.g. `https://api.cms.openzim.org/v1`).
- `ZIMFARM_API`: URL of the Zimfarm API (e.g. `https://api.farm.openzim.org/v2`).
- `OAUTH_BASE_URL`: base URL of the identity provider.
- `LOGIN_MODES`: list of enabled login modes (`local`, `oauth`).
- `MATOMO_ENABLED`, `MATOMO_HOST`, `MATOMO_SITE_ID`, `MATOMO_TRACKER_FILE_NAME`:
  optional analytics configuration.

### Healthcheck

The Healthcheck (image built from the `healthcheck/` folder) is a small monitoring
service that checks the status of the CMS services and components and displays the
results as HTML.

**Key Environment Variables:**

- `CMS_API_URL`: CMS backend API URL.
- `CMS_FRONTEND_URL`: CMS frontend UI URL.
- `CMS_USERNAME`, `CMS_PASSWORD`: credentials of the account used to authenticate.
- `CMS_DATABASE_URL`: database connection string.

The healthchecks it performs are:

- check authentication with CMS API works
- check database connection
- check that frontend is available
- check that no zimfarm notification is stuck in pending state. The
  `ZIMFARM_NOTIFICATION_PENDING_DELAY` environment variable determines how long a
  zimfarm notification in pending state should be flagged as an issue.
- check that books in `quarantine` or `staging` are not stuck requring file operations.
  The `BOOKS_PENDING_MOVE_DELAY` environment variable specifies the duration after which
  books flagged for movement should be marked as problematic if they still require file
  operations
- check that books in `to_delete` locations are not stuck requring file operations. The
  `BOOKS_PENDING_DELETE_DELAY` environment variable specififes the duration after which
  books flagged for deletion should be marked as problematic if they still require file
  operations
- check that catalog generation works for all collections

## Zimfarm API Integration

The CMS interacts with the zimfarm API in two distinct ways, and it is important to
understand **who** is authenticating in each case, because the two flows use different
credentials and serve different purposes.

### Backend calls with CMS credentials

The **API** component authenticates to the Zimfarm API using the CMS's **own service
credentials** (a dedicated machine account on Zimfarm, or an OAuth client). These
credentials are configured through the `ZIMFARM_*` environment variables:

- `ZIMFARM_AUTH_MODE`: either `local` (username/password) or `oauth`
  (client-credentials flow).
- For `local` mode: `ZIMFARM_USERNAME`, `ZIMFARM_PASSWORD`.
- For `oauth` mode: `ZIMFARM_OAUTH_ISSUER`, `ZIMFARM_OAUTH_CLIENT_ID`,
  `ZIMFARM_OAUTH_CLIENT_SECRET`, `ZIMFARM_OAUTH_AUDIENCE_ID`.
- `ZIMFARM_TOKEN_RENEWAL_WINDOW`: how early the access token is renewed.

The CMS uses these credentials when it needs to act **on its own behalf**, i.e. for
operations that are not attributable to a specific user's zimfarm account. Concretely,
this happens when an editor **manually uploads a ZIM** through the CMS:

1. The CMS creates (or updates) a `zimwright_<title_name>` recipe on Zimfarm
   (`GET`/`POST`/`PATCH` on `/recipes`).
2. The CMS requests a task for that recipe (`POST` on `/requested-tasks`).

The reason for using the CMS's own credentials here is that the recipe and task are
CMS-orchestrated. the CMS needs a stable, privileged identity to create the recipe and
trigger the processing of the uploaded file, regardless of which editor triggered the
upload.

> **Note:** the CMS also reads task status from the Zimfarm API (via the
> `/tasks/{id}` and `/requested-tasks/{id}` endpoints) to update the status of title
> uploads. This is a read-only operation performed by the API and by the mill.

### Frontend calls with user credentials

The **frontend** calls the zimfarm API directly, using the **logged-in user's own
Zimfarm credentials** rather than the CMS's service credentials. The frontend keeps a
separate zimfarm token (independent from the CMS token) and attaches it as a
`Authorization: Bearer …` header when calling the Zimfarm API (`ZIMFARM_API`).

The frontend uses this flow for operations that must reflect the **user's own
permissions on Zimfarm**:

- fetching and updating recipes (e.g. when a title's metadata is changed and the change
  must be propagated to the underlying recipe),

The reason for using the user's credentials here is that these operations concern
resources owned by Zimfarm, and the user should only be able to see and modify what
their own Zimfarm account allows. The CMS does not mediate these calls with its own
privileged identity.

## S3 Bucket Setup

The CMS uses two S3 (or S3-compatible) buckets. One is under the CMS's responsibility;
the other is shared with Zimfarm and is not managed by the CMS. It is important to
configure them with the right ownership and credentials.

Both buckets are configured using `kiwixstorage`-style URIs of the form:

```
s3+https://s3.us-west-1.wasabisys.com/?keyId=...&secretAccessKey=...&bucketName=...
```

The `s3+https://` (or `s3+http://`) prefix indicates an S3-compatible endpoint over
HTTPS/HTTP.

### `ZIM_UPLOAD_S3_BUCKET_URI` (CMS responsibility)

This is the bucket used for **ZIM files uploaded manually through the CMS UI**. It is
under the CMS's responsibility as the CMS owns it, generates upload URLs against it, and
cleans it up.

The workflow is:

1. The API generates multipart **presigned upload URLs** for the user's browser to
   upload the ZIM directly to S3 (key pattern: `cms_zim_uploads/<title>/<uuid>.zim`).
2. The API completes the multipart upload.
3. The API generates a **presigned view URL** and passes it to the `zimwright` recipe as
   the `download-from` flag, so Zimfarm can fetch the file.
4. Once the resulting task reaches a terminal state, the mill deletes the uploaded file
   from this bucket.

**Configuration:**

- Set `ZIM_UPLOAD_S3_BUCKET_URI` on the **API** and **mill** containers.

### `ZIMCHECK_RESULTS_S3_BUCKET_URI` (Zimfarm responsibility)

This is the bucket where the **zimfarm** writes the results of `zimcheck` runs. The
CMS does **not** own or create this bucket; it only reads and cleans up.

The workflow is:

1. Zimfarm uploads the zimcheck results to this bucket and sends the CMS a notification
   containing the `zimcheck_url`.
2. The CMS stores that URL on the book.
3. Once the book reaches `prod` or `deleted`, the mill deletes the zimcheck result file
   from this bucket (the `delete_zimcheck_s3_results` task).

**Configuration:**

- Set `ZIMCHECK_RESULTS_S3_BUCKET_URI` on the **mill** container.

### S3 credentials requirements

The CMS validates its S3 credentials before performing tasks related to them using
`check_credentials(list_buckets=True, delete=True)`. As a consequence, the credentials
provided to the CMS **must** have permission to **list buckets** and to **delete
objects**.

## Warehouses & Filesystem

Warehouses are the logical storage locations where ZIM files live. They are persisted
in the database, and the shuttle maps them to local filesystem paths at runtime.

The mapping is configured through the `LOCAL_WAREHOUSE_PATHS` environment variable on
the **shuttle**, as a comma-separated list of `<warehouse_id>:<local_path>` pairs:

```
LOCAL_WAREHOUSE_PATHS=11111111-...:/warehouses/dev-hidden,22222222-...:/warehouses/dev-prod
```

The shuttle will only move/delete files for warehouses present in this mapping. Books
whose locations reference a warehouse that is not mapped are skipped.

Three special warehouses are referenced through dedicated environment variables (set on
the API, Mill and Shuttle as needed):

- **Quarantine**: `QUARANTINE_WAREHOUSE_ID` + `QUARANTINE_BASE_PATH`. Where new books
  first arrive.
- **Staging**: `STAGING_WAREHOUSE_ID` + `STAGING_BASE_PATH`. Where books go while
  awaiting promotion.
- **Backup**: `BACKUP_WAREHOUSE_ID` + `BACKUP_BASE_PATH`. Where backups are stored.

Production collections are each associated with their own warehouse through the
database, so there is no single "prod" environment variable.

## Base URLs

The CMS builds download and view URLs from configured base URLs. This configuration is
done in two places:

- for **staging**, through environment variables:
  - `STAGING_DOWNLOAD_BASE_URL` (e.g. `https://mirror.download.kiwix.org/zim/.hidden/dev/`)
  - `STAGING_VIEW_BASE_URL` (e.g. `https://dev.library.kiwix.org/viewer#`)
- for **each collection**, in the database (`download_base_url` and `view_base_url`).

Download URLs are built as `{download_base_url}{path/filename}` for production books and
`{download_base_url}{filename}` for staging books. The `path/filename` and `{filename}`
do not contain a leading slash, so `download_base_url` must usually contain a trailing
slash.

View URLs are built as `{view_base_url}{filename_without_prefix}`.

Typical values:

- staging: `https://mirror.download.kiwix.org/zim/.hidden/dev/` /
  `https://dev.library.kiwix.org/viewer#`
- `Kiwix` collection: `https://download.kiwix.org/zim/` /
  `https://browse.library.kiwix.org/viewer#`

## Authentication

The CMS supports two authentication modes, controlled independently on the backend and
on the frontend.

### Backend

The backend `AUTH_MODES` environment variable is a comma-separated list of enabled
modes:

- **`local`**: traditional username/password authentication.
- **`oauth`**: OAuth/OIDC authentication backed by [Ory.sh](https://www.ory.com/).

When `oauth` is enabled, you need to configure:

- `OAUTH_JWKS_URI`: the JWKS endpoint for token verification.
- `OAUTH_ISSUER`: the OAuth issuer URL.
- `OAUTH_SESSION_AUDIENCE_ID`: the audience the JWT must contain.
- `OAUTH_SESSION_LOGIN_REQUIRE_2FA`: whether 2FA is required for human users.
- `OAUTH_CLIENT_ID`: the backend's OAuth client ID.
- `CREATE_NEW_OAUTH_ACCOUNT`: set to `"true"` to automatically create a `viewer`
  account when a valid but unknown JWT is presented.

For local authentication, configure:

- `JWT_SECRET`: secret used to sign local JWTs.
- `JWT_TOKEN_ISSUER`, `JWT_TOKEN_EXPIRY_DURATION`, `REFRESH_TOKEN_EXPIRY_DURATION`.

### Frontend

The frontend `LOGIN_MODES` setting (in `config.json`) is a list of enabled modes:
`local`, `oauth`, or both. When `oauth` is enabled, `OAUTH_BASE_URL` must point to the
identity provider.
