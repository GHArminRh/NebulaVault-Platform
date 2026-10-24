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
- `static/portal/js/rich_text_editor.js` and `static/portal/css/rich_text_editor.css`: reusable custom dependency-free Nebula Vault rich text editor
- `templates/portal/`: server-rendered pages

## Native rich-text editing

- Implemented in-house with vanilla JavaScript, HTML, and CSS. It does not load CKEditor, another editor runtime, or third-party editor scripts.
- Enhances eligible portal and Django Admin textareas while preserving the original submitted field; observes dynamically added form fields.
- Includes undo/redo, emphasis, headings, font size, text/highlight colors, alignment, lists, links, block quotes, horizontal rules, tables, and HTML source mode.
- JSON, payload, metadata, config, query, code, and SQL fields are excluded; individual fields can opt out with `data-no-rich-editor`.
- Client-side cleanup is not a security boundary. Sanitize stored rich HTML server-side before rendering it to other users; never mark arbitrary database content as safe.

## Validation

The new `portal.tests.PortalPageTests` covers public page rendering, login protection, registration, trial activation, and the pending-order boundary. Run the full project suite in the configured Django environment:

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

The branch was authored against the existing project structure; run these checks in the repository's configured environment before merging.
