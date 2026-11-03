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
- [Catalogs & Feeds](#catalogs--feeds)
- [Applications & App Builds](#applications--app-builds)
- [Download Statistics](#download-statistics)
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

- persisting titles, books, collections, warehouses, accounts, Zimfarm
  notifications, applications and app builds.
- exposing `catalog.xml` and `opds.xml` endpoints for each collection and for staging.
- authenticating users and enforcing role-based permissions.
- orchestrating manual ZIM uploads (see [Zimfarm API Integration](#zimfarm-api-integration))
  and app builds (see [Applications & App Builds](#applications--app-builds)).
- storing and serving download statistics per title flavour.

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
- `MIN_LANGUAGES_FOR_TITLE_SYNC`: minimum number of languages in book metadata before
  the title's language metadata is updated from a book (default: `5`).
- `ZIMCHECK_SCRAPERS_WHITELIST_REGEX`: regex of scrapers to ignore for zimcheck
  quality checks.
- `ROTTEN_FLAVOUR_THRESHOLD`: duration after which a flavour with no new book is
  considered "rotten".
- `REQUESTS_TIMEOUT`: global HTTP request timeout (e.g. `30s`).
- `BOOK_DELETION_DELAY`: delay before a book scheduled for deletion is removed.
- `OPDS_INLINE_ILLUSTRATION`: set to `"false"` to reference book illustrations by URL
  in OPDS feeds instead of embedding them as base64 data URLs (default: `"true"`).
- `OPDS_ILLUSTRATION_URL_TEMPLATE`: URL template used when illustrations are not
  embedded. The only supported placeholder is `{book_id}`.
- `GITHUB_API_URL`, `GITHUB_TOKEN`, `GITHUB_ANDROID_REPO`,
  `GITHUB_ANDROID_WORKFLOW`, `GITHUB_ANDROID_BRANCH`, `GITHUB_APPLE_REPO`,
  `GITHUB_APPLE_WORKFLOW`, `GITHUB_APPLE_BRANCH`: GitHub integration used to prepare
  app build requests (see [Applications & App Builds](#applications--app-builds)).
- `APP_BUILD_STORES`: comma-separated list of stores exposed for app builds (default:
  `android,apple`).

### Mill

The mill (image `ghcr.io/openzim/cms-mill`) is a background service that periodically
runs tasks. It is responsible for:

- processing incoming zimfarm notifications into books.
- processing title modification events.
- advancing app builds through their GitHub pull request, release and CD phases.
- checking books in transition (files moved, available on mirrors, live in library).
- applying retention rules to titles.
- marking stale staging books for deletion.
- updating the status of title uploads from zimfarm.
- deleting uploaded ZIMs and zimcheck results from S3.
- fetching download statistics from Matomo and recomputing titles popularity.

Each task can be disabled with a dedicated boolean environment variable; its execution
interval is controlled by a separate `*_INTERVAL` variable.

#### Mill technical account

Automated actions performed by the mill are attributed to a technical account. The mill creates this account with the `admin` role on startup if it does not already exist. If an account with the configured username already exists, it is reused as-is.

| Variable                | Default | Description                                                        |
| ----------------------- | ------- | ------------------------------------------------------------------ |
| `MILL_ACCOUNT_USERNAME` | `mill`  | Username of the technical account used for automated mill actions. |


**Key Environment Variables:**

- `DATABASE_URL`, `ALEMBIC_UPGRADE_HEAD_ON_START`.
- `PAUSE_IN_THE_LOOP`: delay between two runs of the task loop (default: `10s`).
- `QUARANTINE_WAREHOUSE_ID`, `QUARANTINE_BASE_PATH`, `STAGING_WAREHOUSE_ID`,
  `STAGING_BASE_PATH`, `STAGING_DOWNLOAD_BASE_URL`, `STAGING_VIEW_BASE_URL`,
  `BACKUP_WAREHOUSE_ID`, `BACKUP_BASE_PATH`, `BACKUP_DOWNLOAD_BASE_URL`,
  `BACKUP_VIEW_BASE_URL`.
- `ZIMCHECK_RESULTS_S3_BUCKET_URI`: S3 bucket where zimcheck results are stored.
- `ZIM_UPLOAD_S3_BUCKET_URI`: S3 bucket for manually uploaded ZIMs.
- `PROCESS_ZIMFARM_NOTIFICATIONS` / `PROCESS_ZIMFARM_NOTIFICATIONS_INTERVAL`.
- `PROCESS_TITLE_MODIFICATIONS` / `PROCESS_EVENTS_INTERVAL`.
- `PROCESS_APP_BUILDS` / `PROCESS_APP_BUILDS_INTERVAL`.
- `CHECK_BOOK_TRANSITIONS` / `CHECK_BOOK_TRANSITIONS_INTERVAL`.
- `PROCESS_RETENTION_RULES` / `PROCESS_RETENTION_RULES_INTERVAL`.
- `MARK_STAGING_BOOKS_FOR_DELETION` / `MARK_STAGING_BOOKS_FOR_DELETION_INTERVAL`.
- `UPDATE_TITLE_UPLOADS_STATUS` / `UPDATE_TITLE_UPLOAD_STATUS_INTERVAL`.
- `DELETE_UPLOADED_ZIMS` / `DELETE_UPLOADED_ZIMS_INTERVAL`.
- `DELETE_ZIMCHECK_S3_RESULTS` / `DELETE_ZIMCHECK_FILES_INTERVAL`.
- `FETCH_DOWNLOAD_STATS` / `FETCH_DOWNLOAD_STATS_INTERVAL`.
- `STAGING_BOOKS_LIFESPAN`, `STAGING_BOOKS_DELETION_GRACE_PERIOD`: how long staging
  books live and how long before they are actually deleted.
- `DOWNLOAD_LB_HOST`: load-balancer host used to decide whether a book is available on
  enough mirrors (default: `lb.download.kiwix.org`).
- `INTERNAL_HOST_MAPPING`: comma-separated `public.host:internal.host` mapping used
  when probing public URLs from inside the infrastructure (e.g. mirror checks).
- `MIN_LANGUAGES_FOR_TITLE_SYNC`: minimum number of languages in book metadata before
  the title's language metadata is updated from a book (default: `5`).
- `GITHUB_API_URL`, `GITHUB_TOKEN`, `GITHUB_ANDROID_REPO`,
  `GITHUB_ANDROID_WORKFLOW`, `GITHUB_ANDROID_BRANCH`, `GITHUB_APPLE_REPO`,
  `GITHUB_APPLE_WORKFLOW`, `GITHUB_APPLE_BRANCH`, `APP_BUILD_STORES`: app build
  configuration (see [Applications & App Builds](#applications--app-builds)).
- `MATOMO_URL`, `MATOMO_SITE_ID`, `DOWNLOAD_STATS_DAYS_AGO`,
  `DOWNLOAD_STATS_YESTERDAY_HOUR`, `DOWNLOAD_STATS_POPULARITY_WINDOW_DAYS`,
  `DOWNLOAD_STATS_REQUEST_DELAY`: download statistics configuration (see
  [Download Statistics](#download-statistics)).

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
- check that books in `quarantine` or `staging` are not stuck requiring file operations.
  The `BOOKS_PENDING_MOVE_DELAY` environment variable specifies the duration after which
  books flagged for movement should be marked as problematic if they still require file
  operations
- check that books in `to_delete` locations are not stuck requiring file operations. The
  `BOOKS_PENDING_DELETE_DELAY` environment variable specifies the duration after which
  books flagged for deletion should be marked as problematic if they still require file
  operations
- check that catalog generation works for all collections

### PostgreSQL Database

All backend components share a single PostgreSQL database. It is the source of truth for
titles, books, file locations, collections, warehouses, accounts and permissions,
applications and app builds, as well as download statistics.

The connection is configured with `DATABASE_URL`. The API and mill can apply pending
Alembic migrations at startup when `ALEMBIC_UPGRADE_HEAD_ON_START` is `"true"`; this is
convenient in development but should be handled deliberately in production. The
`uuid-ossp` extension must be available in the database because primary keys default to
`uuid_generate_v4()`.

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

## Catalogs & Feeds

Each collection exposes two catalog formats, generated on the fly by the API:

- `/collections/{id_or_name}/catalog.xml`: the library catalog consumed by Kiwix
  readers,
- `/collections/{id_or_name}/opds.xml`: the same catalog as an OPDS feed.


**NOTE**: `catalog.xml` format is maintained for legacy purposes and will be phased out in favour
of the `opds.xml` format once [kiwix-serve](https://wiki.kiwix.org/wiki/Kiwix-serve) is updated.

The staging catalog is exposed at `/staging/catalog.xml` and `/staging/opds.xml`. For
private collections, the API only includes titles from collections the current account
can access; an unauthenticated caller only sees public collections.

All catalog endpoints accept an optional `path_prefix` query parameter which is
prepended to the book paths in the generated XML/OPDS feed. Both formats are also
available through `HEAD` requests, with an `ETag` computed from the content.

The OPDS feed embeds the book illustration as a base64 data URL by default. Set
`OPDS_INLINE_ILLUSTRATION` to `"false"` and configure
`OPDS_ILLUSTRATION_URL_TEMPLATE` (with the `{book_id}` placeholder) to reference the
illustration by URL instead. This is usually done to keep the feed small.

## Applications & App Builds

An **application** is the per-store configuration used to build a branded app for one
title flavour. An **app build** is the asynchronous process which updates the branded
app repository, opens and merges a pull request, creates a release, and runs the CD
workflow which publishes the app.

App builds are configured with the `GITHUB_*` environment variables (on the **API** and
**mill**) and are limited to the stores listed in `APP_BUILD_STORES`. Both stores share
the same conventions:

- Android builds use
  [kiwix-android-branded](https://github.com/kiwix/kiwix-android-branded).
- Apple builds use [kiwix-apple-branded](https://github.com/kiwix/kiwix-apple-branded).
- Tags follow the `<app>_<YYYY>.<MM>.<build>` convention. `<build>` starts at 0
  for the first build of a content version and is incremented on every retry.

The GitHub token needs `contents: write`, `pull requests: write`, `actions: read` and
`checks: read`. Branch protection must not require human approvals if the bot is
expected to merge the pull request without review.

Permissions are described in the [Editors Guide](EDITORS_GUIDE.md#roles--permissions).

## Download Statistics

The **mill** fetches, for every title flavour, the daily number of downloads recorded
by the Kiwix download load balancer (`lb.download.kiwix.org`) in the Matomo instance
configured by `MATOMO_URL` / `MATOMO_SITE_ID`.

On each run, the mill:

- fetches every missing day from `DOWNLOAD_STATS_DAYS_AGO` days ago up to yesterday,
  where yesterday is only considered available after `DOWNLOAD_STATS_YESTERDAY_HOUR`
  UTC,
- waits `DOWNLOAD_STATS_REQUEST_DELAY` seconds between two Matomo requests,
- keeps the current and previous calendar years, and purges older data,
- recomputes the popularity of titles from the most recent
  `DOWNLOAD_STATS_POPULARITY_WINDOW_DAYS` fetched days.

## Authentication

Authentication establishes the account; authorization is role-based. Role definitions
and their permissions are centralised in `backend/src/cms_backend/roles.py` and
documented in the [Editors Guide](EDITORS_GUIDE.md#roles--permissions). Accounts can be
created by admins, or automatically with the `public-viewer` role on first OAuth login
when `OAUTH_CREATE_NEW_ACCOUNT` is enabled.

The CMS supports two authentication modes, controlled independently on the backend and
on the frontend.

### Backend

The backend supports multiple authentication modes, controlled by the `AUTH_MODES`
environment variable (comma-separated list, possible to activate as many modes as required):

- **`local`**: Traditional username/password authentication.
- **`oauth-oidc`**: OpenID Connect authentication flow.
- **`oauth-session`**: OAuth session-based authentication (the frontend transform a cookie-based session on identity provider into a JWT, which is then sent to the API).

Both `oauth-oidc` and `oauth-session` are backed by [Ory.sh](https://www.ory.com/) ATM.

When `oauth-oidc` and/or `oauth-session` are activated, you need to configure:

- `OAUTH_JWKS_URI`: The JWKS endpoint for token verification
- `OAUTH_ISSUER`: The OAuth issuer URL
- `OAUTH_CREATE_NEW_ACCOUNT`: Set to `"true"` to automatically create accounts whenever a new valid JWT is presented to the backend. New accounts get the `public-viewer` role (no more permission than when not authenticated); this is convenient to then let admins grant a proper role to this user through the UI.

For `oauth-oidc` you also need to configure:

- `OAUTH_OIDC_AUDIENCE`: The audience the JWT received by the API must contain
- `OAUTH_OIDC_LOGIN_REQUIRE_2FA`: Set to "False" if users can be logged-in without 2FA (default: True)

And for `oauth-session` you also need to configure:

- `OAUTH_SESSION_AUDIENCE`: The audience the JWT received by the API must contain
- `OAUTH_SESSION_LOGIN_REQUIRE_2FA`: Set to "False" if users can be logged-in without 2FA (default: True)

OAuth identities are matched by the `sub` JWT claim which must match the value in `idp_sub` (identity provider subject ID) DB column.
Local users authenticate with username/password and workers authenticate using SSH keys.

OAuth supports both humans and machine-to-machine identities. Humans are detected by the fact that the JWT misses the `client_id` claim (occurs in OAuth session) or has the `profile` value in `scp` claim (occurs in OAuth OIDC). Machines JWTs are expected to have the `sub` equal to the `client_id` (this is enforced in the backend).

Enforcement of 2FA is of-course possible only on human identities, not on machine-to-machine.

#### Frontend

The frontend supports two authentication modes, controlled by the `LOGIN_MODES`
setting (comma-separated list; activate as many modes as required):

- **`local`**: Username/password authentication against the CMS API.
- **`oauth`**: External authentication to an IdP provider.

Both modes can be active, letting the user choose how to authenticate. The frontend
also uses a separate Zimfarm token (see
[Frontend calls with user credentials](#frontend-calls-with-user-credentials)).

When `oauth` mode is activated, choose between session flows (exchange an IdP session
for a JWT) and OIDC flows (standard OIDC exchanges), and configure:

- **`OAUTH_MODE`**: either `session` or `oidc`
- **`OAUTH_BASE_URL`**: base URL to the IdP, e.g. `https://ory.login.kiwix.org`

When `oidc` mode is activated, you also need to configure:

- **`OAUTH_CLIENT_ID`**: the frontend client ID
- **`OAUTH_AUDIENCE`**: the audience to sign JWT for, i.e. the backend client ID
