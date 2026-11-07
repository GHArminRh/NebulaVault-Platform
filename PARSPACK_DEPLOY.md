# Deploy an independent Nebula Vault test instance on ParsPack

This deployment shares the Git codebase with Render, but it is a separate
application with its own database, secrets, domain, cache, and media namespace.
Nothing is synchronized between the two instances.

## Keep the instances separate

Do not point the same public hostname at both deployments. Keep the existing
Render production hostname/domain unchanged. Give ParsPack its own hostname,
for example `parspack.mydigigi.ir`, and use that hostname as `SITE_BASE_URL`
for the ParsPack deployment.

The ParsPack database starts empty. Do not export, clone, restore, or import
any data from Render. Render's database and all existing customer, order,
license, and content records remain untouched.

## Create the ParsPack application and persistent disk

1. Create a new Django PaaS application in ParsPack from
   `GHArminRh/NebulaVault-Platform`.
2. Select branch `feat/parspack-independent-deployment`.
3. Set the Django context directory to the repository root (the directory
   containing `manage.py` and `requirements.txt`).
4. Attach a ParsPack persistent disk to this application.
5. Note the exact mount path configured for that disk. Use that exact path
   for `PARSPACK_DISK_MOUNT_PATH`; do not assume a default mount path.
6. Use the persistent disk for the SQLite database file. The application
   validates that the mount path exists, is writable, and contains the
   configured SQLite database path. Startup fails rather than silently
   creating the database on ephemeral container storage.
7. Do not provision a separate PostgreSQL or Redis service for this test
   deployment. With no `REDIS_URL`, Django uses its database cache backend
   on the same SQLite database.
8. Set `MEDIA_STORAGE_BACKEND=local` for initial testing. Uploaded media
   remains on the app filesystem unless separately configured for persistent
   storage; the persistent database disk does not automatically persist media.

## ParsPack build and runtime settings

Use these application commands:

- Build command: `bash build.sh`
- Start command: `bash start_parspack.sh`
- Gunicorn configuration file (relative to the Django context directory):
  `gunicorn.parspack.conf.py`
- Django context directory: repository root
- Health check path: `/healthz/` (if supported by the ParsPack app settings)

The Gunicorn configuration binds to `0.0.0.0:8000`, as required by the
ParsPack Django runtime. SQLite mode defaults to one worker to reduce
concurrent write contention. Render continues to use its existing
`$PORT` command and existing deployment configuration.

### Managed dependency installation

ParsPack's Django build flow installs the dependencies listed in the root
`requirements.txt` before it runs the custom Build command. Therefore:

- Keep `requirements.txt` in the configured Django context directory.
- Keep the Build command as `bash build.sh`.
- Do not run another `pip install -r requirements.txt` inside `build.sh`.
- Configure the application's `pip_index_url` parameter in ParsPack's
  application/build settings to the package index or mirror intended for this
  app. This is a ParsPack platform setting, not a Django runtime variable.
- If package downloads time out, keep `PIP_TIMEOUT=60` and
  `PIP_RETRIES=10` in Build ENV. These increase pip's wait and retry limits
  but cannot repair an unreachable mirror or redirected download host.
- The custom Build command runs `collectstatic`, so Build ENV must provide
  `DJANGO_SECRET_KEY`. Use a separate temporary build-only secret; keep the
  real ParsPack secret in Runtime ENV.
- For Build ENV only, leave `PARSPACK_USE_SQLITE=False` (or unset it) and
  provide placeholder `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and
  `DB_HOST` values so Django settings can load during `collectstatic`.
  The build does not run migrations. Do not put real Render credentials here.
- In Runtime ENV, set `PARSPACK_USE_SQLITE=True` and
  `PARSPACK_DISK_MOUNT_PATH` to the exact disk mount path from the ParsPack
  disk settings. The SQLite file defaults to
  `<mount path>/nebula-vault.sqlite3`.
- Optionally set `PARSPACK_SQLITE_PATH` to a custom file path, but it must
  remain inside `PARSPACK_DISK_MOUNT_PATH`.
- Do not set `PARSPACK_USE_SQLITE=True` in Build ENV: the persistent disk
  may not be mounted during image build. Never enable this flag on Render.
- Set `MEDIA_STORAGE_BACKEND=local` in Build ENV and Runtime ENV. No S3
  credentials are required for this initial phase.

## Required Runtime ENV

Set these values in ParsPack Runtime ENV. Use values generated specifically
for ParsPack; never copy Render's database credentials or Django secret.

| Variable | ParsPack value |
| --- | --- |
| `DJANGO_SECRET_KEY` | A new, unique, high-entropy secret |
| `DJANGO_DEBUG` | `False` |
| `PARSPACK_USE_SQLITE` | `True` |
| `PARSPACK_DISK_MOUNT_PATH` | Exact mount path configured for the ParsPack persistent disk |
| `PARSPACK_SQLITE_PATH` | Optional; defaults to `<mount path>/nebula-vault.sqlite3` |
| `SITE_BASE_URL` | ParsPack-only HTTPS hostname |
| `DJANGO_ALLOWED_HOSTS` | ParsPack hostname, plus localhost if needed |
| `CSRF_TRUSTED_ORIGINS` | `https://` ParsPack hostname |
| `DJANGO_SECURE_HSTS_SECONDS` | `31536000` after HTTPS is verified |
| `MEDIA_STORAGE_BACKEND` | `local` for initial testing |
| `ZARINPAL_ENABLED` | `False` until the separate instance is configured for payments |
| `ZARINPAL_SANDBOX` | `True` while testing |

Configure only integrations needed for the first test. Email, Turnstile,
Google OAuth, Search Console, and Algolia need valid settings and hostname /
callback configuration before those features can work. Do not paste the
Render `.env` wholesale into ParsPack. Do not copy its database, Redis, B2
storage, Django secret, or payment credentials.

### Independent OAuth and security callbacks

Register the ParsPack hostname as an additional OAuth callback in Google.
Do not remove the existing Render callback URLs. Configure the ParsPack
Turnstile hostname and keys independently. Review any webhook, payment
callback, email link, and external cron URL so that it points to the correct
instance.

## First boot and verification

The ParsPack start script invokes the project's startup management command.
It applies Django migrations to the SQLite database stored on the persistent
disk only. The database starts empty.

After the first successful deploy:

1. Verify `/healthz/` returns HTTP 200.
2. Verify the storefront, static CSS/JS, login, and registration pages.
3. Create a ParsPack-specific administrator using the ParsPack console:
   `python manage.py createsuperuser`.
4. Verify Wagtail at `/cms/` and Django admin at `/admin/`.
5. Test email verification, password reset, Turnstile, OAuth, and file upload.
6. Keep payment processing disabled until merchant credentials and callback
   URLs are deliberately configured for this separate instance.

## Separation checklist

- Render retains its existing PostgreSQL database and environment.
- ParsPack uses SQLite on its own persistent disk and a different
  `DJANGO_SECRET_KEY`.
- The two instances use different canonical hostnames.
- Redis/cache and media storage are not shared.
- No Cloudflare load-balancing or DNS round-robin is configured between
  the two hostnames.
- Application code can be updated from the same repository branch, but data
  changes and admin actions remain local to each instance.

## Rollback

To roll back ParsPack, redeploy the previous ParsPack commit or disable the
ParsPack app. This does not alter Render. Never run database migrations
against the Render database from ParsPack or vice versa.
