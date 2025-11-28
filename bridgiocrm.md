# Bridgio CRM — **Full, Ultra-Detailed Project Requirement Document (Updated & Expanded)**
**Version:** 2.0  
**Date:** 2025-11-27  
**Prepared For:** Mohammad Anas & Partners

---
# 🧩 **TABLE OF CONTENTS**
1. Introduction & Vision
2. Business Goals & Problems Bridgio Solves
3. System Overview
4. User Roles (6 Roles — Fully Redefined)
5. Permissions Matrix (Role-wise Capabilities)
6. Global Functional Requirements
7. Project Module (Ultra Detailed)
8. Leads Module — New Visit + Pretagging (Very Detailed)
9. Pretagging OTP Verification — Closing Managers (Full Flow)
10. Lead Assignment (Project Admin / Site Head)
11. Channel Partner (CP) Management
12. Attendance System (Geo + Selfie) — Engine Logic
13. Calling Workflow (Telecallers + Closers)
14. Booking, Payments, Milestones, Commissions
15. Dashboards (Global / Project / Employee)
16. Data Model — Expanded Entity Definitions
17. System-Wide Data Flow Diagrams (Textual)
18. UI/UX Design Specification (Premium Olive Theme)
19. htmx Interaction Architecture
20. Technical Stack Architecture
21. Security, Logging & Audit Requirements
22. Performance & Scalability Guidelines
23. Future-Proofing & Phase 2 Features

---

# 1. ⭐ **INTRODUCTION & VISION**
**Bridgio CRM** is designed to become **India’s most efficient, mandate-oriented real estate CRM**, handling:
- Mandate owners managing multiple projects
- Site heads allocating leads to teams
- Sourcing managers pretagging CP leads
- Telecallers running structured calling pipelines
- Closing managers verifying, converting & booking clients
- Complete transparency between all stakeholders

Bridgio’s objective is **to reduce leakages, increase conversions, prevent fake CP entries, and give mandate owners full clarity & control.**

---

# 2. 🎯 **BUSINESS GOALS & PROBLEMS BRIDGIO SOLVES**
### **Key real estate mandate problems Bridgio addresses:**
- Fake/duplicate leads by sourcing managers
- CP pretags without verification
- No tracking of who handled which lead
- Poor follow-up by telecallers
- Leads lost because of no proper reminders
- No clarity on which CP booked which deal
- No transparent payment tracking
- Attendance manipulation by remote staff
- No project-wise performance visibility

### **Bridgio solves this by:**
- OTP verification handled *only by Closing Managers*
- Project-wise lead allocation
- Strict role-based workflows
- CP-wise analytics
- Automated reminders
- Geo-based attendance
- Detailed booking + payment lifecycle tracking

---

# 3. 🏗️ **SYSTEM OVERVIEW**
Bridgio is a **6-role, mandate-first CRM** built on:
- Django backend (robust RBAC + forms)
- htmx UI interactions (no page reloads)
- Tailwind CSS (premium olive theme)
- SQLite (Phase 1) → PostgreSQL ready

The system is designed around 6 pillars:
1. **Lead Engine** (New Visit + Pretagging)
2. **OTP Verification Engine**
3. **Calling Engine**
4. **Project Assignment Engine**
5. **Booking & Payment Engine**
6. **Attendance Engine**

---

# 4. 👥 **USER ROLES (UPDATED — 6 ROLES)**
### **1. Super Admin**
- Full controls — system-level
- Creates Mandate Owners, Site Heads
- Can access every project, lead, booking

### **2. Mandate Owner (Business Head)**
- Sees **all projects under their mandate**
- High-level analytics
- Cannot create Super Admins

### **3. Site Head (Project Admin)**
- Admin for one/multiple projects
- Creates employees: Sourcing / Telecallers / Closers
- Assigns leads to employees (with quantity control)
- Checks attendance for their project
 
### **4. Closing Manager**
- Handles **in-person visit stage**
- Sends OTP to verify pretagged phone numbers
- Full calling module
- Creates bookings
- Adds payment entries

### **5. Sourcing Manager**
- Creates: **New Visit** + **Pretagging**
- Cannot verify OTP
- Pretag leads go to Closing Manager queue

### **6. Telecaller**
- Only calling module & reminders
- Cannot change key statuses like Booking

---

# 5. 🔐 **PERMISSIONS MATRIX (ROLE-WISE)**
| Feature | Super Admin | Mandate Owner | Site Head | Closing Manager | Sourcing | Telecaller |
|--------|-------------|---------------|-----------|------------------|----------|------------|
| New Visit | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Pretagging | ❌ | ❌ | ❌ | ❌ | ✔ | ❌ |
| OTP Verify Pretag | ❌ | ❌ | ❌ | ✔ | ❌ | ❌ |
| Lead Assignment | ✔ | ✔ | ✔ | ❌ | ❌ | ❌ |
| Calling | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Booking Creation | ✔ | ✔ | ✔ | ✔ | ❌ | ❌ |
| Payment Updates | ✔ | ✔ | ✔ | ✔ | ❌ | ❌ |
| Attendance Marking | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |

---

# 6. ⚙️ **GLOBAL FUNCTIONAL REQUIREMENTS**
### **Every module must support:**
- htmx-based inline updates
- Real-time role-based restrictions
- Audit logs of who changed what
- Export of table views to Excel
- Soft-delete (archive) not hard delete
- Pagination, searching & filtering
- High performance even with 2–5 lakh leads

---

# 7. 🏢 **PROJECT MODULE (VERY DETAILED)**
Each project has:
- Name
- Builder Name
- Location
- RERA ID
- Project Type (Residential / Commercial / Mixed)
- Configurations (multi-select)
- Starting Price Range
- Inventory Summary
- Site coordinates (needed for attendance)
- Assigned Site Head

### **Project Settings:**
- Default commission % per booking
- Payment milestone patterns
- Auto-assignment strategy for leads (Round Robin / Manual)

### **Project Dashboard:**
- Total Leads
- New Visits today
- Verified Pretags
- Upcoming Visits
- Bookings
- Payment collection status
- Employee performance metrics

---

# 8. 🧾 **LEADS MODULE — NEW VISIT (DETAILED FIELDS)**
### **New Visit Form (Available to All):**
#### Client Information
- Name
- Phone (OTP optional at this stage)
- Email
- Age
- Gender
- Locality
- Current Residence (Own/Rent)
- Occupation (Self Emp / Service / Homemaker / Business / Retired / Other)
- Company Name
- Designation

#### Requirement Details
- Project
- Configuration
- Budget
- Purpose (Investment / First Home / Second Home / Retirement Home)
- Visit Type (Family / Alone)
- First Visit or Revisit
- How did you hear about us

#### CP (Optional)
- Firm Name
- CP Name
- CP Phone
- RERA Number

#### System Metadata
- Created by user
- Role of creator
- Created date & time

---

# 9. 🟩 **PRETAGGING MODULE (SOURCING ONLY)**
Pretagging is identical to New Visit **but CP details are mandatory** and:

### **Pretag Flags**
- `is_pretagged = true`
- `pretag_status = pending_verification`
- `phone_verified = false`

### **Pretag Lifecycle**
**(1) Created by Sourcing → goes to Pretag Queue**
**(2) Closing Manager sees pretags** when they come for site visit
**(3) Closing Manager Sends OTP**
**(4) Client validates OTP → Pretag becomes Verified Lead**

### The pretags must appear in:
- Closing Manager dashboard: **Upcoming Visits / Pending OTP Verification**
- Site Head dashboard: overview only

---

# 10. 🔐 **OTP VERIFICATION ENGINE — CLOSING MANAGER ONLY**
### Detailed Flow
1. Client arrives / connects on call with closer.
2. Closing Manager opens lead detail → clicks **Send OTP**.
3. System generates OTP, stores hash in `OtpLog`.
4. SMS API pushes OTP to client.
5. Closing Manager inputs received OTP.
6. System verifies OTP. If correct:
   - `phone_verified = true`
   - `pretag_status = verified`
   - Lead becomes eligible for booking
7. Audit log created.

### OTP Rules
- Valid for **5 minutes**
- Max **3 attempts**
- OTP cannot be sent by any other role

---

# 11. 🎯 **LEAD ASSIGNMENT — SITE HEAD ONLY**
### Assignment Flow
1. Site Head selects project.
2. Sees list of unassigned leads.
3. Selects employees → enters number of leads.
4. System allocates leads using:
   - Round robin
   - Or sequential
5. Assigned leads appear instantly in employee dashboards.

### Audit Trail
- Who assigned
- To whom
- Lead IDs

---

# 12. 🤝 **CHANNEL PARTNER (CP) MANAGEMENT MODULE**
### CP Master Fields
- Firm Name
- CP Name
- Phone
- Email
- RERA ID
- CP Type (Broker / Agency / Individual)
- Working Area
- Linked Projects

### CP Import
- Excel upload
- Error logs for invalid format / duplicates

### CP WhatsApp Blasts
- Message template engine
- Placeholder replacements like {{project}}, {{price}}, {{offer}}
- Generated via pure WhatsApp deep links

---

# 13. 📍 **ATTENDANCE MODULE (GEO + SELFIE)**
### Key Rules
- Must be **within 20m** of project/office coordinates
- Must click selfie using device camera
- Browser/device location required

### Stored Data
- Latitude / Longitude
- Accuracy Radius
- Timestamp
- Selfie photo
- User agent
- Project mapping

### Reports
- Attendance summary per project
- Late check-ins
- Early check-outs

---

# 14. 📞 **CALLING MODULE — TELECALLERS & CLOSERS**
### Shared Features
- Call using tel: link
- Call notes
- Call outcomes (Connected / Not Reachable / Switched Off / Wrong Number)
- Follow-up reminder creation
- WhatsApp one-click message templates

### Closing Manager Additional Features
- OTP sending for visit confirmation
- Mark lead as **Discussion / Hot / Ready to Book**
- Move lead to Booking stage

---

# 15. 🧾 **BOOKING & PAYMENT ENGINE (VERY DETAILED)**
### Booking Fields
- Project
- Tower / Wing
- Unit Number
- Carpet Area
- Floor
- Final Negotiated Price
- CP Involved
- Token Amount
- Token Receipt Proof

### Payment Entries
- Amount
- Mode (UPI / Cash / Cheque / RTGS)
- Date
- Milestone (Demand 1, Demand 2…)
- Reference No

### System Auto-Calculates
- Total Paid
- Remaining Balance
- Pending Milestones

### Reminders
- Auto reminders for overdue payments
- WhatsApp follow-up templates

---

# 16. 📊 **FULL DASHBOARDS (DETAILED)**
### **Super Admin Dashboard**
- All mandates
- All projects
- Total revenue generated
- Overall booking rate
- CP leaderboard

### **Mandate Owner Dashboard**
- Project comparison chart
- Team performance
- Payment collection trends

### **Site Head Dashboard**
- Unassigned leads
- Visits today
- Pretags pending verification
- Assigned leads per employee

### **Closing Manager Dashboard**
- Pretag queue
- Today’s visits
- Pending OTP verifications
- Hot leads

### **Telecaller Dashboard**
- Today’s callbacks
- Leads untouched for >24 hours
- Follow-up reminders

### **Sourcing Dashboard**
- Visits created
- Pretags awaiting closer action
- CP conversions

---

# 17. 🧱 **DATA MODEL — EXPANDED ENTITY DEFINITIONS**
### Lead Entity (30+ fields)
Includes complete client, CP, project, visit, verification, status lifecycle.

### Booking Entity
Stores pricing, unit, negotiations, CP details.

### Payment Entity
Stores receipts and auto-calculations.

### OTP Log Entity
Stores hashed OTP, attempts, timestamps.

(Resulting data model has 14+ core tables and 30+ mapping/helper tables.)

---

# 18. 🖥️ **PREMIUM OLIVE UI/UX SPECIFICATIONS**
### Color Palette
- Olive Primary: `#556B2F` or `#6B8E23`
- Beige BG: `#F7F6F1`
- Text: `#0B0B0B`
- Muted Gray: `#C9C9C9`

### Typography
- **Headings:** DM Sans (Bold)
- **Body:** Satoshi Variable (Regular / Medium)

### Components
- Rounded 12–16px
- Subtle shadows
- Minimal lines
- htmx modals for overlays

---

# 19. 🔄 **HTMX INTERACTION ARCHITECTURE**
- Inline updates for status changes
- hx-get for list filtering
- hx-post for OTP verification
- hx-target for partial updates
- hx-swap for modal rendering

---

# 20. 🧪 **TECHNICAL ARCHITECTURE**
### Backend
- Django 4+
- SQLite (Phase 1)
- Django ORM

### Frontend
- Tailwind CSS
- htmx
- Minimal JS

### Integrations
- SMS Gateway (MSG91 recommended)
- WhatsApp deep link generator

---

# 21. 🔒 **SECURITY REQUIREMENTS**
- OTP hash stored using SHA256 HMAC
- Role-based middleware
- Lead field masking for Telecallers (optional)
- Signed URLs for attendance photos

---

# 22. ⚡ **PERFORMANCE & SCALABILITY GUIDELINES**
- htmx partial renders for heavy tables
- DB indexing on phone, project, status
- Queueing system for SMS retries
- Pagination mandatory for large datasets

---

# 23. 🚀 **FUTURE PHASE FEATURES**
- WhatsApp Business API integration
- Auto-dialer for telecallers
- AI scoring for leads
- CP payout automation
- Geo-tagged site visit tracking

---

# END OF PRD v2.0 — **Ultra Detailed as Requested**

