"""
Management command to populate GlobalConfiguration with predefined values
Run this before migrating to the new Lead-Project Association model
"""
from django.core.management.base import BaseCommand
from leads.models import GlobalConfiguration


class Command(BaseCommand):
    help = 'Populate GlobalConfiguration with predefined configuration types'

    def handle(self, *args, **options):
        configs = [
            {'name': '1BHK', 'display_name': '1BHK', 'order': 1},
            {'name': '2BHK', 'display_name': '2BHK', 'order': 2},
            {'name': '3BHK', 'display_name': '3BHK', 'order': 3},
            {'name': '4BHK', 'display_name': '4BHK', 'order': 4},
            {'name': '5BHK', 'display_name': '5BHK', 'order': 5},
            {'name': 'PentHouse', 'display_name': 'PentHouse', 'order': 6},
            {'name': 'Villa', 'display_name': 'Villa', 'order': 7},
            {'name': 'Plot', 'display_name': 'Plot', 'order': 8},
        ]
        
        created_count = 0
        for config in configs:
            obj, created = GlobalConfiguration.objects.get_or_create(
                name=config['name'],
                defaults={
                    'display_name': config['display_name'],
                    'order': config['order'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {obj.display_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Already exists: {obj.display_name}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully populated {created_count} new configurations.'))

