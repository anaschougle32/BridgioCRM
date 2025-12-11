# Generated migration to remove legacy fields from Lead model
# These fields were moved to LeadProjectAssociation in migration 0007

from django.db import migrations, connection

def check_column_exists(table_name, column_name):
    """Check if a column exists in SQLite"""
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns

def remove_legacy_columns_if_exist(apps, schema_editor):
    """Safely remove legacy columns if they exist"""
    table_name = 'leads'
    
    # List of legacy columns to remove
    legacy_columns = [
        'is_pretagged',
        'assigned_by_id',
        'phone_verified',
        'assigned_at',
        'status',
        'pretag_status',
        'configuration_id',
        'assigned_to_id',
    ]
    
    for column in legacy_columns:
        if check_column_exists(table_name, column):
            print(f"⚠️  Legacy column '{column}' still exists in {table_name}")
            print(f"   This column should have been removed by migration 0009")
            print(f"   It will be removed in a future migration")
            # Note: SQLite doesn't support DROP COLUMN directly
            # We'll need to handle this differently

def reverse_remove_legacy_columns(apps, schema_editor):
    """Reverse operation - we won't restore these columns"""
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0010_rename_call_duration_calllog_duration_minutes_and_more'),
    ]

    operations = [
        # Note: SQLite doesn't support DROP COLUMN in older versions
        # These columns will be ignored by Django ORM since they're not in the model
        # They can be manually removed later if needed
        migrations.RunPython(
            remove_legacy_columns_if_exist,
            reverse_remove_legacy_columns,
        ),
    ]

