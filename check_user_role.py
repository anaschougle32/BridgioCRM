"""
Quick script to check and set user role
Run: python check_user_role.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from accounts.models import User

print("=" * 50)
print("Current Users and Roles:")
print("=" * 50)
for user in User.objects.all():
    print(f"Username: {user.username}")
    print(f"  Role: {user.role} ({user.get_role_display()})")
    print(f"  is_super_admin(): {user.is_super_admin()}")
    print(f"  is_staff: {user.is_staff}")
    print(f"  is_superuser: {user.is_superuser}")
    print()

