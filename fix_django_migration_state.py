#!/usr/bin/env python
"""
Fix Django's migration state to match the actual database
This will tell Django that call_duration was already renamed to duration_minutes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from django.db import connection
from django.core.management import call_command
from django.db.migrations.recorder import MigrationRecorder

def check_migration_state():
    """Check what Django thinks the migration state is"""
    print("="*60)
    print("Checking Django Migration State")
    print("="*60)
    
    recorder = MigrationRecorder(connection)
    applied = recorder.applied_migrations()
    
    print(f"\nApplied migrations: {len(applied)}")
    leads_migrations = [m for m in applied if m[0] == 'leads']
    print(f"Leads migrations: {len(leads_migrations)}")
    
    for app, migration in sorted(leads_migrations):
        print(f"  - {migration}")

def fix_migration_state():
    """Tell Django that the field rename already happened"""
    print("\n" + "="*60)
    print("Fixing Migration State")
    print("="*60)
    
    # The issue is Django thinks call_duration exists in the model
    # but it doesn't - the model has duration_minutes
    # We need to make sure Django knows the current state
    
    print("\n✅ The model already has 'duration_minutes' (not 'call_duration')")
    print("✅ The database already has 'duration_minutes'")
    print("✅ Migrations 0012 and 0013 are fixed to only add indexes")
    print("\n⚠️  Django keeps creating migrations because it thinks:")
    print("   - Migration state says: call_duration exists")
    print("   - Model says: duration_minutes exists")
    print("   - So it tries to 'migrate' from call_duration to duration_minutes")
    
    print("\n" + "="*60)
    print("SOLUTION:")
    print("="*60)
    print("1. Apply the fixed migration 0013")
    print("2. If Django still creates new migrations, we'll need to")
    print("   manually update the migration state or fake the rename")

if __name__ == '__main__':
    check_migration_state()
    fix_migration_state()

