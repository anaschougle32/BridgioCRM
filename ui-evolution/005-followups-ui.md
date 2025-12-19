# 005 - Follow-Ups UI Enhancement

## Status
Planned

## Goal
Enhance follow-ups interface with Kanban board for desktop and mobile-optimized list for mobile/tablet.

## Requirements

### Desktop (Kanban Board)
- Multiple columns: Pending, Today, Upcoming, Completed
- Draggable cards between columns
- Each card shows: task, due date, lead name, assigned user
- Filter by date or telecaller
- Bulk actions

### Mobile/Tablet (List View)
- Vertical task list
- Swipable tabs for status views (Overdue, Today, Upcoming)
- Checkboxes for quick complete
- Horizontal swipe between status columns
- Pull-to-refresh

### Card Design
- `<div class="bg-white p-4 rounded shadow">`
- Status color coding
- Priority indicators
- Action icons

## Implementation Details

### Files to Modify
- `templates/leads/followups.html` or similar
- Create Kanban component for desktop
- Create list component for mobile

### Tailwind Classes
```html
<!-- Desktop Kanban -->
<div class="flex space-x-4 overflow-x-auto">
  <div class="flex-shrink-0 w-64">
    <h3>Pending</h3>
    <!-- Cards -->
  </div>
</div>

<!-- Mobile List -->
<div class="md:hidden space-y-2">
  <!-- Task cards -->
</div>
```

### HTMX Integration
- Use `hx-post` for status updates
- Use `hx-swap` for card moves
- Use `hx-get` for filtering
- Real-time updates

## Constraints
- **Platform-specific views** (Kanban for desktop, list for mobile)
- **Do not change backend logic**
- **Existing follow-up data structure stays intact**

## Testing Checklist
- [ ] Kanban board works on desktop
- [ ] List view works on mobile
- [ ] Drag and drop functional (desktop)
- [ ] Swipe gestures work (mobile)
- [ ] Status updates correctly
- [ ] Filtering works
- [ ] Tested on all platforms

## Deliverables
- Updated follow-ups templates
- Kanban board (desktop)
- List view (mobile/tablet)
- HTMX integration
- No regressions

