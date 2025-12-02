"""
Override Django's createsuperuser command to automatically set role='super_admin'
"""
from django.contrib.auth.management.commands.createsuperuser import Command as BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create a superuser with super_admin role'

    def handle(self, *args, **options):
        # Store username before calling parent
        username = options.get('username')
        
        # Call the parent handle method to create the user
        # This will prompt for username, email, password if not provided
        super().handle(*args, **options)
        
        # Get the username - either from options or from the most recently created superuser
        if not username:
            try:
                # Get the most recently created superuser
                user = User.objects.filter(is_superuser=True).order_by('-date_joined').first()
                if user:
                    username = user.username
            except Exception:
                pass
        
        # Set role to super_admin for the created user
        if username:
            try:
                user = User.objects.get(username=username, is_superuser=True)
                if user.role != 'super_admin':
                    user.role = 'super_admin'
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'\n✓ Successfully set role to "super_admin" for user "{username}"'
                        )
                    )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" not found after creation')
                )

