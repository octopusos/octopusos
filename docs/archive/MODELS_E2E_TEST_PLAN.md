# Models Management Feature - E2E Test Plan
## Task #5: 端到端功能测试

**Date:** 2026-01-30
**Tester:** Claude Code
**Environment:** macOS, Python 3.x, Ollama 0.15.2

---

## 📋 Test Environment

### Prerequisites
- ✅ Ollama service running (v0.15.2)
- ✅ Model installed: llama3.2:3b (2.0 GB)
- ⚠️ AgentOS WebUI (to be started)

### Environment Setup
```bash
# 1. Check Ollama status
curl http://localhost:11434/api/version
# Expected: {"version":"0.15.2"}

# 2. Check installed models
ollama list
# Expected: List of models

# 3. Start AgentOS WebUI
cd /Users/pangge/PycharmProjects/AgentOS
agentos webui
# Expected: Server starts on http://localhost:8000
```

---

## 🧪 Test Scenarios

### Test 1: Page Access & Initial Load
**Objective:** Verify the Models page loads correctly

**Steps:**
1. Open browser and navigate to http://localhost:8000
2. Click on sidebar: Settings → Models
3. Wait for page to load

**Expected Results:**
- ✅ Page loads without errors
- ✅ No JavaScript console errors
- ✅ CSS styles applied correctly
- ✅ Layout matches Extensions page design
- ✅ Page title shows "Models"
- ✅ Subtitle shows "Manage your AI models (Ollama/llama.cpp)"

**Acceptance Criteria:**
- Page load time < 2 seconds
- No 404 errors in Network tab
- No red errors in Console tab

---

### Test 2: Service Status Display
**Objective:** Verify service status indicators work correctly

**Steps:**
1. Observe the status section at top of page
2. Check Ollama status indicator
3. Check llama.cpp status indicator (if available)

**Expected Results:**
- ✅ Ollama status shows as "Available" or "运行中"
- ✅ Green checkmark (✓) displayed
- ✅ Version number displayed (v0.15.2)
- ✅ Status updates automatically every 5 seconds
- ⚠️ llama.cpp status shows "Not Available" (if not installed)

**Acceptance Criteria:**
- Status check completes < 500ms
- Visual indicators clear and intuitive
- Auto-refresh works without manual reload

---

### Test 3: Model List Display
**Objective:** Verify installed models display correctly

**Steps:**
1. Observe the models grid section
2. Check model card information
3. Verify all fields display correctly

**Expected Results:**
- ✅ llama3.2:3b model displayed in grid
- ✅ Model card shows:
  - Model name: "llama3.2:3b"
  - Provider: "ollama"
  - Size: "2.0 GB"
  - Parameters: "3B" (if extracted)
  - Family: "llama" (if available)
  - Tags: "chat", "fast" (if available)
- ✅ Action buttons visible: [Info] [Delete]
- ✅ Model icon displayed (🤖)

**Acceptance Criteria:**
- All models display correctly
- No missing information
- Cards responsive to screen size

---

### Test 4: Empty State Display
**Objective:** Verify empty state when no models installed

**Note:** This test requires deleting all models first (destructive)

**Steps:**
1. Delete all installed models via UI or CLI
2. Refresh the Models page

**Expected Results:**
- ✅ Empty state icon displayed (🤖)
- ✅ Message: "No Models Installed"
- ✅ Subtitle: "Get started by downloading your first model"
- ✅ [Download Model] button prominently displayed

**Status:** ⚠️ SKIPPED (preserve existing models)

---

### Test 5: Download Model Dialog
**Objective:** Verify download modal opens and displays correctly

**Steps:**
1. Click [+ Download Model] button
2. Observe modal dialog
3. Check recommended models list
4. Check custom input field

**Expected Results:**
- ✅ Modal opens smoothly (fade-in animation)
- ✅ Modal title: "Download Model"
- ✅ Recommended models section displays:
  - qwen2.5:7b (4.7 GB) - Chinese optimized
  - llama3.2:3b (2.0 GB) - Fast response
  - llama3.2:1b (1.3 GB) - Lightweight
  - gemma2:2b (1.6 GB) - Google model
  - qwen2.5-coder:7b (4.7 GB) - Code generation
- ✅ Each model shows: display name, size, description, tags
- ✅ Custom input field with placeholder text
- ✅ Form divider with "OR" label
- ✅ Action buttons: [Cancel] [Download]

**Acceptance Criteria:**
- Modal centered and responsive
- All recommended models display correctly
- Tags color-coded appropriately
- Close button (×) visible

---

### Test 6: Model Selection in Dialog
**Objective:** Verify model selection behavior

**Steps:**
1. Open download modal
2. Click on a recommended model card
3. Click on a different model card
4. Type in custom input field

**Expected Results:**
- ✅ Clicking model card highlights it (selected state)
- ✅ Only one model can be selected at a time
- ✅ Typing in custom input clears recommended selection
- ✅ [Download] button enabled when selection made

**Acceptance Criteria:**
- Visual feedback for selection (border highlight)
- Mutually exclusive selection
- Smooth interaction (no lag)

---

### Test 7: Model Download - Small Model (llama3.2:1b)
**Objective:** Verify model download with progress tracking

**Test Model:** llama3.2:1b (~1.3 GB, fastest download)

**Steps:**
1. Open download modal
2. Select llama3.2:1b from recommended list
3. Click [Download] button
4. Observe progress bar and status

**Expected Results:**
- ✅ Modal closes after clicking Download
- ✅ Progress section appears below status cards
- ✅ Progress bar displays with model name
- ✅ Progress percentage updates in real-time
- ✅ Status text shows current step:
  - "Starting download..."
  - "Pulling manifest"
  - "Downloading: X%"
  - "Verifying checksum"
  - "Download complete"
- ✅ Progress bar fills from 0% to 100%
- ✅ Download completes successfully
- ✅ Success notification appears
- ✅ Model appears in model list automatically
- ✅ Progress section disappears after 2 seconds

**Acceptance Criteria:**
- Progress updates < 1 second latency
- Download completes without errors
- Progress bar smooth (no jumps)
- Model list refreshes automatically
- Download time: 5-15 minutes (depending on network)

**Performance Metrics:**
- Initial response: < 1 second
- Progress poll interval: 500ms
- Progress update latency: < 1 second
- UI remains responsive during download

---

### Test 8: Custom Model Download
**Objective:** Verify custom model name input works

**Test Model:** gemma2:2b (or any unlisted model)

**Steps:**
1. Open download modal
2. Type "gemma2:2b" in custom input field
3. Click [Download] button
4. Observe download progress

**Expected Results:**
- ✅ Custom model name accepted
- ✅ Download starts successfully
- ✅ Progress tracking works same as recommended models
- ✅ Model appears in list after download

**Status:** ⚠️ OPTIONAL (to save time/bandwidth)

---

### Test 9: Concurrent Downloads
**Objective:** Verify multiple downloads can run simultaneously

**Steps:**
1. Start downloading llama3.2:1b
2. Immediately start downloading gemma2:2b
3. Observe both progress bars

**Expected Results:**
- ✅ Two progress bars display simultaneously
- ✅ Both progress bars update independently
- ✅ Both downloads complete successfully
- ✅ No interference between downloads
- ✅ Both models appear in list

**Status:** ⚠️ OPTIONAL (to save time)

---

### Test 10: Model Info Dialog
**Objective:** Verify model information display

**Steps:**
1. Click [Info] button on any model card
2. Observe information modal
3. Check all displayed fields

**Expected Results:**
- ✅ Modal opens with "Model Information" title
- ✅ Basic Information section shows:
  - Name: llama3.2:3b
  - Provider: ollama
  - Family: llama
  - Size: 2.0 GB
  - Parameters: 3B
  - Quantization: (if available)
- ✅ Tags section (if tags exist)
- ✅ Additional Details section:
  - Last Modified: timestamp
  - Digest: (if available)
- ✅ [Close] button works

**Acceptance Criteria:**
- All available fields display correctly
- Timestamps formatted properly
- Modal scrollable if content long
- Close on background click works

---

### Test 11: Model Deletion
**Objective:** Verify model deletion with confirmation

**⚠️ WARNING:** This is a destructive operation

**Steps:**
1. Click [Delete] button on a model card
2. Observe confirmation dialog
3. Click [Cancel] (first time)
4. Click [Delete] again and click [Delete] (confirm)

**Expected Results:**
- ✅ Confirmation modal appears
- ✅ Warning message displayed:
  - "Are you sure you want to delete?"
  - Model name highlighted
  - Yellow warning box with icon
  - "This action cannot be undone" text
- ✅ Action buttons: [Cancel] [Delete]
- ✅ Clicking [Cancel] closes modal without deleting
- ✅ Clicking [Delete] removes model
- ✅ Success notification appears
- ✅ Model removed from list immediately
- ✅ Model list refreshes

**Acceptance Criteria:**
- Confirmation dialog prevents accidental deletion
- Deletion completes < 5 seconds
- Model actually removed from Ollama
- No errors in console

---

### Test 12: Responsive Layout
**Objective:** Verify layout adapts to different screen sizes

**Steps:**
1. Open Models page in full screen
2. Resize browser window to tablet size (768-1024px)
3. Resize to mobile size (<768px)
4. Check all elements at each size

**Expected Results:**
- ✅ Desktop (>1024px): 3-column grid
- ✅ Tablet (768-1024px): 2-column grid
- ✅ Mobile (<768px): 1-column grid
- ✅ All buttons remain accessible
- ✅ Modals adapt to screen width
- ✅ Text remains readable
- ✅ No horizontal scrolling
- ✅ Touch targets adequate size (mobile)

**Acceptance Criteria:**
- Layout transitions smooth
- No overlapping elements
- All features accessible on mobile
- Consistent with Extensions page responsiveness

---

### Test 13: Error Handling - Ollama Stopped
**Objective:** Verify graceful degradation when Ollama stops

**Steps:**
1. Stop Ollama service: `pkill ollama`
2. Wait for status refresh (5 seconds)
3. Try to download a model
4. Try to delete a model
5. Restart Ollama: `ollama serve &`

**Expected Results:**
- ✅ Status indicator changes to "Not Available"
- ✅ Red X (✗) displayed
- ✅ Model list shows empty or cached state
- ✅ Download attempt shows error: "Ollama service not running"
- ✅ Delete attempt shows error: "Ollama service not running"
- ✅ Error messages user-friendly (not technical)
- ✅ After restart, status recovers automatically
- ✅ Models reappear in list

**Acceptance Criteria:**
- No crashes or freezes
- Error messages clear
- Recovery automatic (no page reload needed)

---

### Test 14: Error Handling - Invalid Model Name
**Objective:** Verify validation of model names

**Steps:**
1. Open download modal
2. Enter invalid model name: "invalid-model-xyz"
3. Click [Download]
4. Observe error handling

**Expected Results:**
- ✅ Download starts (API accepts any name)
- ✅ Progress bar appears
- ✅ After attempt, error message appears
- ✅ Error indicates model not found
- ✅ Progress bar shows failure state
- ✅ User can retry with different name

**Acceptance Criteria:**
- Error message explains issue
- No silent failures
- User can recover and retry

---

### Test 15: Error Handling - Network Interruption
**Objective:** Verify behavior during network issues

**Steps:**
1. Start downloading a large model
2. Disable network (turn off Wi-Fi)
3. Wait for timeout/error
4. Re-enable network

**Expected Results:**
- ✅ Download continues or shows timeout error
- ✅ Error message if download fails
- ✅ User can retry download
- ✅ No permanent broken state

**Status:** ⚠️ OPTIONAL (difficult to test reliably)

---

### Test 16: Browser Console Check
**Objective:** Verify no JavaScript errors during normal operation

**Steps:**
1. Open browser DevTools (F12)
2. Go to Console tab
3. Perform all basic operations:
   - Load page
   - Open download modal
   - Select model
   - Close modal
   - Click Info button
   - Close info modal
4. Check for any errors

**Expected Results:**
- ✅ No red error messages
- ✅ No failed network requests (except expected 404s)
- ✅ No unhandled promise rejections
- ✅ Info/warning logs acceptable
- ✅ All API calls return 200 or expected status codes

**Acceptance Criteria:**
- Zero critical errors
- All resources load successfully
- API responses valid JSON

---

### Test 17: Network Tab Check
**Objective:** Verify API calls are efficient

**Steps:**
1. Open DevTools → Network tab
2. Clear network log
3. Load Models page
4. Observe API calls

**Expected Results:**
- ✅ `/api/models/status` called once
- ✅ `/api/models/list` called once
- ✅ No duplicate API calls
- ✅ All responses < 500ms (for list/status)
- ✅ Proper HTTP methods used (GET/POST/DELETE)
- ✅ Response sizes reasonable

**Acceptance Criteria:**
- No unnecessary API calls
- Efficient data transfer
- Proper caching (if applicable)

---

### Test 18: Performance - Page Load Time
**Objective:** Measure page load performance

**Steps:**
1. Open DevTools → Performance tab
2. Record page load
3. Navigate to Models page
4. Stop recording
5. Analyze metrics

**Expected Results:**
- ✅ Time to Interactive (TTI) < 2 seconds
- ✅ First Contentful Paint (FCP) < 1 second
- ✅ Largest Contentful Paint (LCP) < 2 seconds
- ✅ No long tasks blocking UI (>50ms)
- ✅ CSS loads before render
- ✅ JavaScript loads efficiently

**Acceptance Criteria:**
- Page load < 2 seconds
- No layout shifts
- Smooth animation/transitions

---

### Test 19: Performance - Memory Leak Check
**Objective:** Verify no memory leaks during extended use

**Steps:**
1. Open DevTools → Memory tab
2. Take heap snapshot (baseline)
3. Navigate to Models page
4. Perform various actions (10 times):
   - Open/close download modal
   - Open/close info modal
   - Refresh model list
5. Navigate away from Models page
6. Take another heap snapshot
7. Compare memory usage

**Expected Results:**
- ✅ Memory increase < 10 MB
- ✅ Event listeners cleaned up
- ✅ No detached DOM nodes
- ✅ Intervals/timeouts cleared
- ✅ Memory released after navigation

**Status:** ⚠️ ADVANCED (optional for basic testing)

---

### Test 20: Accessibility Check
**Objective:** Verify basic accessibility compliance

**Steps:**
1. Use keyboard only (no mouse)
2. Tab through all interactive elements
3. Test with screen reader (if available)
4. Check color contrast

**Expected Results:**
- ✅ All buttons focusable via Tab key
- ✅ Focus indicators visible
- ✅ Enter/Space triggers buttons
- ✅ Modals can be closed with Escape key
- ✅ Semantic HTML used (buttons, headings)
- ✅ Alt text on images/icons
- ✅ Color contrast ratio > 4.5:1
- ✅ Form labels associated with inputs

**Status:** ⚠️ OPTIONAL (basic accessibility)

---

## 📊 Performance Benchmarks

### Target Metrics
| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Page Load Time | < 2s | < 5s |
| Model List Refresh | < 500ms | < 1s |
| Status Check | < 500ms | < 1s |
| Download Progress Update | < 1s | < 2s |
| Modal Open/Close | < 300ms | < 500ms |
| API Response (list) | < 500ms | < 1s |
| API Response (status) | < 500ms | < 1s |

### Measured Performance
*(To be filled in during testing)*

| Metric | Measured | Status |
|--------|----------|--------|
| Page Load Time | - | - |
| Model List Refresh | - | - |
| Status Check | - | - |
| Progress Update Latency | - | - |
| Download Time (1.3GB) | - | - |

---

## ✅ Acceptance Criteria Summary

### Functionality (Must Pass)
- [ ] All core features working
- [ ] Models display correctly
- [ ] Download with progress tracking works
- [ ] Model info displays correctly
- [ ] Model deletion works with confirmation
- [ ] Service status detection accurate
- [ ] Error handling graceful

### User Experience (Should Pass)
- [ ] Intuitive UI (< 3 clicks for common tasks)
- [ ] Clear error messages
- [ ] Responsive layout (desktop/tablet/mobile)
- [ ] Visual feedback for actions
- [ ] Consistent with Extensions page design

### Performance (Should Pass)
- [ ] Page load < 2 seconds
- [ ] API responses < 500ms
- [ ] Progress updates < 1 second
- [ ] No memory leaks
- [ ] Smooth animations

### Code Quality (Should Pass)
- [ ] No console errors
- [ ] No failed network requests
- [ ] Clean code structure
- [ ] Proper error handling
- [ ] Consistent styling

---

## 🐛 Known Issues / Bugs

*(To be documented during testing)*

### Critical
- None

### Minor
- None

### Future Enhancements
- Add model search/filter
- Add model size sorting
- Add download queue management
- Add pause/resume for downloads
- Add model comparison feature

---

## 📝 Test Execution Notes

### Test Environment Details
- **OS:** macOS (Darwin 25.2.0)
- **Browser:** (to be specified)
- **Ollama Version:** 0.15.2
- **Python Version:** (to be specified)
- **Network:** (to be specified)

### Test Execution
- **Date:** 2026-01-30
- **Duration:** (to be measured)
- **Tester:** Claude Code

### Prerequisites Met
- ✅ Ollama running
- ✅ Models API implemented
- ✅ Frontend view created
- ✅ CSS styling complete
- ✅ Navigation integrated

---

## 🚀 How to Run Tests

### Automated Tests
```bash
cd /Users/pangge/PycharmProjects/AgentOS

# Start WebUI first
agentos webui &

# Wait for server to start
sleep 5

# Run automated test suite
python3 test_models_e2e.py

# View test report
cat MODELS_E2E_TEST_REPORT.md
```

### Manual Tests
1. Start Ollama: `ollama serve` (if not running)
2. Start WebUI: `agentos webui`
3. Open browser: http://localhost:8000
4. Navigate to: Settings → Models
5. Follow test scenarios above
6. Document results in this file

---

## 📸 Screenshots

*(To be added during testing)*

### Desktop View
- [ ] Models list with cards
- [ ] Download modal with recommendations
- [ ] Progress tracking
- [ ] Model info modal
- [ ] Delete confirmation

### Tablet View
- [ ] 2-column grid layout

### Mobile View
- [ ] 1-column stack layout
- [ ] Responsive modals

---

## 🎯 Final Assessment

### Overall Result
- [ ] **PASSED** - All acceptance criteria met
- [ ] **PASSED WITH WARNINGS** - Core features work, minor issues
- [ ] **FAILED** - Critical issues found

### Sign-Off
- **Feature Ready for Production:** [ ] Yes [ ] No
- **Meets Requirements:** [ ] Yes [ ] No
- **Approved By:** _______________
- **Date:** _______________

---

## 📚 References

- Backend API: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/models.py`
- Frontend View: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/views/ModelsView.js`
- CSS Styling: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/css/models.css`
- Test Script: `/Users/pangge/PycharmProjects/AgentOS/test_models_e2e.py`

---

**END OF TEST PLAN**
