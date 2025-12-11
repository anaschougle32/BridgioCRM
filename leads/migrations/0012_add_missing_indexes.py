# Generated migration to add missing indexes and fix Django migration state
# Migration 0008 renamed call_duration to duration_minutes in the database using RunPython,
# but didn't update Django's migration state. This migration updates the state.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0011_remove_legacy_lead_fields'),
    ]

    operations = [
        # Update Django's migration state: tell it call_duration was renamed to duration_minutes
        # The database already has duration_minutes, so we use SeparateDatabaseAndState
        # to update the state without touching the database
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # Do nothing in the database - it already has duration_minutes
            ],
            state_operations=[
                # Update the state: remove call_duration, add duration_minutes
                migrations.RemoveField(
                    model_name='calllog',
                    name='call_duration',
                ),
                migrations.AddField(
                    model_name='calllog',
                    name='duration_minutes',
                    field=models.IntegerField(blank=True, null=True),
                ),
            ],
        ),
        # Add the indexes that are missing
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS lead_projec_project_e57839_idx 
            ON lead_project_associations(project_id, status, is_archived);
            CREATE INDEX IF NOT EXISTS lead_projec_assigne_9c1e2a_idx 
            ON lead_project_associations(assigned_to_id, status);
            CREATE INDEX IF NOT EXISTS lead_projec_is_pret_abf9d6_idx 
            ON lead_project_associations(is_pretagged, pretag_status);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS lead_projec_project_e57839_idx;
            DROP INDEX IF EXISTS lead_projec_assigne_9c1e2a_idx;
            DROP INDEX IF EXISTS lead_projec_is_pret_abf9d6_idx;
            """,
        ),
    ]
