# Celery worker on Enzonic (free tier)

This repository provides the worker entry point; the worker is a separate
process and is not part of the Render web service.

## Enzonic startup settings

- Runtime: Python 3.14
- Main File: worker.py
- User Uploaded Files: disabled (0)
- Git Repository: https://github.com/GHArminRh/NebulaVault-Platform.git
- Git Branch: feat/celery-cloudamqp-enzonic-worker
- Additional Packages: leave blank when the platform installs the repository's
  requirements.txt on startup. If the panel requires explicit packages,
  use its documented requirements-file installation method rather than
  duplicating the full Django dependency list here.

## Private environment variables

Set these in the Enzonic server's environment-variable/Startup Variables UI.
Never put their values in Git, issue comments, or chat messages.

Required to import the Django project and connect to its database:

- DJANGO_SECRET_KEY: same secret as the Render web service.
- DATABASE_URL: the Render PostgreSQL external connection URL, not its
  internal-only hostname. Keep SSL enabled as required by the database.
- CELERY_BROKER_URL: the CloudAMQP AMQPS connection URL (scheme must be
  amqps://). Do not use the Render cache's REDIS_URL as a broker.

This project uses Backblaze B2/S3 media storage in production. Copy the
matching storage configuration from Render so Django can initialize and any
tasks that read or write media use the same bucket:

- MEDIA_STORAGE_BACKEND=s3
- AWS_STORAGE_BUCKET_NAME
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_S3_REGION_NAME
- AWS_S3_ENDPOINT_URL
- AWS_S3_CUSTOM_DOMAIN (only if configured on Render)
- AWS_QUERYSTRING_AUTH (same value as Render)

Only add other application variables (for example email-provider credentials)
if a task actually needs them. Do not copy unrelated secrets unnecessarily.

## Important deployment notes

- The worker is configured with one process (solo pool) to fit the small
  free instance. It processes one task at a time.
- The website must also receive the same CELERY_BROKER_URL in Render before
  web requests can enqueue Celery tasks.
- The worker will exit with a clear error if the broker URL is absent or is
  not encrypted with AMQPS.
- The existing Render Redis/Valkey instance remains cache-only. Its
  allkeys-lru eviction policy and disabled persistence make it unsuitable
  as a Celery broker.
- This starts the worker infrastructure; application tasks still need to be
  implemented and explicitly queued before it performs background work.
