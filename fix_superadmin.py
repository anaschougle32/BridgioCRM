"""
Quick script to set your user as Super Admin
Run: python fix_superadmin.py <username>
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from accounts.models import User

if len(sys.argv) < 2:
    print("=" * 60)
    print("Super Admin Setup Script")
    print("=" * 60)
    print("\nUsage: python fix_superadmin.py <username>")
    print("\nAvailable users:")
    print("-" * 60)
    for u in User.objects.all():
        print(f"  {u.username:20} | Role: {u.role:20} | Super Admin: {u.is_super_admin()}")
    sys.exit(1)

username = sys.argv[1]

try:
    user = User.objects.get(username=username)
    
    print("=" * 60)
    print(f"Setting {username} as Super Admin...")
    print("=" * 60)
    print(f"\nBefore:")
    print(f"  Role: {user.role}")
    print(f"  is_staff: {user.is_staff}")
    print(f"  is_superuser: {user.is_superuser}")
    print(f"  is_super_admin(): {user.is_super_admin()}")
    
    # Set as super admin
    user.role = 'super_admin'
    user.is_staff = True
    user.is_superuser = True
    user.save()
    
    # Refresh from DB
    user.refresh_from_db()
    
    print(f"\nAfter:")
    print(f"  Role: {user.role}")
    print(f"  is_staff: {user.is_staff}")
    print(f"  is_superuser: {user.is_superuser}")
    print(f"  is_super_admin(): {user.is_super_admin()}")
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS! User is now Super Admin")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Logout and login again")
    print("2. You should see 'Super Admin Dashboard'")
    print("3. Navigation should show: Users, Projects, Leads")
    
except User.DoesNotExist:
    print(f"\n❌ ERROR: User '{username}' does not exist")
    print("\nAvailable users:")
    for u in User.objects.all():
        print(f"  - {u.username}")

