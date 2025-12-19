# 007 - Desktop Efficiency Enhancements

## Status
Planned

## Goal
Enhance desktop experience with keyboard shortcuts, bulk actions, and power-user features.

## Requirements

### Keyboard Shortcuts
- Ctrl+N: New Lead
- Ctrl+F: Search
- /: Quick search
- Keyboard Shortcuts help overlay
- Shortcuts bypass visual hunting

### Bulk Actions
- Bulk-select checkboxes in tables
- Bulk-action dropdown (Delete, Assign, Change Status)
- Select all/none functionality
- Visual feedback for selected items

### Table Enhancements
- Column sorting (▼▲ icons)
- Column freezing for large data
- Horizontal scroll if needed
- Row hover highlights
- Striped rows for readability

### Power Features
- Advanced filters (multi-select dropdowns)
- Column toggling (show/hide columns)
- Export functionality
- Quick actions on hover

## Implementation Details

### Files to Modify
- `templates/leads/list.html` - Table enhancements
- `templates/base.html` - Keyboard shortcuts
- Add JavaScript for shortcuts (minimal, HTMX-focused)

### Tailwind Classes
```html
<!-- Bulk Select -->
<div class="flex items-center space-x-2">
  <input type="checkbox" class="bulk-select-all">
  <select class="bulk-actions">
    <!-- Actions -->
  </select>
</div>

<!-- Sortable Columns -->
<th class="cursor-pointer hover:bg-gray-100">
  Name
  <span class="sort-icon">▼</span>
</th>
```

### HTMX Integration
- Use `hx-post` for bulk actions
- Use `hx-swap` for table updates
- Use `hx-trigger` for keyboard events
- Preserve selections during updates

## Constraints
- **Desktop only** (≥1025px breakpoint)
- **Do not change backend logic**
- **Existing data structure stays intact**

## Testing Checklist
- [ ] Keyboard shortcuts work
- [ ] Bulk selection functional
- [ ] Bulk actions execute correctly
- [ ] Column sorting works
- [ ] Column freezing works
- [ ] Advanced filters work
- [ ] Column toggling works
- [ ] Tested on desktop browsers

## Deliverables
- Updated desktop templates
- Keyboard shortcuts
- Bulk action functionality
- Table enhancements
- HTMX integration
- No regressions on mobile/tablet

