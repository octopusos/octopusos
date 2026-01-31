# Task #3: Mode Selector & Phase Selector - Manual Testing Guide

## Overview
This guide provides step-by-step instructions for manually testing the Mode Selector and Phase Selector components in the AgentOS WebUI.

## Prerequisites
- AgentOS WebUI running on http://localhost:8000 or http://localhost:9090
- Browser with Developer Console open (F12)

## Files Implemented

### Backend (API)
- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/sessions.py`
  - `PATCH /api/sessions/{session_id}/mode` - Update conversation mode
  - `PATCH /api/sessions/{session_id}/phase` - Update execution phase

### Frontend (Components)
- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/components/ModeSelector.js`
- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/components/PhaseSelector.js`
- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/css/mode-selector.css`

### Integration
- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/main.js`
  - Added Row 3 in chat toolbar for selectors
  - Added initialization functions
  - Added session switch handlers

- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/templates/index.html`
  - Added CSS import for mode-selector.css
  - Added JS imports for ModeSelector.js and PhaseSelector.js

## Test Cases

### Test 1: Visual Verification
**Objective**: Verify that Mode and Phase selectors appear in the chat interface

**Steps**:
1. Open AgentOS WebUI in browser
2. Navigate to Chat view
3. Create a new chat session or select existing one

**Expected Result**:
- Row 3 appears in chat toolbar below Session Status
- Mode Selector shows 5 options: Chat, Discussion, Plan, Development, Task
- Phase Selector shows 2 options: Planning, Execution
- Default mode: Chat (blue/active)
- Default phase: Planning (green/active)

---

### Test 2: Mode Switching
**Objective**: Test switching between all 5 conversation modes

**Steps**:
1. Click on "Discussion" mode
2. Observe visual feedback and console logs
3. Click on "Plan" mode
4. Click on "Development" mode
5. Click on "Task" mode
6. Click back to "Chat" mode

**Expected Result**:
- Each click triggers API call: `PATCH /api/sessions/{id}/mode`
- Active mode button changes color (blue background)
- Previous mode button returns to default state
- Toast notification shows: "Mode changed to: {mode}"
- Console log: "Conversation mode changed: {mode}"

**Dev Console Check**:
```javascript
// Check current mode
modeSelectorInstance.currentMode
// Should match the selected mode
```

---

### Test 3: Phase Selector - Planning Phase
**Objective**: Test switching to planning phase

**Steps**:
1. Ensure mode is NOT "plan" (use "chat" or "development")
2. Click on "Planning" phase button

**Expected Result**:
- API call: `PATCH /api/sessions/{id}/phase` with `phase: "planning"`
- Active phase button changes to green
- Toast notification: "Phase changed to: planning"
- No confirmation dialog (planning is safe)

---

### Test 4: Phase Selector - Execution Phase (Confirmation)
**Objective**: Test execution phase with confirmation dialog

**Steps**:
1. Ensure mode is NOT "plan"
2. Click on "Execution" phase button
3. Confirmation dialog appears

**Expected Result**:
- Dialog shows warning icon ⚠️
- Title: "Confirm Phase Change"
- Message: "Switch to execution phase? This allows external communication including web search and URL fetching."
- Two buttons: "Cancel" and "Switch to Execution"

**Test 4a: Cancel**:
- Click "Cancel"
- Phase remains at "Planning"
- No API call made

**Test 4b: Confirm**:
- Click "Switch to Execution"
- API call: `PATCH /api/sessions/{id}/phase` with `phase: "execution"`, `confirmed: true`
- Active phase changes to "Execution" (amber/orange color)
- Toast notification: "Phase changed to: execution"

---

### Test 5: Plan Mode Blocks Execution Phase
**Objective**: Verify that plan mode disables phase selector

**Steps**:
1. Select "Plan" mode
2. Observe Phase Selector state

**Expected Result**:
- Phase Selector becomes disabled (grayed out)
- Both phase buttons show `disabled` attribute
- Phase is automatically set to "Planning"
- Hint text appears: "Fixed to Planning in Plan mode"
- Clicking phase buttons does nothing
- Cursor changes to `not-allowed`

**Steps to Verify Block**:
3. Try to click "Execution" phase (should not work)
4. Switch to "Development" mode
5. Phase selector becomes enabled again

---

### Test 6: Session Switching Preserves Mode/Phase
**Objective**: Verify mode/phase persist across session switches

**Steps**:
1. In Session A, set mode to "Development" and phase to "Execution"
2. Create a new session (Session B)
3. Verify Session B has defaults (Chat, Planning)
4. Switch back to Session A

**Expected Result**:
- Session A shows: Development mode, Execution phase
- Session B shows: Chat mode, Planning phase
- Mode/Phase selectors update correctly on each session switch

---

### Test 7: API Error Handling
**Objective**: Test error scenarios

**Test 7a: Invalid Session ID**:
```javascript
// In browser console
fetch('/api/sessions/invalid-id/mode', {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mode: 'chat'})
})
```
**Expected**: 404 Not Found

**Test 7b: Invalid Mode**:
```javascript
fetch('/api/sessions/{valid-session-id}/mode', {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mode: 'invalid'})
})
```
**Expected**: 400 Bad Request with valid modes list

**Test 7c: Execution without Confirmation**:
```javascript
fetch('/api/sessions/{valid-session-id}/phase', {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({phase: 'execution'})
})
```
**Expected**: 400 Bad Request with hint about confirmation

**Test 7d: Execution in Plan Mode**:
```javascript
// First set plan mode, then try execution
fetch('/api/sessions/{valid-session-id}/phase', {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({phase: 'execution', confirmed: true})
})
```
**Expected**: 403 Forbidden with message about plan mode blocking

---

### Test 8: Responsive Design
**Objective**: Verify layout on different screen sizes

**Steps**:
1. Open browser DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M or Cmd+Shift+M)
3. Test on various viewport sizes:
   - Desktop: 1920x1080
   - Tablet: 768x1024
   - Mobile: 375x667

**Expected Result**:
- On desktop: Selectors appear side-by-side
- On mobile: Selectors stack vertically
- Buttons remain clickable and readable
- No horizontal overflow

---

### Test 9: Audit Logging
**Objective**: Verify phase changes are audited

**Steps**:
1. Switch to execution phase (with confirmation)
2. Check AgentOS logs or audit events API

**Expected Result**:
- Audit event created with:
  - `event_type: "execution_phase_changed"`
  - `actor: "user"`
  - `reason: "User switched to execution phase via WebUI"`
  - `confirmed: true`
- Response includes `audit_id`

---

### Test 10: Browser Console Validation
**Objective**: Verify no JavaScript errors

**Steps**:
1. Open browser console (F12)
2. Perform all test cases above
3. Watch for errors or warnings

**Expected Result**:
- No JavaScript errors
- No 404s for component files
- Console logs show mode/phase changes
- WebSocket logs show connection status

---

## Known Limitations

1. **Session Creation**: New sessions default to "chat" mode and "planning" phase
2. **Plan Mode Lock**: Phase selector is completely disabled in plan mode
3. **Confirmation Required**: Execution phase always requires user confirmation
4. **No Auto-Revert**: If execution phase is set, it won't auto-revert when switching modes

---

## Troubleshooting

### Selectors Not Visible
- Check browser console for component loading errors
- Verify CSS file is loaded: `/static/css/mode-selector.css`
- Verify JS files are loaded: `ModeSelector.js`, `PhaseSelector.js`
- Check `index.html` for correct script/link tags

### API Calls Failing
- Check WebUI server is running
- Verify API routes in `sessions.py` are registered
- Check `app.py` includes sessions router
- Restart WebUI server to load new routes

### Selectors Not Updating
- Check session ID is set: `state.currentSession`
- Verify `updateModePhaseSelectorsForSession()` is called in `switchSession()`
- Check component instances exist: `modeSelectorInstance`, `phaseSelectorInstance`

### Dialog Not Showing
- Verify `Dialog.js` component is loaded
- Check `window.Dialog` is available in console
- Fallback to native `confirm()` if Dialog component fails

---

## Success Criteria

✅ All 5 modes switchable without errors
✅ Both phases switchable with proper confirmation
✅ Plan mode correctly disables phase selector
✅ Confirmation dialog appears for execution phase
✅ Mode/phase persist across session switches
✅ No JavaScript console errors
✅ Responsive design works on mobile
✅ Audit events created for phase changes
✅ Toast notifications appear
✅ API error handling works correctly

---

## Completion Checklist

- [x] Backend API endpoints implemented
- [x] ModeSelector.js component created
- [x] PhaseSelector.js component created
- [x] CSS styles implemented
- [x] Integration in main.js
- [x] HTML template updated
- [x] Manual test guide created
- [ ] Manual testing completed
- [ ] Screenshots captured (optional)
- [ ] Task #3 marked as completed

---

**Next Steps**: After manual testing passes, mark Task #3 as completed and proceed to Task #4 (if applicable).
