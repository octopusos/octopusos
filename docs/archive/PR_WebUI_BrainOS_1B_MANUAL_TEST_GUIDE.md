# PR-WebUI-BrainOS-1B: Manual Testing Guide
## Explain Button Embedding - Verification Checklist

**Date**: 2026-01-30
**Tester**: _____________
**Browser**: _____________
**OS**: _____________

---

## 🚀 Pre-Test Setup

### 1. Start AgentOS WebUI
```bash
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.cli.webui
```

### 2. Ensure BrainOS Index Exists
```bash
# Check if .brainos directory exists
ls -la .brainos/

# If not, build index (optional, can test without index too)
# The Explain button should show "BrainOS index not found" error gracefully
```

### 3. Open Browser
- Navigate to `http://localhost:5000` (or configured port)
- Open Developer Console (F12)
- Check for any JavaScript errors (should be none)

---

## ✅ Test 1: Tasks View - Explain Button

### Steps:
1. Click "**Tasks**" in left sidebar
2. If no tasks exist:
   - Click "**Create Task**" button
   - Fill in: Title = "Test Task", Description = "Testing Explain"
   - Submit
3. Click on any task row to open detail drawer
4. **Look for 🧠 button** next to task title in drawer header

### Expected Results:
- [  ] 🧠 button visible next to task title
- [  ] Button has 50% opacity, increases to 100% on hover
- [  ] Cursor changes to pointer on hover

### Action: Click 🧠 Button
- [  ] Drawer slides in from right side
- [  ] Drawer header shows "🧠 Explain: [Task Title]"
- [  ] 4 tabs visible: Why, Impact, Trace, Map
- [  ] "Why" tab active by default
- [  ] Loading spinner appears briefly
- [  ] Result appears (or error message if no index)

### Test Each Tab:
- [  ] Click "**Why**" tab → Shows paths or "No explanation found"
- [  ] Click "**Impact**" tab → Shows affected nodes or "No dependencies found"
- [  ] Click "**Trace**" tab → Shows timeline or "No history found"
- [  ] Click "**Map**" tab → Shows subgraph or "No related entities"

### Close Drawer:
- [  ] Click **X button** → Drawer closes
- [  ] Re-open drawer, click **overlay** (dark area) → Drawer closes
- [  ] Re-open drawer, press **ESC key** → Drawer closes

### Check Console:
- [  ] No JavaScript errors in console

---

## ✅ Test 2: Extensions View - Explain Button

### Steps:
1. Click "**Extensions**" in left sidebar (under Settings section)
2. Wait for extensions to load
3. **Look for 🧠 button** next to each extension name

### Expected Results:
- [  ] 🧠 button visible next to extension name in card header
- [  ] Button appears for ALL extensions in grid
- [  ] Button styling consistent with Tasks view

### Action: Click 🧠 Button on First Extension
- [  ] Drawer opens from right
- [  ] Header shows "🧠 Explain: [Extension Name]"
- [  ] Tabs: Why, Impact, Trace, Map

### Test Query:
- [  ] "**Why**" tab → Should show capability origin or "No explanation"
- [  ] "**Trace**" tab → Should show documentation references or timeline
- [  ] Seed auto-derived as `capability:[extension_name]`

### Test Multiple Extensions:
- [  ] Close drawer
- [  ] Click 🧠 on a DIFFERENT extension
- [  ] Drawer updates with new extension name
- [  ] Query results refresh for new extension

### Check Console:
- [  ] No JavaScript errors

---

## ✅ Test 3: Context View - Explain Button

### Steps:
1. Click "**Context**" in left sidebar (under System section)
2. If you have a session ID:
   - Paste session ID in input field
   - Click "**Load Context Status**"
3. If you don't have a session ID:
   - Click "**Recent Sessions**" button
   - Select any session from list

### Expected Results:
- [  ] Context status loads successfully
- [  ] **Look for 🧠 button** in "Context Status" section header (top-right area)

### Action: Click 🧠 Button
- [  ] Drawer opens
- [  ] Header shows "🧠 Explain: Session [session_id]"
- [  ] Tabs visible

### Test Queries:
- [  ] "**Why**" tab → Queries `file:session:[id]` (may have no results)
- [  ] "**Impact**" tab → Shows what depends on this session context
- [  ] "**Map**" tab → Shows related entities (files, tasks, etc.)

### Check Console:
- [  ] No JavaScript errors

---

## ✅ Test 4: Responsiveness & Mobile

### Steps:
1. Resize browser window to mobile size (e.g., 375px width)
2. Open Tasks view → Click task → Click 🧠

### Expected Results:
- [  ] Drawer takes 90% of screen width (or full width)
- [  ] Tabs wrap gracefully (or scroll horizontally)
- [  ] Content scrollable
- [  ] Drawer still closeable with X button

### Desktop View:
- [  ] Resize back to desktop
- [  ] Drawer width fixed at 500px
- [  ] Does not block entire screen

---

## ✅ Test 5: Error Handling

### Scenario A: BrainOS Index Not Built
- [  ] If `.brainos/` directory doesn't exist:
  - Click 🧠 on any entity
  - Query should return: "BrainOS index not found. Build index first."
  - Error message displayed in drawer (not JS console crash)

### Scenario B: Network Failure (Simulate)
- [  ] Open DevTools → Network tab
- [  ] Throttle to "Offline" mode
- [  ] Click 🧠 button
- [  ] Should show error: "Failed to query BrainOS" (not crash)

### Scenario C: No Results Found
- [  ] Query an entity with no references (e.g., new task)
- [  ] Should show: "No explanation found. This may indicate missing documentation..."
- [  ] NOT a JavaScript error

---

## ✅ Test 6: XSS Protection

### Steps:
1. Create a task with special characters in title:
   - Title: `<script>alert('XSS')</script>`
2. Open task detail
3. Click 🧠 button

### Expected Results:
- [  ] Drawer header shows escaped HTML: `&lt;script&gt;...`
- [  ] NO alert popup appears
- [  ] No script execution

---

## ✅ Test 7: Evidence Links (If BrainOS Index Exists)

### Steps:
1. Query an entity that has evidence (e.g., a file with doc references)
2. In "**Why**" tab results, look for evidence section
3. Click on any "**View**" link next to evidence item

### Expected Results:
- [  ] Link navigates to correct view (e.g., `/#/knowledge?doc=...`)
- [  ] Navigation works within same page (SPA routing)
- [  ] Drawer remains open (or closes, depending on design choice)

---

## ✅ Test 8: Rapid Clicks (Edge Case)

### Steps:
1. Open Tasks view
2. Rapidly click 🧠 button 5 times in 1 second

### Expected Results:
- [  ] Only ONE drawer instance appears
- [  ] No duplicate drawers stacked
- [  ] No console errors about duplicate event listeners

---

## ✅ Test 9: Tab Switching Performance

### Steps:
1. Open Explain drawer
2. Rapidly switch between tabs: Why → Impact → Trace → Map → Why
3. Do this 5 times quickly

### Expected Results:
- [  ] Loading spinner appears each time
- [  ] Results render correctly for each tab
- [  ] No "stale" results from previous tab
- [  ] No memory leaks (check Task Manager if concerned)

---

## ✅ Test 10: Browser Compatibility

### Browsers to Test:
- [  ] **Chrome/Edge** (Chromium) - Primary target
- [  ] **Firefox** - Secondary target
- [  ] **Safari** (if on macOS) - Optional

### Check for Each Browser:
- [  ] Drawer animation smooth
- [  ] Button hover effects work
- [  ] Query results render correctly
- [  ] No layout issues
- [  ] No console errors

---

## 🐛 Bug Report Template

If you find any issues, use this template:

```
**Bug Title**: [Brief description]

**Steps to Reproduce**:
1.
2.
3.

**Expected Behavior**:
[What should happen]

**Actual Behavior**:
[What actually happens]

**Screenshot/Console Error**:
[Paste here]

**Browser**: Chrome 120.0.0 / Firefox 121.0 / etc.
**OS**: macOS 14 / Windows 11 / Ubuntu 22.04

**Severity**: Critical / High / Medium / Low
```

---

## ✅ Final Acceptance Checklist

### Core Functionality:
- [  ] Explain button appears in Tasks view
- [  ] Explain button appears in Extensions view
- [  ] Explain button appears in Context view
- [  ] Drawer opens/closes correctly
- [  ] All 4 query types work (Why, Impact, Trace, Map)
- [  ] Auto seed derivation works
- [  ] Error handling graceful (no crashes)

### UI/UX:
- [  ] Button styling consistent across views
- [  ] Drawer animation smooth
- [  ] Loading states visible
- [  ] Empty states friendly
- [  ] Mobile responsive
- [  ] No visual glitches

### Security:
- [  ] HTML escaping works (no XSS)
- [  ] No sensitive data exposed in console

### Performance:
- [  ] No memory leaks
- [  ] Fast query execution (< 2s for typical query)
- [  ] No lag when switching tabs

---

## 📋 Test Summary

**Date Completed**: ___________
**Total Tests Run**: ____ / 10
**Tests Passed**: ____
**Tests Failed**: ____
**Critical Bugs Found**: ____

**Overall Status**: ❌ Failed / ⚠️ Partial / ✅ Passed

**Notes**:
_______________________________________________________
_______________________________________________________
_______________________________________________________

**Tester Signature**: _____________

---

## 🚀 Next Steps After Testing

If all tests pass:
1. Mark PR-WebUI-BrainOS-1B as **COMPLETE**
2. Commit changes with commit message from Implementation Report
3. Update project documentation
4. Demo to team (optional)

If tests fail:
1. Document bugs using template above
2. Prioritize fixes (Critical → High → Medium → Low)
3. Apply fixes
4. Re-test failed scenarios
5. Repeat until all tests pass

---

**Happy Testing!** 🧠✨
