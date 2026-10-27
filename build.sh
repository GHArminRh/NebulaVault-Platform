#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt

# The deployment branch currently lacks committed migrations for several
# project apps. Generate them into the build artifact so the start command's
# `migrate` step can create every app table on Render.
python manage.py makemigrations --noinput
python manage.py collectstatic --noinput
