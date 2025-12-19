# UI Evolution Changelog

This file defines what is allowed to change. Only items listed in "Planned" or "In Progress" sections should be worked on.

## [Unreleased]

### Planned
- 002 Leads list cards (mobile)
- 003 Lead detail slide panel (mobile)
- 004 Tablet split-view navigation
- 005 Follow-ups UI (mobile/tablet)
- 006 Dashboard UI (all platforms)
- 007 Desktop efficiency enhancements

### In Progress
- None

---

## [0.3.0] – Mobile Lead Detail Slide Panel
### Changed
- Implemented full-screen slide panel for lead detail on mobile (≤768px)
- Added sticky header with lead name, status badge, and close button
- Made sections collapsible (Client Info, Notes, OTP, Call History, Reminders)
- Added fixed action buttons at bottom (Call and Email)
- Implemented swipe down to close gesture
- HTMX integration for dynamic updates

### Scope
- Mobile only (≤768px breakpoint using `md:hidden`)
- Desktop detail view remains unchanged (≥769px using `hidden md:block`)
- No backend changes

### Verified
- Panel opens from leads list
- Swipe down closes panel
- All sections display correctly
- Collapsible sections work
- Action buttons functional
- Edit modals work
- HTMX updates smooth

---

## [0.2.0] – Mobile Leads List Cards
### Changed
- Enhanced mobile card view for leads list (≤768px only)
- Cards are now tappable to open detail view
- Improved touch targets (minimum 48px)
- Better card styling with status badges
- HTMX integration for smooth navigation

### Scope
- Mobile only (≤768px breakpoint using `md:hidden`)
- Desktop table remains unchanged (≥769px using `hidden md:block`)
- No backend changes

### Verified
- Cards display correctly on mobile
- Table still works on desktop
- Card tap opens detail view
- All lead data displays correctly
- Action buttons functional

---

## [0.1.0] – Mobile Bottom Navigation
### Changed
- Added bottom navigation bar on mobile devices (≤768px)
- Navigation items: Dashboard, Leads, Visits (role-specific), Profile
- Hide on scroll down, reveal on scroll up
- HTMX integration for smooth navigation without full page reloads
- Active state highlighting based on current URL

### Scope
- Mobile only (≤768px breakpoint using `md:hidden`)
- Desktop sidebar navigation remains unchanged
- No backend changes

### Verified
- Navigation appears only on mobile
- All tabs functional with HTMX
- Active state works correctly
- Hide/show on scroll works
- Tested for Telecaller, Closing Manager, Admin roles

---

## [0.0.0] – Initial State
### Current
- Existing production CRM
- Desktop-first design
- Standard sidebar navigation
- Table-based leads list
- Modal-based detail views

### Scope
- All platforms use same UI patterns
- No platform-specific optimizations

### Verified
- All existing roles and flows working

---

## Notes

### How to Add a New Task

1. Add task to "Planned" section above
2. Create corresponding markdown file (e.g., `001-mobile-navigation.md`)
3. Move task to "In Progress" when starting work
4. Move to versioned section when complete

### Task Format

Each completed task should include:
- **Changed**: What was modified
- **Scope**: Platform/breakpoint restrictions
- **Verified**: Roles/flows tested

