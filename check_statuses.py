#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from leads.models import LeadProjectAssociation

statuses = LeadProjectAssociation.objects.values('status').distinct()
print('Available statuses:')
for s in statuses:
    count = LeadProjectAssociation.objects.filter(status=s['status']).count()
    print(f'  {s["status"]}: {count}')

# Also check for any visits with names containing 'tej', 'bhu', 'mo', 'an', 'anas', 'ana'
print('\nSearching for specific leads:')
for search_term in ['tej', 'bhu', 'mo', 'an', 'anas', 'ana']:
    count = LeadProjectAssociation.objects.filter(lead__name__icontains=search_term).count()
    print(f'  Leads with "{search_term}": {count}')
