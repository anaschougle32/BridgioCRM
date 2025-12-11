# Generated migration for Lead-Project Association model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def populate_global_configurations(apps, schema_editor):
    """Populate GlobalConfiguration with predefined values"""
    GlobalConfiguration = apps.get_model('leads', 'GlobalConfiguration')
    
    configs = [
        {'name': '1BHK', 'display_name': '1BHK', 'order': 1},
        {'name': '2BHK', 'display_name': '2BHK', 'order': 2},
        {'name': '3BHK', 'display_name': '3BHK', 'order': 3},
        {'name': '4BHK', 'display_name': '4BHK', 'order': 4},
        {'name': '5BHK', 'display_name': '5BHK', 'order': 5},
        {'name': 'PentHouse', 'display_name': 'PentHouse', 'order': 6},
        {'name': 'Villa', 'display_name': 'Villa', 'order': 7},
        {'name': 'Plot', 'display_name': 'Plot', 'order': 8},
    ]
    
    for config in configs:
        GlobalConfiguration.objects.get_or_create(
            name=config['name'],
            defaults={
                'display_name': config['display_name'],
                'order': config['order'],
                'is_active': True
            }
        )


def handle_duplicate_phones(apps, schema_editor):
    """Handle duplicate phone numbers before making phone unique"""
    Lead = apps.get_model('leads', 'Lead')
    
    # Find all duplicate phone numbers
    from django.db.models import Count
    duplicates = Lead.objects.values('phone').annotate(
        count=Count('phone')
    ).filter(count__gt=1)
    
    for dup in duplicates:
        phone = dup['phone']
        if not phone:  # Skip empty phones
            continue
            
        # Get all leads with this phone number
        leads_with_phone = Lead.objects.filter(phone=phone).order_by('id')
        
        # Keep the first one (oldest), merge data from others, then delete duplicates
        primary_lead = leads_with_phone.first()
        duplicate_leads = leads_with_phone[1:]
        
        for dup_lead in duplicate_leads:
            # Merge notes if both have notes
            if dup_lead.notes and primary_lead.notes:
                primary_lead.notes = f"{primary_lead.notes}\n\n[Merged from duplicate lead #{dup_lead.id}]: {dup_lead.notes}"
            elif dup_lead.notes:
                primary_lead.notes = dup_lead.notes
            
            # Update other fields if primary is missing them
            if not primary_lead.email and dup_lead.email:
                primary_lead.email = dup_lead.email
            if not primary_lead.name and dup_lead.name:
                primary_lead.name = dup_lead.name
            
            # Save primary lead
            primary_lead.save()
            
            # Delete the duplicate lead
            dup_lead.delete()


def migrate_existing_leads(apps, schema_editor):
    """Migrate existing leads to LeadProjectAssociation"""
    Lead = apps.get_model('leads', 'Lead')
    LeadProjectAssociation = apps.get_model('leads', 'LeadProjectAssociation')
    GlobalConfiguration = apps.get_model('leads', 'GlobalConfiguration')
    ProjectConfiguration = apps.get_model('projects', 'ProjectConfiguration')
    
    # Migrate each existing lead
    for lead in Lead.objects.all():
        if not hasattr(lead, 'project') or not lead.project:
            continue  # Skip leads without project (shouldn't happen, but safety check)
            
        # Get field values safely (they might not exist in new model)
        status = getattr(lead, 'status', 'new')
        is_pretagged = getattr(lead, 'is_pretagged', False)
        pretag_status = getattr(lead, 'pretag_status', 'pending_verification')
        phone_verified = getattr(lead, 'phone_verified', False)
        assigned_to = getattr(lead, 'assigned_to', None)
        assigned_at = getattr(lead, 'assigned_at', None)
        assigned_by = getattr(lead, 'assigned_by', None)
        notes = getattr(lead, 'notes', '')
        created_by = getattr(lead, 'created_by', None)
        created_at = getattr(lead, 'created_at', None)
        
        # Create association for the lead's project
        association, created = LeadProjectAssociation.objects.get_or_create(
            lead=lead,
            project=lead.project,
            defaults={
                'status': status,
                'is_pretagged': is_pretagged,
                'pretag_status': pretag_status,
                'phone_verified': phone_verified,
                'assigned_to': assigned_to,
                'assigned_at': assigned_at,
                'assigned_by': assigned_by,
                'notes': notes,
                'created_by': created_by,
                'created_at': created_at,
            }
        )
        
        # Migrate configuration if exists
        if hasattr(lead, 'configuration') and lead.configuration:
            # Try to match project configuration to global configuration
            config_name = lead.configuration.name
            # Normalize config name (e.g., "1BHK", "2 BHK" -> "1BHK", "2BHK")
            normalized = config_name.replace(' ', '').replace('-', '').upper()
            
            try:
                global_config = GlobalConfiguration.objects.get(name=normalized)
                lead.configurations.add(global_config)
            except GlobalConfiguration.DoesNotExist:
                # If exact match not found, try to find similar
                for gc in GlobalConfiguration.objects.all():
                    if gc.name.upper() in normalized or normalized in gc.name.upper():
                        lead.configurations.add(gc)
                        break


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0006_remove_otplog_otp_code_otplog_gateway_response_and_more'),
        ('projects', '0001_initial'),
        ('accounts', '0001_initial'),
        ('channel_partners', '0001_initial'),
    ]

    operations = [
        # Step 1: Create GlobalConfiguration model
        migrations.CreateModel(
            name='GlobalConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('1BHK', '1BHK'), ('2BHK', '2BHK'), ('3BHK', '3BHK'), ('4BHK', '4BHK'), ('5BHK', '5BHK'), ('PentHouse', 'PentHouse'), ('Villa', 'Villa'), ('Plot', 'Plot')], max_length=50, unique=True)),
                ('display_name', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.IntegerField(default=0, help_text='Display order')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'global_configurations',
                'ordering': ['order', 'name'],
            },
        ),
        
        # Step 2: Populate GlobalConfiguration
        migrations.RunPython(populate_global_configurations, migrations.RunPython.noop),
        
        # Step 3: Add configurations ManyToMany to Lead (temporary, will be populated later)
        migrations.AddField(
            model_name='lead',
            name='configurations',
            field=models.ManyToManyField(blank=True, help_text='Preferred configurations (multiple selection)', related_name='leads', to='leads.globalconfiguration'),
        ),
        
        # Step 4: Create LeadProjectAssociation model
        migrations.CreateModel(
            name='LeadProjectAssociation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('new', 'New'), ('contacted', 'Contacted'), ('visit_scheduled', 'Visit Scheduled'), ('visit_completed', 'Visit Completed'), ('discussion', 'Discussion'), ('hot', 'Hot'), ('ready_to_book', 'Ready to Book'), ('booked', 'Booked'), ('lost', 'Lost')], db_index=True, default='new', max_length=20)),
                ('is_pretagged', models.BooleanField(default=False)),
                ('pretag_status', models.CharField(blank=True, choices=[('pending_verification', 'Pending Verification'), ('verified', 'Verified'), ('rejected', 'Rejected')], default='pending_verification', max_length=20)),
                ('phone_verified', models.BooleanField(default=False)),
                ('assigned_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, help_text='Project-specific notes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_archived', models.BooleanField(default=False)),
                ('assigned_by', models.ForeignKey(blank=True, limit_choices_to={'role__in': ['super_admin', 'mandate_owner', 'site_head']}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lead_association_assignments', to=settings.AUTH_USER_MODEL)),
                ('assigned_to', models.ForeignKey(blank=True, limit_choices_to={'role__in': ['closing_manager', 'telecaller', 'sourcing_manager']}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_lead_associations', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_lead_associations', to=settings.AUTH_USER_MODEL)),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_associations', to='leads.lead')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lead_associations', to='projects.project')),
            ],
            options={
                'db_table': 'lead_project_associations',
                'ordering': ['-created_at'],
                'unique_together': {('lead', 'project')},
            },
        ),
        
        # Step 5: Migrate existing lead data to associations
        migrations.RunPython(migrate_existing_leads, migrations.RunPython.noop),
        
        # Step 6: Handle duplicate phone numbers before making phone unique
        migrations.RunPython(handle_duplicate_phones, migrations.RunPython.noop),
        
        # Step 7: Make phone unique (duplicates have been handled)
        migrations.AlterField(
            model_name='lead',
            name='phone',
            field=models.CharField(db_index=True, help_text='Unique phone number - used for deduplication', max_length=15, unique=True),
        ),
        
        # Step 8: Change project FK to nullable for backward compatibility
        migrations.AlterField(
            model_name='lead',
            name='project',
            field=models.ForeignKey(
                blank=True,
                help_text='DEPRECATED: Use project_associations instead',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='legacy_leads',
                to='projects.project'
            ),
        ),
    ]

