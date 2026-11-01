# Wagtail CMS — Nebula Vault

Wagtail is integrated into the existing Django project. The existing storefront,
customer accounts, API, billing, staff model, and Django administration remain
in place.

## Open the CMS

- CMS: `/cms/`
- Existing Django administration: `/admin/`
- Public site: `/`
- Wagtail-managed content pages: their published slug at the site root (for example, `/about/`).

Sign in to Wagtail with the existing active staff superuser account. The project
keeps its existing staff login model; no second administrator account or new
password is required. The Django admin login and its English interface remain
separate and unchanged.

## Edit the existing homepage

1. Open **Pages** in the Wagtail sidebar.
2. Open the page named **صفحه اصلی نبیولا والت**.
3. Select **Edit**.
4. Update the hero eyebrow, title, highlighted title, description, primary
   button label/link, or the additional rich-text content.
5. Preview the draft, then publish it.

The existing storefront layout, product/plan/release data, blog listing, account
links, and other dynamic sections are still rendered by the original templates.
Wagtail controls the editable homepage copy and the additional editorial block;
it does not replace the storefront with a generic Wagtail starter theme.

## Create ordinary content pages

1. From **Pages**, select the homepage or another content page.
2. Choose **Add a child page → صفحه محتوایی**.
3. Enter the page title, short introduction, and body.
4. Preview and publish.

Published content pages use their normal root-relative Wagtail URLs (for example,
`/about/`); this keeps Wagtail previews and canonical links aligned. The editor supports headings,
links, lists, quotes, images, documents, and approved embeds.

## Manage the existing blog

Use **مقالات وبلاگ** and **برچسب‌های وبلاگ** in the Wagtail sidebar. These are
the existing `BlogPost` and `Tag` records, not a parallel blog database. Existing
articles, tags, comments, ratings, and API endpoints remain attached to the
same models. The blog editor is intentionally limited to rich-text features
that are compatible with the existing HTML sanitizer.

## Images and documents

Use Wagtail's **Images** and **Documents** libraries for assets inserted into
Wagtail page rich text. The Wagtail image library creates image renditions and
supports image metadata. Documents are managed through the document library.

The legacy blog cover-image field remains compatible with existing media files
and is not destructively converted to a different database field.

## Wagtail roles and permissions

The project's existing UUID-backed **Staff & Permissions** groups are preserved.
Wagtail page/document permissions use a separate Django-group relationship on
staff users. Manage Wagtail permissions through Wagtail's **Users** and
**Groups** sections; assign editors to the required Wagtail groups and grant
those groups access to the relevant page tree or media collections.

The existing Django admin still uses the project's original staff groups.

## Production storage requirements

The current Render service is on the Free plan. Its local filesystem is
ephemeral: uploaded files stored locally can disappear after a restart,
spin-down, or redeploy. Do not use local media storage for production uploads.

The project is prepared for Cloudflare R2 through its existing
`django-storages` S3-compatible backend. To connect it:

1. In Cloudflare, open **Storage & databases → R2** and create a Standard
   bucket, for example `nebula-vault-media`.
2. Under **Manage in API Tokens**, create an R2 token with **Object Read &
   Write** permission, scoped to this bucket only. Keep the Access Key ID and
   Secret Access Key private; the secret is shown only once.
3. Copy the account's S3 API endpoint. For a regular R2 bucket it has the form
   `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`. The S3 region is
   `auto`; the project detects this automatically for R2 endpoints unless
   `AWS_S3_REGION_NAME` is explicitly set.
4. For public website assets, connect a custom domain to the bucket under
   **Bucket → Settings → Custom Domains**. For this site,
   `media.mydigigi.ir` is the suggested hostname, provided
   `mydigigi.ir` is managed in the same Cloudflare account. Cloudflare's
   `r2.dev` address is intended for non-production use.
5. In the Render service's environment settings, set:
   - `MEDIA_STORAGE_BACKEND=s3`
   - `AWS_STORAGE_BUCKET_NAME=nebula-vault-media`
   - `AWS_ACCESS_KEY_ID=<R2 Access Key ID>`
   - `AWS_SECRET_ACCESS_KEY=<R2 Secret Access Key>`
   - `AWS_S3_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
   - `AWS_S3_REGION_NAME=auto`
   - `AWS_S3_CUSTOM_DOMAIN=media.mydigigi.ir` (or the exact active R2
     custom domain, without `https://`)
   - `AWS_QUERYSTRING_AUTH=False`

The R2 bucket must be publicly readable through its custom domain for public
website images and documents. Keep the S3 API credentials scoped to the single
bucket and never put them in Git or ordinary application logs. The Django
settings now fail at startup instead of silently falling back to ephemeral
local storage when S3 storage is explicitly enabled but its credentials are
missing. For R2, they also reject unsigned public URLs when no public domain
has been configured.

After adding the Render variables, deploy and test an actual upload, public
read, delete, and persistence across a service restart/redeploy. The Wagtail
image and document libraries share this configured media storage. Private or
confidential files should not be placed in this public media bucket.

The current Render PostgreSQL database is also a Free instance scheduled to
expire on **26 November 2026**. Upgrade/replace it and take a tested backup
before relying on it for long-term CMS content, customer, billing, or license
data. The deployment does not automatically upgrade either resource or incur
additional cost.

## Deployment

The Render service tracks `deploy/render-ready` and automatically deploys new
commits to that branch. Keep CMS changes on a feature branch and merge them
after the Django checks, migrations checks, and CMS tests pass. The service's
startup command applies committed migrations before launching Gunicorn.
