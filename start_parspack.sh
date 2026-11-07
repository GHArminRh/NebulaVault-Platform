#!/usr/bin/env bash
set -euo pipefail

# ParsPack has its own PostgreSQL DATABASE_URL and its own application secret.
# This startup command intentionally operates only on that deployment's DB.
python manage.py render_startup

exec gunicorn config.wsgi:application --config gunicorn.parspack.conf.py
