#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run migrations (create database if needed)
python manage.py migrate --noinput || true

# Collect static files
python manage.py collectstatic --noinput || true

