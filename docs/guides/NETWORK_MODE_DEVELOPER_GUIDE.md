# Network Mode Integration - Developer Guide

## Quick Start

This guide helps developers understand and work with the network mode integration in CommunicationView.js.

## File Location

```
agentos/webui/static/js/views/CommunicationView.js
```

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│         CommunicationView.js                │
│                                             │
│  ┌───────────────────────────────────┐     │
│  │  loadNetworkMode()                │     │
│  │  - Fetches current mode from API  │     │
│  │  - Updates UI on success          │     │
│  │  - Handles errors gracefully      │     │
│  └───────────────────────────────────┘     │
│                                             │
│  ┌───────────────────────────────────┐     │
│  │  setNetworkMode(mode)             │     │
│  │  - Validates input                │     │
│  │  - Disables buttons (loading)     │     │
│  │  - Calls API to change mode       │     │
│  │  - Updates UI on response         │     │
│  │  - Re-enables buttons             │     │
│  └───────────────────────────────────┘     │
│                                             │
│  ┌───────────────────────────────────┐     │
│  │  updateNetworkModeUI(mode)        │     │
│  │  - Updates button states          │     │
│  │  - Updates description text       │     │
│  │  - Updates mode value display     │     │
│  └───────────────────────────────────┘     │
│                                             │
└─────────────────────────────────────────────┘
                     │
                     │ HTTP API
                     ▼
┌─────────────────────────────────────────────┐
│    Backend API (communication.py)           │
│                                             │
│  GET  /api/communication/mode               │
│  PUT  /api/communication/mode               │
└─────────────────────────────────────────────┘
```

## API Reference

### loadNetworkMode()

**Purpose:** Load current network mode from backend and initialize UI

**Signature:**
```javascript
async loadNetworkMode()
```

**Parameters:** None

**Returns:** Promise<void>

**Side Effects:**
- Calls `updateNetworkModeUI()` with current mode
- Shows Toast warning on error
- Logs to console

**Example Usage:**
```javascript
await this.loadNetworkMode();
```

**Error Handling:**
- API failure → Default to 'on' mode
- Invalid response → Default to 'on' mode
- Network error → Default to 'on' mode

---

### setNetworkMode(mode)

**Purpose:** Change network mode via API

**Signature:**
```javascript
async setNetworkMode(mode: string)
```

**Parameters:**
- `mode` (string): One of 'off', 'readonly', or 'on'

**Returns:** Promise<void>

**Side Effects:**
- Disables all mode buttons during request
- Calls `updateNetworkModeUI()` on success
- Shows Toast notifications (success or error)
- Re-enables buttons in finally block

**Example Usage:**
```javascript
await this.setNetworkMode('readonly');
```

**Error Handling:**
- Invalid mode → Error Toast, return early
- 403 Forbidden → Permission error Toast
- 400 Bad Request → Validation error Toast
- Network error → Connection error Toast
- Other errors → Generic error Toast

**State Management:**
```javascript
// Before API call
buttons.disabled = true
buttons.opacity = 0.6

// After API call (success or error)
buttons.disabled = false
buttons.opacity = 1
```

---

### updateNetworkModeUI(mode)

**Purpose:** Update UI elements to reflect given mode

**Signature:**
```javascript
updateNetworkModeUI(mode: string)
```

**Parameters:**
- `mode` (string): One of 'off', 'readonly', or 'on'

**Returns:** void

**Side Effects:**
- Updates button active states
- Updates mode description text
- Updates mode value display

**Example Usage:**
```javascript
this.updateNetworkModeUI('off');
```

**UI Elements Updated:**
- `.mode-btn` → Remove 'active' class from all
- `[data-mode="${mode}"]` → Add 'active' class
- `#mode-description` → Set description text
- `#network-mode-value` → Set mode name (uppercase)

---

## HTTP API Endpoints

### GET /api/communication/mode

**Purpose:** Retrieve current network mode and metadata

**Request:**
```http
GET /api/communication/mode HTTP/1.1
Host: localhost:8000
```

**Response (Success - 200 OK):**
```json
{
  "ok": true,
  "data": {
    "current_state": {
      "mode": "on",
      "updated_at": "2026-01-31T10:30:00Z",
      "updated_by": "admin",
      "metadata": {}
    },
    "recent_history": [
      {
        "previous_mode": "readonly",
        "new_mode": "on",
        "changed_at": "2026-01-31T10:30:00Z",
        "changed_by": "admin",
        "reason": "End of maintenance"
      }
    ],
    "available_modes": ["off", "readonly", "on"]
  }
}
```

**Response (Error - 500):**
```json
{
  "ok": false,
  "error": "Failed to retrieve network mode",
  "reason_code": "INTERNAL_ERROR"
}
```

---

### PUT /api/communication/mode

**Purpose:** Change the network mode

**Request:**
```http
PUT /api/communication/mode HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "mode": "readonly",
  "updated_by": "webui_user",
  "reason": "Manual change from WebUI"
}
```

**Response (Success - 200 OK):**
```json
{
  "ok": true,
  "data": {
    "previous_mode": "on",
    "new_mode": "readonly",
    "changed": true,
    "timestamp": "2026-01-31T10:35:00Z",
    "updated_by": "webui_user",
    "reason": "Manual change from WebUI"
  }
}
```

**Response (Permission Error - 403):**
```json
{
  "ok": false,
  "error": "Permission denied",
  "reason_code": "AUTH_FORBIDDEN"
}
```

**Response (Validation Error - 400):**
```json
{
  "ok": false,
  "error": "Invalid network mode: invalid_value",
  "reason_code": "VALIDATION_ERROR",
  "hint": "Valid modes: off, readonly, on"
}
```

---

## Code Examples

### Example 1: Basic Mode Change

```javascript
// In CommunicationView instance
async changeToReadOnly() {
    await this.setNetworkMode('readonly');
    // Success or error handled automatically
}
```

### Example 2: Get Current Mode

```javascript
// Load current mode
await this.loadNetworkMode();

// The current mode is now reflected in UI
// You can't get the value directly, but you can:
const activeButton = this.container.querySelector('.mode-btn.active');
const currentMode = activeButton.dataset.mode;
console.log('Current mode:', currentMode);
```

### Example 3: Manual UI Update (for testing)

```javascript
// Force UI to show OFF mode (without API call)
this.updateNetworkModeUI('off');

// Revert to actual mode
await this.loadNetworkMode();
```

### Example 4: Custom Error Handling

```javascript
async setNetworkMode(mode) {
    try {
        // ... existing code ...
    } catch (error) {
        // Custom error handling
        this.handleModeChangeError(error);
    }
}

handleModeChangeError(error) {
    // Log to external monitoring service
    console.error('Mode change failed:', error);
    // Send to error tracking (e.g., Sentry)
    // Sentry.captureException(error);
}
```

---

## Integration Points

### 1. Auto-Refresh Integration

Network mode is included in the auto-refresh cycle:

```javascript
async loadAllData() {
    await Promise.all([
        this.loadNetworkMode(),  // ← Included here
        this.loadStatus(),
        this.loadPolicy(),
        this.loadAudits()
    ]);
}
```

When auto-refresh is enabled (10-second interval), network mode is refreshed along with other data.

### 2. Toast Notifications

Uses the global `Toast` utility for user feedback:

```javascript
// Success
Toast.success('Network mode changed to ON');

// Error
Toast.error('Failed to change network mode: ...');

// Warning
Toast.warning('Could not load network mode, showing default state');

// Info (not currently used)
Toast.info('Network mode is changing...');
```

### 3. Event Listeners

Mode buttons are set up in `setupEventListeners()`:

```javascript
this.container.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const mode = btn.dataset.mode;
        this.setNetworkMode(mode);
    });
});
```

---

## Debugging

### Console Logs

The implementation includes console logs for debugging:

```javascript
// Success
console.log('Network mode changed:', result.data);

// Error
console.error('Error loading network mode:', error);
console.error('Failed to set network mode:', result);
console.error('Error setting network mode:', error);

// Warning
console.warn('Network mode API returned no data, using default mode');
```

### Browser DevTools

**Network Tab:**
1. Filter by "communication"
2. Look for GET/PUT requests to `/api/communication/mode`
3. Inspect request/response payloads
4. Check status codes

**Console Tab:**
1. Look for errors or warnings
2. Check for uncaught exceptions
3. Verify Toast messages appear

**Elements Tab:**
1. Inspect `.mode-btn` elements
2. Check for `active` class on correct button
3. Verify `disabled` attribute during API calls
4. Inspect `#mode-description` and `#network-mode-value` text

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Mode not loading | Backend API down | Check backend is running |
| Mode change fails | Permission denied | Verify user has permission |
| Buttons stay disabled | JavaScript error | Check console for errors |
| UI not updating | CSS issue | Check `.mode-btn.active` styles |
| Toast not showing | Toast utility issue | Verify Toast is loaded |
| Mode reverts after change | API returns error | Check API response in Network tab |

---

## Testing

### Manual Testing

```javascript
// Open browser console
const view = document.querySelector('.communication-view');

// Test loadNetworkMode
await CommunicationView.prototype.loadNetworkMode.call(view);

// Test setNetworkMode
await CommunicationView.prototype.setNetworkMode.call(view, 'readonly');

// Test updateNetworkModeUI
CommunicationView.prototype.updateNetworkModeUI.call(view, 'off');
```

### Mocking API Responses

```javascript
// Mock successful mode change
fetchMock.put('/api/communication/mode', {
    ok: true,
    data: {
        previous_mode: 'on',
        new_mode: 'readonly',
        changed: true,
        timestamp: new Date().toISOString()
    }
});

// Mock permission error
fetchMock.put('/api/communication/mode', {
    status: 403,
    body: {
        ok: false,
        error: 'Permission denied',
        reason_code: 'AUTH_FORBIDDEN'
    }
});
```

---

## Best Practices

### 1. Always Use Async/Await

```javascript
// ✅ Good
async handleModeChange() {
    await this.setNetworkMode('off');
}

// ❌ Bad
handleModeChange() {
    this.setNetworkMode('off'); // Promise not awaited
}
```

### 2. Don't Bypass updateNetworkModeUI

```javascript
// ✅ Good
this.updateNetworkModeUI('readonly');

// ❌ Bad
this.container.querySelector('[data-mode="readonly"]').classList.add('active');
this.container.querySelector('#mode-description').textContent = '...';
// ... manually updating each element
```

### 3. Handle Errors Gracefully

```javascript
// ✅ Good
try {
    await this.setNetworkMode(mode);
} catch (error) {
    console.error('Mode change failed:', error);
    // UI automatically shows error Toast
}

// ❌ Bad
await this.setNetworkMode(mode); // Unhandled errors
```

### 4. Use Descriptive Toast Messages

```javascript
// ✅ Good
Toast.error("You don't have permission to change network mode. Please contact administrator.");

// ❌ Bad
Toast.error('Error'); // Too vague
```

---

## Extending the Implementation

### Add a New Mode

1. **Backend:** Add mode to `NetworkMode` enum
```python
class NetworkMode(str, Enum):
    OFF = "off"
    READONLY = "readonly"
    ON = "on"
    THROTTLED = "throttled"  # NEW
```

2. **Frontend:** Add button to HTML (in `init()` method)
```html
<button class="mode-btn mode-throttled" data-mode="throttled">
    <span class="material-icons">speed</span>
    THROTTLED
</button>
```

3. **Frontend:** Add description to `updateNetworkModeUI()`
```javascript
const descriptions = {
    off: 'All external communications are disabled',
    readonly: 'External data can be fetched but not modified',
    on: 'All external communications are enabled',
    throttled: 'Communications are rate-limited'  // NEW
};
```

4. **CSS:** Add styling for new mode button
```css
.mode-btn.mode-throttled.active {
    background: #FFA500;
}
```

### Add Mode Change Confirmation

```javascript
async setNetworkMode(mode) {
    // Add confirmation for OFF mode
    if (mode === 'off') {
        const confirmed = confirm('Are you sure you want to disable all communications?');
        if (!confirmed) {
            return;
        }
    }

    // ... rest of existing code
}
```

### Add Optimistic UI Updates

```javascript
async setNetworkMode(mode) {
    // Save current state
    const previousMode = this.getCurrentMode();

    // Optimistically update UI
    this.updateNetworkModeUI(mode);

    try {
        // ... API call ...
    } catch (error) {
        // Revert on error
        this.updateNetworkModeUI(previousMode);
        Toast.error('...');
    }
}

getCurrentMode() {
    const activeBtn = this.container.querySelector('.mode-btn.active');
    return activeBtn ? activeBtn.dataset.mode : 'on';
}
```

### Add Mode History Display

```javascript
async showModeHistory() {
    const response = await fetch('/api/communication/mode/history?limit=10');
    const result = await response.json();

    if (result.ok) {
        this.renderModeHistory(result.data.history);
    }
}

renderModeHistory(history) {
    const html = history.map(h => `
        <div class="history-item">
            <span>${h.previous_mode} → ${h.new_mode}</span>
            <span>${new Date(h.changed_at).toLocaleString()}</span>
            <span>by ${h.changed_by}</span>
        </div>
    `).join('');

    // Render in UI...
}
```

---

## Performance Considerations

### 1. Parallel Loading

Network mode loads in parallel with other data:

```javascript
// ✅ Efficient - parallel loading
await Promise.all([
    this.loadNetworkMode(),
    this.loadStatus(),
    this.loadPolicy(),
    this.loadAudits()
]);

// ❌ Inefficient - sequential loading
await this.loadNetworkMode();
await this.loadStatus();
await this.loadPolicy();
await this.loadAudits();
```

### 2. Debouncing (if needed)

If rapid mode changes become an issue:

```javascript
setNetworkMode = debounce(async (mode) => {
    // ... existing implementation
}, 500);
```

### 3. Caching (future enhancement)

```javascript
let modeCache = null;
let cacheTime = null;

async loadNetworkMode() {
    const now = Date.now();
    if (modeCache && (now - cacheTime) < 5000) {
        // Use cached value if less than 5 seconds old
        this.updateNetworkModeUI(modeCache);
        return;
    }

    // ... fetch from API ...
    modeCache = currentMode;
    cacheTime = now;
}
```

---

## Security Considerations

### 1. Input Validation

Mode is validated before sending to API:

```javascript
const validModes = ['off', 'readonly', 'on'];
if (!validModes.includes(mode)) {
    Toast.error(`Invalid network mode: ${mode}`);
    return;
}
```

### 2. XSS Prevention

Mode descriptions are static strings (not user input):

```javascript
// Safe - static strings
const descriptions = {
    off: 'All external communications are disabled',
    // ...
};
```

### 3. Permission Handling

Permission errors are explicitly handled:

```javascript
if (response.status === 403) {
    Toast.error("You don't have permission to change network mode.");
}
```

---

## Troubleshooting Checklist

- [ ] Is the backend running?
- [ ] Is the API endpoint accessible?
- [ ] Are there any console errors?
- [ ] Are the button event listeners attached?
- [ ] Is the Toast utility loaded?
- [ ] Is the CSS properly loaded?
- [ ] Are there any network errors in DevTools?
- [ ] Is the response format correct?
- [ ] Are all required DOM elements present?
- [ ] Is JavaScript enabled in browser?

---

## Resources

### Files
- `agentos/webui/static/js/views/CommunicationView.js` - Frontend implementation
- `agentos/webui/api/communication.py` - Backend API endpoints
- `agentos/core/communication/network_mode.py` - Network mode manager

### Documentation
- `NETWORK_MODE_INTEGRATION_SUMMARY.md` - Complete implementation summary
- `NETWORK_MODE_QUICK_REFERENCE.md` - Quick reference guide
- `NETWORK_MODE_FLOW_DIAGRAM.md` - Visual flow diagrams
- `NETWORK_MODE_TEST_PLAN.md` - Comprehensive test plan

### External Resources
- [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [Async/Await](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function)
- [Promise.all()](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/all)

---

**Last Updated:** 2026-01-31
**Version:** 1.0
**Maintainer:** AgentOS Team
