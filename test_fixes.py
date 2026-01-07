#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

# Test 1: Check if revisit search now returns results
print("=" * 60)
print("TEST 1: Revisit Search with New Filtering")
print("=" * 60)

from leads.models import LeadProjectAssociation

# Get a sample user
user = User.objects.first()
if user:
    # Test search for 'tej'
    results = LeadProjectAssociation.objects.filter(
        is_archived=False,
        lead__name__icontains='tej'
    )
    print(f"Searching for 'tej': Found {results.count()} results")
    for r in results[:3]:
        print(f"  - {r.lead.name} ({r.lead.phone}) - Status: {r.status}")
    
    # Test search for 'bhu'
    results = LeadProjectAssociation.objects.filter(
        is_archived=False,
        lead__name__icontains='bhu'
    )
    print(f"\nSearching for 'bhu': Found {results.count()} results")
    for r in results[:3]:
        print(f"  - {r.lead.name} ({r.lead.phone}) - Status: {r.status}")

# Test 2: Check URL patterns
print("\n" + "=" * 60)
print("TEST 2: URL Pattern Verification")
print("=" * 60)

from django.urls import reverse, resolve

try:
    url = reverse('leads:track_call_click', kwargs={'pk': 2056})
    print(f"✓ URL pattern for track_call_click: {url}")
except Exception as e:
    print(f"✗ Error: {e}")

try:
    url = reverse('leads:search_existing_visits')
    print(f"✓ URL pattern for search_existing_visits: {url}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Check if getCookie function is in template
print("\n" + "=" * 60)
print("TEST 3: Template JavaScript Functions")
print("=" * 60)

with open('templates/leads/list.html', 'r') as f:
    content = f.read()
    if 'function getCookie' in content:
        print("✓ getCookie function found in template")
    else:
        print("✗ getCookie function NOT found in template")
    
    if 'function trackCallClick' in content:
        print("✓ trackCallClick function found in template")
    else:
        print("✗ trackCallClick function NOT found in template")
    
    if '/leads/${leadId}/track-call-click/' in content:
        print("✓ Correct URL pattern in trackCallClick function")
    else:
        print("✗ Incorrect URL pattern in trackCallClick function")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
