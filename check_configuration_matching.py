"""
Diagnostic script to check configuration matching
Run: python check_configuration_matching.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from projects.models import Project, ProjectConfiguration
from leads.models import Lead
from leads.utils import match_configuration, normalize_configuration_name

print("=" * 60)
print("Configuration Matching Diagnostic")
print("=" * 60)

# Check all projects
projects = Project.objects.filter(is_active=True)
print(f"\nFound {projects.count()} active project(s)\n")

for project in projects:
    print(f"Project: {project.name} (ID: {project.id})")
    configs = project.configurations.all()
    print(f"  Configurations: {configs.count()}")
    if configs.exists():
        for config in configs:
            print(f"    - {config.name}")
    else:
        print("    ⚠️  NO CONFIGURATIONS FOUND FOR THIS PROJECT!")
        print("    You need to add configurations in the admin panel or project settings.")
    print()

# Test matching with sample inputs
print("\n" + "=" * 60)
print("Testing Configuration Matching")
print("=" * 60)

test_inputs = [
    "1BHK",
    "1bhk",
    "1 BHK",
    "1 or 2 BHK",
    "1/2 BHK",
    "2BHK",
    "2 BHK",
    "3BHK",
]

for project in projects:
    configs = project.configurations.all()
    if not configs.exists():
        continue
    
    print(f"\nProject: {project.name}")
    for test_input in test_inputs:
        matched = match_configuration(test_input, project)
        normalized = normalize_configuration_name(test_input)
        if matched:
            print(f"  ✓ '{test_input}' -> '{matched.name}' (normalized: '{normalized}')")
        else:
            print(f"  ✗ '{test_input}' -> No match (normalized: '{normalized}')")

# Check leads without configurations
print("\n" + "=" * 60)
print("Leads Without Configurations")
print("=" * 60)

leads_without_config = Lead.objects.filter(configuration__isnull=True, is_archived=False)
print(f"Total leads without configuration: {leads_without_config.count()}")

if leads_without_config.exists():
    print("\nSample leads (first 10):")
    for lead in leads_without_config[:10]:
        print(f"  - {lead.name} (Project: {lead.project.name}, ID: {lead.id})")

print("\n" + "=" * 60)
print("Recommendations:")
print("=" * 60)
print("1. Make sure each project has configurations set up")
print("2. Check the Django admin or project settings to add configurations")
print("3. Re-upload leads after adding configurations")
print("4. Check server logs for configuration matching warnings")
print("=" * 60)

