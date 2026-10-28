# Project structure audit and refactoring plan

## Baseline

This audit starts from `deploy/render-ready` (commit `6687d4f41f39b9d6dd801047c572b0cb759aeaad`, 2026-10-28). The deployment branch is treated as the behavior baseline; this work must not be merged into the deployment branch until reviewed and tested.

The repository already uses a conventional Django layout: one project package (`config`), domain apps at repository root, app-owned templates/static files where appropriate, and shared templates/assets at root. Moving every app under a new `apps/` package would create unnecessary import, migration, and deployment risk. The goal is to improve consistency within the current layout rather than reorganize directories for appearance alone.

## Initial observations

- `config/settings.py` contains several long, compressed lists and repeated environment-condition checks. Formatting and grouping can improve readability without changing settings semantics.
- `accounts/views.py` and `billing/services.py` are large modules with multiple responsibilities. Split them only in small, tested changes; preserve imports and public function behavior during the transition.
- Test files are inconsistent: some apps use `tests.py`, others use multiple `test_*.py` modules. Django supports both patterns, so do not move tests until discovery and CI behavior are verified.
- Some supporting apps have very small placeholder modules. Do not remove them until `INSTALLED_APPS`, migrations, model references, URLs, admin registrations, and historical database state have been checked.
- The repository has no root README at this baseline; a project overview and repeatable local-check commands are needed.
- CI currently runs targeted licensing/account tests rather than the full suite. Expand coverage only after confirming the complete suite runs reliably in a clean PostgreSQL environment.

## Intended standards

1. Keep the existing app boundaries and root-level Django app layout.
2. Use one responsibility per module; extract helpers/services only when the separation is clear and behavior can be covered by tests.
3. Keep view functions focused on request/response handling; keep business rules in service functions.
4. Preserve database schema, migration history, route names, templates, static paths, environment variable names, payment flows, and licensing interfaces unless a separately reviewed change explicitly requires otherwise.
5. Use consistent Python formatting, imports, and naming. Configure lint rules based on the actual repository baseline rather than making CI fail on unreviewed legacy warnings.
6. Keep tests close to the app they cover. Standardize test naming incrementally, not through a mass move.
7. Keep shared templates in `templates/` and shared assets in `static/`; app-specific templates and assets can remain app-local.
8. Keep secrets and local environment files out of version control.

## Refactoring sequence

### Phase 1 — Safe foundations
- Add a root README and this audit document.
- Establish a consistent formatting/lint configuration.
- Reformat low-risk configuration modules without changing behavior.
- Run Django checks and migration consistency checks.

### Phase 2 — Focused module decomposition
- [x] Split `billing/services.py` implementations into `billing/order_services.py`, `billing/attempt_services.py`, and `billing/finalization_services.py`.
- [x] Keep `billing.services` as a compatibility facade so existing callers and tests can retain their imports.
- [x] Add billing regression tests to the pull-request CI workflow.
- [ ] Map responsibilities and call sites in `accounts/views.py`; extract account flows in a separate, tested change.
- Avoid circular imports and avoid importing Django models at module load when a local import is currently required to break a dependency cycle.

### Phase 3 — Test and CI consistency
- Inventory all tests and determine the complete suite command and runtime.
- Add full-suite CI only after it is stable and compatible with PostgreSQL.
- Keep payment, account, license, and admin regression tests explicit.

### Phase 4 — Optional cleanup
- Evaluate placeholder apps and duplicated files based on references and migration history.
- Remove dead code only with evidence that it is unreachable and unreferenced.
- Consider directory moves only if they provide a measurable benefit and include a complete import/configuration update.

## Validation checklist

Before a refactor is accepted:

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- Relevant app tests, followed by `python manage.py test` where the configured database is available
- Verify login, email verification/reset, customer dashboard, cart/order creation, Zarinpal callbacks, license issuance, and Django admin behavior
- Inspect the complete Git diff and confirm no secrets, migrations, or generated files changed unintentionally
- Confirm Render build and health check on a branch/deployment preview before promoting changes

## Explicit non-goals

This cleanup does not translate or redesign the Django admin, alter customer-facing Persian copy, change payment configuration, change security policy, or change the desktop application's license protocol.


## Validation findings and test maintenance

- Ruff passes for the formatted settings files and the extracted billing service modules.
- Licensing, Turnstile, and email-backend tests passed in the latest completed CI run.
- The billing regression suite passed after correcting two test issues: a renewal test now checks the delivery-only attribute on the instance returned by `finalize_payment()`, and concurrent worker connections are closed after the test.
- Account tests were updated to isolate the shared database cache and to reflect the current Persian verification/password-reset flows. One test exposed a real email-change detection bug: validating a Django `ModelForm` mutates its bound instance in memory, so the previous email must be captured before validation. The fix is in `accounts/views.py`; CI is rerunning against that fix before this branch is considered ready.
- Keep the full test suite and the production-like Render checks as merge gates; a green targeted run is not a substitute for reviewing the complete diff.

## Billing service split (2026-10-28)

The first behavior-preserving module split is in place on the cleanup branch:

- `billing/order_services.py`: single-plan and multi-item cart order creation.
- `billing/attempt_services.py`: idempotent payment-attempt creation.
- `billing/finalization_services.py`: finalization after trusted provider-side verification, including subscription/license updates and notifications.
- `billing/services.py`: compatibility facade exposing the existing service names and error classes.

No model fields, migrations, payment URLs, Zarinpal request/verification flow, or database transaction boundaries were intentionally changed by this split. The new CI job runs `billing.tests`; the refactor is not considered validated until that job completes and the diff is reviewed.


The billing regression suite also exposed a stale assertion in the pre-existing renewal test: it checked a dynamically attached, delivery-only attribute on the original model instance even though `finalize_payment()` locks, reloads, and returns a separate instance. The test now asserts against the returned instance; production payment behavior was not changed for this test.
