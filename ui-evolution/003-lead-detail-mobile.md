# 003 - Lead Detail Mobile Slide Panel

## Status
Planned

## Goal
Implement bottom sheet or slide-in panel for lead detail view on mobile devices (≤768px).

## Requirements

### Panel Design
- Bottom sheet or full-screen slide-in panel
- Summary at top: lead name, status pill, last activity
- Collapsible sections for details
- Big floating action buttons: "Call" and "Email"
- Slide-up modals for edits

### Layout
- Full-width on mobile
- Sticky header with lead name and close button
- Scrollable content area
- Fixed action buttons at bottom
- Sections: Contact Info, Timeline, Notes, Documents

### Interactions
- Swipe down to close panel
- Tap section headers to expand/collapse
- Tap action buttons for quick actions
- Slide-up modal for edit forms
- HTMX for dynamic updates

## Implementation Details

### Files to Modify
- `templates/leads/detail.html` - Add mobile panel view
- Create mobile-specific detail template or conditional rendering

### Tailwind Classes
```html
<!-- Mobile Panel -->
<div class="fixed inset-0 bg-white z-50 md:hidden transform transition-transform">
  <div class="h-full flex flex-col">
    <!-- Header -->
    <div class="sticky top-0 bg-white border-b p-4">
      <!-- Lead name, status, close button -->
    </div>
    <!-- Scrollable content -->
    <div class="flex-1 overflow-y-auto p-4">
      <!-- Collapsible sections -->
    </div>
    <!-- Fixed actions -->
    <div class="sticky bottom-0 bg-white border-t p-4">
      <!-- Call and Email buttons -->
    </div>
  </div>
</div>
```

### HTMX Integration
- Use `hx-get` to load detail content
- Use `hx-swap="innerHTML"` for section updates
- Use `hx-post` for action buttons
- Smooth transitions between states

## Constraints
- **Mobile only** (≤768px breakpoint)
- **Desktop detail view remains unchanged**
- **Do not change backend logic**
- **Existing detail data structure stays intact**

## Testing Checklist
- [ ] Panel opens from leads list
- [ ] Swipe down closes panel
- [ ] All sections display correctly
- [ ] Collapsible sections work
- [ ] Action buttons functional
- [ ] Edit modals work
- [ ] HTMX updates smooth
- [ ] Tested on actual mobile device

## Deliverables
- Updated `templates/leads/detail.html`
- Mobile panel layout
- Swipe gesture support
- Collapsible sections
- HTMX integration
- No regressions on desktop

