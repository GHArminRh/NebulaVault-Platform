#!/usr/bin/env bash
set -euo pipefail

# ParsPack uses its own SQLite database on the attached persistent disk.
# This startup command intentionally operates only on that deployment's DB.
python manage.py render_startup

exec gunicorn config.wsgi:application --config gunicorn.parspack.conf.py
