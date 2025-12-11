#!/usr/bin/env python
"""
Comprehensive fix for migration issues
This will:
1. Check database schema
2. Create missing migrations if needed
3. Fix any schema mismatches
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from django.db import connection
from django.core.management import call_command
import sys

def check_and_fix_schema():
    """Check schema and create migration if needed"""
    print("="*60)
    print("STEP 1: Checking database schema...")
    print("="*60)
    
    # Check CallLog table
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(call_logs)")
        calllog_cols = {row[1]: row for row in cursor.fetchall()}
        print(f"\nCallLog columns: {list(calllog_cols.keys())}")
        
        # Ensure user_id exists (not called_by_id)
        if 'called_by_id' in calllog_cols and 'user_id' not in calllog_cols:
            print("⚠️  Fixing: called_by_id should be user_id")
            cursor.execute("ALTER TABLE call_logs RENAME COLUMN called_by_id TO user_id")
            print("✅ Fixed: renamed called_by_id to user_id")
        
        # Ensure duration_minutes exists (not call_duration)
        if 'call_duration' in calllog_cols and 'duration_minutes' not in calllog_cols:
            print("⚠️  Fixing: call_duration should be duration_minutes")
            cursor.execute("ALTER TABLE call_logs RENAME COLUMN call_duration TO duration_minutes")
            print("✅ Fixed: renamed call_duration to duration_minutes")
        
        # Ensure call_date exists
        if 'call_date' not in calllog_cols:
            print("⚠️  Adding: call_date column")
            cursor.execute("ALTER TABLE call_logs ADD COLUMN call_date DATETIME")
            cursor.execute("UPDATE call_logs SET call_date = created_at WHERE call_date IS NULL")
            print("✅ Fixed: added call_date")
    
    print("\n" + "="*60)
    print("STEP 2: Checking what Django wants to migrate...")
    print("="*60)
    
    # Capture makemigrations output
    try:
        from io import StringIO
        output = StringIO()
        call_command('makemigrations', 'leads', '--dry-run', stdout=output, verbosity=1)
        output_str = output.getvalue()
        
        if output_str.strip() and 'No changes detected' not in output_str:
            print("\n⚠️  Django detected changes:")
            print(output_str)
            print("\n✅ Run: python manage.py makemigrations leads")
            print("Then: python manage.py migrate leads")
        else:
            print("\n✅ No changes detected - migrations are up to date!")
            print("\n✅ Run: python manage.py migrate")
            print("Then: python manage.py check")
    except Exception as e:
        print(f"\n⚠️  Error checking migrations: {e}")
        print("Try running manually: python manage.py makemigrations leads --dry-run")
    
    print("\n" + "="*60)
    print("Done!")
    print("="*60)

if __name__ == '__main__':
    check_and_fix_schema()

