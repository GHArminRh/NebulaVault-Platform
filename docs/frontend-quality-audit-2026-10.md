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

This is a source-level audit, not a claim that every route has been exhaustively exercised in every browser. The production app is Django-rendered; this change adds a dev-only Node package.json and repeatable front-end validation/browser-test workflows without changing the production build pipeline.

## Confirmed issues and corrections in this change

1. **Page progress completion was capped at 94%.** The setter capped every value at 94, including the completion call. Completion now explicitly permits 100, so the visual indicator and aria-valuenow can report the actual finished state.
2. **Mobile menu button semantics were incomplete.** The menu toggle now has type="button", a stable ID, and aria-controls; the controlled navigation has the matching ID.
3. **Global shell CSS was embedded in two inline style blocks.** These rules now live in static/portal/css/site-shell.css, in the same cascade position relative to the generated CMS CSS block. This separates presentation from the Django template.
4. **Global color tokens were declared twice.** The final values were consolidated into the first :root block in site.css; the redundant later token block and equivalent body background override were removed. The effective token values remain the same.
5. **PWA failure handling was too silent/fragile.** Rejected install-prompt calls now fall back to browser-specific installation guidance. Service-worker registration remains non-blocking, but failures are visible in the local development console.

## Structural findings requiring careful follow-up

### CSS cascade and duplication

A static selector scan found many repeated selector groups, most with different declarations or at different cascade points. After removing only exact selector/declaration duplicates within the same media context, the reviewed CSS files have no identical duplicate blocks. Current `!important` text counts are:

| File | `!important` occurrences found by text scan |
|---|---:|
| site.css | 9 |
| unified-experience.css | 420 |
| responsive-system.css | 146 |
| blog.css | 4 |
| cms-builder.css | 2 |
| site-shell.css | 1 |
| dashboard.css | 2 |
| orders.css | 0 |
| payment-result.css | 0 |
| **Total** | **584** |

Repeated selectors can be appropriate across media queries, so these figures are indicators, not a list of defects. The strongest maintainability concern is unified-experience.css: it contains successive override/fix sections (including responsive hardening and dashboard rail fixes) and relies heavily on !important. Blindly deleting those rules could reintroduce the mobile overflow or break dashboard navigation. Consolidation should be done by component/breakpoint and verified with browser-level visual regression tests.

### Readability and component ownership

- The header now uses a shared `templates/portal/_cart_nav.html` include for authenticated and anonymous states, so cart-preview markup is maintained in one place.
- Public CSS/JavaScript and most public templates have been normalized for readable diffs. The shared base and cart include are manually kept readable and excluded from Djlint because its formatter reports changes on every pass for these two files; the separate source audit still inspects them.
- The responsive styles are split across the base stylesheet, unified experience layer, and responsive system. The source order is currently part of the behavior; document and gradually reduce cross-file overrides instead of adding more late fixes.
- Some styles intentionally override earlier design tokens/rules. Their purpose should be documented or moved to a single component-owned rule during the next consolidation pass.

### JavaScript and accessibility

- The inspected JavaScript assets do not use `eval`, `document.write`, or `innerHTML`. The audited public template interactions have been moved away from inline event-handler attributes. The Django Admin templates are deliberately left unchanged, and email-message templates retain inline CSS for compatibility with email clients. The starfield respects reduced motion and background-tab visibility.
- The mobile menu now exposes its controlled element explicitly. Continue testing keyboard operation, focus visibility, reduced motion, zoom/reflow, and color contrast on public pages and account flows.
- The starfield and ambient pointer effects are decorative; retain their reduced-motion and touch-device safeguards.

## Recommended verification gate for the next consolidation pass

1. Re-run the Playwright browser suite after deployment and fix remaining real-device/browser findings.
2. Add authenticated-session browser coverage for dashboard, orders, subscriptions, and license copying after arranging a dedicated test account.
3. Capture visual baselines before consolidating remaining CSS cascade overrides. Review focus, keyboard use, reduced motion, zoom/reflow, and responsive layout at supported breakpoints.
4. Consolidate one component at a time and remove only rules proven redundant.
5. Keep Django Admin styles isolated from public-site CSS.

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

The legacy `static/portal/js/language.js` file has no committed reference in the scanned templates, but it is retained because CMS-managed or dynamic content could load it. Confirm runtime usage before any later removal. The public interface remains rendered in Persian.

## Change boundary and remaining work

The fixes above cover source-level issues found while scanning public templates and frontend assets. The repeatable source audit checks 48 public templates and 244 source files, but does not exhaustively exercise every CMS-managed page, authenticated state, browser, or viewport. The broader legacy CSS cascade remains the main technical-debt area: `unified-experience.css` still has hundreds of `!important` declarations associated with dashboard-rail stacking, mobile navigation, and earlier responsive hardening. Consolidate those rules only component-by-component after browser-level visual checks so the homepage overflow fix and dashboard navigation are not regressed.

The repository now has dedicated source-formatting and front-end validation workflows. The quality workflow runs Prettier checks, Djlint checks on stable public templates, JavaScript syntax validation, ESLint, and a source-level Django template/asset audit. The formatter runs on the maintenance branch with branch-level concurrency control and commits only when formatting changes are needed. Django Admin and email templates stay excluded; email templates retain inline styles for email-client compatibility.


## Comprehensive audit pass (29 October 2026)

### Fixes made during browser-driven verification

- Added an automated Playwright suite covering route smoke checks, same-origin CSS/JS loading, JavaScript page errors, RTL/Persian document metadata, horizontal overflow at 320, 375, 768, and 1280 CSS pixels, and WCAG A/AA axe checks on core public pages.
- The first browser run against the then-deployed baseline found an overflow on the home page at 1280px (document scroll width 1450px for a 1280px viewport), a low-contrast footer label and authentication security note, and an invalid ARIA label on the Turnstile wrapper. The source clips root-level horizontal overflow with `overflow-x: clip`, anchors the decorative left glow at the viewport edge to prevent RTL desktop scroll-width expansion, adjusts low-contrast muted labels to `#8292b1`, and gives each Turnstile wrapper a `group` role. The earlier failures are retained here as findings; the fixes were subsequently verified by the browser suite.
- Extracted the identical cart preview from both authenticated and anonymous header states into `templates/portal/_cart_nav.html`, keeping its context and rendered content shared.
- Public navigation now handles malformed URL fragments without allowing `decodeURIComponent` exceptions to abort page initialization.
- Removed exact duplicate CSS blocks only where selector, declarations, and media context all matched. Selector repeats with different declarations remain because they are part of the established responsive cascade.

### Validation status and remaining risk

The post-fix deployed build passed the browser suite on 29 October 2026: 22 tests passed, including route smoke checks, Persian RTL metadata, no horizontal overflow at 320, 375, 768, and 1280 CSS pixels, and serious/critical axe accessibility checks on six public pages. The largest technical-debt area remains `unified-experience.css`: it has many late overrides and `!important` declarations tied to dashboard-rail stacking, mobile navigation, and previously fixed viewport overflow. Do not delete or combine those rules in bulk. Reduce them by component and breakpoint only when browser tests and visual comparison prove the result unchanged.

Django Admin templates and email templates were intentionally excluded from public-interface formatting; email templates retain inline styling for email-client compatibility. CMS-managed pages and routes requiring an authenticated session need additional manual review beyond the public-route smoke tests.


## Source audit results

The latest successful source audit reported 48 public templates checked, 245 source files scanned, and 18 Django static references checked. It found no inline event-handler attributes, no images missing an `alt` attribute, no buttons missing an explicit `type`, and no inline style attributes in the scanned public templates. The browser-source audit found no confirmed unreferenced CSS/JS assets apart from the retained legacy language helper, which remains flagged for manual CMS/runtime verification.

The source-quality workflow currently validates the public templates and browser scripts. The Playwright suite runs against the Render service URL to avoid Cloudflare challenge HTML interfering with automated browser checks. It does not submit authentication forms or claim to validate the Turnstile challenge itself. The post-fix browser run passed all 22 checks on the live build. `static/portal/js/language.js` remains a possible unreferenced legacy helper; it was deliberately retained because dynamic CMS/runtime usage has not been conclusively ruled out.


## Follow-up cleanup pass (1 November 2026)

This pass starts from the current `deploy/render-ready` frontend after Django CMS was removed. It keeps the existing public design and business flows intact and applies narrowly scoped maintenance changes:

- The public base template now exposes a `blog_css` block. The home page and blog list/article templates load `blog.css` through that block; product, pricing, account, cart, and dashboard pages no longer download blog-only styles. The stylesheet remains in the same cascade position as before on pages that use it.
- The Google Fonts request now includes the three families declared by the site styles (`Vazirmatn`, `DM Sans`, and `Space Grotesk`), and preconnects to the font asset origin.
- Removed `static/portal/js/language.js`. It had no active template or source-code reference, and its client-side text replacement conflicted with the server-enforced Persian public interface. The server locale middleware and its tests remain unchanged; Django Admin remains English.
- Fixed a duplicate `class` attribute on the dashboard license section. The missing `nv-licenses-panel` class meant its existing page-specific spacing rule was silently ignored.
- Extended the source audit to report duplicate attributes within public HTML opening tags, and removed the obsolete CMS-template exception from the template formatter configuration.
- Frontend GitHub Actions workflows now use `npm ci` with the committed lockfile rather than resolving dependencies with `npm install`.

The core design stylesheets were intentionally not flattened or mass-pruned. `unified-experience.css` and `responsive-system.css` contain layered component and breakpoint overrides, including protections for mobile navigation, dashboard layout, and horizontal overflow. Selector repetition or `!important` alone does not establish that a rule is dead. A further reduction should be performed by component with browser visual comparisons, not by deleting late rules in bulk.

The Playwright suite now additionally checks that `blog.css` is present on the home/blog pages and absent from unrelated public pages. Source checks, formatter checks, JavaScript lint/syntax checks, and browser regression checks remain the validation gates for this maintenance branch. This branch is not considered production-deployed until it is merged into `deploy/render-ready` and its Render deployment is verified.


## CSS cascade cleanup pass (1 November 2026)

The follow-up pass reduced the current public frontend's !important declarations from **593 to 21** (a 96.5% reduction) without deleting the responsive layout rules themselves.

- The selectors in unified-experience.css and responsive-system.css are now explicitly scoped to the public portal root (body.nv-portal). The root and dashboard selectors use the existing body classes, while the source order of the two stylesheets is retained.
- Component styles in blog.css, dashboard.css, and the relevant overrides in site.css now use scoped selectors instead of priority flags. This keeps blog, account-dashboard, and public-shell styling from leaking to unrelated documents.
- The 21 remaining declarations are deliberate reduced-motion safeguards in unified-experience.css, responsive-system.css, site.css, site-shell.css, and the separate Django Admin motion stylesheet. They are retained so reduced-motion preferences continue to take precedence over decorative animation and transitions.
- The source audit now enforces a maximum budget of 25 !important declarations. A small allowance remains for accessibility-specific overrides; ordinary component styling should use scoped selectors and predictable cascade order.
- Playwright now checks that the mobile navigation opens as a fixed, scrollable two-column menu and returns to its hidden state when toggled closed.

This pass keeps the existing breakpoints and component declarations; it does not mass-delete responsive rules. The full quality workflow and the deployed browser suite remain the acceptance gates for this cascade change.
