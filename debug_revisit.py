#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from leads.models import LeadProjectAssociation, Lead
from django.contrib.auth import get_user_model

User = get_user_model()

# Get a test user
user = User.objects.filter(role='closing_manager').first()
if not user:
    user = User.objects.first()

print(f"Testing with user: {user.username} ({user.role})")
print("=" * 60)

# Test 1: Direct database query
print("\nTEST 1: Direct database query for 'tej'")
results = LeadProjectAssociation.objects.filter(
    is_archived=False,
    lead__name__icontains='tej'
)
print(f"Found {results.count()} results")
for r in results:
    print(f"  - {r.id}: {r.lead.name} ({r.lead.phone}) - Status: {r.status}")

# Test 2: Check if user has permission to see these results
print("\nTEST 2: User permission filtering")
if user.is_telecaller():
    filtered = results.filter(assigned_to=user)
    print(f"Telecaller view: {filtered.count()} results")
elif user.is_closing_manager():
    filtered = results.filter(assigned_to=user)
    print(f"Closing Manager view: {filtered.count()} results")
else:
    print(f"Other role ({user.role}): {results.count()} results")

# Test 3: Check the actual view logic
print("\nTEST 3: Simulating view logic")
from django.db.models import Q

search_query = 'tej'
project_id = ''

associations = LeadProjectAssociation.objects.filter(
    is_archived=False
).select_related('lead', 'project', 'assigned_to')

print(f"Total non-archived associations: {associations.count()}")

# Apply project filter if specified
if project_id:
    associations = associations.filter(project_id=project_id)
    print(f"After project filter: {associations.count()}")

# Apply user role filtering
if user.is_telecaller():
    associations = associations.filter(assigned_to=user)
    print(f"After telecaller filter: {associations.count()}")
elif user.is_closing_manager():
    associations = associations.filter(assigned_to=user)
    print(f"After closing manager filter: {associations.count()}")
elif user.is_sourcing_manager():
    associations = associations.filter(project__in=user.assigned_projects.all())
    print(f"After sourcing manager filter: {associations.count()}")
elif user.is_site_head():
    associations = associations.filter(project__site_head=user)
    print(f"After site head filter: {associations.count()}")
elif user.is_mandate_owner():
    associations = associations.filter(project__mandate_owner=user)
    print(f"After mandate owner filter: {associations.count()}")
else:
    print(f"Super admin or other role: {associations.count()}")

# Search by lead name, phone, or email
associations = associations.filter(
    Q(lead__name__icontains=search_query) |
    Q(lead__phone__icontains=search_query) |
    Q(lead__email__icontains=search_query)
).distinct()

print(f"After search filter for '{search_query}': {associations.count()}")
for assoc in associations[:5]:
    print(f"  - {assoc.id}: {assoc.lead.name} ({assoc.lead.phone})")
