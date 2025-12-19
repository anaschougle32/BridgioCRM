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

## [0.7.0] – Desktop Efficiency Enhancements
### Changed
- Added keyboard shortcuts for desktop power users (≥1025px)
  - Ctrl+N: New Lead
  - Ctrl+F: Focus Search
  - /: Quick Search
  - ?: Show Keyboard Shortcuts Help
  - Esc: Close Modals
- Implemented bulk selection and actions in leads table
  - Select all/none checkboxes
  - Bulk action dropdown (Assign, Change Status, Export)
  - Visual feedback for selected items
- Enhanced table with sortable columns
  - Click column headers to sort (Name, Budget, Status)
  - Sort indicators (⇅ icons)
  - Hover effects on sortable columns
- Improved table styling
  - Striped rows for better readability
  - Row hover highlights
  - Better visual hierarchy

### Scope
- Desktop only (≥1025px breakpoint)
- Mobile and tablet unchanged
- No backend changes (frontend-only enhancements)

### Verified
- Keyboard shortcuts work
- Bulk selection functional
- Column sorting works
- Table enhancements visible
- Tested on desktop browsers

---

## [0.6.0] – Dashboard UI Enhancement
### Changed
- Enhanced dashboard templates with platform-specific layouts
- Desktop: Improved grid layout with 2-column sections, better card design
- Mobile/Tablet: Added sticky header, "My Today" card with key metrics
- Mobile: Added FAB (Floating Action Button) for quick actions
- Improved card styling with hover effects and transitions
- Touch-friendly buttons (48px+ tap targets) on mobile
- Better responsive breakpoints for all screen sizes

### Scope
- Updated `dashboard_telecaller.html` and `dashboard_closing_manager.html`
- Desktop: Enhanced grid layout (≥1025px)
- Mobile/Tablet: Vertical stack with sticky header (≤1024px)
- No backend changes

### Verified
- Desktop grid layout works
- Mobile stack layout works
- Cards display correctly
- FAB functional (mobile)
- Tested responsive breakpoints

---

## [0.5.0] – Follow-Ups UI Enhancement
### Changed
- Created dedicated follow-ups page with Kanban board (desktop) and list view (mobile/tablet)
- Desktop: 4-column Kanban board (Overdue, Today, Upcoming, Completed)
- Mobile/Tablet: Swipeable tabs for status views
- Filter by assigned user and date range
- HTMX integration for completing reminders
- Touch-friendly buttons (48px+ tap targets)
- Added Follow-Ups link to sidebar navigation

### Scope
- New page: `/leads/followups/`
- Desktop: Kanban board layout (≥1025px)
- Mobile/Tablet: List view with tabs (≤1024px)
- No backend changes (uses existing reminder model)

### Verified
- Kanban board works on desktop
- List view works on mobile/tablet
- Status updates correctly via HTMX
- Filtering works
- Navigation link added

---

## [0.4.0] – Tablet Split-View Navigation
### Changed
- Implemented split-view layout for tablets (768px-1024px)
- Left column (40%): Leads list with compact filters
- Right column (60%): Lead detail panel
- Sidebar visible by default on tablets
- HTMX integration for dynamic detail loading
- Tapping list item updates detail panel
- Active state highlighting for selected lead

### Scope
- Tablet only (768px-1024px breakpoint using `md:flex lg:hidden`)
- Desktop and mobile remain unchanged
- No backend changes

### Verified
- Split-view appears on tablet
- List and detail side-by-side
- Tapping list item updates detail
- Navigation drawer functional
- Filter pane works
- Tested in tablet viewport

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

