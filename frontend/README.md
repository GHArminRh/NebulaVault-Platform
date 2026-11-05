# Front-end source architecture

## CSS source of truth

Edit CSS modules under `frontend/css/`. Files are grouped by feature and carry a numeric prefix to make cascade order explicit.

- `frontend/css/site/` separates the global shell, homepage hero and sections, catalog pages, dashboard, authentication/messages, responsive rules, and visual utilities into ordered feature modules.
- `frontend/css/experience/` contains the extended storefront experience, authentication/dashboard refinements, navigation/effects, general responsive layouts, navigation-specific responsive rules, dashboard responsive rules, dashboard shell, and header effects.

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

## Other stylesheets

The source modules above deliberately cover only the two large shared bundles. The remaining stylesheets keep their current, focused roles:

- `tokens.css` owns shared design tokens and loads before the site foundation.
- `responsive-system.css` remains the final shared responsive override layer in the public base template.
- `site-shell.css`, `page-transitions.css`, and `form-icons.css` stay separate because they have independent shared responsibilities.
- `blog.css`, `search.css`, `dashboard.css`, and other page/component styles remain conditionally loaded by their owning templates.

Avoid moving these files into the generated bundles unless their ownership, load order, and browser behavior are explicitly reviewed. The goal is clearer source ownership without turning the site into a larger number of network requests.

## Cascade and maintenance rules

1. Preserve the declared module order in `scripts/build_frontend_css.py`; order is part of the site's CSS architecture.
2. Keep page-specific and breakpoint-specific rules in the feature that owns them.
3. Do not remove repeated selectors solely because they look similar. Review specificity, media-query scope, load order, and all supported viewport sizes first.
4. Prefer design tokens and scoped selectors over new `!important` declarations.
5. Keep the public Django templates and static URL contract stable unless a separate browser-tested change explicitly requires otherwise.
6. Django Admin styles and email templates remain outside this public-front-end refactor.
