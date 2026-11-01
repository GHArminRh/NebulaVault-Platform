# Wagtail scheduled publishing with cron-job.org

This project exposes a narrowly scoped HTTP trigger for Wagtail's
`publish_scheduled` management command. It avoids a paid Render Cron service.

## 1. Configure the shared secret on Render

Generate a cryptographically random secret of at least 32 characters, for example
with Python:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

In the Render dashboard, open the `nebula-vault` web service, then
**Environment** and add:

- Key: `WAGTAIL_CRON_SECRET`
- Value: the generated secret

Save the change. Render will restart/redeploy the web service. Never commit the
secret to Git or place it in the request URL.

## 2. Create the free cron-job.org task

Create an account at https://console.cron-job.org/signup and add a job with:

- URL: `https://mydigigi.ir/internal/cron/wagtail/publish-scheduled/`
- Schedule: every hour (minute 0)
- Request method: `POST`
- Request header: `Authorization: Bearer YOUR_WAGTAIL_CRON_SECRET`
- Request body: empty
- Enable failure notifications.

Use the exact same secret value configured on Render. Keep it only in the
provider's custom-header field; do not append it to the URL.

## 3. Verify

Use cron-job.org's **Test run**. A successful response is HTTP 200 with JSON
containing `"status": "ok"`. HTTP 403 means the header/secret is incorrect;
HTTP 503 means the Render environment variable is missing or too short;
HTTP 409 means another publishing run is already active; HTTP 500 means the
Django command failed (the detailed exception is retained in Render logs).

The endpoint accepts POST only, does not require a browser session or CSRF
cookie, compares the bearer secret in constant time, and never returns the
secret. PostgreSQL advisory locking prevents overlapping publishing runs
across web workers.

cron-job.org documents that jobs can run hourly (or as often as once a minute),
accept custom headers and POST requests, and are free of charge. Its HTTP
execution timeout is 30 seconds, so the Wagtail command should finish promptly.
