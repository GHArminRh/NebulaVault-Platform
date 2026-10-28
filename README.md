# Nebula Vault Platform

Nebula Vault is a Django application for the Persian-language customer portal, product catalog, subscriptions, billing, and license management. The Django administration interface remains the standard English Django admin.

## Main components

| Path | Responsibility |
| --- | --- |
| `config/` | Django settings, URL routing, WSGI/ASGI entry points, and shared admin helpers |
| `accounts/` | Customer accounts, email verification, password reset, authentication, and account security |
| `staff/` | Staff identity and Django permissions; staff accounts are separate from customer accounts |
| `portal/` | Public/customer pages, shared context, middleware, and template tags |
| `catalog/` | Products, plans, releases, and rich-text content |
| `subscriptions/` | Trials, subscriptions, and renewals |
| `billing/` | Orders, payment attempts, cart checkout, and Zarinpal integration; `services.py` preserves the public service imports while implementations are separated into `order_services.py`, `attempt_services.py`, and `finalization_services.py` |
| `licensing/` | License issuance and license lifecycle |
| `audit/`, `devices/`, `notifications/` | Supporting Django apps; keep installed until references and migrations are audited |
| `templates/` | Shared site and Django admin templates |
| `static/` | Shared CSS, JavaScript, and images |
| `docs/` | Setup, deployment, and feature documentation |
| `tools/` | Development/test utilities; not part of the public request path |

## Requirements

- Python 3.11 or newer (use a version supported by the deployed dependencies)
- PostgreSQL for the configured application database
- Environment variables described in `.env.example`

## Local development (PowerShell)

1. Create and activate a virtual environment:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Create a local `.env` from `.env.example` and set a unique `DJANGO_SECRET_KEY` plus the PostgreSQL connection variables. Never commit `.env`.

4. Run database migrations and checks:

   ```powershell
   python manage.py migrate
   python manage.py check
   python manage.py test
   ```

5. Start the local development server:

   ```powershell
   python manage.py runserver
   ```

For the guided Windows launcher, see [Local Windows setup](docs/LOCAL_WINDOWS_SETUP.md).

## Configuration and deployment

- Render setup: [RENDER_DEPLOY.md](RENDER_DEPLOY.md)
- Email setup: [docs/email-setup.md](docs/email-setup.md)
- Zarinpal setup: [docs/zarinpal-setup.md](docs/zarinpal-setup.md)
- Signed offline license leases: [docs/signed-offline-license-leases.md](docs/signed-offline-license-leases.md)
- Project structure and safe refactoring plan: [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)

## Safe change policy

- Make structural refactors on a feature branch and review the diff before merging.
- Do not delete or regenerate migrations as a cleanup step.
- Do not change URL names, model fields, payment behavior, license contracts, or staff/admin behavior as part of formatting-only work.
- Keep secrets, production database contents, and uploaded customer files out of Git.
- Run `python manage.py check`, the relevant tests, and migration consistency checks before deployment.

## Deployment note

The Render Blueprint contains environment defaults intended for the repository's existing deployment setup. Review `render.yaml` and Render environment values before changing production payment or email settings.
