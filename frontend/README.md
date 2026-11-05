# Front-end source architecture

## CSS source of truth

Edit CSS modules under `frontend/css/`. Files are grouped by feature and carry a numeric prefix to make cascade order explicit.

- `frontend/css/site/` contains the foundational public-site styles, authentication, storefront/dashboard styling, commerce/account rules, and shared visual utilities.
- `frontend/css/experience/` contains the extended storefront experience, authentication and dashboard refinements, navigation/effects, responsive layouts, dashboard shell, and header effects.

The modules are assembled into the existing static files:

- `static/portal/css/site.css`
- `static/portal/css/unified-experience.css`

These generated files remain the browser-facing assets. Their URLs and their order in `templates/portal/base.html` are intentionally unchanged, so this refactor does not add stylesheet requests or alter the cascade contract.

## Commands

Regenerate the committed bundles after editing source modules:

```bash
python scripts/build_frontend_css.py --write
```

Validate that generated files match the source modules:

```bash
python scripts/build_frontend_css.py --check
```

Run all front-end formatting and validation checks:

```bash
npm run format
npm run check:frontend
```

Render runs the bundle check before collecting static files. A stale or missing generated bundle therefore fails the build instead of silently deploying mismatched CSS.

## Cascade and maintenance rules

1. Preserve the declared module order in `scripts/build_frontend_css.py`; order is part of the site's CSS architecture.
2. Keep page-specific and breakpoint-specific rules in the feature that owns them.
3. Do not remove repeated selectors solely because they look similar. Review specificity, media-query scope, load order, and all supported viewport sizes first.
4. Prefer design tokens and scoped selectors over new `!important` declarations.
5. Keep the public Django templates and static URL contract stable unless a separate browser-tested change explicitly requires otherwise.
6. Django Admin styles and email templates remain outside this public-front-end refactor.
