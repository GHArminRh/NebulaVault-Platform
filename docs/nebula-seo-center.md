# Nebula SEO Center

## Current repository findings

- The project is on Django 5.2 and Wagtail 8.0.1.
- Public HTML currently has shared default description and Open Graph values in `templates/portal/base.html`.
- Blog posts already have `seo_title` and `seo_description`; product records do not yet have equivalent SEO fields.
- Wagtail's sitemap view is already mounted at `/sitemap.xml`. It needs to be extended or replaced carefully so public Django product and blog URLs are represented too.
- No project-owned `robots.txt` endpoint or file was found in the active branch tree.
- The `wagtail-seo` package currently advertises Wagtail support through version 7, while this project uses Wagtail 8.0.1. Do not add it until upstream explicitly supports Wagtail 8 and compatibility tests pass.

## Implementation principles

- Keep SEO tooling in a dedicated Django app named `seo`.
- Treat Google Search Console as the source of truth for search performance metrics.
- Keep crawl findings factual and actionable; do not present an invented SEO score as a Google ranking signal.
- Crawl only the configured public site origin. Never follow links to authentication, checkout, account, admin, API, or other private routes.
- Make audit runs bounded, rate-limited, observable, and safe to retry.
- Keep the existing storefront, product, blog, account, payment, licensing, and Wagtail behavior intact.
- Prefer first-party Django/Wagtail features and free/open-source components. Add paid APIs only as optional integrations.

## Planned phases

1. Audit persistence and admin visibility.
2. Safe same-origin crawler and technical checks.
3. SEO metadata integration for catalog products, blog posts, and Wagtail pages.
4. Correct combined sitemap, robots policy, and redirect diagnostics.
5. Google Search Console integration with explicit consent and token security.
6. Dashboard, history, scheduled reports, and regression tests.
7. Optional competitor and keyword research adapters.
