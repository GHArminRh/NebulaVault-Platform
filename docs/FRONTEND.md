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

## Rich-text editor

- A custom in-house editor with a CKEditor-inspired classic editing layout: menu bar, grouped multi-row toolbar, color palettes, contextual selection toolbar, dialogs, element path, word/character counts, and fullscreen/source views. It does not load CKEditor or a third-party editor runtime.
- Core tools include undo/redo, paragraph styles and headings, bold/italic/underline/strikethrough, subscript/superscript, font family/size, text/highlight colors, alignment, lists, indentation, links, image URLs and secure image-file uploads with alternative text/captions, sandboxed YouTube/Vimeo embeds, table insertion and row/column operations, block quotes, code blocks, horizontal/page breaks, special characters, find/replace, import/export HTML, block boundaries, direction controls, print, and keyboard shortcuts.
- Uses an explicit field allowlist instead of turning every textarea into HTML. The current model fields enabled by default are `description` and `release_notes`; other forms can opt in with `data-rich-editor` or `.rich-text`. JSON, credentials, code, and other non-prose fields remain plain text.
- Textareas remain the submitted form fields. Source mode and visual mode are synchronized before form submission; HTML is cleaned before it leaves the editor.
- A server-side `nh3` allow-list sanitizer is applied when product descriptions/release notes are saved and again when product-description HTML is rendered. Scripts, event-handler attributes, embedded frames, and unapproved CSS are not allowed. The client-side sanitizer is not treated as a security boundary.
- Office/PDF conversion, track changes, comments, revision history, and real-time multi-user collaboration are not implemented in this custom editor yet; those require additional document/conversion and collaboration infrastructure. AI features are intentionally excluded.

## Validation

The new `portal.tests.PortalPageTests` covers public page rendering, login protection, registration, trial activation, and the pending-order boundary. Run the full project suite in the configured Django environment:

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

The branch was authored against the existing project structure; run these checks in the repository's configured environment before merging.
