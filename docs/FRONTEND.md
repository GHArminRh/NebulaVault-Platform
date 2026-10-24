# Nebula Vault Django portal

This branch adds a server-rendered Django frontend for the existing catalog, subscription, and billing models. It intentionally uses Django templates, CSS, and small vanilla JavaScript rather than introducing a separate frontend build system.

## Included routes

- `/`: landing page with active products and published releases
- `/products/` and `/products/<slug>/`: product catalog, plan details, published downloads, and trial entry point
- `/pricing/`: active plans from `catalog.Plan`
- `/accounts/login/`, `/accounts/logout/`, and `/register/`: Django session authentication and account creation
- `/dashboard/`: account overview
- `/subscriptions/`: the signed-in user's subscriptions
- `/orders/`: the signed-in user's orders
- `/trial/<slug>/`: POST-only trial activation through `subscriptions.services.start_trial`
- `/orders/create/<plan_id>/`: POST-only order creation through `billing.services.create_payment_order`

## Model and security boundaries

- Catalog pages only show active products/plans and published releases.
- Trial and order actions require login and POST + CSRF protection.
- Prices are sourced from the database; the browser never supplies an amount.
- Order/subscription queries are scoped to the signed-in user.
- The UI does not mark an order paid and does not simulate a payment. The current backend has no payment-provider checkout flow wired to the UI, so a new order remains pending until trusted server-side payment processing finalizes it.
- Download links are taken from published `catalog.Release` rows; configure only trusted release URLs in admin.
- The account registration form requires the unique email field on the custom `accounts.User` model.

## Assets

- `static/portal/css/site.css`: responsive dark, space-inspired design
- `static/portal/js/site.js`: mobile navigation, password visibility, dismissible messages, and subtle reveal transitions
- `static/portal/js/ckeditor_integration.js` and `static/portal/css/ckeditor_integration.css`: CKEditor 5 integration based on the supplied CKEditor Builder configuration; CKEditor 5 core and premium bundles are loaded from the CKEditor CDN.
- `templates/portal/`: server-rendered pages.

## Rich-text editor

- The previous in-house editor assets have been removed from the page templates and replaced with CKEditor 5 (version 48.5.1), using the supplied Builder-style classic editor and menu bar. AI tools, CKBox, presence, cloud comments, real-time collaboration, and revision-history UI are not enabled because they require separate services/configuration.
- The editor is attached only to the existing rich-text allowlist: `description`, `release_notes`, and explicitly opted-in fields via `data-rich-editor` or `.rich-text`. JSON, credentials, code, and other non-prose fields remain plain text.
- The underlying textarea remains the submitted form field. Editor changes are synchronized back to it, including immediately before form submission.
- Image upload uses the existing staff-only `/admin/editor-upload/` endpoint, which validates and re-encodes uploaded images. The server-side `nh3` allow-list sanitizer remains active when product descriptions/release notes are saved and rendered; client-side editing is not treated as a security boundary.
- The provided Builder license key is a temporary trial key and will expire; replace it with a valid key appropriate for your CKEditor plan before production use. CDN availability is required for the editor to load. Import/export Word/PDF and other premium features may also depend on CKEditor Cloud Services credentials and account entitlements.

## Validation

The new `portal.tests.PortalPageTests` covers public page rendering, login protection, registration, trial activation, and the pending-order boundary. Run the full project suite in the configured Django environment:

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

The branch was authored against the existing project structure; run these checks in the repository's configured environment before merging.
