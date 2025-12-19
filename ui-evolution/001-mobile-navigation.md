# 001 - Mobile Bottom Navigation

## Status
Planned

## Goal
Implement bottom navigation bar for mobile devices (≤768px) to provide app-like navigation experience.

## Requirements

### Navigation Items
- Dashboard (icon: home)
- Leads (icon: users/list)
- Visits (icon: calendar)
- Follow-Ups (icon: bell/reminder) - if applicable for role
- Profile (icon: user)

### Design Specifications
- Fixed bottom position
- Height: 64px
- Background: white with shadow
- Active tab: highlighted with primary color
- Icons: 24px, labels: 12px text
- Touch targets: minimum 48px

### Behavior
- Hide on scroll down, reveal on scroll up
- Smooth transitions
- Active state persists across page loads
- No full page reloads (use HTMX)

## Implementation Details

### Files to Modify
- `templates/base.html` - Add bottom navigation component
- Add conditional rendering for mobile only (`md:hidden` or `hidden md:block`)

### Tailwind Classes
```html
<nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 md:hidden z-50">
  <div class="flex justify-around items-center h-16">
    <!-- Navigation items -->
  </div>
</nav>
```

### HTMX Integration
- Use `hx-get` for navigation links
- Target main content area
- Use `hx-swap="innerHTML"` for smooth transitions
- Preserve active state via URL matching

## Constraints
- **Mobile only** (≤768px breakpoint)
- **Do not touch desktop** navigation
- **Do not change backend logic**
- **Existing routes stay intact**

## Testing Checklist
- [ ] Navigation appears only on mobile
- [ ] All tabs functional
- [ ] Active state works correctly
- [ ] Hide/show on scroll works
- [ ] HTMX transitions smooth
- [ ] Tested on actual mobile device
- [ ] Verified for all roles (Telecaller, Closing Manager, Admin)

## Deliverables
- Updated `templates/base.html`
- Tailwind classes for bottom navigation
- HTMX attributes for navigation
- No regressions on desktop

