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

