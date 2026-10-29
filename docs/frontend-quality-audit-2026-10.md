# Front-end quality audit — 29 October 2026

## Scope reviewed

This pass inspected the public portal's shared template, home page, primary stylesheets, browser JavaScript, and PWA entry point on the deploy/render-ready branch:

- shared public templates, error pages, account forms, dashboard, orders, payment result, CMS media plugins, and blog/comment templates
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
| site.css | 117 | 9 |
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

- The inspected JavaScript assets do not use `eval`, `document.write`, or `innerHTML`. The audited public template interactions have been moved away from inline event-handler attributes. The Django Admin templates are deliberately left unchanged, and email-message templates retain inline CSS for compatibility with email clients. The starfield respects reduced motion and background-tab visibility.
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
- Styles were also extracted from the order list, payment-result page, and error-page fragment. CMS media templates now use reusable component classes in `cms-builder.css` instead of repeated inline styling.
- The page-specific CSS block is rendered after CMS-generated CSS so its narrowly scoped styles can override shared defaults as intended.
- Feature-specific code has been removed from the shared `site.js` bundle where dedicated entry points are more appropriate.

The legacy `static/portal/js/language.js` file was removed after confirming that the shared base template did not load it and the scanned templates contained no language-toggle references. The public interface is rendered in Persian; keep site language behavior in Django/template code rather than an unreferenced client-side translation map.

## Change boundary and remaining work

The fixes above cover confirmed defects and maintainability problems found while scanning the 56 HTML templates under the main template directories. The scan uses source-level checks; it is not represented as an exhaustive audit of every browser state or every CMS-managed page. A number of legacy page templates are still compressed onto one line; formatting them should be done in an isolated follow-up to keep whitespace-sensitive markup and behavioral changes reviewable. The broader legacy CSS cascade is still the main cleanup target: `unified-experience.css` and `responsive-system.css` have accumulated late overrides and many `!important` declarations. That cleanup should happen component-by-component, after browser-level visual baselines and smoke tests exist, so the working mobile overflow fix and dashboard rail behavior are not regressed.

The repository now has dedicated source-formatting and front-end validation workflows. The quality workflow runs Prettier checks, Djlint checks, JavaScript syntax validation, ESLint, and a source-level Django template/asset audit. The formatting workflow is manually invoked to prevent overlapping auto-format commits from racing with normal development.


## Comprehensive audit pass (29 October 2026)

### Fixes made during browser-driven verification

- Added an automated Playwright suite covering route smoke checks, same-origin CSS/JS loading, JavaScript page errors, RTL/Persian document metadata, horizontal overflow at 320, 375, 768, and 1280 CSS pixels, and WCAG A/AA axe checks on core public pages.
- The first browser run against the then-deployed baseline found an overflow on the home page at 1280px (document scroll width 1450px for a 1280px viewport), a low-contrast footer label and authentication security note, and an invalid ARIA label on the Turnstile wrapper. The source now clips root-level horizontal overflow with `overflow-x: clip`, adjusts the two muted text colors to `#8292b1`, and gives each Turnstile wrapper a `group` role. These changes remain pending verification against a deployment containing the fixes; the earlier failure is recorded rather than represented as a pass.
- Extracted the identical cart preview from both authenticated and anonymous header states into `templates/portal/_cart_nav.html`, keeping its context and rendered content shared.
- Public navigation now handles malformed URL fragments without allowing `decodeURIComponent` exceptions to abort page initialization.
- Removed exact duplicate CSS blocks only where selector, declarations, and media context all matched. Selector repeats with different declarations remain because they are part of the established responsive cascade.

### Validation status and remaining risk

The maintenance branch now includes browser automation and source-quality tooling, but a successful browser run on the post-fix deployed build is the acceptance gate. The largest technical-debt area remains `unified-experience.css`: it has many late overrides and `!important` declarations tied to dashboard-rail stacking, mobile navigation, and previously fixed viewport overflow. Do not delete or combine those rules in bulk. Reduce them by component and breakpoint only when browser tests and visual comparison prove the result unchanged.

Django Admin templates and email templates were intentionally excluded from public-interface formatting; email templates retain inline styling for email-client compatibility. CMS-managed pages and routes requiring an authenticated session need additional manual review beyond the public-route smoke tests.
