# Nebula SEO Center

## Current repository findings

- The project uses Django 5.2 and Wagtail 8.0.1.
- Public HTML currently has shared default description and Open Graph values in `templates/portal/base.html`.
- Blog posts already have `seo_title` and `seo_description`; product records do not yet have equivalent SEO fields.
- Wagtail Page has native SEO fields.
- The `/sitemap.xml` route currently uses Wagtail's sitemap view and does not yet explicitly cover all public Django catalog and blog URLs.
- Public `robots.txt` and a combined sitemap index now cover Wagtail pages, Django products, blog posts, and core public routes.
- Do not install `wagtail-seo` until it explicitly supports the project's Wagtail 8 release.

## Current implementation

- A dedicated `seo` Django app stores audit runs and individual findings.
- `python manage.py run_seo_audit` runs a bounded technical crawl against `SITE_BASE_URL`.
- The crawler reads robots.txt, discovers the combined sitemap index, follows same-origin public HTML links, and records metadata, heading, canonical, image-alt, duplicate-title, redirect, and HTTP findings.
- The crawler skips authentication, account, cart, checkout, billing, admin, CMS, API, and other sensitive route prefixes.
- It rejects cross-origin URLs and redirects, query-string variants, non-public resolved IP addresses, and oversized responses.
- Crawl limits include maximum pages, per-request timeout, response size, request delay, and total execution duration.

## Implementation principles

- Treat Google Search Console as the source of truth for search performance metrics.
- Keep crawl findings factual and actionable; do not present an invented SEO score as a Google ranking signal.
- Make audit runs bounded, rate-limited, observable, and safe to retry.
- Keep existing storefront, product, blog, account, payment, licensing, and Wagtail behavior intact.
- Prefer first-party Django/Wagtail features and free/open-source components. Add paid APIs only as optional integrations.

## Planned phases

1. Audit persistence and admin visibility. (implemented)
2. Safe same-origin crawler and technical checks. (implemented; tests added)
3. SEO metadata integration for catalog products, blog posts, and Wagtail pages. (product fields and social metadata implemented; Wagtail native metadata retained)
4. Correct combined sitemap, robots policy, and redirect diagnostics. (robots and sitemap endpoints implemented)
5. Google Search Console integration with explicit consent and token security.
6. Dashboard, history, scheduled reports, and regression tests.
7. Optional competitor and keyword research adapters.
