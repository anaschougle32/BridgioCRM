"""
Delete all leads from the database
Run: python delete_all_leads.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from leads.models import Lead

print("=" * 60)
print("Deleting All Leads")
print("=" * 60)

count = Lead.objects.count()
print(f"\nTotal leads in database: {count}")

if count == 0:
    print("\n✅ No leads to delete. Database is already empty.")
    exit(0)

# Delete all leads
Lead.objects.all().delete()

print(f"\n✅ Successfully deleted {count} lead(s) from the database.")
print("\nYou can now upload leads again!")

