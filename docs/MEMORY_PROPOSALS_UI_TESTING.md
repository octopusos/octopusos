# Memory Proposals UI Testing Guide

## Task #18: UI Display Capability Status

This document provides testing procedures for the Memory Proposals UI implementation.

## Prerequisites

1. AgentOS webUI running: `agentos webui`
2. Browser with developer tools open
3. User with ADMIN capability

## Test Cases

### TC1: Navigation and Empty State

**Objective**: Verify navigation and empty state display

**Steps**:
1. Open AgentOS WebUI (http://localhost:5002)
2. Navigate to Agent → Memory Proposals
3. Verify page loads without errors
4. Check console for JavaScript errors

**Expected Results**:
- "Memory Proposals" page displays
- Empty state shows: inbox icon with "No pending proposals" message
- Filter buttons show: Pending (0), Approved (0), Rejected (0), All
- No JavaScript errors in console

### TC2: Proposals Badge Visibility

**Objective**: Verify notification badge shows/hides correctly

**Steps**:
1. Check "Memory Proposals" menu item
2. Verify badge is initially hidden (no pending proposals)
3. Create a proposal via API or backend
4. Wait up to 30 seconds for badge to update
5. Verify badge appears with count

**Expected Results**:
- Badge hidden when no pending proposals
- Badge appears with correct count when pending proposals exist
- Badge auto-updates every 30 seconds

**API Command to Create Test Proposal**:
```bash
curl -X POST "http://localhost:5002/api/memory/propose" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "chat:test_agent",
    "memory_item": {
      "type": "preference",
      "scope": "global",
      "content": {
        "key": "test_preference",
        "value": "test_value"
      }
    },
    "reason": "Testing proposals UI"
  }'
```

### TC3: Filter Functionality

**Objective**: Verify filter buttons work correctly

**Steps**:
1. Navigate to Memory Proposals
2. Create proposals with different statuses (pending, approved, rejected)
3. Click each filter button
4. Verify correct proposals display

**Expected Results**:
- "Pending" filter shows only pending proposals
- "Approved" filter shows only approved proposals
- "Rejected" filter shows only rejected proposals
- "All" filter shows all proposals
- Active filter button has blue background
- Counts in parentheses are correct

### TC4: Proposal Card Display

**Objective**: Verify proposal card shows all information

**Steps**:
1. Create a test proposal with all fields
2. Navigate to Memory Proposals
3. Inspect the proposal card

**Expected Results**:
Proposal card displays:
- Proposal ID (first 8 characters)
- Status badge with correct color:
  - Pending: Orange background
  - Approved: Green background
  - Rejected: Red background
- Memory type badge
- Scope badge
- Proposed timestamp (relative time)
- Memory content (key → value)
- Proposer ID
- Proposer reason (if provided)
- For reviewed proposals:
  - Reviewer ID
  - Review reason
  - Resulting memory ID (if approved)
- Action buttons (for pending proposals only):
  - Green "Approve" button
  - Red "Reject" button

### TC5: Approve Workflow

**Objective**: Verify approval workflow works end-to-end

**Steps**:
1. Create a pending proposal
2. Click "Approve" button
3. Enter optional approval reason in prompt
4. Click OK

**Expected Results**:
- Prompt dialog appears asking for approval reason
- After clicking OK:
  - Success toast shows: "Proposal approved! Memory ID: {memory_id}"
  - Proposal card updates to show "approved" status
  - Approve/Reject buttons disappear
  - Review section appears with reviewer info
  - Pending count decreases by 1
  - Approved count increases by 1
  - Memory item created in database

**Validation**:
```bash
# Verify memory item was created
curl "http://localhost:5002/api/memory/search?namespace=default&limit=10"
```

### TC6: Reject Workflow

**Objective**: Verify rejection workflow works correctly

**Steps**:
1. Create a pending proposal
2. Click "Reject" button
3. Case A: Enter rejection reason
4. Case B: Leave reason empty or click Cancel

**Expected Results**:

**Case A (with reason)**:
- Prompt dialog appears asking for rejection reason
- After entering reason and clicking OK:
  - Success toast shows: "Proposal rejected: {reason}"
  - Proposal card updates to show "rejected" status
  - Approve/Reject buttons disappear
  - Review section appears with rejection reason
  - Pending count decreases by 1
  - Rejected count increases by 1

**Case B (empty reason)**:
- Warning toast shows: "Rejection reason is required"
- Proposal remains in pending state

### TC7: Auto-Refresh

**Objective**: Verify auto-refresh updates data without page reload

**Steps**:
1. Open Memory Proposals page
2. In another tab/terminal, create a new proposal via API
3. Wait up to 30 seconds
4. Verify new proposal appears without manual refresh

**Expected Results**:
- New proposal appears automatically
- Counts update automatically
- No page reload or flicker
- Console shows no errors

### TC8: Manual Refresh

**Objective**: Verify manual refresh button works

**Steps**:
1. Open Memory Proposals page
2. Click the "Refresh" button
3. Verify data reloads

**Expected Results**:
- Success toast shows: "Loaded {count} proposals"
- Proposals list updates
- Counts update
- No errors

### TC9: Error Handling

**Objective**: Verify proper error handling and display

**Steps**:
1. Stop the backend server
2. Navigate to Memory Proposals
3. Or: Try to approve/reject with backend down

**Expected Results**:
- Error state displays with red error icon
- Error message shows: "Failed to load proposals"
- Error detail shows network error message
- Error toast appears
- No JavaScript errors crash the page

### TC10: Permission Enforcement

**Objective**: Verify non-admin users cannot approve/reject

**Steps**:
1. Create user with READ capability (not ADMIN)
2. Login as that user
3. Navigate to Memory Proposals
4. Verify proposals are visible but not actionable

**Expected Results**:
- Proposals list loads successfully
- Proposal cards display without Approve/Reject buttons
- Or: Attempting to approve/reject shows 403 Forbidden error

### TC11: Responsive Design

**Objective**: Verify UI works on different screen sizes

**Steps**:
1. Open Memory Proposals in browser
2. Resize browser window to various sizes:
   - Desktop: 1920x1080
   - Tablet: 768x1024
   - Mobile: 375x667
3. Verify layout adapts correctly

**Expected Results**:
- Layout adapts to screen size
- Filter buttons wrap on smaller screens
- Proposal cards stack vertically
- No horizontal scrolling
- Action buttons stack vertically on mobile

### TC12: Timestamp Formatting

**Objective**: Verify timestamps display correctly

**Steps**:
1. Create proposals at different times:
   - Just now
   - 5 minutes ago
   - 2 hours ago
   - 2 days ago
2. View proposals list

**Expected Results**:
Timestamps show relative time:
- Less than 1 minute: "just now"
- Less than 1 hour: "{N} min(s) ago"
- Less than 24 hours: "{N} hour(s) ago"
- More than 24 hours: Date formatted as "Mon DD, HH:MM"

## Acceptance Criteria Checklist

Task #18 is complete when all of the following are true:

- [ ] MemoryProposalsView.js implemented with all required methods
- [ ] memory-proposals.css created with responsive styles
- [ ] Navigation menu item added with proposals badge
- [ ] Route handler added to main.js
- [ ] Badge update function integrated
- [ ] All test cases pass (TC1-TC12)
- [ ] No console errors during normal operation
- [ ] UI matches design specifications
- [ ] Integration with Task #17 API endpoints verified
- [ ] Documentation completed

## Known Issues / Future Improvements

1. **Batch Operations**: No multi-select for bulk approve/reject
2. **Search**: No search functionality in proposals list
3. **Sorting**: No custom sorting options
4. **Pagination**: All proposals loaded at once (limit: 100)
5. **Real-time Updates**: Uses polling (30s) instead of WebSocket
6. **History View**: No detailed audit trail view per proposal

## Related Tests

- Backend tests: `/tests/unit/core/memory/test_proposals.py`
- API tests: Can be added to `/tests/integration/test_memory_api.py`
- E2E tests: Can be added using Playwright/Selenium

## Debug Tips

### View Badge Update Logs
Open browser console and run:
```javascript
// Check if badge update is working
setInterval(() => {
  const badge = document.getElementById('proposals-badge');
  console.log('Badge display:', badge?.style.display, 'Content:', badge?.textContent);
}, 5000);
```

### Manually Trigger Badge Update
```javascript
updateProposalsBadge().then(() => console.log('Badge updated'));
```

### Check Proposals Data
```javascript
// In MemoryProposalsView
const view = state.currentViewInstance;
console.log('Proposals:', view.proposals);
console.log('Current filter:', view.currentFilter);
```

### Test API Endpoints Directly
```bash
# List proposals
curl "http://localhost:5002/api/memory/proposals?agent_id=user:current"

# Get stats
curl "http://localhost:5002/api/memory/proposals/stats?agent_id=user:current"
```

## Test Report Template

```
Test Date: YYYY-MM-DD
Tester: [Name]
Browser: [Chrome/Firefox/Safari] [Version]
OS: [macOS/Windows/Linux]

Test Results:
- TC1: ✓ Pass / ✗ Fail - [Notes]
- TC2: ✓ Pass / ✗ Fail - [Notes]
- TC3: ✓ Pass / ✗ Fail - [Notes]
...

Issues Found:
1. [Issue description]
2. [Issue description]

Overall Status: ✓ All Pass / ✗ Needs Fixes
```
