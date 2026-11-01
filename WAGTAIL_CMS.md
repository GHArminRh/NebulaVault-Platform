# Wagtail CMS — Nebula Vault

Wagtail is integrated into the existing Django project. The existing storefront,
customer accounts, API, billing, staff model, and Django administration remain
in place.

## Open the CMS

- CMS: `/cms/`
- Existing Django administration: `/admin/`
- Public site: `/`
- Wagtail-managed content pages: their published slug at the site root (for example, `/about/`).
- XML sitemap: `/sitemap.xml`

Sign in to Wagtail with the existing active staff superuser account. The project
keeps its existing staff login model; no second administrator account or new
password is required. The Django admin login and its English interface remain
separate and unchanged.

## Edit the existing homepage

1. Open **Pages** in the Wagtail sidebar.
2. Open the page named **صفحه اصلی نبیولا والت**.
3. Select **Edit**.
4. Update the hero eyebrow, title, highlighted title, description, primary
   button label/link, or the additional editorial content.
5. In **بخش‌های قابل چیدمان صفحه اصلی**, add, remove, or reorder StreamField
   blocks. The available blocks are heading, formatted text, image, card list,
   call to action, quote, notice, feature grid, FAQ, proof strip, product listing,
   blog listing, and release listing.
6. Preview the draft, then publish it.

The StreamField blocks render in their saved order after the hero section. The
previous feature cards, trust strip, FAQ, final call-to-action, and product,
blog, and release section headings are seeded into Wagtail and rendered from
StreamField rather than remaining hard-coded. The actual product, article, and
release records continue to come from the existing Django models; do not
duplicate product, pricing, release, order, or license records in Wagtail.

## Manage the global header and footer

Open **Settings → تنظیمات سربرگ و پابرگ** in Wagtail. This is a site-specific
setting for the current Wagtail site.

You can edit:
- Brand name, subtitle and symbol shown in the header and footer
- Desktop and mobile navigation links (the same menu is used in both places)
- Footer description, note, copyright text and footer links
- Whether the install-app button is shown

Each navigation item accepts an internal path, a page fragment, or an HTTPS
address. External links can optionally open in a new tab. If a settings record
has not been created yet, the public site keeps its existing navigation and
branding as a safe fallback.

Account controls such as login, registration, dashboard, cart and logout remain
application-controlled links. They are intentionally not arbitrary CMS links,
so changing site navigation cannot break authentication or checkout behavior.

## Create ordinary content pages

1. From **Pages**, select the homepage or another content page.
2. Choose **Add a child page → صفحه محتوایی**.
3. Enter the page title, short introduction, and body.
4. Add/reorder the available StreamField blocks.
5. Preview and publish.

Published content pages use their normal root-relative Wagtail URLs (for example,
`/about/`); this keeps Wagtail previews and canonical links aligned. The editor
supports headings, formatted text, lists, card groups, images, call-to-action
links, quotes, and notices. The legacy rich-text body remains available for
backward compatibility.

## SEO

Homepage and content-page SEO titles and search descriptions are connected to
the public HTML title, description, and Open Graph metadata. Complete these
fields in the page's Wagtail settings panel before publishing. The XML sitemap
is available at `/sitemap.xml`.

## Manage the existing blog

Use **مقالات وبلاگ** and **برچسب‌های وبلاگ** in the Wagtail sidebar. These are
the existing `BlogPost` and `Tag` records, not a parallel blog database.
Existing articles, tags, comments, ratings, and API endpoints remain attached
to the same models. The blog editor is intentionally limited to rich-text
features that are compatible with the existing HTML sanitizer.

The blog editor now uses Wagtail's native snippet revision and draft-state
mixins. Editors can save unpublished changes without replacing the currently
published article, inspect revision history, preview article content in the
site's existing design, publish/unpublish, and set a scheduled go-live or
expiry time in the Publishing panel. The legacy integer primary key, UUID,
slug, status, published_at, image field, tag relation table, comments, ratings,
API fields and public article URLs are retained. Existing published records
are migrated as live content; existing drafts remain unpublished.

For scheduled publication/expiry to run automatically, a periodic process
must execute `python manage.py publish_scheduled` (for example, a Render Cron
Job running every minute). The Wagtail editor can store schedules immediately,
but this repository change does not provision a separate Render service or
incur additional hosting cost. Until a scheduler is configured, publish and
unpublish actions can still be performed manually from the Wagtail editor.

## Images and documents

Use Wagtail's **Images** and **Documents** libraries for assets inserted into
Wagtail page rich text or StreamField blocks. The Wagtail image library creates
image renditions and supports image metadata. Documents are managed through the
document library.

The legacy blog cover-image field remains compatible with existing media files
and is not destructively converted to a different database field.

### Production object storage

The production media path uses the private Backblaze B2 bucket through the
S3-compatible Django storage backend. Keep the bucket **Private**.

When `MEDIA_STORAGE_BACKEND=s3` is selected, startup now fails if the bucket,
access key, secret key, region, or endpoint is missing. It does not silently
fall back to Render's ephemeral local filesystem. Never put storage credentials
in Git or share them in support messages.

Public Wagtail images are served through the same-origin Django media proxy.
Wagtail documents continue to use `serve_view` so collection permissions are
checked before a document is streamed. Do not use public image URLs for
confidential documents.

The B2 image upload and retrieval path has been verified after a Render
redeploy. Keep the private bucket configuration and proxy route intact.

## Wagtail roles and permissions

The project's existing UUID-backed **Staff & Permissions** groups are preserved.
Wagtail page/document permissions use a separate Django-group relationship on
staff users. Manage Wagtail permissions through Wagtail's **Users** and
**Groups** sections; assign editors to the required Wagtail groups and grant
those groups access to the relevant page tree or media collections.

The existing Django admin still uses the project's original staff groups.

## Deployment and data safety

The Render service tracks `deploy/render-ready` and automatically deploys new
commits to that branch. Keep CMS changes on a feature branch and merge them
after Django checks, production migration checks, Wagtail integration tests,
and frontend checks pass. The service's startup command applies committed
migrations before launching Gunicorn.

Before relying on the service for long-term CMS content, customer, billing, or
license data, confirm that the Render PostgreSQL plan and backup/retention
arrangements meet the required durability. Do not change plans or incur costs
without an explicit decision.
