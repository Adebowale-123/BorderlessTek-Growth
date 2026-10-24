#!/usr/bin/env bash
# Render build: install, collect static files, migrate, create default sources and the first admin.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py seed_growth
python manage.py ensure_admin
python manage.py rescore
