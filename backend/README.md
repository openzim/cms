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
