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
- `static/portal/js/ckeditor_integration.js` and `static/portal/css/ckeditor_integration.css`: CKEditor 5 Free-plan integration; the core bundle is loaded from the CKEditor CDN, and the premium bundle is loaded only when Cloud Services document export is explicitly configured.
- `templates/portal/`: server-rendered pages.

## Rich-text editor

- The editor uses CKEditor 5 version 48.5.1 from the official CDN and the **Free commercial plan**. The production license key is read from `CKEDITOR_LICENSE_KEY`; do not commit account-specific values to Git.
- The Free plan is cloud-hosted, includes up to 1,000 editor loads per month, and includes 5 Word exports and 5 PDF exports per month. It displays the CKEditor watermark. Usage beyond the included allowance may cause read-only behavior when no payment method is on file; review current plan terms in the CKEditor Customer Portal.
- Configure `CKEDITOR_LICENSE_KEY` in the server environment using the production key shown under **CKEditor 5 Free** in the Customer Portal. The `.env.example` file documents the variable names; do not paste the actual key into tracked files.
- The basic editor does not load premium-only controls such as Track Changes, Import from Word, Format Painter, multi-level lists, footnotes, bookmarks, page breaks, HTML Embed, table of contents, templates, or inline-style export.
- Export to Word/PDF is part of the Free plan but uses Cloud Services. Those buttons are shown only when `CKEDITOR_CLOUD_SERVICES_TOKEN_URL` is configured with the appropriate **production** token URL from the Customer Portal's **Cloud environments / Access credentials** section. The previous Builder `/token/dev/` URL is deliberately not reused. Without this URL, the core editor still works and the export buttons are hidden.
- The editor is attached only to the existing rich-text allowlist: `description`, `release_notes`, and explicitly opted-in fields via `data-rich-editor` or `.rich-text`. JSON, credentials, code, and other non-prose fields remain plain text.
- The underlying textarea remains the submitted form field. Editor changes are synchronized back to it, including immediately before form submission.
- Image upload uses the existing staff-only `/admin/editor-upload/` endpoint, which validates and re-encodes uploaded images. The server-side `nh3` allow-list sanitizer remains active when product descriptions/release notes are saved and rendered; client-side editing is not treated as a security boundary.
- CDN availability is required for the editor to load. Consult the official [CKEditor pricing page](https://ckeditor.com/pricing/) and [license activation guide](https://ckeditor.com/docs/ckeditor5/latest/getting-started/licensing/license-key-and-activation.html) before changing the plan.


## Validation

The new `portal.tests.PortalPageTests` covers public page rendering, login protection, registration, trial activation, and the pending-order boundary. Run the full project suite in the configured Django environment:

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

The branch was authored against the existing project structure; run these checks in the repository's configured environment before merging.

### CKEditor troubleshooting

- If the editor remains a plain textarea and a notice says the editor is not enabled, this is expected until the project-root `.env` contains `CKEDITOR_LICENSE_KEY=<your CKEditor 5 Free production key>`. `.env.example` is documentation only; Django does not automatically read values from that file. Restart the Django process after editing `.env`.
- If the key is present but the editor does not load, inspect the browser Console and Network panels for CDN, licensing, CSP, or script errors. The integration now shows an on-page notice for missing configuration and a visible error if CDN loading fails.
