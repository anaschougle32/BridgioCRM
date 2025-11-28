# Bridgio CRM

A comprehensive real estate CRM system built with Django, htmx, and Tailwind CSS.

## Features

- **6 Role-Based Access Control**: Super Admin, Mandate Owner, Site Head, Closing Manager, Sourcing Manager, Telecaller
- **Lead Management**: New Visits, Pretagging, OTP Verification
- **Project Management**: Multi-project support with configurations and milestones
- **Booking & Payments**: Complete booking lifecycle with payment tracking
- **Channel Partner Management**: CP master data and commission tracking
- **Attendance System**: Geo-location based attendance with selfie verification
- **Calling Module**: Call logs and follow-up reminders
- **Premium UI**: Olive-themed design with Tailwind CSS and htmx interactions

## Tech Stack

- **Backend**: Django 4.2.7
- **Database**: SQLite (Phase 1, PostgreSQL ready)
- **Frontend**: Tailwind CSS, htmx
- **Authentication**: Django's built-in auth with custom User model

## Installation

1. **Clone the repository**
   ```bash
   cd BridgioCRM
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

5. **Run development server**
   ```bash
   python manage.py runserver
   ```

6. **Access the application**
   - Main app: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## Project Structure

```
BridgioCRM/
├── accounts/          # User authentication and roles
├── projects/          # Project management
├── leads/            # Lead management (New Visit, Pretagging)
├── bookings/         # Booking and payment management
├── attendance/       # Attendance with geo-location
├── channel_partners/ # CP management
├── templates/        # HTML templates
├── static/           # Static files
└── bridgio/          # Main project settings
```

## User Roles

1. **Super Admin**: Full system access
2. **Mandate Owner**: Manages multiple projects
3. **Site Head**: Manages one/multiple projects, assigns leads
4. **Closing Manager**: Handles visits, OTP verification, bookings
5. **Sourcing Manager**: Creates New Visits and Pretagging
6. **Telecaller**: Calling module and reminders

## Key Modules

### Leads Module
- New Visit creation (all roles)
- Pretagging (Sourcing Manager only)
- OTP Verification (Closing Manager only)
- Lead assignment (Site Head)
- Status tracking

### Booking Module
- Booking creation
- Payment entries
- Milestone tracking
- Commission calculation

### Attendance Module
- Geo-location verification (within 20m)
- Selfie capture
- Check-in/Check-out tracking

## Development Notes

- All models use soft-delete (is_archived flag)
- Audit logging for all critical actions
- Role-based middleware for access control
- htmx for seamless UI interactions
- Premium olive theme (#556B2F, #6B8E23)

## Next Steps

- Implement OTP SMS integration (MSG91)
- Add Excel export functionality
- Implement pagination for large datasets
- Add WhatsApp deep link generation
- Create comprehensive dashboards per role

## License

Proprietary - Mohammad Anas & Partners


