# Network Mode Integration - Test Plan

## Overview
Comprehensive test plan for the network mode integration in CommunicationView.js

**File:** `agentos/webui/static/js/views/CommunicationView.js`
**Lines Modified:** Multiple sections (319-341, 343-373, 375-382, 701-775)
**Total Lines:** 880

## Pre-Test Setup

### Backend Requirements
- [ ] AgentOS backend is running
- [ ] `/api/communication/mode` GET endpoint is functional
- [ ] `/api/communication/mode` PUT endpoint is functional
- [ ] NetworkModeManager is properly initialized

### Frontend Requirements
- [ ] WebUI is accessible
- [ ] Browser console is open for debugging
- [ ] Network tab is open for API monitoring
- [ ] Communication View is accessible from navigation

### Test Environment
- **Browser:** Chrome/Firefox/Safari (latest)
- **Network:** Normal (and throttled for network error tests)
- **Backend:** Running on expected port
- **User:** Appropriate permissions configured

## Test Cases

### TC-001: Initial Page Load - Success
**Priority:** HIGH
**Type:** Functional

**Steps:**
1. Navigate to Communication View
2. Observe network mode section

**Expected Results:**
- [ ] GET /api/communication/mode is called
- [ ] Mode value displays current mode (e.g., "ON")
- [ ] Correct button is highlighted with 'active' class
- [ ] Description text matches mode
- [ ] No error messages shown
- [ ] No console errors

**API Call Verification:**
```
Request: GET /api/communication/mode
Expected Response: 200 OK
{
  "ok": true,
  "data": {
    "current_state": {
      "mode": "on",
      "updated_at": "...",
      "updated_by": "..."
    }
  }
}
```

---

### TC-002: Initial Page Load - API Failure
**Priority:** HIGH
**Type:** Error Handling

**Steps:**
1. Stop backend or block API endpoint
2. Navigate to Communication View
3. Observe network mode section

**Expected Results:**
- [ ] GET /api/communication/mode fails
- [ ] Mode defaults to "ON"
- [ ] ON button is highlighted
- [ ] Toast warning: "Could not load network mode, showing default state"
- [ ] Console warning logged
- [ ] User can still interact with UI

---

### TC-003: Mode Change - OFF to READONLY (Success)
**Priority:** HIGH
**Type:** Functional

**Pre-condition:** Current mode is "OFF"

**Steps:**
1. Click READONLY button
2. Wait for API response
3. Observe UI changes

**Expected Results:**
- [ ] Buttons become disabled immediately
- [ ] Buttons opacity changes to 0.6
- [ ] PUT /api/communication/mode is called with body:
  ```json
  {
    "mode": "readonly",
    "updated_by": "webui_user",
    "reason": "Manual change from WebUI"
  }
  ```
- [ ] On success (200 OK):
  - [ ] READONLY button becomes active
  - [ ] Mode value shows "READONLY"
  - [ ] Description: "External data can be fetched but not modified"
  - [ ] Success Toast: "Network mode changed to READONLY"
  - [ ] Buttons re-enabled
  - [ ] Buttons opacity returns to 1
  - [ ] Console log shows change details

**Timeline:**
- T+0ms: Button clicked
- T+10ms: Buttons disabled
- T+100-500ms: API response
- T+510ms: UI updated, buttons enabled

---

### TC-004: Mode Change - READONLY to ON (Success)
**Priority:** HIGH
**Type:** Functional

**Pre-condition:** Current mode is "READONLY"

**Steps:**
1. Click ON button
2. Wait for API response
3. Observe UI changes

**Expected Results:**
- [ ] Same as TC-003, but:
  - [ ] ON button becomes active
  - [ ] Mode value shows "ON"
  - [ ] Description: "All external communications are enabled"
  - [ ] Success Toast: "Network mode changed to ON"

---

### TC-005: Mode Change - ON to OFF (Success)
**Priority:** HIGH
**Type:** Functional

**Pre-condition:** Current mode is "ON"

**Steps:**
1. Click OFF button
2. Wait for API response
3. Observe UI changes

**Expected Results:**
- [ ] Same as TC-003, but:
  - [ ] OFF button becomes active
  - [ ] Mode value shows "OFF"
  - [ ] Description: "All external communications are disabled"
  - [ ] Success Toast: "Network mode changed to OFF"

---

### TC-006: Mode Change - Permission Denied (403)
**Priority:** HIGH
**Type:** Error Handling

**Pre-condition:** User lacks permission to change mode

**Steps:**
1. Configure backend to return 403 for mode change
2. Click any mode button
3. Wait for API response

**Expected Results:**
- [ ] Buttons disabled during request
- [ ] PUT /api/communication/mode called
- [ ] API returns 403 Forbidden
- [ ] Error Toast: "You don't have permission to change network mode. Please contact administrator."
- [ ] UI remains in previous state (no mode change)
- [ ] Buttons re-enabled
- [ ] Console error logged
- [ ] Previous mode button still active

**API Response:**
```json
{
  "ok": false,
  "error": "Permission denied",
  "reason_code": "AUTH_FORBIDDEN"
}
```

---

### TC-007: Mode Change - Validation Error (400)
**Priority:** MEDIUM
**Type:** Error Handling

**Pre-condition:** Backend validates and rejects invalid request

**Steps:**
1. Configure backend to return 400 for mode change
2. Click mode button
3. Wait for API response

**Expected Results:**
- [ ] Buttons disabled during request
- [ ] PUT /api/communication/mode called
- [ ] API returns 400 Bad Request
- [ ] Error Toast: "Invalid request: {error_message}"
- [ ] UI remains in previous state
- [ ] Buttons re-enabled
- [ ] Console error logged

**API Response:**
```json
{
  "ok": false,
  "error": "Invalid mode: invalid_value",
  "reason_code": "VALIDATION_ERROR"
}
```

---

### TC-008: Mode Change - Network Error
**Priority:** HIGH
**Type:** Error Handling

**Pre-condition:** Network connection fails or is throttled

**Steps:**
1. Enable network throttling or disconnect
2. Click mode button
3. Wait for timeout/failure

**Expected Results:**
- [ ] Buttons disabled during request
- [ ] PUT /api/communication/mode called
- [ ] Network error occurs (TypeError)
- [ ] Error Toast: "Network error: Could not connect to server"
- [ ] UI remains in previous state
- [ ] Buttons re-enabled after timeout
- [ ] Console error logged

---

### TC-009: Mode Change - Generic Server Error (500)
**Priority:** MEDIUM
**Type:** Error Handling

**Pre-condition:** Backend returns 500 error

**Steps:**
1. Configure backend to return 500
2. Click mode button
3. Wait for API response

**Expected Results:**
- [ ] Buttons disabled during request
- [ ] PUT /api/communication/mode called
- [ ] API returns 500 Internal Server Error
- [ ] Error Toast: "Failed to change network mode: {error_message}"
- [ ] UI remains in previous state
- [ ] Buttons re-enabled
- [ ] Console error logged

---

### TC-010: Rapid Click Prevention
**Priority:** MEDIUM
**Type:** UX/Race Condition

**Steps:**
1. Click READONLY button
2. Immediately click ON button (before first request completes)
3. Observe behavior

**Expected Results:**
- [ ] First click disables all buttons
- [ ] Second click has no effect (buttons disabled)
- [ ] Only first request is sent
- [ ] After first request completes, buttons re-enable
- [ ] User can then make second selection

---

### TC-011: Same Mode Click (Idempotent)
**Priority:** LOW
**Type:** Functional

**Pre-condition:** Current mode is "ON"

**Steps:**
1. Click ON button (same as current)
2. Wait for API response

**Expected Results:**
- [ ] PUT request sent normally
- [ ] Backend may return "no change" or success
- [ ] Success Toast shown
- [ ] UI remains stable (ON still active)
- [ ] No visual glitches

---

### TC-012: Auto-Refresh Integration
**Priority:** MEDIUM
**Type:** Integration

**Steps:**
1. Enable auto-refresh toggle
2. Wait 10 seconds
3. Observe network calls

**Expected Results:**
- [ ] Every 10 seconds, GET /api/communication/mode is called
- [ ] UI updates if backend mode changed externally
- [ ] If mode changed by another user/process:
  - [ ] UI silently updates to reflect new mode
  - [ ] No Toast notification (silent sync)
  - [ ] Correct button highlighted

---

### TC-013: Browser Refresh Persistence
**Priority:** LOW
**Type:** Functional

**Pre-condition:** Current mode is "READONLY"

**Steps:**
1. Note current mode (READONLY)
2. Refresh browser (F5 or Ctrl+R)
3. Wait for page to reload

**Expected Results:**
- [ ] Page reloads
- [ ] loadNetworkMode() called on init
- [ ] UI shows READONLY (not "Loading..." or default)
- [ ] Correct button highlighted
- [ ] State persisted via backend API

---

### TC-014: Multiple Concurrent Users
**Priority:** LOW
**Type:** Integration

**Setup:** Open Communication View in two browser tabs/windows

**Steps:**
1. Tab 1: Change mode to OFF
2. Tab 2: Enable auto-refresh or manually refresh
3. Observe Tab 2 UI

**Expected Results:**
- [ ] Tab 1 changes mode successfully
- [ ] Tab 2 (with auto-refresh) syncs after 10 seconds
- [ ] Tab 2 shows OFF mode
- [ ] No conflicts or race conditions
- [ ] Both tabs show consistent state

---

### TC-015: Console Error Validation
**Priority:** HIGH
**Type:** Quality

**Steps:**
1. Navigate to Communication View
2. Change mode several times (OFF → READONLY → ON)
3. Check browser console

**Expected Results:**
- [ ] No uncaught exceptions
- [ ] No undefined variable errors
- [ ] No Promise rejection warnings
- [ ] Only expected console.log messages
- [ ] No CSS/DOM errors related to mode buttons

---

### TC-016: Accessibility (A11y)
**Priority:** LOW
**Type:** Accessibility

**Steps:**
1. Navigate to Communication View using Tab key
2. Focus on mode buttons using Tab
3. Activate button using Enter/Space

**Expected Results:**
- [ ] Buttons are keyboard accessible
- [ ] Focus indicator visible on active button
- [ ] Enter/Space keys trigger mode change
- [ ] Screen reader announces button states
- [ ] Disabled state is announced during API call

---

### TC-017: Mobile/Responsive View
**Priority:** LOW
**Type:** UI/UX

**Steps:**
1. Open Communication View in mobile view (DevTools)
2. Change network mode
3. Observe button layout and interactions

**Expected Results:**
- [ ] Buttons are properly sized for touch
- [ ] Button layout adapts to screen size
- [ ] Toast notifications visible
- [ ] No overlapping elements
- [ ] Mode description readable

---

### TC-018: Long Description Text
**Priority:** LOW
**Type:** Edge Case

**Pre-condition:** Mode descriptions are standard length

**Steps:**
1. Cycle through all three modes (OFF, READONLY, ON)
2. Observe description text rendering

**Expected Results:**
- [ ] OFF: "All external communications are disabled"
- [ ] READONLY: "External data can be fetched but not modified"
- [ ] ON: "All external communications are enabled"
- [ ] Text does not overflow container
- [ ] Text is fully readable
- [ ] No text truncation

---

### TC-019: API Response Delay (Slow Network)
**Priority:** MEDIUM
**Type:** Performance

**Steps:**
1. Enable network throttling (Slow 3G)
2. Click mode button
3. Wait for response (may take 3-5 seconds)

**Expected Results:**
- [ ] Buttons remain disabled during entire wait
- [ ] No timeout errors
- [ ] UI remains responsive
- [ ] Success Toast appears after response
- [ ] No double-submission of request
- [ ] User understands something is happening (opacity change)

---

### TC-020: Backend Unavailable During Page Load
**Priority:** MEDIUM
**Type:** Resilience

**Steps:**
1. Stop backend server
2. Navigate to Communication View
3. Start backend server
4. Click Refresh All button

**Expected Results:**
- [ ] Initial load shows default mode with warning Toast
- [ ] After backend restart and refresh:
  - [ ] GET /api/communication/mode succeeds
  - [ ] Correct mode loaded and displayed
  - [ ] User can now change modes

---

## Performance Benchmarks

### Load Time
- [ ] loadNetworkMode() completes in < 500ms (normal network)
- [ ] Page load not blocked by network mode fetch (parallel)
- [ ] UI renders immediately (no blocking)

### Mode Change Time
- [ ] Button click to API call: < 50ms
- [ ] API response to UI update: < 100ms
- [ ] Total time for mode change: < 1 second (normal network)

### Memory Usage
- [ ] No memory leaks after multiple mode changes
- [ ] Event listeners properly cleaned up
- [ ] No zombie intervals from auto-refresh

## Browser Compatibility

Test in the following browsers:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

## Test Data

### Valid Modes
- `off` - All communications disabled
- `readonly` - Fetch only, no modifications
- `on` - All communications enabled

### Invalid Modes (should be validated)
- `invalid_mode` - Should return 400 error
- `null` - Should return 400 error
- Empty string - Should return 400 error

## Bug Report Template

If issues are found during testing:

```markdown
### Bug Report: [Short Description]

**Test Case:** TC-XXX
**Priority:** HIGH/MEDIUM/LOW
**Browser:** Chrome 120.0.0

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Expected Result:**
What should happen

**Actual Result:**
What actually happened

**Screenshots:**
[Attach screenshots if applicable]

**Console Errors:**
```
[Paste console errors here]
```

**Network Log:**
```
[Paste relevant API calls here]
```

**Additional Context:**
Any other relevant information
```

## Test Execution Checklist

### Pre-Flight
- [ ] Backend is running and accessible
- [ ] Test data is prepared
- [ ] Browser DevTools are open
- [ ] Test plan is reviewed

### Execution
- [ ] Run all HIGH priority tests
- [ ] Run all MEDIUM priority tests
- [ ] Run all LOW priority tests
- [ ] Document any failures
- [ ] Take screenshots of issues
- [ ] Save console logs for errors

### Post-Flight
- [ ] All tests documented
- [ ] Bugs reported in issue tracker
- [ ] Test summary created
- [ ] Sign-off obtained (if applicable)

## Test Summary Template

```markdown
# Network Mode Integration - Test Summary

**Date:** [YYYY-MM-DD]
**Tester:** [Name]
**Environment:** [Browser, OS, Backend version]

## Results

- Total Tests: XX
- Passed: XX
- Failed: XX
- Blocked: XX
- Skipped: XX

## Pass Rate: XX%

## Critical Issues
1. [Issue description with TC number]
2. [Issue description with TC number]

## Medium Issues
1. [Issue description with TC number]

## Low Issues
1. [Issue description with TC number]

## Recommendations
- [Recommendation 1]
- [Recommendation 2]

## Sign-Off
- [ ] All critical issues resolved
- [ ] All high-priority tests pass
- [ ] Feature ready for production
```

## Automated Testing (Future Enhancement)

### Unit Tests (Jest/Vitest)
```javascript
describe('CommunicationView - Network Mode', () => {
  test('loadNetworkMode should fetch current mode', async () => {
    // Test implementation
  });

  test('setNetworkMode should disable buttons during request', async () => {
    // Test implementation
  });

  test('updateNetworkModeUI should highlight correct button', () => {
    // Test implementation
  });

  test('error handling shows appropriate Toast messages', async () => {
    // Test implementation
  });
});
```

### E2E Tests (Playwright/Cypress)
```javascript
describe('Network Mode E2E', () => {
  it('should change mode from OFF to ON', () => {
    cy.visit('/communication');
    cy.get('[data-mode="on"]').click();
    cy.get('.toast-success').should('contain', 'Network mode changed to ON');
    cy.get('[data-mode="on"]').should('have.class', 'active');
  });

  it('should handle permission error gracefully', () => {
    cy.intercept('PUT', '/api/communication/mode', {
      statusCode: 403,
      body: { ok: false, error: 'Permission denied' }
    });
    cy.get('[data-mode="off"]').click();
    cy.get('.toast-error').should('contain', 'permission');
  });
});
```

---

**Test Plan Status:** ✅ Ready for Execution
**Last Updated:** 2026-01-31
**Version:** 1.0
