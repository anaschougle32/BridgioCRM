# 006 - Dashboard UI Enhancement

## Status
Completed

## Goal
Enhance dashboard with platform-specific layouts: cards for desktop, widgets for mobile/tablet.

## Requirements

### Desktop Dashboard
- Tailwind card components for metrics
- Interactive charts in cards
- Summary stats: total leads, conversion rate, upcoming tasks
- Grid layout (2-3 columns)
- Collapsible sections

### Mobile/Tablet Dashboard
- Vertical stack of cards
- "My Today" card with upcoming tasks
- Summary chart widget
- Quick-add button (FAB)
- Sticky header with page title
- FAB ("+") in bottom-right

### Card Components
- `<div class="bg-white rounded-lg p-4 shadow">`
- Consistent spacing
- Responsive grid
- Auto-layout

## Implementation Details

### Files to Modify
- `templates/dashboard_*.html` files
- Create reusable card components
- Platform-specific layouts

### Tailwind Classes
```html
<!-- Desktop Grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <div class="bg-white rounded-lg p-4 shadow">
    <!-- Card content -->
  </div>
</div>

<!-- Mobile Stack -->
<div class="md:hidden space-y-4">
  <!-- Cards -->
</div>
```

### HTMX Integration
- Use `hx-get` for auto-refresh
- Use `hx-swap` for partial updates
- Use `hx-trigger` for periodic updates
- Skeleton loaders during load

## Constraints
- **Platform-specific layouts**
- **Do not change backend logic**
- **Existing dashboard data stays intact**

## Testing Checklist
- [ ] Desktop grid layout works
- [ ] Mobile stack layout works
- [ ] Cards display correctly
- [ ] Charts render properly
- [ ] Auto-refresh works
- [ ] FAB functional (mobile)
- [ ] Tested on all platforms

## Deliverables
- Updated dashboard templates
- Card components
- Platform-specific layouts
- HTMX integration
- No regressions

