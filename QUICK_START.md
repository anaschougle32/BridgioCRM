# Quick Start Guide - Super Admin Setup

## 🚀 Quick Fix for Super Admin Dashboard

### Step 1: Set Your User as Super Admin

Run this command (replace `your_username` with your actual username):
```bash
python fix_superadmin.py your_username
```

Or use Django Admin:
1. Go to: http://127.0.0.1:8000/admin/
2. Accounts > Users > Your User
3. Set Role to: `super_admin`
4. Check: Staff status ✅
5. Check: Superuser status ✅
6. Save

### Step 2: Logout and Login Again

This ensures the session is refreshed with your new role.

### Step 3: Verify

You should now see:
- ✅ "Super Admin Dashboard" title
- ✅ Navigation: Dashboard, Users, Projects, Leads, Admin, Logout
- ✅ System-wide statistics
- ✅ Top Projects by Revenue table
- ✅ Channel Partner Leaderboard
- ✅ User Statistics by Role

## 📋 Super Admin Features Available

### 1. User Management (`/accounts/users/`)
- ✅ Create users with any role
- ✅ Edit user details
- ✅ Assign users to Mandate Owners
- ✅ Toggle active/inactive
- ✅ Search and filter

### 2. Project Management (`/projects/`)
- ✅ Create projects
- ✅ Assign to Mandate Owners
- ✅ Assign Site Heads
- ✅ View project statistics
- ✅ Edit project details

### 3. Dashboard (`/`)
- ✅ System-wide analytics
- ✅ All projects overview
- ✅ Revenue tracking
- ✅ CP leaderboard

### 4. Leads Management (`/leads/`)
- ✅ View all leads across all projects
- ✅ Filter and search
- ✅ View lead details

## 🎨 Fonts

The system now uses:
- **DM Sans** (from Google Fonts) - for headings
- **Satoshi** (from Fontshare) - for body text

Both fonts are loaded via CDN and should work automatically.

## 🧪 Testing Checklist

- [ ] Login as Super Admin
- [ ] See Super Admin Dashboard
- [ ] Navigate to Users - create a Mandate Owner
- [ ] Navigate to Projects - create a Project
- [ ] Assign Site Head to Project
- [ ] Create employees (Site Head, Closing Manager, Sourcing, Telecaller)
- [ ] View all leads
- [ ] Check navigation menu

## 🐛 Troubleshooting

**Dashboard shows basic view:**
- Run: `python fix_superadmin.py your_username`
- Logout and login again
- Check: `python check_user_role.py`

**Fonts not loading:**
- Check browser console
- Verify internet connection
- Fonts load from CDN (Google Fonts & Fontshare)

**Navigation missing links:**
- Ensure role is `super_admin`
- Check `is_staff` and `is_superuser` are both `True`

## 📝 Next Steps

1. Create Mandate Owners
2. Create Projects
3. Create Site Heads
4. Create Employees
5. Test all features

---

**Need Help?** Check `SUPER_ADMIN_SETUP.md` for detailed instructions.

