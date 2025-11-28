"""
Create test users for all roles
Run: python create_test_users.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from accounts.models import User

# Get first mandate owner
mandate_owner = User.objects.filter(role='mandate_owner').first()
if not mandate_owner:
    print("[ERROR] No Mandate Owner found. Please create a Mandate Owner first.")
    exit(1)

print("=" * 60)
print("Creating Test Users")
print("=" * 60)
print(f"\nAssigning all users to Mandate Owner: {mandate_owner.username}\n")

users_to_create = [
    # Site Heads
    {'username': 'sitehead1', 'email': 'sitehead1@bridgio.com', 'role': 'site_head', 'password': 'sitehead123'},
    {'username': 'sitehead2', 'email': 'sitehead2@bridgio.com', 'role': 'site_head', 'password': 'sitehead123'},
    
    # Closing Managers
    {'username': 'closer1', 'email': 'closer1@bridgio.com', 'role': 'closing_manager', 'password': 'closer123'},
    {'username': 'closer2', 'email': 'closer2@bridgio.com', 'role': 'closing_manager', 'password': 'closer123'},
    
    # Sourcing Managers
    {'username': 'sourcing1', 'email': 'sourcing1@bridgio.com', 'role': 'sourcing_manager', 'password': 'sourcing123'},
    {'username': 'sourcing2', 'email': 'sourcing2@bridgio.com', 'role': 'sourcing_manager', 'password': 'sourcing123'},
    
    # Telecallers
    {'username': 'telecaller1', 'email': 'telecaller1@bridgio.com', 'role': 'telecaller', 'password': 'telecaller123'},
    {'username': 'telecaller2', 'email': 'telecaller2@bridgio.com', 'role': 'telecaller', 'password': 'telecaller123'},
]

created_users = []
for user_data in users_to_create:
    username = user_data['username']
    if User.objects.filter(username=username).exists():
        print(f"[SKIP] User {username} already exists, skipping...")
        continue
    
    user = User.objects.create_user(
        username=username,
        email=user_data['email'],
        password=user_data['password'],
        role=user_data['role'],
        mandate_owner=mandate_owner,
        is_active=True
    )
    created_users.append({
        'username': username,
        'password': user_data['password'],
        'role': user.get_role_display()
    })
    print(f"[OK] Created: {username} ({user.get_role_display()})")

print("\n" + "=" * 60)
print("USER CREDENTIALS")
print("=" * 60)
print("\nAll users are assigned to Mandate Owner:", mandate_owner.username)
print("\n" + "-" * 60)
for user in created_users:
    print(f"\nUsername: {user['username']}")
    print(f"Password: {user['password']}")
    print(f"Role: {user['role']}")
    print("-" * 60)

print(f"\n[SUCCESS] Total users created: {len(created_users)}")
print("\nYou can now login with any of these credentials!")

