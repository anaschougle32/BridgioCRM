"""
Quick script to set a user as Super Admin
Run: python set_superadmin.py <username>
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from accounts.models import User

if len(sys.argv) < 2:
    print("Usage: python set_superadmin.py <username>")
    sys.exit(1)

username = sys.argv[1]
try:
    user = User.objects.get(username=username)
    user.role = 'super_admin'
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"✅ Successfully set {username} as Super Admin")
    print(f"   Role: {user.role}")
    print(f"   Is Staff: {user.is_staff}")
    print(f"   Is Superuser: {user.is_superuser}")
except User.DoesNotExist:
    print(f"❌ User '{username}' does not exist")
    print("\nAvailable users:")
    for u in User.objects.all():
        print(f"  - {u.username} ({u.get_role_display()})")

