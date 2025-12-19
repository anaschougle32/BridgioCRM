# BridgioCRM UI Vision

## Primary Principle
**Efficiency over beauty.**

## Design Philosophy
- **Desktop = Power CRM** - Tables, keyboard shortcuts, bulk actions, data density
- **Mobile + Tablet = App-like CRM** - Touch-first, cards, gestures, bottom navigation
- **Tablet is expanded mobile, not desktop** - Two-column layouts, larger touch targets

## Rules
- **HTMX only** - No React/Vue/SPA patterns
- **Tailwind only** - No custom CSS frameworks
- **No full page reloads** for primary flows
- **Mobile & tablet must be touch-first** - 48px+ tap targets, swipe gestures
- **Desktop keeps tables & keyboard workflows** - Maintain power-user efficiency

## Navigation Rules
- **Mobile & tablet**: Bottom navigation bar (3-5 tabs)
- **Desktop**: Fixed sidebar navigation

## Interaction Rules
- **Mobile actions**: Gestures, bottom sheets, cards, swipe actions
- **Desktop actions**: Tables, keyboard shortcuts, modals, bulk operations

## Platform-Specific Guidelines

### Desktop View (PC-first, Office/Admin Portal)

**Layout & Navigation:**
- Fixed sidebar (`<aside class="flex flex-col w-64 h-screen bg-gray-100">`) for primary navigation
- Top bar with global tools (search, notifications, user avatar, "Add New" button)
- CSS grid/flex for dashboard panels

**Dashboard Screen:**
- Tailwind card components (`<div class="bg-white rounded-lg p-4 shadow">`) for metrics
- Interactive charts in cards
- Summary stats: total leads, conversion rate, upcoming tasks

**Leads List:**
- Smart table with columns (Name, Source, Status, Assigned To)
- Tailwind `table-auto` with hover highlight and striped rows
- Search/filter bar above table
- Column sorting buttons (▼▲ icons)
- Pagination controls
- Bulk-select checkboxes and bulk-action dropdown
- Column freezing for large data

**Leads Detail:**
- Two-column layout: left (lead info, timeline, notes), right (actions)
- HTMX triggers for dynamic updates
- Modal for "Edit Lead" forms
- Tabs/accordion for Lead History, Notes, Documents

**Visits & Follow-Ups:**
- Calendar or list view for Visits
- Weekly calendar (Tailwind CSS grid) or list table
- Kanban or tabbed view for Follow-Ups (Pending, Completed)
- Draggable cards for tasks
- Filtering by date or telecaller

**User Profile:**
- Clean form layout with avatar, name, contact fields
- Tailwind form classes
- Collapsible panels for Account Settings and Preferences

**Admin Panel:**
- Multiple tabs or sidebar for User Management, Roles, Settings
- Table of users with in-line role edits
- "Add User" and "Invite" modals
- Grouped form fields and toggles

**Keyboard Shortcuts:**
- Ctrl+N for New Lead
- Ctrl+F for Search
- / for quick search
- Keyboard Shortcuts help overlay

**Role-Specific Enhancements:**
- **Telecaller**: "Call" icon on each row, quick-add inputs, "Today's Calls" list
- **Closing Manager**: Pipeline view, funnel charts, KPIs, tagging leads
- **Admin**: Full sidebar, column toggling, advanced filters, Audit Logs

### Tablet View (Field usage, hybrid)

**General Layout:**
- Start from mobile patterns, expand to two columns where space allows
- Split view: list on left (narrow), details on right
- Touch-friendly elements (larger buttons, spacing)

**Navigation:**
- Collapsible side drawer or bottom nav
- Show side menu by default, allow hiding on demand
- 3-5 main nav items

**Dashboard:**
- Cards in 2 columns or grid
- Wider charts
- Collapsible sections

**Leads List & Detail:**
- Table on left, detail panel on right
- Swipe between lead details
- Persistent filter pane on wider tablets

**Visits & Follow-Ups:**
- Calendar with week and list combined
- Follow-Ups Kanban in two columns side by side
- Responsive grid

**Forms & Modals:**
- Popover dialogs or slide-in panels
- Cards that overlay part of screen
- Full-page forms for critical actions

**Interactions:**
- Tap targets at least 48px
- Swipe gestures (swipe right to mark called)
- Swipe list item to reveal "Edit/Delete"

### Mobile View (App-like PWA experience)

**Native Feel & Navigation:**
- Bottom navigation bar with 3-5 tabs (Dashboard, Leads, Visits, Follow-Ups, Profile)
- Each tab has icon and label
- Active tab highlighted
- Hide navigation on scroll down, reveal on scroll up

**Home Screen / Dashboard:**
- Vertical stack of cards
- "My Today" card with upcoming tasks
- Summary chart
- Quick-add button (FAB)
- Sticky header with page title
- FAB ("+") in bottom-right for "New Lead/Visit"

**Leads Screen:**
- Vertical list of cards (`<div class="bg-white rounded-lg p-4 mb-3 shadow">`)
- Key info: name, stage, next action
- Action icons (call, email, complete)
- Swipe gestures (swipe left to archive, swipe right to call)
- Infinite scroll or "Load More"
- Clicking card opens Lead Detail

**Lead Detail (Mobile):**
- Bottom sheet or full-screen panel
- Summary at top (lead name, status pill, last activity)
- Details in collapsible sections
- Big "Call" and "Email" floating buttons
- Edits in slide-up modals or separate screens

**Visits & Follow-Ups:**
- Horizontal calendar strip (date picker)
- List of visits below
- Swipable tabs for Today, Week, Month
- Follow-Ups: vertical task list or mini-Kanban
- Horizontal swipe for status views (Overdue, Today, Upcoming)
- Checkboxes for quick complete

**User Profile:**
- Stacked card layout
- Avatar (circular), name, role at top
- Editable fields in form list
- "Dark Mode" toggle
- "Log Out" button at bottom

**Mobile-Specific Components:**
- **Floating Action Button (FAB)**: For primary actions (Add Lead, Schedule Visit)
- **Drawers/Sheets**: Left-side hamburger drawer for secondary menu, bottom sheets for forms
- **Gestures**: Pull-to-refresh, swipe down to refresh, swipe on table rows
- **PWA**: Web App Manifest, service workers for offline caching, "Install App" prompt

## Component & Interaction Guidelines (All Platforms)

**Cards & Containers:**
- Tailwind card layouts (`<div class="bg-white p-4 rounded shadow">`)
- Auto-layout, avoid fixed heights

**Tables:**
- Desktop: HTML tables (`<table class="min-w-full divide-y divide-gray-200">`)
- Mobile: Tables collapse into card lists or scrollable divs

**Forms & Inputs:**
- Standard form controls with Tailwind classes
- Desktop: Multi-column grids
- Mobile: Stack fields vertically
- Client-side validation hints

**Kanban & Boards:**
- Flex or grid with columns
- Each status column: `<div class="flex-shrink-0 w-64">`
- Horizontal scroll if overflow
- Mobile: Stack columns vertically or sideways swipe

**Search/Filter:**
- Search input and filter dropdowns on list pages
- Desktop: Filters in sidebar or above table
- Mobile: Collapsible top filter panel

**Modals & Overlays:**
- Desktop: Centered modals
- Mobile: Full-screen modals or sheets
- Smooth transitions (fade or slide)

**Notifications & Toasts:**
- Tailwind toast alerts (`<div class="fixed bottom-4 right-4 bg-green-500 text-white p-3 rounded">`)
- Mobile: In-app banner

**ARIA & Accessibility:**
- Label interactive elements (`aria-label` on icon buttons)
- Ensure color contrast

**HTMX Integration:**
- Structure HTML with Tailwind classes
- Add HTMX attributes for dynamic parts
- Use `hx-get`, `hx-post`, `hx-confirm` appropriately
- Leverage HTMX for partial updates

## Progressive Web App Enhancements

1. **Web App Manifest** (`manifest.json`) with app name/icon
2. **Service Worker** (`sw.js`) to cache assets and API responses
3. **HTMX boost** for prefetching linked pages
4. **Skeleton loaders** for slow networks
5. **Responsive content** using `sm:`, `md:` prefixes
6. **"Add to Home Screen"** flows

## Implementation Constraints

- **No backend logic changes** unless explicitly stated
- **One UI change at a time**
- **One screen or flow per iteration**
- **Each change documented in CHANGELOG.md**
- **Each change verifiable**
- **All changes must respect existing routes & data**

