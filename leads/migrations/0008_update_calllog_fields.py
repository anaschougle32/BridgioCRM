# Generated migration to update CallLog fields - Safe version that checks schema

from django.db import migrations, models
from django.db import connection


def check_column_exists(table_name, column_name):
    """Check if a column exists in SQLite"""
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns


def set_call_date_from_created_at(apps, schema_editor):
    """Set call_date from created_at for existing CallLog records using raw SQL"""
    if check_column_exists('call_logs', 'call_date') and check_column_exists('call_logs', 'created_at'):
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE call_logs 
                SET call_date = created_at 
                WHERE call_date IS NULL
            """)


def reverse_set_call_date(apps, schema_editor):
    """Reverse operation"""
    pass


def rename_called_by_to_user(apps, schema_editor):
    """Rename called_by to user if it exists"""
    if check_column_exists('call_logs', 'called_by') and not check_column_exists('call_logs', 'user'):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE call_logs RENAME COLUMN called_by TO user")


def rename_call_duration_to_duration_minutes(apps, schema_editor):
    """Rename call_duration to duration_minutes if it exists"""
    if check_column_exists('call_logs', 'call_duration') and not check_column_exists('call_logs', 'duration_minutes'):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE call_logs RENAME COLUMN call_duration TO duration_minutes")


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0007_add_lead_project_association'),
    ]

    operations = [
        # Step 1: Add call_date field (nullable first, we'll populate it)
        migrations.AddField(
            model_name='calllog',
            name='call_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        
        # Step 2: Populate call_date from created_at
        migrations.RunPython(set_call_date_from_created_at, reverse_set_call_date),
        
        # Step 3: Make call_date non-nullable
        migrations.AlterField(
            model_name='calllog',
            name='call_date',
            field=models.DateTimeField(),
        ),
        
        # Step 4: Conditionally rename called_by to user
        migrations.RunPython(rename_called_by_to_user, migrations.RunPython.noop),
        
        # Step 5: Conditionally rename call_duration to duration_minutes
        migrations.RunPython(rename_call_duration_to_duration_minutes, migrations.RunPython.noop),
    ]
