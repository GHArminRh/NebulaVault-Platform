#!/usr/bin/env bash
set -euo pipefail

# Verify that browser-facing CSS bundles were generated from the reviewed source modules.
python scripts/build_frontend_css.py --check

# Render already provides pip. Upgrading it on every deploy adds an avoidable
# network install and can make otherwise identical builds less reproducible.
python -m pip install --disable-pip-version-check -r requirements.txt

# Schema changes must be generated locally, reviewed, and committed. Never
# create migrations during a deploy build; Render applies committed migrations
# during the release/startup preparation step.
python manage.py collectstatic --noinput
