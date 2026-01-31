# Lead Scan History View - Acceptance Checklist

## Overview
This checklist verifies that the Lead Scan History View meets all requirements and acceptance criteria.

---

## 1. View Accessibility

### Navigation
- [ ] Governance section visible in sidebar
- [ ] "Lead Scans" menu item appears under Governance
- [ ] Menu item has clipboard checkmark icon
- [ ] Clicking menu item loads view
- [ ] View title shows "Lead Scans" in header
- [ ] URL/state updates to reflect current view

---

## 2. Page Layout and Components

### Header Section
- [ ] View header displays "Lead Agent - Risk Mining"
- [ ] Three action buttons present:
  - [ ] "Dry Run (Preview)" button (secondary style)
  - [ ] "Real Run (Create Tasks)" button (danger/red style)
  - [ ] "Refresh" button
- [ ] All buttons have appropriate icons

### Information Banner
- [ ] Info banner displays below header
- [ ] Banner has blue background with info icon
- [ ] Text explains: "Lead Agent runs automatically via Cron..."
- [ ] Banner is clearly visible and readable

### Scan Configuration
- [ ] "Scan Window" label present
- [ ] Dropdown shows three options:
  - [ ] "24h (Last 24 hours)" - selected by default
  - [ ] "7d (Last 7 days)"
  - [ ] "30d (Last 30 days)"
- [ ] Help text explains window purpose
- [ ] Dropdown is styled consistently

### Statistics Section
- [ ] Stats section initially hidden (no findings yet)
- [ ] After findings exist, stats section displays
- [ ] Six stat cards shown:
  - [ ] Total Findings
  - [ ] Critical (red icon)
  - [ ] High (orange icon)
  - [ ] Medium (blue icon)
  - [ ] Low (green icon)
  - [ ] Unlinked (needs tasks)
- [ ] Stat cards have hover effects
- [ ] Numbers display in monospace font
- [ ] Cards are responsive and align properly

### Scan Result Section
- [ ] Initially hidden (no scan run yet)
- [ ] Appears after manual scan execution
- [ ] Shows scan ID with timestamp
- [ ] Displays mode badge (DRY RUN or REAL RUN)
- [ ] Shows scan timestamp
- [ ] Displays four statistics:
  - [ ] Window (24h/7d/30d)
  - [ ] Findings count
  - [ ] New findings count (highlighted)
  - [ ] Tasks created count
- [ ] Top Findings section shows when findings exist
- [ ] Up to 10 findings displayed
- [ ] Each finding shows:
  - [ ] Severity badge with icon and color
  - [ ] Finding code in monospace
  - [ ] Count badge
  - [ ] Task link (if task created)

### Findings Table
- [ ] Table displays below scan result
- [ ] Header shows "Recent Findings"
- [ ] Six columns present:
  - [ ] Finding Code
  - [ ] Severity
  - [ ] Window
  - [ ] Count
  - [ ] Last Seen
  - [ ] Follow-up Task
- [ ] Table uses DataTable component
- [ ] Pagination shows (20 items per page)
- [ ] Empty state shows helpful message
- [ ] Loading state works correctly

---

## 3. Dry Run Functionality

### Button Behavior
- [ ] "Dry Run" button clickable initially
- [ ] Button disables during scan
- [ ] Loading state activates (buttons disabled, select disabled)
- [ ] Button re-enables after scan completes

### Scan Execution
- [ ] Toast notification: "Starting Dry Run (24h)..."
- [ ] API call to `/api/lead/scan?window=24h&dry_run=true`
- [ ] Scan completes within reasonable time (<2 minutes)
- [ ] No errors occur during scan

### Results Display
- [ ] Scan result card appears
- [ ] Scan ID displays with timestamp
- [ ] "DRY RUN" badge shows (blue background)
- [ ] Findings count is accurate
- [ ] New findings count is accurate
- [ ] Tasks created count is 0
- [ ] Top findings list populates
- [ ] Findings table refreshes with new data
- [ ] Stats section updates
- [ ] Success toast: "Scan completed: X findings (Y new)"
- [ ] Page scrolls to scan result

---

## 4. Real Run Functionality

### Confirmation Dialog
- [ ] Clicking "Real Run" shows confirmation dialog
- [ ] Dialog title: "Confirm Real Run"
- [ ] Dialog message: "This will create follow-up tasks for new findings. Continue?"
- [ ] Dialog has two buttons:
  - [ ] "Cancel" (secondary)
  - [ ] "Run Scan" (danger/red)
- [ ] Clicking "Cancel" closes dialog without scanning
- [ ] Clicking "Run Scan" proceeds with scan

### Scan Execution
- [ ] After confirmation, scan begins
- [ ] Toast notification: "Starting Real Run (window)..."
- [ ] API call to `/api/lead/scan?window=X&dry_run=false`
- [ ] Scan completes successfully
- [ ] No errors occur

### Results Display
- [ ] Scan result card appears
- [ ] "REAL RUN" badge shows (red background)
- [ ] Tasks created count > 0 (if new findings exist)
- [ ] Follow-up tasks link to Tasks view
- [ ] Findings table shows linked task IDs
- [ ] Success toast appears
- [ ] Page scrolls to scan result

### Task Creation
- [ ] Navigate to Tasks view
- [ ] New tasks visible with Lead Agent as creator
- [ ] Task IDs match linked_task_id in findings
- [ ] Tasks have appropriate status (pending/running)

---

## 5. Window Selection

### 24h Window
- [ ] Select "24h" from dropdown
- [ ] Run Dry Run scan
- [ ] Results show window="24h"
- [ ] Findings are from last 24 hours

### 7d Window
- [ ] Select "7d" from dropdown
- [ ] Run Dry Run scan
- [ ] Results show window="7d"
- [ ] Findings are from last 7 days

### 30d Window
- [ ] Select "30d" from dropdown
- [ ] Run Dry Run scan
- [ ] Results show window="30d"
- [ ] Findings are from last 30 days

---

## 6. Statistics Display

### Data Loading
- [ ] Stats load automatically on page load
- [ ] API call to `/api/lead/stats`
- [ ] Stats populate correctly
- [ ] No errors during loading

### Stat Cards
- [ ] Total shows sum of all findings
- [ ] CRITICAL count matches backend
- [ ] HIGH count matches backend
- [ ] MEDIUM count matches backend
- [ ] LOW count matches backend
- [ ] Unlinked count shows findings without tasks
- [ ] All numbers formatted correctly
- [ ] Icons match severity levels
- [ ] Colors match severity levels

---

## 7. Findings Table

### Data Loading
- [ ] Findings load automatically on page load
- [ ] API call to `/api/lead/findings?limit=200`
- [ ] Table populates with findings
- [ ] No errors during loading

### Table Display
- [ ] Finding codes in monospace font
- [ ] Severity badges color-coded:
  - [ ] CRITICAL - red
  - [ ] HIGH - orange
  - [ ] MEDIUM - blue
  - [ ] LOW - green
- [ ] Window badges display correctly
- [ ] Count badges show accurate numbers
- [ ] Timestamps are relative (e.g., "2h ago", "Just now")
- [ ] Task links display when task exists
- [ ] "None" shows when no task linked

### Pagination
- [ ] Pagination controls visible (if >20 findings)
- [ ] "Previous" and "Next" buttons work
- [ ] Page numbers update correctly
- [ ] Correct items show on each page

### Task Navigation
- [ ] Clicking task ID button triggers navigation
- [ ] Navigates to Tasks view
- [ ] Correct task displays (matching task_id)
- [ ] Navigation works from both:
  - [ ] Top findings list
  - [ ] Findings table

---

## 8. Refresh Functionality

### Refresh Button
- [ ] "Refresh" button clickable
- [ ] Clicking triggers refresh
- [ ] Toast notification: "Refreshing..."
- [ ] Both stats and findings reload
- [ ] Data updates to latest
- [ ] Success toast: "Findings refreshed"
- [ ] No errors occur

---

## 9. Loading States

### During Scan
- [ ] All three header buttons disable
- [ ] Scan window dropdown disables
- [ ] Button text remains visible
- [ ] Cursor shows "not-allowed" on hover
- [ ] Buttons have reduced opacity

### Table Loading
- [ ] Loading spinner shows in table
- [ ] Loading text: "Loading findings..."
- [ ] Table clears previous data
- [ ] After load, spinner disappears
- [ ] Data populates table

---

## 10. Error Handling

### API Errors
- [ ] Test scan with network disconnected
- [ ] Error toast displays
- [ ] Error message is user-friendly
- [ ] Buttons re-enable after error
- [ ] View remains functional

### Empty States
- [ ] With no findings:
  - [ ] Stats section hidden
  - [ ] Table shows: "No findings yet. Run a scan to discover risks."
- [ ] After failed scan:
  - [ ] Previous data remains visible
  - [ ] Error toast shows
  - [ ] Can retry scan

---

## 11. Responsive Design

### Desktop (>1200px)
- [ ] Full layout displays
- [ ] Stats grid: 6 columns
- [ ] Scan stats grid: 4 columns
- [ ] All content readable
- [ ] No horizontal scroll

### Tablet (768px - 1200px)
- [ ] Stats grid: 3 columns
- [ ] Scan stats grid: 2 columns
- [ ] Table columns adjust
- [ ] Buttons stack if needed
- [ ] Content remains readable

### Mobile (<768px)
- [ ] Stats grid: 1-2 columns
- [ ] Scan stats grid: 1-2 columns
- [ ] Table scrolls horizontally
- [ ] Buttons stack vertically
- [ ] Text sizes appropriate

---

## 12. Severity Color Coding

### Visual Consistency
- [ ] CRITICAL uses consistent red (#f8d7da background, #721c24 text)
- [ ] HIGH uses consistent orange (#fff3cd background, #856404 text)
- [ ] MEDIUM uses consistent blue (#d1ecf1 background, #0c5460 text)
- [ ] LOW uses consistent green (#d4edda background, #155724 text)
- [ ] Colors match across:
  - [ ] Stat cards
  - [ ] Severity badges
  - [ ] Top findings list
  - [ ] Findings table

### Icons
- [ ] CRITICAL shows error icon
- [ ] HIGH shows warning icon
- [ ] MEDIUM shows info icon
- [ ] LOW shows check circle icon
- [ ] Icons match Material Design

---

## 13. User Experience

### Visual Feedback
- [ ] Hover states work on:
  - [ ] Buttons
  - [ ] Stat cards
  - [ ] Task links
  - [ ] Table rows
- [ ] Active/clicked states visible
- [ ] Transitions smooth (0.2s)

### Notifications
- [ ] Toast positions correctly (top-right)
- [ ] Toasts auto-dismiss after timeout
- [ ] Toast types correct:
  - [ ] Success (green)
  - [ ] Error (red)
  - [ ] Info (blue)
- [ ] Multiple toasts stack properly

### Scrolling
- [ ] After scan completes, page scrolls to result
- [ ] Scroll is smooth (not jarring)
- [ ] Result visible without manual scroll

---

## 14. Accessibility

### Keyboard Navigation
- [ ] Tab moves through interactive elements
- [ ] Tab order is logical:
  1. Dry Run button
  2. Real Run button
  3. Refresh button
  4. Window dropdown
  5. Task links
  6. Pagination controls
- [ ] Enter/Space activate buttons
- [ ] Arrow keys work in dropdown
- [ ] Escape closes dialog

### Screen Reader
- [ ] Button labels are descriptive
- [ ] Stat cards have aria-labels
- [ ] Table has proper headers
- [ ] Loading states announced
- [ ] Error messages announced
- [ ] Success messages announced

### Color Contrast
- [ ] All text meets WCAG AA (4.5:1)
- [ ] Severity colors have sufficient contrast
- [ ] Button text readable
- [ ] Links distinguishable

---

## 15. Browser Compatibility

### Chrome/Edge
- [ ] View loads correctly
- [ ] All features work
- [ ] No console errors
- [ ] Styles render properly

### Firefox
- [ ] View loads correctly
- [ ] All features work
- [ ] No console errors
- [ ] Styles render properly

### Safari
- [ ] View loads correctly
- [ ] All features work
- [ ] No console errors
- [ ] Styles render properly

---

## 16. Performance

### Load Time
- [ ] Initial page load < 2 seconds
- [ ] Stats load < 1 second
- [ ] Findings load < 2 seconds
- [ ] No blocking operations

### Scan Time
- [ ] Dry Run completes < 2 minutes
- [ ] Real Run completes < 2 minutes
- [ ] Timeout set to 2 minutes (120000ms)
- [ ] No memory leaks

### Table Performance
- [ ] 200 findings render quickly
- [ ] Pagination is instant
- [ ] Sorting is fast
- [ ] No lag when scrolling

---

## 17. Integration

### With Tasks View
- [ ] Task links navigate correctly
- [ ] Task IDs match between views
- [ ] Can return to Lead Scans view
- [ ] Navigation history works

### With API
- [ ] POST /api/lead/scan works
- [ ] GET /api/lead/findings works
- [ ] GET /api/lead/stats works
- [ ] Error responses handled
- [ ] Response formats match expectations

### With Components
- [ ] DataTable renders correctly
- [ ] Dialog component works
- [ ] Toast component works
- [ ] ApiClient handles requests
- [ ] navigateToView function works

---

## 18. Code Quality

### JavaScript
- [ ] No console errors
- [ ] No console warnings
- [ ] Proper error handling
- [ ] Memory cleanup on destroy
- [ ] Follows existing patterns
- [ ] Comments where needed
- [ ] Variable names clear

### CSS
- [ ] No style conflicts
- [ ] Follows naming conventions
- [ ] Responsive classes work
- [ ] No unused styles
- [ ] Consistent spacing
- [ ] Proper specificity

### HTML
- [ ] Semantic markup
- [ ] Valid HTML structure
- [ ] Proper nesting
- [ ] Consistent indentation
- [ ] No duplicate IDs

---

## 19. Security

### Input Validation
- [ ] Window parameter validated
- [ ] Scan type validated (dry_run boolean)
- [ ] No SQL injection risk
- [ ] No XSS vulnerabilities

### Authorization
- [ ] Anyone can view findings (read-only data)
- [ ] Real Run requires confirmation
- [ ] API validates all requests
- [ ] Task creation logged

---

## 20. Documentation

### Code Documentation
- [ ] LeadScanHistoryView.js has header comment
- [ ] Functions have JSDoc comments
- [ ] Complex logic explained
- [ ] Implementation guide exists
- [ ] Acceptance checklist exists

### User Documentation
- [ ] Info banner explains purpose
- [ ] Help text on window selection
- [ ] Error messages are clear
- [ ] Success messages are informative

---

## Summary

**Total Checks**: ~250 items across 20 categories

**Completion Status**:
- [ ] All checks passed
- [ ] View ready for production
- [ ] Documentation complete
- [ ] No blocking issues

**Sign-off**:
- Developer: _______________  Date: ___________
- QA Tester: _______________  Date: ___________
- Product Owner: ___________  Date: ___________

---

## Notes

Any issues found during testing should be documented below:

---

**Issue 1**:
- Description:
- Severity: [ ] Critical [ ] High [ ] Medium [ ] Low
- Status: [ ] Open [ ] Fixed [ ] Won't Fix
- Notes:

---

**Issue 2**:
- Description:
- Severity: [ ] Critical [ ] High [ ] Medium [ ] Low
- Status: [ ] Open [ ] Fixed [ ] Won't Fix
- Notes:

---

## Test Data Setup

For comprehensive testing, ensure:
1. At least 25 findings exist (to test pagination)
2. Findings span multiple severity levels
3. Some findings have linked tasks
4. Some findings are unlinked
5. Findings exist in multiple windows (24h, 7d, 30d)

Run this to seed test data:
```bash
# Run Lead Agent scan to generate findings
# (This would be in your test environment setup)
```
