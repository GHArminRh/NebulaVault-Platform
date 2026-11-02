# Deploy Nebula Vault on Render

This branch adds a Render Blueprint for the Django project. It does not deploy the service by itself.

## Deploy

1. Sign in to Render and connect the GitHub account that can read `GHArminRh/NebulaVault-Platform`.
2. In Render, choose **New + → Blueprint** and select this repository.
3. Select branch `deploy/render-ready` and apply the Blueprint from `render.yaml`.
4. Wait for the web service and PostgreSQL database to finish provisioning. Render will generate `DJANGO_SECRET_KEY` automatically.
5. Open the service URL ending in `.onrender.com`. Check the deploy logs if the health check fails.

## Important production setup

- The Blueprint intentionally keeps Zarinpal disabled and sandbox mode enabled. Before accepting payments, configure and test `ZARINPAL_MERCHANT_ID`, set `ZARINPAL_SANDBOX` to the intended mode, and explicitly enable `ZARINPAL_ENABLED`.
- To send real email, add `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and any provider-specific SMTP settings in Render's Environment page. Do not commit secrets to GitHub.
- If you add a custom domain, update `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in the Render environment to include that domain.
- To enable privacy-gated Google Analytics 4, create a GA4 Web data stream for your public domain and set its Measurement ID as `GA4_MEASUREMENT_ID` in the Render service environment. The public site shows a consent notice first; Google Analytics is not loaded unless the visitor opts in. Do not put the Measurement ID in source-controlled secrets or send account identifiers, emails, passwords, verification tokens, or license keys to Analytics.
- The free Render PostgreSQL database is for testing and has a limited lifetime. Do not rely on it for permanent customer, license, billing, or audit data; plan a paid database and backups before production.
- The free web service uses an ephemeral filesystem. Files uploaded to `MEDIA_ROOT` (for example release installers) can disappear after redeploy/restart. Before relying on downloads in production, move media/uploads to object storage or another persistent storage solution.
- Render free services may sleep when idle, so the first request after inactivity can be slow.
- After first deployment, create an administrator account from the Render Shell using `python manage.py createsuperuser`.

## What this branch changes

- Adds Gunicorn, WhiteNoise, and `dj-database-url`.
- Supports Render's `DATABASE_URL` while preserving the existing local `DB_NAME` / `DB_USER` / `DB_PASSWORD` configuration.
- Defaults Django debug mode to off, configures HTTPS proxy handling and secure cookies, and serves collected static files through WhiteNoise.
- Adds a Render Blueprint and build script.
