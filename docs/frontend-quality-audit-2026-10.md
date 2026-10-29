# Front-end quality audit — 29 October 2026

## Scope reviewed

This pass inspected the public portal's shared template, home page, primary stylesheets, browser JavaScript, and PWA entry point on the deploy/render-ready branch:

- templates/portal/base.html and templates/portal/home.html
- static/portal/css/site.css
- static/portal/css/unified-experience.css
- static/portal/css/responsive-system.css
- static/portal/css/blog.css
- static/portal/css/cms-builder.css
- static/portal/js/site.js and static/portal/js/pwa.js

This is a source-level audit, not a claim that every route has been exhaustively exercised in every browser. The production app is Django-rendered and the repository does not currently have a Node package.json or an evident front-end lint/test workflow.

## Confirmed issues and corrections in this change

1. **Page progress completion was capped at 94%.** The setter capped every value at 94, including the completion call. Completion now explicitly permits 100, so the visual indicator and aria-valuenow can report the actual finished state.
2. **Mobile menu button semantics were incomplete.** The menu toggle now has type="button", a stable ID, and aria-controls; the controlled navigation has the matching ID.
3. **Global shell CSS was embedded in two inline style blocks.** These rules now live in static/portal/css/site-shell.css, in the same cascade position relative to the generated CMS CSS block. This separates presentation from the Django template.
4. **Global color tokens were declared twice.** The final values were consolidated into the first :root block in site.css; the redundant later token block and equivalent body background override were removed. The effective token values remain the same.
5. **PWA failure handling was too silent/fragile.** Rejected install-prompt calls now fall back to browser-specific installation guidance. Service-worker registration remains non-blocking, but failures are visible in the local development console.

## Structural findings requiring careful follow-up

### CSS cascade and duplication

A static selector scan found repeated selector groups in all major stylesheets. Approximate counts from the current source were:

| File | Repeated selector groups | !important occurrences found by text scan |
|---|---:|---:|
| site.css | 119 | 9 |
| unified-experience.css | 125 | 424 |
| responsive-system.css | 32 | 146 |
| blog.css | 12 | 4 |
| cms-builder.css | 1 | 2 |

Repeated selectors can be appropriate across media queries, so these figures are indicators, not a list of defects. The strongest maintainability concern is unified-experience.css: it contains successive override/fix sections (including responsive hardening and dashboard rail fixes) and relies heavily on !important. Blindly deleting those rules could reintroduce the mobile overflow or break dashboard navigation. Consolidation should be done by component/breakpoint and verified with browser-level visual regression tests.

### Readability and component ownership

- base.html contains repeated cart-preview markup for authenticated and anonymous states. Consider extracting a shared include after validating context dependencies.
- Several CSS files mix compact, single-line rules with formatted blocks. Standardizing formatting is valuable, but should be done as a dedicated formatting-only change so behavioral changes remain reviewable.
- The responsive styles are split across the base stylesheet, unified experience layer, and responsive system. The source order is currently part of the behavior; document and gradually reduce cross-file overrides instead of adding more late fixes.
- Some styles intentionally override earlier design tokens/rules. Their purpose should be documented or moved to a single component-owned rule during the next consolidation pass.

### JavaScript and accessibility

- The inspected scripts do not use eval, document.write, or innerHTML; they contain no inline event-handler attributes. The starfield respects reduced motion and background-tab visibility.
- The mobile menu now exposes its controlled element explicitly. Continue testing keyboard operation, focus visibility, reduced motion, zoom/reflow, and color contrast on public pages and account flows.
- The starfield and ambient pointer effects are decorative; retain their reduced-motion and touch-device safeguards.

## Recommended verification gate for the next consolidation pass

1. Add a front-end lint baseline (CSS parser/linter and JavaScript syntax/lint checks) compatible with this Django repository.
2. Add browser smoke tests for home, login/register, product detail, cart, blog, and dashboard at narrow mobile, tablet, and desktop widths.
3. Capture visual baselines before consolidating repeated CSS. Check for horizontal overflow and keyboard/focus regressions.
4. Consolidate one component at a time, review computed styles at affected breakpoints, and remove only rules proven redundant.
5. Keep Django admin styles isolated from public-site CSS.

## Second pass: inline behavior and page-level separation

The second pass expanded the inspection to account verification, authentication, the dashboard license section, comments, and the offline fallback:

- Cloudflare Turnstile was being loaded twice from the shared login/register fragment. There is now one provider script with explicit rendering, and the initialization callback is in `static/portal/js/auth-turnstile.js`.
- The license-key copy button no longer contains an inline event handler. Its behavior is isolated in `static/portal/js/dashboard.js`, with visible copy-success/failure feedback.
- The dashboard template had multiple inline style attributes for license layout and key presentation. They now use semantic classes and `static/portal/css/dashboard.css`; the base template exposes an `extra_css` block for page-owned styles.
- Comment reply toggles and delete-confirmation behavior are in `static/portal/js/comments.js`. The reply toggle exposes `aria-controls` and `aria-expanded`, and delete confirmation uses a data attribute rather than an inline submit handler.
- Email resend cooldown logic is in `static/portal/js/email-code-resend.js`. Both verification and reset forms expose their purpose and email through data attributes.
- The offline fallback uses a normal link for retry instead of an inline `onclick` handler. Inline CSS remains inside the generated offline response intentionally so it stays readable when the network is unavailable.
- Feature-specific code has been removed from the shared `site.js` bundle where dedicated entry points are more appropriate.

A text search did not find a committed reference to `static/portal/js/language.js` in the scanned source, so it is flagged as a possible unused asset but was **not deleted**: confirm whether it is loaded through CMS/plugin content or another runtime path before removal.

## Change boundary and remaining work

The fixes above cover confirmed defects and maintainability problems in the inspected flows. They are not represented as an exhaustive audit of every possible browser state or every CMS-managed page. The broader legacy CSS cascade is still the main cleanup target: `unified-experience.css` and `responsive-system.css` have accumulated late overrides and many `!important` declarations. That cleanup should happen component-by-component, after browser-level visual baselines and smoke tests exist, so the working mobile overflow fix and dashboard rail behavior are not regressed.

The repository did not previously have a dedicated front-end syntax-check workflow. A lightweight CI check is being added for JavaScript syntax without requiring a separate Node build for the Django application.
