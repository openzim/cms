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

## App build

Titles whose flavours are enabled for a given store (Android and/or Apple) can
trigger a branded-app build from the CMS. The pipeline is asynchronous:

1. `POST /app-builds` records the request and emits an `app_build_requested`
   event. It is rejected with a conflict if another build for the same app
   has not reached a terminal status.
2. The mill consumes the event, updates the app's `info.json` `zim_url`
    and opens a pull request.
3. A mill task advances the build through checks, merge, release and the
   CD workflow. The CMS merges the pull request itself once checks pass
4. Once the CD workflow succeeds, the build is complete and the app is
   considered uploaded to the store. Store review is outside the CMS scope.

Tags are created after the pull request is merged and follow the
`<app>_<YYYY>.<MM>[suffix].<build>` convention for every store. `<build>` starts
at 0 for the first build of a given content version and is incremented on
every retry (for example after a failed build)

Android builds use
[kiwix-android-branded](https://github.com/kiwix/kiwix-android-branded) whereas
apple builds use [kiwix-apple-branded](https://github.com/kiwix/kiwix-android-branded)

The GitHub token needs `contents: write`, `pull requests: write`, `actions: read`
and `checks: read`. Branch protection must not require human approvals if the
bot is expected to merge without review.

Relevant environment variables:

| Variable                            | Default                       | Description                                          |
| ----------------------------------- | ----------------------------- | ---------------------------------------------------- |
| `GITHUB_API_URL`                    | `https://api.github.com`      | GitHub API base URL                                  |
| `GITHUB_TOKEN`                      | (empty)                       | Token for contents, pull requests, actions and checks |
| `GITHUB_ANDROID_REPO`               | `kiwix/kiwix-android-branded` | Android branded apps repository                      |
| `GITHUB_ANDROID_WORKFLOW`           | `cd.yml`                      | Android CD workflow used for status tracking         |
| `GITHUB_ANDROID_BRANCH`             | `main`                        | Base branch for Android build pull requests    |
| `GITHUB_APPLE_REPO`                 | `kiwix/kiwix-apple-branded`
| `GITHUB_APPLE_WORKFLOW`             | `cd.yml`                      | Apple CD workflow used for status tracking           |
| `GITHUB_APPLE_BRANCH`               | `main`                        | Base branch for Apple build pull requests      |
| `APP_BUILD_STORES`                | `android,apple`                     | Comma-separated stores exposed to the UI             |

| `PROCESS_APP_BUILD_REQUESTS`      | `true`                        | Enable the build request event processor       |
| `PROCESS_APP_BUILD_REQUESTS_INTERVAL` | `10s`                     | Event processor interval                             |
| `ADVANCE_APP_BUILDS`              | `true`                        | Enable the build state-machine task            |
| `ADVANCE_APP_BUILDS_INTERVAL`     | `30s`                         | Build state-machine interval                  |
