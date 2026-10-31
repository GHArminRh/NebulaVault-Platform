#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt

# Schema changes must be generated locally, reviewed, and committed. Never
# create migrations during a deploy build; Render's start command applies the
# committed migration graph to the persistent database.
python manage.py collectstatic --noinput
