# Nebula Vault App Licensing

## Architecture

The `licensing` Django app owns license records, one-time key issuance, device activations, and a JSON API for the desktop client. A license belongs to exactly one subscription; its expiry and product entitlement are derived from that subscription and related product/plan.

## Key security

- Keys are generated with cryptographically secure randomness and are stored only as SHA-256 digests. The full key is shown once in a dedicated Django Admin notice after creation; it is held temporarily in the server-side session, not stored in the database or a cookie-based success message.
- Device fingerprints are hashed before storage. Use a stable, app-generated identifier; do not send raw hardware serial numbers or other sensitive hardware data.
- API requests are JSON POST only. Request bodies are capped at 16 KB and rate-limited per client IP using Django's cache. Use a shared production cache such as Redis for limits shared across workers.
- Always serve the API over HTTPS. A desktop client cannot keep a distributed shared secret confidential; do not embed a server secret in the application.

## API

Base path: `/api/licensing/`

- `POST activate/` — `license_key`, `device_fingerprint`, optional `device_name`, optional `app_version`. Creates or reactivates an activation within the plan's device limit.
- `POST validate/` — `license_key`, `device_fingerprint`, optional `app_version`. Checks an existing activation; it never activates a new device implicitly.
- `POST deactivate/` — `license_key`, `device_fingerprint`. Deactivates that device but does not revoke the license.

Successful responses include `license_id`, `status`, `expires_at`, `product`, `device_limit`, and `active_devices`. Failures include stable machine-readable `code` values. Invalid license and entitlement failures are returned as HTTP 403; malformed requests are HTTP 400; throttling is HTTP 429.

## Admin workflow

1. Create or select a valid subscription.
2. In **App Licensing**, add a license and select that subscription.
3. Copy the key from the one-time notice above the form. It cannot be recovered later because only its digest is stored.
4. Suspend or revoke the license from its admin record. The API rejects it on the next online check. Deactivating a device frees one activation slot.
5. If a key is lost or compromised, select exactly one license in the admin list and run **Rotate the selected license key**. The old key becomes invalid immediately and the replacement is shown once.

## Database setup and migrations

Several existing apps in this branch do not yet have checked-in initial migrations. For a development database, the current models can be synchronized with:

```powershell
python manage.py migrate --run-syncdb
```

Before a production release, generate initial migrations for all currently unmigrated apps together from the repository root:

```powershell
python manage.py makemigrations
```

Review and commit the generated migration files, then apply them with:

```powershell
python manage.py migrate
```

Do not generate a migration for `licensing` in isolation while its dependency apps remain unmigrated; Django must build a consistent migration graph across the related customer, catalog, subscription, and licensing models. The current execution environment does not have this repository checked out with its Python dependencies, so those generated migration files and a passing test run have not been verified here.

## Important limitation

This provides online licensing and device activation, not tamper-proof offline licensing. A desktop client must check the server response over HTTPS. Offline grace periods or signed offline licenses should be designed separately if required.
