# Data Deduplication Solution for Multi-Project CRM

## Problem Statement
When multiple projects run in the same locality with the same target audience, leads and channel partners (CPs) can be duplicated across projects, leading to:
- Data redundancy
- Inconsistent information
- Difficulty tracking customer/CP history across projects
- Increased storage and maintenance overhead

## Proposed Solutions

### Solution 1: Global Master Data with Project Associations (Recommended)

**Concept**: Create a global master database for Leads and CPs, with project-specific associations.

#### For Channel Partners:
- **Master CP Table**: One record per unique CP (identified by phone number or CP ID)
- **Project Association Table**: Many-to-many relationship linking CPs to projects
- **Project-Specific Data**: Store project-specific commission rates, linked projects, etc. in association table

**Benefits**:
- Single source of truth for CP information
- Easy to track CP performance across all projects
- Update CP details once, reflects everywhere
- Can see which CPs work on which projects

**Implementation**:
```python
# ChannelPartner model (already exists as master)
# Add: linked_projects (ManyToMany) - already exists

# When creating/uploading CP:
1. Check if CP exists by phone number
2. If exists, link to new project (add to linked_projects)
3. If not, create new CP and link to project
```

#### For Leads:
- **Master Lead Table**: One record per unique lead (identified by phone number)
- **Lead-Project Association Table**: Track which projects a lead is associated with
- **Project-Specific Data**: Store project-specific requirements, status, assignments per project

**Benefits**:
- Complete customer history across all projects
- Avoid duplicate entries for same customer
- Better customer relationship management
- Can track customer journey across projects

**Implementation**:
```python
# New model: LeadProjectAssociation
class LeadProjectAssociation(models.Model):
    lead = ForeignKey(Lead)
    project = ForeignKey(Project)
    status = CharField()  # project-specific status
    assigned_to = ForeignKey(User, null=True)
    created_at = DateTimeField()
    # Other project-specific fields

# When creating/uploading lead:
1. Check if lead exists by phone number
2. If exists:
   - Check if already associated with this project
   - If not, create LeadProjectAssociation
   - If yes, update existing association
3. If not, create new lead and association
```

### Solution 2: Soft Deduplication with Merge Feature

**Concept**: Allow duplicates but provide tools to identify and merge them.

**Features**:
- **Duplicate Detection**: Show potential duplicates based on phone number, name similarity
- **Merge Tool**: Allow users to merge duplicate records
- **History Tracking**: Keep audit trail of merged records

**Benefits**:
- Less disruptive to current workflow
- Users can choose when to merge
- Preserves all historical data

**Implementation**:
```python
# Add duplicate detection view
def find_duplicates(request):
    # Find leads/CPs with same phone number across projects
    duplicates = Lead.objects.values('phone').annotate(
        count=Count('id'),
        projects=Count('project', distinct=True)
    ).filter(count__gt=1)

# Add merge functionality
def merge_leads(request, primary_id, duplicate_id):
    # Merge duplicate into primary
    # Update all references
    # Archive duplicate
```

### Solution 3: Hybrid Approach (Best of Both Worlds)

**Concept**: Use Solution 1 for CPs (master data) and Solution 2 for Leads (with merge option).

**Rationale**:
- **CPs**: More stable data, less frequent changes, easier to maintain as master
- **Leads**: More dynamic, project-specific requirements vary, merge when needed

## Recommended Implementation Plan

### Phase 1: CP Master Data (Immediate)
1. Ensure CP creation/upload checks for existing CP by phone
2. Link existing CPs to new projects instead of creating duplicates
3. Update CP detail view to show all associated projects
4. Update CP performance dashboard to show cross-project metrics

### Phase 2: Lead Deduplication Detection (Short-term)
1. Add duplicate detection view for leads
2. Show potential duplicates in lead list/detail pages
3. Add "Merge" button for duplicates
4. Implement merge functionality with audit trail

### Phase 3: Lead-Project Association (Long-term)
1. Create LeadProjectAssociation model
2. Migrate existing data
3. Update lead creation/upload to use associations
4. Update all views to work with associations

## Database Schema Changes

### For CPs (Minimal Changes Needed)
```python
# ChannelPartner model already has:
# - linked_projects (ManyToMany) ✓
# - phone (unique=True) ✓

# Just need to ensure:
# - When creating CP, check phone first
# - Link to project instead of duplicating
```

### For Leads (New Model Needed)
```python
class LeadProjectAssociation(models.Model):
    lead = ForeignKey(Lead, related_name='project_associations')
    project = ForeignKey(Project, related_name='lead_associations')
    status = CharField(max_length=50)  # project-specific status
    assigned_to = ForeignKey(User, null=True, blank=True)
    assigned_at = DateTimeField(null=True, blank=True)
    assigned_by = ForeignKey(User, null=True, blank=True, related_name='assigned_leads')
    is_pretagged = BooleanField(default=False)
    pretag_status = CharField(max_length=50, blank=True)
    phone_verified = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['lead', 'project']
```

## Migration Strategy

1. **Backup**: Full database backup before migration
2. **Identify Duplicates**: Run script to find duplicate leads/CPs
3. **Merge CPs**: Merge duplicate CPs, link to all projects
4. **Create Associations**: For leads, create LeadProjectAssociation records
5. **Update Views**: Modify all views to use new structure
6. **Testing**: Thorough testing before production deployment

## User Experience Considerations

1. **Search**: When searching for lead/CP, show all projects they're associated with
2. **Filters**: Add "Show duplicates" filter in lists
3. **Notifications**: Alert users when creating potential duplicate
4. **Merge UI**: Simple, intuitive merge interface with preview
5. **History**: Show merge history in lead/CP detail pages

## Questions to Consider

1. **Should leads be automatically merged or require manual approval?**
   - Recommendation: Manual approval for safety

2. **What happens to project-specific data when merging?**
   - Recommendation: Preserve all project-specific data in associations

3. **How to handle conflicting information?**
   - Recommendation: Show conflicts during merge, let user choose

4. **Should we allow "unmerge"?**
   - Recommendation: No, but keep audit trail

## Next Steps

1. Review and approve solution approach
2. Create detailed technical specification
3. Implement Phase 1 (CP master data)
4. Test thoroughly
5. Roll out to production
6. Plan Phase 2 and 3

