#!/usr/bin/env python
"""
Find what fields are missing between model and database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from django.db import connection
from leads.models import Lead, CallLog, GlobalConfiguration, LeadProjectAssociation

def check_table_schema(table_name, model_class):
    """Compare model fields with database columns"""
    print(f"\n{'='*60}")
    print(f"Checking {table_name} (Model: {model_class.__name__})")
    print(f"{'='*60}")
    
    # Get model fields
    model_fields = {f.name: f for f in model_class._meta.get_fields() if hasattr(f, 'column')}
    model_columns = {f.column: f.name for f in model_class._meta.get_fields() if hasattr(f, 'column')}
    
    # Get database columns
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        db_columns = {row[1]: row for row in cursor.fetchall()}
    
    print(f"\nModel expects {len(model_columns)} columns")
    print(f"Database has {len(db_columns)} columns")
    
    # Find missing in DB
    missing_in_db = set(model_columns.keys()) - set(db_columns.keys())
    if missing_in_db:
        print(f"\n⚠️  Missing in DATABASE:")
        for col in missing_in_db:
            field_name = model_columns[col]
            field = model_fields[field_name]
            print(f"  - {col} ({field_name}) - {type(field).__name__}")
    
    # Find extra in DB
    extra_in_db = set(db_columns.keys()) - set(model_columns.keys())
    if extra_in_db:
        print(f"\n⚠️  Extra in DATABASE (not in model):")
        for col in extra_in_db:
            print(f"  - {col}")
    
    if not missing_in_db and not extra_in_db:
        print("\n✅ Schema matches!")

# Check each model
try:
    check_table_schema('leads', Lead)
except Exception as e:
    print(f"Error checking Lead: {e}")

try:
    check_table_schema('leads_calllog', CallLog)
except Exception as e:
    print(f"Error checking CallLog: {e}")

try:
    check_table_schema('global_configurations', GlobalConfiguration)
except Exception as e:
    print(f"Error checking GlobalConfiguration: {e}")

try:
    check_table_schema('lead_project_associations', LeadProjectAssociation)
except Exception as e:
    print(f"Error checking LeadProjectAssociation: {e}")

print("\n" + "="*60)
print("Done!")
print("="*60)

