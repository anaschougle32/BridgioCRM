"""
Export all database data to fixtures for deployment
Run this locally to export your database before deploying
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from django.core.management import call_command
from django.conf import settings

if __name__ == '__main__':
    print("Exporting database to fixtures...")
    
    # Create fixtures directory if it doesn't exist
    fixtures_dir = os.path.join(settings.BASE_DIR, 'fixtures')
    os.makedirs(fixtures_dir, exist_ok=True)
    
    # Export all data
    output_file = os.path.join(fixtures_dir, 'initial_data.json')
    
    try:
        call_command('dumpdata', 
                    exclude=['contenttypes', 'auth.permission', 'sessions'],
                    natural_foreign=True,
                    natural_primary=True,
                    indent=2,
                    output=output_file)
        print(f"✅ Database exported successfully to {output_file}")
        print(f"📦 File size: {os.path.getsize(output_file) / 1024:.2f} KB")
    except Exception as e:
        print(f"❌ Error exporting database: {e}")

