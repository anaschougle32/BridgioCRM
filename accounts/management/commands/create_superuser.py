from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create a super admin user'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='Username for super admin')
        parser.add_argument('--email', type=str, default='admin@bridgio.com', help='Email for super admin')
        parser.add_argument('--password', type=str, default='admin123', help='Password for super admin')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User {username} already exists.'))
            return

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='super_admin',
            is_staff=True,
            is_superuser=True,
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS(f'Super admin user "{username}" created successfully!'))
        self.stdout.write(self.style.SUCCESS(f'Username: {username}'))
        self.stdout.write(self.style.SUCCESS(f'Password: {password}'))

