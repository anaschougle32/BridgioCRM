# Bridgio CRM - Setup Guide

## Initial Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create Superuser
```bash
python manage.py createsuperuser
```

When creating the superuser, you'll need to set the role manually in the Django admin or via Python shell:

```python
python manage.py shell
```

```python
from accounts.models import User
user = User.objects.get(username='your_username')
user.role = 'super_admin'
user.save()
```

### 4. Run Development Server
```bash
python manage.py runserver
```

## Creating Initial Data

### Create a Mandate Owner
1. Go to Admin panel: http://127.0.0.1:8000/admin/
2. Navigate to Users
3. Create a new user with role "Mandate Owner"

### Create a Project
1. Go to Projects in Admin
2. Create a new project
3. Assign Mandate Owner and Site Head
4. Add Project Configurations (1BHK, 2BHK, etc.)
5. Add Payment Milestones

### Create Employees
1. Create users with appropriate roles:
   - Site Head
   - Closing Manager
   - Sourcing Manager
   - Telecaller

## Testing the Application

1. **Login**: http://127.0.0.1:8000/accounts/login/
2. **Dashboard**: http://127.0.0.1:8000/
3. **Leads**: http://127.0.0.1:8000/leads/
4. **Admin**: http://127.0.0.1:8000/admin/

## Role-Based Access

- **Super Admin**: Full access to everything
- **Mandate Owner**: Sees all projects under their mandate
- **Site Head**: Manages projects, assigns leads
- **Closing Manager**: Handles visits, OTP verification, bookings
- **Sourcing Manager**: Creates New Visits and Pretags
- **Telecaller**: Calling module and reminders

## Next Development Steps

1. Implement form handling in `leads/views.py` for create/pretag
2. Implement OTP sending functionality
3. Add Excel export for leads
4. Implement pagination
5. Add WhatsApp deep link generation
6. Complete attendance module with geo-location
7. Add comprehensive dashboards per role


