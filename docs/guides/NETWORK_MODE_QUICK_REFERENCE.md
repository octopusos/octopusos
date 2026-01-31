# Network Mode Integration - Quick Reference

## Summary of Changes

**File:** `agentos/webui/static/js/views/CommunicationView.js`

### Methods Modified/Added

| Method | Type | Lines | Description |
|--------|------|-------|-------------|
| `loadNetworkMode()` | NEW | 319-341 | Loads current network mode from API |
| `updateNetworkModeUI(mode)` | NEW | 343-373 | Updates UI elements for given mode |
| `setNetworkMode(mode)` | MODIFIED | 701-775 | Changed from placeholder to real API call |
| `loadAllData()` | MODIFIED | 375-382 | Added `loadNetworkMode()` to parallel loads |

### Key Features

#### 1. Initial Load
- ✅ Fetches current mode on page load
- ✅ Updates UI with correct button state
- ✅ Shows appropriate description text
- ✅ Fallback to default mode on error

#### 2. Mode Switching
- ✅ Real API integration with PUT request
- ✅ Loading state (disabled buttons)
- ✅ Success/error notifications
- ✅ Permission error handling
- ✅ Network error handling

#### 3. Error Handling
```javascript
// Permission denied (403)
"You don't have permission to change network mode. Please contact administrator."

// Network error
"Network error: Could not connect to server"

// Validation error (400)
"Invalid request: {error_message}"

// Generic error
"Failed to change network mode: {error_message}"
```

### API Endpoints

#### GET /api/communication/mode
```javascript
// Response
{
  "ok": true,
  "data": {
    "current_state": { "mode": "on", "updated_at": "...", "updated_by": "..." }
  }
}
```

#### PUT /api/communication/mode
```javascript
// Request
{
  "mode": "readonly",
  "updated_by": "webui_user",
  "reason": "Manual change from WebUI"
}

// Response
{
  "ok": true,
  "data": {
    "previous_mode": "on",
    "new_mode": "readonly",
    "changed": true,
    "timestamp": "..."
  }
}
```

### Testing Checklist

- [ ] Page loads and shows current mode
- [ ] Clicking OFF button changes mode and shows success Toast
- [ ] Clicking READONLY button changes mode and shows success Toast
- [ ] Clicking ON button changes mode and shows success Toast
- [ ] Permission error shows appropriate message
- [ ] Network error shows appropriate message
- [ ] Buttons are disabled during mode change
- [ ] Buttons re-enable after API call completes
- [ ] Auto-refresh updates network mode
- [ ] Mode description updates correctly
- [ ] Mode value (OFF/READONLY/ON) displays correctly

### Browser Console Commands

```javascript
// Test loadNetworkMode
await window.CommunicationView.prototype.loadNetworkMode.call(view);

// Test setNetworkMode
await window.CommunicationView.prototype.setNetworkMode.call(view, 'readonly');

// Test updateNetworkModeUI
window.CommunicationView.prototype.updateNetworkModeUI.call(view, 'off');
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Mode not loading | Check browser console for API errors |
| Mode change fails | Check backend API is running |
| Permission denied | Verify user has appropriate permissions |
| UI not updating | Check CSS for `.mode-btn.active` class |
| Buttons stay disabled | Check browser console for JavaScript errors |

### Code Locations

```
agentos/webui/static/js/views/CommunicationView.js
├── Line 27-151:   init()
├── Line 319-341:  loadNetworkMode()       [NEW]
├── Line 343-373:  updateNetworkModeUI()   [NEW]
├── Line 375-382:  loadAllData()           [MODIFIED]
└── Line 701-775:  setNetworkMode()        [MODIFIED]
```

### Valid Modes

- `off` - All external communications disabled
- `readonly` - External data can be fetched but not modified
- `on` - All external communications enabled

### UI Elements

| Selector | Purpose |
|----------|---------|
| `.mode-btn` | Mode selection buttons |
| `.mode-btn.active` | Currently active mode |
| `#mode-description` | Mode description text |
| `#network-mode-value` | Mode value display (OFF/READONLY/ON) |

---

**Status:** ✅ Implementation Complete
**Syntax Check:** ✅ Passed
**Ready for Testing:** ✅ Yes
