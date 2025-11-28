# Super Admin Setup Guide

## Quick Setup Steps

### 1. Set Your User as Super Admin

**Option A: Using Django Admin**
1. Go to: http://127.0.0.1:8000/admin/
2. Navigate to: Accounts > Users
3. Find your user and click to edit
4. Set:
   - Role: `super_admin`
   - Staff status: ✅ (checked)
   - Superuser status: ✅ (checked)
5. Save

**Option B: Using Python Script**
```bash
python set_superadmin.py <your_username>
```

**Option C: Using Django Shell**
```bash
python manage.py shell
```
Then run:
```python
from accounts.models import User
user = User.objects.get(username='<your_username>')
user.role = 'super_admin'
user.is_staff = True
user.is_superuser = True
user.save()
print(f"✅ {user.username} is now Super Admin")
```

**Option D: Using Management Command**
```bash
python manage.py set_super_admin <your_username>
```

### 2. Check Your Role
```bash
python check_user_role.py
```

### 3. Login and Test
1. Logout and login again
2. You should see "Super Admin Dashboard" with:
   - System-wide statistics
   - Top Projects by Revenue
   - Channel Partner Leaderboard
   - User Statistics by Role
   - Navigation: Dashboard, Users, Projects, Leads, Admin, Logout

## Super Admin Features

### ✅ User Management
- **URL**: `/accounts/users/`
- Create users with any role
- Edit user details
- Assign users to Mandate Owners
- Toggle active/inactive status
- Search and filter by role

### ✅ Project Management
- **URL**: `/projects/`
- Create projects
- Assign to Mandate Owners and Site Heads
- View project statistics
- Edit project details

### ✅ Dashboard
- **URL**: `/`
- System-wide analytics
- All projects overview
- Revenue tracking
- CP leaderboard
- User statistics

### ✅ Leads Management
- **URL**: `/leads/`
- View all leads across all projects
- Filter and search
- View lead details

## Creating Test Data

### Create a Mandate Owner
1. Go to: `/accounts/users/create/`
2. Fill in:
   - Username: `mandate1`
   - Email: `mandate1@example.com`
   - Password: (choose a password)
   - Role: `Mandate Owner`
   - Active: ✅
3. Save

### Create a Site Head
1. Go to: `/accounts/users/create/`
2. Fill in:
   - Username: `sitehead1`
   - Email: `sitehead1@example.com`
   - Password: (choose a password)
   - Role: `Site Head`
   - Mandate Owner: Select the Mandate Owner created above
   - Active: ✅
3. Save

### Create a Project
1. Go to: `/projects/create/`
2. Fill in:
   - Project Name: `Test Project`
   - Builder Name: `Test Builder`
   - Location: `Mumbai, Maharashtra`
   - Project Type: `Residential`
   - Mandate Owner: Select the Mandate Owner
   - Site Head: Select the Site Head
3. Save

### Create Employees
1. Go to: `/accounts/users/create/`
2. Create users with roles:
   - Closing Manager
   - Sourcing Manager
   - Telecaller
3. Assign them to the Mandate Owner

## Troubleshooting

### Dashboard shows basic view instead of Super Admin
- Check your role: `python check_user_role.py`
- Ensure role is set to `super_admin`
- Logout and login again
- Clear browser cache

### Navigation doesn't show Super Admin links
- Check that `user.is_super_admin()` returns `True`
- Verify `is_staff` and `is_superuser` are both `True`

### Fonts not loading
- Check browser console for errors
- Verify internet connection (fonts load from CDN)
- Fonts used:
  - DM Sans: Google Fonts
  - Satoshi: Fontshare API

## Next Steps

After setting up Super Admin:
1. Create Mandate Owners
2. Create Projects
3. Create Site Heads and assign to projects
4. Create employees (Closing Managers, Sourcing, Telecallers)
5. Test all features

