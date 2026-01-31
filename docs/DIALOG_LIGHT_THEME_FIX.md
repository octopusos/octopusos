# Dialog Light Theme Fix

## Issue

Dialog was showing dark colors instead of light theme.

## Root Cause

The `dialog.css` had a `@media (prefers-color-scheme: dark)` rule that automatically switched to dark theme when the system was in dark mode.

## Fix

Removed the dark mode media query to **force light theme** for all dialogs, ensuring consistent light appearance regardless of system theme preference.

## Changes

### File: `agentos/webui/static/css/dialog.css`

**Removed**:
```css
@media (prefers-color-scheme: dark) {
    .dialog-container {
        background: #1F2937;
    }
    .dialog-title {
        color: #F9FAFB;
    }
    .dialog-message {
        color: #D1D5DB;
    }
    .dialog-btn.btn-secondary {
        background-color: #374151;
        color: #F9FAFB;
    }
    .dialog-btn.btn-secondary:hover {
        background-color: #4B5563;
    }
}
```

**Replaced with**:
```css
/* Force light theme - dialog always uses light colors for consistency */
/* Dark mode removed to ensure consistent light appearance */
```

### File: `agentos/webui/templates/index.html`

Updated version: `dialog.css?v=2` → `dialog.css?v=3`

## Light Theme Colors

Now all dialogs will always use these light colors:

**Dialog Container**:
- Background: `white`
- Title: `#111827` (dark gray)
- Message: `#4B5563` (medium gray)

**Buttons**:
- Primary: `#2563EB` (blue) with white text
- Secondary: `#F3F4F6` (light gray) with `#374151` (dark gray) text
- Danger: `#DC2626` (red) with white text

**Backdrop**: Semi-transparent black `rgba(0, 0, 0, 0.5)`

## Visual Preview

```
┌────────────────────────────────────────┐
│ Confirm Phase Change              [×]  │  ← Dark gray (#111827)
├────────────────────────────────────────┤
│                                        │
│ Switch to execution phase?             │  ← Medium gray (#4B5563)
│                                        │
│ This allows external communication     │
│ including web search and URL fetching. │
│                                        │
│          ┌─────────┐ ┌───────────────┐│
│          │ Cancel  │ │ Switch to     ││
│          │         │ │ Execution     ││  ← Blue button
│          └─────────┘ └───────────────┘│
│           ↑ Light      ↑ Blue (#2563EB)
│           gray
└────────────────────────────────────────┘
    ↑ White background
```

## Testing

### 1. Clear Browser Cache

**Important**: Must clear cache to see the changes!

```
Cmd + Shift + R (Mac)
Ctrl + Shift + R (Windows/Linux)
```

### 2. Start App

```bash
python3 -m agentos.webui.app
```

### 3. Test Dialog

1. Go to http://localhost:5000
2. Open Chat page
3. Click Phase selector button (Planning → Execution)

### 4. Verify Light Theme

**✅ Should see**:
- White background
- Dark gray title text
- Medium gray body text
- Light gray "Cancel" button
- Blue "Switch to Execution" button
- Clean, professional light theme

**❌ Should NOT see**:
- Dark gray/black background
- Light colored text
- Dark themed buttons

## Browser DevTools Check

Open DevTools (F12) → Elements tab → Find `.dialog-container` element:

**Computed styles should show**:
```css
background-color: rgb(255, 255, 255)  /* white */
color: rgb(17, 24, 39)                /* dark gray */
```

**Should NOT show**:
```css
background-color: rgb(31, 41, 55)     /* dark gray - BAD */
```

## If Still Showing Dark

### Check 1: Cache Cleared?

Hard refresh the page:
- `Cmd + Shift + R` (Mac)
- `Ctrl + Shift + R` (Windows/Linux)

Or disable cache in DevTools:
1. Open DevTools (F12)
2. Network tab
3. Check "Disable cache"
4. Refresh page

### Check 2: CSS Loaded?

In DevTools → Network tab:
1. Filter: `css`
2. Look for `dialog.css?v=3`
3. Status should be `200`
4. Click on it, check the response contains the CSS

### Check 3: System Dark Mode?

Even with system dark mode enabled, the dialog should still be light. If not:

1. Check Console for CSS errors
2. Verify no other CSS is overriding the styles
3. Check Elements tab to see what styles are applied

## Additional Notes

### Why Force Light Theme?

- **Consistency**: Ensures dialogs always look the same
- **Clarity**: Light theme is easier to read for important confirmations
- **Professional**: Clean, consistent appearance

### Future Dark Mode Support

If you want to add proper dark mode support later:
1. Use a class-based approach (e.g., `.dark-mode .dialog-container`)
2. Add a theme toggle in app settings
3. Store user preference in localStorage
4. Apply class to `<body>` or root element

## Files Modified

- `agentos/webui/static/css/dialog.css` - Removed dark mode media query
- `agentos/webui/templates/index.html` - Updated version to v=3

## Status

- ✅ Dark mode media query removed
- ✅ Light theme forced
- ✅ Version updated to v=3
- ⏳ Awaiting browser testing

---

**Fixed**: 2026-01-31
**Status**: ✅ Ready to test with cache cleared
