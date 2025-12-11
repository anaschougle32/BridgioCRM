# Views Update Summary for Lead-Project Association

## Overview
This document tracks the systematic update of all views to work with the new Lead-Project Association model.

## Key Changes Required

### 1. Lead Model Access Patterns

**Old Pattern:**
```python
lead.project
lead.status
lead.is_pretagged
lead.assigned_to
lead.configuration
```

**New Pattern:**
```python
# Get association for a specific project
association = get_lead_association(lead, project)
association.status
association.is_pretagged
association.assigned_to

# Get all projects
lead.all_projects
lead.primary_project

# Get configurations (ManyToMany)
lead.configurations.all()
```

### 2. Views to Update

#### Critical Views (Must Update First):
1. ✅ `lead_create` - Updated
2. ✅ `lead_pretag` - Updated  
3. ⏳ `lead_list` - In Progress
4. ⏳ `lead_detail` - Pending
5. ⏳ `schedule_visit` - Pending
6. ⏳ `lead_upload` - Pending
7. ⏳ `search_leads` - Pending
8. ⏳ `upcoming_visits` - Pending
9. ⏳ `pretagged_leads` - Pending
10. ⏳ `scheduled_visits` - Pending
11. ⏳ `closing_manager_visits` - Pending
12. ⏳ `visits_list` - Pending

#### Booking Views:
13. ⏳ `booking_create` - Pending
14. ⏳ `unit_calculation` - Pending

#### Project Views:
15. ⏳ `project_detail` - Pending
16. ⏳ `unit_selection` - Pending

#### Report Views:
17. ⏳ `employee_performance` - Pending
18. ⏳ `cp_performance` - Pending

### 3. Common Patterns

#### Creating a Lead with Association:
```python
# Check if lead exists
lead, created = Lead.objects.get_or_create(phone=normalized_phone, defaults={...})

# Add configurations
config_ids = request.POST.getlist('configurations')
if config_ids:
    configs = GlobalConfiguration.objects.filter(id__in=config_ids, is_active=True)
    lead.configurations.set(configs)

# Create association
association, assoc_created = LeadProjectAssociation.objects.get_or_create(
    lead=lead,
    project=project,
    defaults={
        'status': 'new',
        'is_pretagged': False,
        'created_by': request.user,
    }
)
```

#### Filtering Leads by Project/Status:
```python
# Old way
leads = Lead.objects.filter(project=project, status='new')

# New way
associations = LeadProjectAssociation.objects.filter(
    project=project,
    status='new',
    is_archived=False
)
lead_ids = associations.values_list('lead_id', flat=True).distinct()
leads = Lead.objects.filter(id__in=lead_ids)
```

#### Getting Lead Status for Display:
```python
# Old way
status = lead.status

# New way (for a specific project)
association = get_lead_association(lead, project)
status = association.status if association else None

# Or get all associations
associations = lead.project_associations.filter(is_archived=False)
```

### 4. Template Updates Needed

Templates that display `lead.project`, `lead.status`, `lead.configuration` need to be updated to:
- Show all projects: `lead.all_projects`
- Show status per project: `association.status`
- Show configurations: `lead.configurations.all()`

### 5. Forms Updates Needed

Forms need to:
- Use `GlobalConfiguration` for configuration selection (multiple)
- Allow selecting multiple projects for pretagging
- Show all leads in budget dropdown (not filtered by project)

## Progress Tracking

- [x] Models created
- [x] Migration file created
- [x] lead_create updated
- [x] lead_pretag updated
- [ ] lead_list updated
- [ ] lead_detail updated
- [ ] schedule_visit updated
- [ ] lead_upload updated
- [ ] All other views updated
- [ ] Templates updated
- [ ] Forms updated
- [ ] Testing completed

