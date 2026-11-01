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
spin-down, or redeploy. Before using the CMS for production uploads, configure
the existing S3-compatible media-storage settings in Render:

- `MEDIA_STORAGE_BACKEND=s3`
- `AWS_STORAGE_BUCKET_NAME`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- Optional: `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL`,
  `AWS_S3_CUSTOM_DOMAIN`, and `AWS_QUERYSTRING_AUTH`

Never put storage credentials in Git. Alternatively, move the Render web
service to a paid plan and attach a persistent disk, then ensure its mount path
matches the configured `MEDIA_ROOT`.

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
