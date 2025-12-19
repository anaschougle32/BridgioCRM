# 002 - Leads List Mobile Cards

## Status
Completed

## Goal
Transform leads list from table to card-based layout on mobile devices (≤768px) for better touch interaction.

## Requirements

### Card Design
- Vertical list of cards
- Each card: `<div class="bg-white rounded-lg p-4 mb-3 shadow">`
- Key info displayed: Name, Status, Assigned To, Last Activity
- Action icons: Call, Email, View Details
- Swipe gestures: swipe left to archive, swipe right to call

### Layout
- Full-width cards
- Spacing: 12px between cards
- Padding: 16px inside cards
- Status badge/pill visible
- Avatar or initials for assigned user

### Interactions
- Tap card to open detail view
- Swipe left: reveal archive/delete actions
- Swipe right: quick call action
- Pull-to-refresh for list updates
- Infinite scroll or "Load More" button

## Implementation Details

### Files to Modify
- `templates/leads/list.html` - Add mobile card view
- Conditionally show cards on mobile, table on desktop

### Tailwind Classes
```html
<!-- Mobile Cards (hidden on desktop) -->
<div class="md:hidden space-y-3">
  <div class="bg-white rounded-lg p-4 shadow">
    <!-- Card content -->
  </div>
</div>

<!-- Desktop Table (hidden on mobile) -->
<div class="hidden md:block">
  <!-- Existing table -->
</div>
```

### HTMX Integration
- Use `hx-get` for card taps to load detail
- Use `hx-post` for swipe actions
- Use `hx-swap` for smooth updates
- Implement pull-to-refresh with HTMX

## Constraints
- **Mobile only** (≤768px breakpoint)
- **Desktop table remains unchanged**
- **Do not change backend logic**
- **Existing data structure stays intact**

## Testing Checklist
- [ ] Cards display correctly on mobile
- [ ] Table still works on desktop
- [ ] Swipe gestures functional
- [ ] Card tap opens detail view
- [ ] Pull-to-refresh works
- [ ] All lead data displays correctly
- [ ] Action buttons functional
- [ ] Tested on actual mobile device

## Deliverables
- Updated `templates/leads/list.html`
- Mobile card layout
- Swipe gesture support
- HTMX integration
- No regressions on desktop

