# Lead-Project Association Migration Guide

## Overview
This migration implements Phase 3: Lead-Project Association model for full cross-project tracking, along with global configurations.

## Key Changes

### 1. New Models

#### GlobalConfiguration
- Predefined configuration types: 1BHK, 2BHK, 3BHK, 4BHK, 5BHK, PentHouse, Villa, Plot
- Not project-specific - can be used across all projects
- Multiple selections allowed per lead

#### LeadProjectAssociation
- Links leads to projects (many-to-many relationship)
- Stores project-specific data:
  - Status (per project)
  - Pretagging flags (per project)
  - Assignment (per project)
  - Notes (per project)

### 2. Lead Model Changes

#### Removed:
- `project` FK (moved to association)
- `configuration` FK (replaced with ManyToMany to GlobalConfiguration)
- `status`, `is_pretagged`, `pretag_status`, `phone_verified`, `assigned_to`, `assigned_at`, `assigned_by` (moved to association)

#### Added:
- `configurations` ManyToMany to GlobalConfiguration
- `phone` is now unique (for deduplication)
- Properties: `primary_project`, `all_projects`

### 3. Migration Strategy

The migration file `0007_add_lead_project_association.py` handles:
1. Creating GlobalConfiguration model and populating it
2. Creating LeadProjectAssociation model
3. Migrating existing lead data to associations
4. Making phone unique
5. Keeping legacy `project` field temporarily for backward compatibility

## Steps to Apply Migration

### Before Migration:
1. **Backup your database**
2. Check for duplicate phone numbers:
   ```python
   from leads.models import Lead
   from django.db.models import Count
   duplicates = Lead.objects.values('phone').annotate(count=Count('id')).filter(count__gt=1)
   ```
3. Resolve duplicates manually if any exist

### Apply Migration:
```bash
python manage.py migrate leads
```

### After Migration:
1. Verify data migration:
   ```python
   from leads.models import Lead, LeadProjectAssociation
   # Check all leads have associations
   leads_without_assoc = Lead.objects.filter(project_associations__isnull=True)
   # Should be empty or only new leads
   ```

2. Test key functionality:
   - Lead creation
   - Lead listing
   - Project associations
   - Configuration selection

## View Updates Required

All views that access `lead.project`, `lead.status`, `lead.assigned_to`, etc. need to be updated to use:
- `lead.primary_project` or `lead.project_associations.filter(project=project).first()`
- `association.status` instead of `lead.status`
- `association.assigned_to` instead of `lead.assigned_to`

## Breaking Changes

1. **Lead.project** - Now use `lead.primary_project` or `lead.project_associations`
2. **Lead.status** - Now use `association.status` for project-specific status
3. **Lead.configuration** - Now use `lead.configurations.all()` (ManyToMany)
4. **Phone uniqueness** - Duplicate phones will cause migration to fail

## Rollback Plan

If migration fails:
1. Restore database backup
2. Fix duplicate phones
3. Re-run migration

## Testing Checklist

- [ ] Global configurations are populated
- [ ] Existing leads have associations created
- [ ] Lead creation works with new structure
- [ ] Lead listing shows correct project associations
- [ ] Configuration selection works (multiple)
- [ ] Budget dropdown shows all leads
- [ ] Project-specific status works correctly
- [ ] Assignment works per project
- [ ] Pretagging works per project
- [ ] Booking creation works
- [ ] All reports work correctly

