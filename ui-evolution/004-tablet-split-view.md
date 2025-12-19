# 004 - Tablet Split-View Navigation

## Status
Planned

## Goal
Implement split-view layout for tablets (769px-1024px) with list on left and details on right.

## Requirements

### Layout
- Two-column layout: 40% list, 60% details
- Collapsible side drawer for navigation
- Persistent filter pane on wider tablets
- Touch-friendly elements (48px+ tap targets)

### Navigation
- Side menu visible by default
- Can be hidden on demand
- 3-5 main nav items
- Bottom nav alternative for portrait mode

### List & Detail
- Table/list on left column
- Detail panel on right column
- Tapping list item updates detail panel
- Swipe between detail items
- Filter/search visible in top bar

## Implementation Details

### Files to Modify
- `templates/base.html` - Tablet navigation
- `templates/leads/list.html` - Split-view layout
- `templates/leads/detail.html` - Side-by-side detail

### Tailwind Classes
```html
<!-- Tablet Split View -->
<div class="flex flex-col md:flex-row h-screen">
  <!-- List Column -->
  <div class="w-full md:w-2/5 border-r overflow-y-auto">
    <!-- List content -->
  </div>
  <!-- Detail Column -->
  <div class="w-full md:w-3/5 overflow-y-auto">
    <!-- Detail content -->
  </div>
</div>
```

### HTMX Integration
- Use `hx-get` for list item selection
- Target detail panel with `hx-target`
- Use `hx-swap="innerHTML"` for updates
- Preserve scroll position

## Constraints
- **Tablet only** (769px-1024px breakpoint)
- **Desktop and mobile remain unchanged**
- **Do not change backend logic**
- **Existing routes stay intact**

## Testing Checklist
- [ ] Split-view appears on tablet
- [ ] List and detail side-by-side
- [ ] Tapping list item updates detail
- [ ] Swipe between details works
- [ ] Navigation drawer functional
- [ ] Filter pane works
- [ ] Tested on actual tablet device
- [ ] Portrait and landscape modes

## Deliverables
- Updated templates for tablet view
- Split-view layout
- Navigation drawer
- HTMX integration
- No regressions on desktop/mobile

