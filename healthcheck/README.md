## Healthcheck

This service monitors the status of CMS services and components and displays results as HTML

### Environment variables

- CMS_API_URL: CMS backend API URL.
- CMS_FRONTEND_URL: CMS frontend UI URL.
- CMS_USERNAME: Username to authenticate with on CMS.
- CMS_PASSWORD: Password of user to authenticate with on CMS.
- CMS_DATABASE_URL: CMS database connection URL, including the driver, user credentials, host and port e.g `postgresql+psycopg://cms:cmspass@postgresdb:5432/cms`.
