from django.core.management.base import BaseCommand
from django.core.management import call_command
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Load initial data from fixtures (runs during deployment)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-if-exists',
            action='store_true',
            help='Skip loading if data already exists',
        )

    def handle(self, *args, **options):
        fixtures_dir = os.path.join(settings.BASE_DIR, 'fixtures')
        fixture_file = os.path.join(fixtures_dir, 'initial_data.json')
        
        # Check if fixture file exists
        if not os.path.exists(fixture_file):
            self.stdout.write(self.style.WARNING(f'Fixture file not found: {fixture_file}'))
            self.stdout.write(self.style.WARNING('Skipping data load. Database will be empty.'))
            return
        
        # Check if data already exists (optional)
        if options['skip_if_exists']:
            from accounts.models import User
            if User.objects.exists():
                self.stdout.write(self.style.SUCCESS('Data already exists. Skipping load.'))
                return
        
        try:
            self.stdout.write('Loading initial data from fixtures...')
            call_command('loaddata', fixture_file, verbosity=0)
            self.stdout.write(self.style.SUCCESS('✅ Initial data loaded successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error loading fixtures: {e}'))
            # Don't fail the build if fixtures can't be loaded
            self.stdout.write(self.style.WARNING('Continuing with empty database...'))

