# CMS Backend

This is the backend of the CMS system.

The backend is responsible to:

- provide API endpoints to the CMS UI and the Zimfarm Backend
- manage books and titles
- interact with the CMS File Manager to list / move / copy / delete books on "filesystems"

## Download statistics

The mill fetches, for every title flavour, the daily number of downloads made on
`lb.download.kiwix.org` from the Matomo instance at `stats.kiwix.org` (site id
24).
The job fetches every missing day from `DOWNLOAD_STATS_DAYS_AGO` days ago up
to yesterday (yesterday only after `DOWNLOAD_STATS_YESTERDAY_HOUR` UTC), and
purges data older than the previous year.

Relevant environment variables:

| Variable                        | Default                    | Description                                 |
| ------------------------------- | -------------------------- | ------------------------------------------- |
| `MATOMO_URL`                    | `https://stats.kiwix.org/` | Matomo API base URL                         |
| `MATOMO_SITE_ID`                | `24`                       | Matomo site id of `lb.download.kiwix.org`   |
| `DOWNLOAD_STATS_DAYS_AGO`       | `365`                      | How far back statistics are fetched         |
| `DOWNLOAD_STATS_YESTERDAY_HOUR` | `4`                        | UTC hour after which yesterday is available |
| `FETCH_DOWNLOAD_STATS_INTERVAL` | `1d`                       | How often the mill runs the job             |
| `DOWNLOAD_STATS_REQUEST_DELAY`  | `10`                       | Seconds between two Matomo requests         |

## Mill technical account

Automated actions performed by the mill (processing Zimfarm notifications and title
modifications) are attributed to a technical account. The mill creates this account
with role `mill` on startup if it does not already exist. If an account with the
configured username already exists, it is reused as-is.

| Variable                | Default | Description                                                        |
| ----------------------- | ------- | ------------------------------------------------------------------ |
| `MILL_ACCOUNT_USERNAME` | `mill`  | Username of the technical account used for automated mill actions. |

## App publication

Titles whose flavours are enabled for a given store (Android and/or Apple) can
trigger a branded-app release from the CMS. The backend creates a tag pointing
at the configured branch and a GitHub release, which triggers the branded app
CD workflow. Tags are the same for every store:

- `<app>_<YYYY>.<MM>[suffix].<build>`

`<build>` starts at 0 for the first publication of a given content version and
is incremented on every retry (for example after a failed build). Legacy/manual
releases using the bare app folder name as the tag remain supported.

Android publications use
[kiwix-android-branded](https://github.com/kiwix/kiwix-android-branded). Apple
publications are supported by the same generic code path but stay disabled
until an Apple repository is configured (`GITHUB_APPLE_REPO`).

Relevant environment variables:

| Variable                  | Default                       | Description                                       |
| ------------------------- | ----------------------------- | ------------------------------------------------- |
| `GITHUB_API_URL`          | `https://api.github.com`      | GitHub API base URL                               |
| `GITHUB_TOKEN`            | (empty)                       | Token with `contents: write` on the branded repo  |
| `GITHUB_ANDROID_REPO`     | `kiwix/kiwix-android-branded` | Android branded apps repository                   |
| `GITHUB_ANDROID_WORKFLOW` | `cd.yml`                      | Android CD workflow used for status tracking      |
| `GITHUB_ANDROID_BRANCH`   | `main`                        | Branch the Android publication tag points to      |
| `GITHUB_APPLE_REPO`       | (empty)                       | Apple branded apps repository (disabled if empty) |
| `GITHUB_APPLE_WORKFLOW`   | `cd.yml`                      | Apple CD workflow used for status tracking        |
| `GITHUB_APPLE_BRANCH`     | `main`                        | Branch the Apple publication tag points to        |
| `PUBLICATION_STORES`      | `android`                     | Comma-separated stores exposed to the UI          |
