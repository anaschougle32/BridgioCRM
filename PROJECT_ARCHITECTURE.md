# Bridgio CRM - Complete System Architecture & Understanding

## 🏗️ SYSTEM OVERVIEW

**Bridgio CRM** is a comprehensive real estate CRM system built with:
- **Backend**: Django 4.2.7
- **Database**: SQLite (Phase 1, PostgreSQL ready)
- **Frontend**: Tailwind CSS + htmx
- **Authentication**: Custom User model with 6 role-based access control
- **Theme**: Premium Olive (#556B2F, #6B8E23)

---

## 📦 PROJECT STRUCTURE

```
BridgioCRM/
├── accounts/          # User authentication, roles, audit logs
├── projects/          # Project management, configurations, units
├── leads/            # Lead management (New Visit, Pretagging, OTP)
├── bookings/         # Booking and payment management
├── attendance/       # Geo-location based attendance
├── channel_partners/ # CP master data and management
├── reports/          # Analytics and reporting
├── bridgio/          # Main project settings
└── templates/        # HTML templates with Tailwind CSS
```

---

## 👥 USER ROLES & PERMISSIONS

### 1. **Super Admin**
- Full system access
- Creates Mandate Owners and Site Heads
- Sees all projects, leads, bookings, employees
- Can assign employees to projects
- Can assign leads with daily quotas

### 2. **Mandate Owner** (EXACTLY LIKE SUPER ADMIN)
- **Same permissions as Super Admin** (recently updated)
- Sees all projects, leads, bookings, employees
- Can assign employees to projects
- Can assign leads with daily quotas
- Cannot create Super Admins
- Display name: "Mandate Owner" (not "Super Admin")

### 3. **Site Head** (Project Admin)
- Manages one/multiple projects
- **Strict isolation**: Only sees their own projects and employees assigned to their projects
- Cannot see other site heads' data or telecallers
- Assigns leads to employees (with daily quotas)
- Checks attendance for their projects
- Creates employees: Sourcing Managers, Telecallers, Closing Managers

### 4. **Closing Manager**
- Handles in-person visit stage
- Sends OTP to verify pretagged phone numbers (ONLY role that can send/verify OTP)
- Full calling module
- Creates bookings
- Adds payment entries
- Sees only assigned leads

### 5. **Sourcing Manager**
- Creates: New Visit + Pretagging
- Cannot verify OTP
- Pretag leads go to Closing Manager queue
- Sees leads they created or are assigned to

### 6. **Telecaller**
- Only calling module & reminders
- Cannot change key statuses like Booking
- Sees only assigned leads

---

## 🗄️ DATA MODEL ARCHITECTURE

### **Core Models**

#### 1. **User (accounts.User)**
- Extends AbstractUser
- Fields: `role`, `phone`, `mandate_owner` (FK to self), `assigned_projects` (M2M)
- Methods: `is_super_admin()`, `is_mandate_owner()`, `is_site_head()`, etc.
- **Key Relationship**: `assigned_projects` M2M links employees to projects

#### 2. **Project (projects.Project)**
- Fields: `name`, `builder_name`, `location`, `rera_id`, `project_type`, `mandate_owner` (FK), `site_head` (FK)
- Tower/Unit Structure: `number_of_towers`, `floors_per_tower`, `units_per_floor`
- Settings: `default_commission_percent`, `auto_assignment_strategy`
- Related: `configurations`, `assigned_telecallers` (M2M reverse)

#### 3. **ProjectConfiguration (projects.ProjectConfiguration)**
- Represents BHK types: "1BHK", "2BHK", "3BHK", etc.
- Fields: `name`, `price_per_sqft`, `stamp_duty_percent`, `gst_percent`, `registration_charges`, `legal_charges`, `development_charges`
- Methods: `calculate_agreement_value()`, `calculate_total_cost()`
- **Key**: Multiple area types per configuration (e.g., 1BHK can have 379sqft or 404sqft)

#### 4. **ConfigurationAreaType (projects.ConfigurationAreaType)**
- Represents area variations within a configuration
- Fields: `carpet_area`, `buildup_area`, `rera_area`, `description`
- Example: "1BHK-379sqft", "1BHK-404sqft" (both under Configuration "1BHK")
- Method: `get_display_name()` returns "1BHK-379sqft"

#### 5. **UnitConfiguration (projects.UnitConfiguration)**
- Maps individual units to area types
- Fields: `tower_number`, `floor_number`, `unit_number`, `area_type` (FK), `is_excluded`
- **Unit Numbering**: `floor_num * 100 + unit_idx` (e.g., Floor 1, Unit 1 = 101)
- **Unique Constraint**: `(project, tower_number, floor_number, unit_number)`

#### 6. **Lead (leads.Lead)**
- Main lead entity with 30+ fields
- Client Info: `name`, `phone`, `email`, `age`, `gender`, `locality`, etc.
- Requirement: `project`, `configuration`, `budget`, `purpose`, `visit_type`
- CP Info: `channel_partner` (FK), `cp_name`, `cp_phone`, `cp_rera_number`
- Pretagging: `is_pretagged`, `pretag_status`, `phone_verified`
- Status: `status` (new, contacted, visit_scheduled, visit_completed, discussion, hot, ready_to_book, booked, lost)
- Assignment: `assigned_to` (FK), `assigned_by` (FK), `assigned_at`
- System: `created_by`, `created_at`, `is_archived`

#### 7. **OtpLog (leads.OtpLog)**
- Stores OTP verification logs
- Fields: `otp_hash` (HMAC-SHA256), `attempts`, `max_attempts`, `is_verified`, `expires_at`
- **Security**: OTP stored as hash, never plain text

#### 8. **DailyAssignmentQuota (leads.DailyAssignmentQuota)**
- Daily lead assignment quotas per employee per project
- Fields: `project`, `employee`, `daily_quota`, `is_active`
- **Auto-assignment**: Management command runs daily to assign leads based on quotas

#### 9. **Booking (bookings.Booking)**
- One-to-one with Lead
- Fields: `tower_wing`, `unit_number`, `carpet_area`, `floor`, `final_negotiated_price`, `token_amount`
- CP: `channel_partner`, `cp_commission_percent`
- Properties: `total_paid`, `remaining_balance`

#### 10. **Payment (bookings.Payment)**
- Payment entries for bookings
- Fields: `amount`, `payment_mode`, `payment_date`, `milestone` (FK), `reference_number`

#### 11. **ChannelPartner (channel_partners.ChannelPartner)**
- CP master data
- Fields: `firm_name`, `cp_name`, `cp_unique_id` (5-char: 2 letters + 3 numbers), `phone`, `rera_id`, `cp_type`
- Related: `linked_projects` (M2M)

#### 12. **Attendance (attendance.Attendance)**
- Geo-location based attendance
- Fields: `latitude`, `longitude`, `accuracy_radius`, `selfie_photo`, `check_in_time`, `check_out_time`
- Validation: `is_within_radius` (must be within 20m of project coordinates)

---

## 🔄 KEY BUSINESS FLOWS

### **1. Project Creation Flow**
1. Super Admin/Mandate Owner creates project
2. Adds configurations (1BHK, 2BHK, etc.)
3. For each configuration, adds area types (carpet + buildup area)
4. Saves configurations
5. Maps floors/units to configurations (tower-based)
6. Assigns employees to project (closing managers, sourcing managers, telecallers)

### **2. Lead Creation Flow**
- **New Visit**: All roles can create
- **Pretagging**: Only Sourcing Managers (CP details mandatory)
- Lead goes to unassigned pool
- Site Head assigns leads to employees (with daily quotas)

### **3. Pretagging & OTP Verification Flow**
1. Sourcing Manager creates pretag (CP details mandatory)
2. Lead status: `is_pretagged=True`, `pretag_status='pending_verification'`
3. Closing Manager sees pretag in their queue
4. Closing Manager sends OTP (generates 6-digit, stores hash)
5. OTP sent via SMS/WhatsApp deep link
6. Client provides OTP
7. Closing Manager verifies OTP (max 3 attempts, 5 min expiry)
8. If verified: `phone_verified=True`, `pretag_status='verified'`
9. Lead becomes eligible for booking

### **4. Lead Assignment Flow**
1. Site Head/Super Admin/Mandate Owner goes to "Assign Leads"
2. Selects project
3. Sees employees assigned to that project
4. Sets daily quota for each employee (e.g., 10 leads/day)
5. Optionally assigns immediately
6. Daily cron job (`auto_assign_leads`) assigns leads based on quotas

### **5. Employee Assignment Flow**
1. Super Admin/Mandate Owner goes to project detail
2. Clicks "Assign Employees"
3. Selects employees (closing managers, sourcing managers, telecallers)
4. Employees are assigned to project via `assigned_projects` M2M
5. Only assigned employees appear in lead assignment UI

### **6. Lead Upload Flow**
1. Super Admin/Site Head uploads Excel/CSV
2. System auto-detects columns (name, phone, configuration, budget)
3. Uses NLP matching for configurations (`match_configuration()`)
4. Parses budget strings (`parse_budget()`)
5. Creates leads with matched configurations and budgets
6. Errors logged for review

### **7. Booking & Payment Flow**
1. Closing Manager creates booking from lead
2. Enters unit details, negotiated price, token amount
3. Adds payment entries (milestone-based)
4. System calculates: `total_paid`, `remaining_balance`
5. Commission calculated based on `cp_commission_percent`

---

## 🔐 PERMISSION MATRIX (UPDATED)

| Feature | Super Admin | Mandate Owner | Site Head | Closing Manager | Sourcing | Telecaller |
|---------|-------------|---------------|-----------|-----------------|----------|------------|
| View All Projects | ✅ | ✅ | ❌ (only assigned) | ❌ | ❌ | ❌ |
| View All Leads | ✅ | ✅ | ❌ (only project leads) | ❌ (only assigned) | ❌ (only created/assigned) | ❌ (only assigned) |
| View All Employees | ✅ | ✅ | ❌ (only assigned to projects) | ❌ | ❌ | ❌ |
| Create Project | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Edit Project | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign Employees | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign Leads | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| New Visit | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Pretagging | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Send/Verify OTP | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Create Booking | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Add Payment | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

---

## 🎯 CRITICAL BUSINESS RULES

### **Site Head Isolation**
- Site Head 1 **CANNOT** see Site Head 2's:
  - Projects
  - Leads
  - Employees (telecallers, closing managers, sourcing managers)
  - Bookings
  - Attendance records
- **Implementation**: All queries filter by `project__site_head=request.user`

### **Employee Assignment**
- Employees (closing managers, sourcing managers, telecallers) must be assigned to projects via `assigned_projects` M2M
- Only assigned employees appear in lead assignment UI
- Site Head only sees employees assigned to their projects

### **Lead Assignment**
- Daily quotas stored in `DailyAssignmentQuota`
- Auto-assignment runs via management command
- Immediate assignment available in UI
- Leads assigned based on `created_at` order (oldest first)

### **Unit Numbering**
- Format: `floor_num * 100 + unit_idx`
- Example: Floor 1, Unit 1 = 101; Floor 2, Unit 1 = 201
- Same unit numbers can exist in different towers
- Unique constraint: `(project, tower_number, floor_number, unit_number)`

### **Configuration Matching (NLP)**
- Uses `match_configuration()` in `leads/utils.py`
- Handles variations: "1BHK", "1bhk", "1 BHK", "1 or 2 BHK"
- Scoring algorithm: exact match > contains match > fuzzy similarity > number overlap > word overlap
- Threshold: 0.5 (50% similarity)

### **Budget Parsing**
- Uses `parse_budget()` in `leads/utils.py`
- Handles: "35-40 L", "1.2Cr", "5000000", "Open Budget"
- Returns Decimal or None

---

## 🔧 TECHNICAL DETAILS

### **OTP System**
- Generation: 6-digit random number
- Storage: HMAC-SHA256 hash (never plain text)
- Verification: Constant-time comparison (`hmac.compare_digest`)
- Expiry: 5 minutes
- Max Attempts: 3
- Sending: WhatsApp deep link (fallback) or SMS API (Twilio/MSG91)

### **SMS/WhatsApp Integration**
- Primary: WhatsApp deep links (`wa.me/{phone}?text={message}`)
- Fallback: Twilio SMS or MSG91 SMS
- OTP message format: "Here's the OTP to confirm your visit for {project_name}. Thank you. Please provide this OTP to the executive. OTP: *{otp}*"

### **File Upload**
- Supports: Excel (.xlsx, .xls) and CSV
- Auto-column detection with manual override
- NLP matching for configurations and budgets
- Error logging with CSV download

### **Audit Logging**
- Model: `AuditLog` in `accounts/models.py`
- Tracks: user, action, model_name, object_id, changes (JSON)
- Logged for: lead assignment, OTP verification, booking creation, etc.

### **Soft Delete**
- All models use `is_archived` flag (not hard delete)
- Queries filter: `.filter(is_archived=False)`

---

## 📊 URL ROUTING

### **Main URLs (bridgio/urls.py)**
- `/` → Dashboard (role-based)
- `/admin/` → Django admin
- `/accounts/` → Authentication & user management
- `/projects/` → Project management
- `/leads/` → Lead management
- `/bookings/` → Booking & payments
- `/channel-partners/` → CP management
- `/attendance/` → Attendance
- `/reports/` → Analytics

### **Key Endpoints**
- `POST /leads/<pk>/send-otp/` → Send OTP (Closing Manager only)
- `POST /leads/<pk>/verify-otp/` → Verify OTP (Closing Manager only)
- `POST /leads/assign-admin/` → Assign leads with daily quotas
- `GET /projects/<pk>/assign-employees/` → Assign employees to project
- `GET /projects/<pk>/units/` → Interactive unit selection (BookMyShow-style)

---

## 🎨 UI/UX ARCHITECTURE

### **Design System**
- **Colors**: Olive primary (#273B09), Olive secondary (#58641D)
- **Fonts**: DM Sans (headings), Satoshi Variable (body)
- **Components**: Rounded 12-16px, subtle shadows, minimal lines
- **Interactions**: htmx for seamless updates (no page reloads)

### **Key Templates**
- `base.html` → Main layout with sidebar navigation
- `dashboard_*.html` → Role-specific dashboards
- `projects/create.html` → Two-step project creation (configurations → floor mapping)
- `projects/edit.html` → Same two-step workflow for editing
- `projects/unit_selection.html` → BookMyShow-style unit grid
- `leads/assign_admin.html` → Simplified lead assignment UI

---

## 🔄 DATA FLOW DIAGRAMS

### **Lead Lifecycle**
```
New Visit/Pretag → Unassigned Pool → Assigned to Employee → 
Contacted → Visit Scheduled → Visit Completed → 
Discussion → Hot → Ready to Book → Booked
```

### **Pretag Lifecycle**
```
Sourcing Manager creates Pretag → 
Pending Verification → 
Closing Manager sends OTP → 
Client verifies OTP → 
Verified Lead → Eligible for Booking
```

### **Employee-Project Assignment**
```
Super Admin/Mandate Owner → 
Select Project → 
Assign Employees (M2M) → 
Employees appear in Lead Assignment UI → 
Set Daily Quotas → 
Auto-assignment runs daily
```

---

## ⚠️ CRITICAL FIXES IMPLEMENTED

1. **Mandate Owner = Super Admin**: All views updated to treat mandate owners exactly like super admins
2. **Site Head Isolation**: Fixed to only show employees assigned to their projects
3. **Edit Page**: Fixed save button, project type dropdown, JavaScript validation
4. **Employee Assignment UI**: Created new view and template for assigning employees to projects
5. **Simplified Lead Assignment**: Only shows employees assigned to selected project
6. **Unit Tooltip Positioning**: Fixed for bottom units (dynamic positioning)

---

## 🚀 DEPLOYMENT

- **Database**: SQLite (dev) → PostgreSQL (production via DATABASE_URL)
- **Static Files**: WhiteNoise middleware
- **Media Files**: Served via Django in production
- **Environment Variables**: SECRET_KEY, DATABASE_URL, SMS_PROVIDER, etc.

---

## 📝 KEY FILES REFERENCE

- **Models**: `accounts/models.py`, `projects/models.py`, `leads/models.py`, `bookings/models.py`
- **Views**: `bridgio/views.py` (dashboard), `projects/views.py`, `leads/views.py`
- **Utils**: `leads/utils.py` (OTP, NLP matching, budget parsing)
- **SMS**: `leads/sms_adapter.py` (WhatsApp/Twilio/MSG91 adapters)
- **Templates**: `templates/projects/`, `templates/leads/`

---

## ✅ VALIDATION STATUS

- ✅ All models properly defined
- ✅ All views have proper permission checks
- ✅ Site head isolation implemented
- ✅ Mandate owner = super admin permissions
- ✅ Employee assignment working
- ✅ Lead assignment simplified
- ✅ OTP system secure
- ✅ NLP matching functional
- ✅ Unit numbering correct
- ✅ No syntax errors (checked with `python manage.py check`)

---

**Last Updated**: 2025-12-03
**Status**: System fully understood and ready for further development

