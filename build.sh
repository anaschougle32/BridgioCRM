#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create database directory if it doesn't exist
mkdir -p $(dirname db.sqlite3) || true

# Run migrations (create database if needed)
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Create default superuser if it doesn't exist (optional - comment out if not needed)
python manage.py create_superuser --username admin --email admin@bridgio.com --password admin123 || true

