#!/usr/bin/env python
"""
Comprehensive script to fix all migration issues
Run: python fix_all_migrations.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from django.db import connection

def fix_calllog_table():
    """Fix CallLog table - rename called_by_id to user_id"""
    with connection.cursor() as cursor:
        # Get table info
        cursor.execute("PRAGMA table_info(call_logs)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        print("Current CallLog columns:", list(columns.keys()))
        
        # Rename called_by_id to user_id if needed
        if 'called_by_id' in columns and 'user_id' not in columns:
            print("Renaming called_by_id to user_id...")
            cursor.execute("ALTER TABLE call_logs RENAME COLUMN called_by_id TO user_id")
            print("✓ called_by_id renamed to user_id")
        elif 'user_id' in columns:
            print("✓ user_id already exists")
        else:
            print("⚠ No called_by_id or user_id found")
        
        # Ensure duration_minutes exists (should already exist)
        if 'duration_minutes' in columns:
            print("✓ duration_minutes exists")
        elif 'call_duration' in columns:
            print("Renaming call_duration to duration_minutes...")
            cursor.execute("ALTER TABLE call_logs RENAME COLUMN call_duration TO duration_minutes")
            print("✓ call_duration renamed to duration_minutes")
        
        # Ensure call_date exists
        if 'call_date' not in columns:
            print("Adding call_date column...")
            cursor.execute("ALTER TABLE call_logs ADD COLUMN call_date DATETIME")
            cursor.execute("UPDATE call_logs SET call_date = created_at WHERE call_date IS NULL")
            print("✓ call_date added and populated")
        else:
            print("✓ call_date exists")
        
        print("\nCallLog table is now up to date!")

def fix_indexes():
    """Fix missing indexes"""
    with connection.cursor() as cursor:
        # Check if index exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='lead_projec_is_pret_abf9d6_idx'")
        index_exists = cursor.fetchone() is not None
        
        if not index_exists:
            print("Creating missing index: lead_projec_is_pret_abf9d6_idx...")
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS lead_projec_is_pret_abf9d6_idx 
                    ON lead_project_associations(is_pretagged, pretag_status)
                """)
                print("✓ Index created")
            except Exception as e:
                print(f"⚠ Could not create index: {e}")
        else:
            print("✓ Index lead_projec_is_pret_abf9d6_idx already exists")

if __name__ == '__main__':
    print("=" * 50)
    print("Fixing all migration issues...")
    print("=" * 50)
    print()
    
    print("Step 1: Fixing CallLog table...")
    fix_calllog_table()
    print()
    
    print("Step 2: Fixing indexes...")
    fix_indexes()
    print()
    
    print("=" * 50)
    print("Done! Now run: python manage.py migrate --fake-initial")
    print("=" * 50)

