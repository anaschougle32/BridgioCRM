from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Set a user as Super Admin'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to set as Super Admin')

    def handle(self, *args, **options):
        username = options['username']
        try:
            user = User.objects.get(username=username)
            user.role = 'super_admin'
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully set {username} as Super Admin')
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" does not exist')
            )

