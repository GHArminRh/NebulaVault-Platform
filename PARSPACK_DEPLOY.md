# Deploy an independent Nebula Vault instance on ParsPack

This deployment shares the Git codebase with Render, but it is a separate
application with its own database, secrets, domain, cache, and media namespace.
Nothing is synchronized between the two instances.

## Important: keep the instances on different hostnames

Do not point the same public hostname at both deployments. Because their
databases are independent, traffic splitting would make accounts, sessions,
orders, licenses, products, and CMS content appear to disappear depending on
which server receives a request.

Keep the existing Render production hostname/domain unchanged. Give ParsPack
its own hostname, for example `parspack.mydigigi.ir`, and use that hostname
as `SITE_BASE_URL` for the ParsPack deployment.

## Database initialization decision

The ParsPack database is intentionally **empty and initialized from scratch**.
Do not export, clone, restore, or import any data from Render. The first
ParsPack deployment should apply Django migrations to its own newly provisioned
PostgreSQL database, then create its own administrator account. Render's
database and all existing customer/order/license/content records remain
untouched and are not copied.

## Create the independent resources first

1. Create a new Django PaaS application in ParsPack from
   `GHArminRh/NebulaVault-Platform`.
2. Select branch `feat/parspack-independent-deployment`.
3. Set the Django context directory to the repository root (the directory
   containing `manage.py` and `requirements.txt`).
4. For the initial limited-user / smoke-test phase, do **not** provision a
   PostgreSQL database. Enable the ParsPack-only ephemeral SQLite mode below.
   The database file lives under `/tmp` and can disappear whenever the app
   container is replaced or restarted.
5. Do not provision Redis for this phase. With no `REDIS_URL`, Django uses
   its database cache backend on the selected SQLite database.
6. Set `MEDIA_STORAGE_BACKEND=local` for initial testing. Uploaded media is
   stored on the app filesystem and may disappear when the container is
   replaced. Do not reuse Render's B2 bucket or credentials.

## ParsPack build and runtime settings

Use the following application commands:

- Build command: `bash build.sh`
- Start command: `bash start_parspack.sh`
- Gunicorn configuration file (relative to the Django context directory):
  `gunicorn.parspack.conf.py`
- Django context directory: repository root
- Health check path: `/healthz/` (if supported by the ParsPack app settings)

The Gunicorn configuration binds to `0.0.0.0:8000`, as required by the
ParsPack Django runtime. The Render service continues to use its existing
`$PORT` command and its existing Render Blueprint.

### Managed dependency installation (important)

ParsPack's Django build flow installs the dependencies listed in the root
`requirements.txt` before it runs the custom Build command. Therefore:

- Keep `requirements.txt` in the configured Django context directory (the
  repository root).
- Keep the Build command as `bash build.sh`.
- Do not run another `pip install -r requirements.txt` inside `build.sh`;
  that would download and install the same packages twice.
- Configure the application's `pip_index_url` parameter in ParsPack's
  application/build settings to the package index or mirror intended for this
  app. This is a ParsPack platform setting, not a Django runtime variable.
- If package downloads time out, set `PIP_TIMEOUT=60` and
  `PIP_RETRIES=10` in the application's **Build ENV** (not only Runtime ENV).
  These increase pip's wait and retry limits during dependency installation;
  they cannot repair an unreachable mirror or a failing redirected download
  host. Confirm in the build log that the effective timeout is no longer 15s.
- The custom Build command runs Django's `collectstatic`, so its Build ENV
  must also provide `DJANGO_SECRET_KEY`. Use a separate temporary build-only
  secret; keep the real ParsPack secret in Runtime ENV.
- Set `PARSPACK_USE_SQLITE=True` in **both Build ENV and Runtime ENV**. This
  makes settings load without PostgreSQL credentials and ensures migrations
  run against SQLite at runtime. Do not set this variable on Render.
- Set `MEDIA_STORAGE_BACKEND=local` in Build ENV and Runtime ENV. No S3
  credentials are required for this initial phase.
- Do not add `DATABASE_URL`, `DB_NAME`, `DB_USER`, or `DB_PASSWORD` to
  ParsPack while SQLite mode is enabled. Never copy Render's DB credentials.
- Keep `PIP_TIMEOUT=60` and `PIP_RETRIES=10` in Build ENV as already
  configured. If you later switch to PostgreSQL, remove `PARSPACK_USE_SQLITE`
  from Build ENV and Runtime ENV and configure a new ParsPack-only
  `DATABASE_URL`.

The custom `build.sh` now only validates the committed frontend CSS bundles
and runs `collectstatic`. Database migrations are deliberately deferred to
`start_parspack.sh`, which runs `render_startup` against the independent
ParsPack database.

## Required environment variables

Set these values in the ParsPack application's environment settings. Use
values generated specifically for ParsPack; never copy Render's database
credentials or Django secret.

| Variable | ParsPack value |
| --- | --- |
| `DJANGO_SECRET_KEY` | A new, unique, high-entropy secret |
| `DJANGO_DEBUG` | `False` |
| `PARSPACK_USE_SQLITE` | `True` in both Build ENV and Runtime ENV for the temporary SQLite phase |
| `SITE_BASE_URL` | The ParsPack-only HTTPS hostname |
| `DJANGO_ALLOWED_HOSTS` | ParsPack hostname, plus localhost if needed |
| `CSRF_TRUSTED_ORIGINS` | `https://` ParsPack hostname |
| `DJANGO_SECURE_HSTS_SECONDS` | `31536000` after HTTPS is verified |
| `MEDIA_STORAGE_BACKEND` | `local` for the initial temporary phase |
| `ZARINPAL_ENABLED` | `False` until the separate instance is configured for payments |
| `ZARINPAL_SANDBOX` | `True` while testing |

Configure only integrations needed for the first test. Email, Turnstile,
Google OAuth, Search Console, and Algolia need valid settings and hostname /
callback configuration before those features can work. Do not paste the
Render `.env` wholesale into ParsPack. Do not copy its database, Redis, B2
storage, Django secret, or payment credentials. Uploaded files are local and
ephemeral in this phase.

### Independent OAuth and security callbacks

Register the ParsPack hostname as an additional OAuth callback in Google.
Do not remove the existing Render callback URLs. Configure the ParsPack
Turnstile hostname and keys independently. Review any webhook, payment
callback, email link, and external cron URL so that it points to the correct
instance.

## Database and first boot

The ParsPack start script invokes the same project startup management command
used by the existing Render deployment. It will apply the committed Django
migrations to the ParsPack SQLite database only. The database starts empty.
Because the file is under `/tmp`, a container replacement/restart may erase
accounts and other app data; this is accepted only for the initial test phase.
Keep a single Gunicorn worker in SQLite mode to reduce write contention.

After the first successful deploy:

1. Verify `/healthz/` returns HTTP 200.
2. Verify the storefront, static CSS/JS, login and registration pages.
3. Create a ParsPack-specific administrator using the ParsPack console:
   `python manage.py createsuperuser`.
4. Verify Wagtail at `/cms/` and Django admin at `/admin/`.
5. Test email verification, password reset, Turnstile, OAuth, and file upload.
6. Keep payment processing disabled until merchant credentials and callback
   URLs are deliberately configured for this separate instance.

## Separation checklist

- Render retains its existing PostgreSQL database and environment.
- ParsPack uses explicit ephemeral SQLite mode for the initial test phase
  and a different `DJANGO_SECRET_KEY`.
- The two instances use different canonical hostnames.
- Redis/cache and media buckets are not shared when strict data separation
  is required.
- No Cloudflare load-balancing or DNS round-robin is configured between the
  two hostnames.
- Application code can be updated from the same repository branch, but data
  changes and admin actions remain local to each instance.

## Rollback

To roll back ParsPack, redeploy the previous ParsPack commit or disable the
ParsPack app. This does not alter Render. Never run database migrations against
the Render database from ParsPack or vice versa.
