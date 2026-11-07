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
4. Provision a **new PostgreSQL database for ParsPack**. Do not copy the
   Render `DATABASE_URL`, Render database hostname, username, or password.
5. Provision a separate Redis-compatible service only if you intend to use
   Redis-backed cache or background jobs on this instance. Do not reuse
   Render's private Key Value URL.
6. For fully independent uploads, create a separate S3-compatible media
   bucket, e.g. `nebula-vault-media-parspack-2026`. The current Render B2
   bucket should not be configured here if media isolation is required.

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

## Required environment variables

Set these values in the ParsPack application's environment settings. Use
values generated specifically for ParsPack; never copy Render's database
credentials or Django secret.

| Variable | ParsPack value |
| --- | --- |
| `DJANGO_SECRET_KEY` | A new, unique, high-entropy secret |
| `DJANGO_DEBUG` | `False` |
| `DATABASE_URL` | Connection string for the new ParsPack PostgreSQL database |
| `SITE_BASE_URL` | The ParsPack-only HTTPS hostname |
| `DJANGO_ALLOWED_HOSTS` | ParsPack hostname, plus localhost if needed |
| `CSRF_TRUSTED_ORIGINS` | `https://` ParsPack hostname |
| `DJANGO_SECURE_HSTS_SECONDS` | `31536000` after HTTPS is verified |
| `ZARINPAL_ENABLED` | `False` until the separate instance is configured for payments |
| `ZARINPAL_SANDBOX` | `True` while testing |

Also configure the provider credentials you actually intend to use on this
instance: Resend or SMTP, Cloudflare Turnstile, Google OAuth, Google Search
Console, Algolia, and S3-compatible media storage. Each integration must be
configured for the ParsPack hostname and its own data scope where applicable.

### Independent OAuth and security callbacks

Register the ParsPack hostname as an additional OAuth callback in Google.
Do not remove the existing Render callback URLs. Configure the ParsPack
Turnstile hostname and keys independently. Review any webhook, payment
callback, email link, and external cron URL so that it points to the correct
instance.

## Database and first boot

The ParsPack start script invokes the same project startup management command
used by the existing Render deployment. It will apply the committed Django
migrations to the ParsPack database only. Since this database is new and
independent, it starts with an empty application dataset.

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
- ParsPack uses a different PostgreSQL database and a different
  `DJANGO_SECRET_KEY`.
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
