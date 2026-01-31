# Quick Test - Phase Selector Fix (English)

## 🚀 Test in 30 Seconds

### 1. Verify Fix
```bash
python3 test_phase_selector_fix.py
```
✅ Should see: "All tests passed!"

### 2. Start App
```bash
python3 -m agentos.webui.app
```

### 3. Browser Test

1. Open http://localhost:5000
2. Press `F12` (open DevTools)
3. In Console, type:
   ```javascript
   window.Dialog
   ```
   ✅ Should see: `class Dialog { ... }`

4. Go to Chat page
5. Click Phase selector button (Planning → Execution)

## ✅ What You Should See

**Dialog Popup** (NOT browser native):
```
┌────────────────────────────────────────┐
│ Confirm Phase Change              [×]  │
├────────────────────────────────────────┤
│                                        │
│ Switch to execution phase?             │
│                                        │
│ This allows external communication     │
│ including web search and URL fetching. │
│                                        │
│                   [Cancel] [Switch to  │
│                            Execution]  │
└────────────────────────────────────────┘
```

**Styled with**:
- ✅ Rounded corners
- ✅ Drop shadow
- ✅ Semi-transparent backdrop
- ✅ Fade-in animation
- ✅ **All text in English**

**Console Output**:
```
[PhaseSelector] Attempting to switch phase: planning -> execution
[PhaseSelector] Sending API request: {...}
[PhaseSelector] API response status: 200 OK
[PhaseSelector] Phase updated successfully
```

**Success Toast**:
```
✓ Phase changed to: execution
```

## ❌ What You Should NOT See

- ❌ Browser native gray confirm dialog
- ❌ Chinese text (中文)
- ❌ "Dialog component not loaded" error

## 🔧 If Still Seeing Issues

**Clear browser cache**:
```
Cmd + Shift + R (Mac)
Ctrl + Shift + R (Windows/Linux)
```

Or in DevTools:
1. Network tab
2. Check "Disable cache"
3. Refresh page

## ✅ Test Checklist

Copy and check:
```
[ ] python3 test_phase_selector_fix.py passes
[ ] App starts without errors
[ ] window.Dialog exists in browser console
[ ] Phase selector shows custom Dialog (not native)
[ ] Dialog text is in English
[ ] Dialog has nice styling and animation
[ ] "Cancel" button closes dialog
[ ] "Switch to Execution" button changes phase
[ ] Success message: "Phase changed to: execution"
[ ] No errors in console
```

## 🎉 Success Criteria

All text must be in **English**:
- ✅ "Confirm Phase Change"
- ✅ "Switch to execution phase?"
- ✅ "Switch to Execution"
- ✅ "Cancel"
- ✅ "Phase changed to: execution"

## 📞 Still Having Issues?

Check:
1. Browser cache cleared?
2. `window.Dialog` exists in console?
3. PhaseSelector.js version is v=3?
4. Any errors in Network tab?

---

**Ready to test?** Run: `python3 -m agentos.webui.app` 🚀
