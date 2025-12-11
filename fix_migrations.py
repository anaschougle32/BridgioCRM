#!/usr/bin/env python
"""
Script to fix migration issues
Run: python fix_migrations.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from django.db import connection

def check_and_fix_calllog():
    """Check CallLog table schema and fix if needed"""
    with connection.cursor() as cursor:
        # Get table info
        cursor.execute("PRAGMA table_info(call_logs)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        print("Current CallLog columns:", list(columns.keys()))
        
        # Check if call_date exists, if not add it
        if 'call_date' not in columns:
            print("Adding call_date column...")
            cursor.execute("ALTER TABLE call_logs ADD COLUMN call_date DATETIME")
            # Populate from created_at
            cursor.execute("UPDATE call_logs SET call_date = created_at WHERE call_date IS NULL")
            print("✓ call_date added and populated")
        
        # Rename called_by to user if needed
        if 'called_by' in columns and 'user' not in columns:
            print("Renaming called_by to user...")
            cursor.execute("ALTER TABLE call_logs RENAME COLUMN called_by TO user")
            print("✓ called_by renamed to user")
        
        # Rename call_duration to duration_minutes if needed
        if 'call_duration' in columns and 'duration_minutes' not in columns:
            print("Renaming call_duration to duration_minutes...")
            cursor.execute("ALTER TABLE call_logs RENAME COLUMN call_duration TO duration_minutes")
            print("✓ call_duration renamed to duration_minutes")
        
        print("\nCallLog table is now up to date!")

if __name__ == '__main__':
    print("Fixing CallLog table schema...")
    check_and_fix_calllog()
    print("\nDone! Now run: python manage.py migrate")

