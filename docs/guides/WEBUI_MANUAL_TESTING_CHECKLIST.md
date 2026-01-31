# WebUI Manual Testing Checklist

## Prerequisites
- [x] WebUI server is running (http://localhost:8000)
- [x] tools.test extension is installed

## Test 1: Extension List View
- [ ] Navigate to Extensions page
- [ ] Locate tools.test extension card
- [ ] Verify displays "Python 3.8" badge with purple gradient
- [ ] Verify displays "ADR-EXT-002" badge with green color
- [ ] Verify badges are positioned correctly in meta area
- [ ] Take screenshot: extensions-list-view.png

## Test 2: Extension Detail View
- [ ] Click on tools.test extension
- [ ] Scroll to find "Runtime Information" section
- [ ] Verify shows:
  - [ ] Runtime Type: python (with badge)
  - [ ] Python Version: 3.8
  - [ ] Python Dependencies: (none) or empty list
  - [ ] External Binaries: ✓ None (Python-only) (green text)
  - [ ] ADR-EXT-002 Compliance: Compliant (green badge)
- [ ] Take screenshot: extension-detail-view.png

## Test 3: Extension Wizard - Step 1
- [ ] Click "Create Extension Template" button
- [ ] Verify policy notice box appears at top
- [ ] Verify blue gradient background with left border
- [ ] Verify info icon is displayed
- [ ] Verify title: "Python-Only Runtime Policy (ADR-EXT-002)"
- [ ] Verify three bullet points about Security, Cross-platform, Simplicity
- [ ] Verify lightbulb tip at bottom
- [ ] Take screenshot: wizard-step1-policy.png

## Test 4: Extension Wizard - Step 2
- [ ] Proceed to Capabilities step
- [ ] Add at least one capability
- [ ] Scroll down to find "Python-Only Best Practices" section
- [ ] Verify three practice items with colored icons:
  - [ ] Green checkmark: Use Python packages from PyPI
  - [ ] Green checkmark: Use Python standard library
  - [ ] Red X: Don't use external binaries
- [ ] Verify reference link to tools.test extension
- [ ] Take screenshot: wizard-step2-practices.png

## Test 5: Template Generation
- [ ] Complete wizard and generate template
- [ ] Download generates successfully
- [ ] Extract ZIP and open manifest.json
- [ ] Verify contains:
  - [ ] "runtime": "python"
  - [ ] "python": {"version": "3.8", "dependencies": []}
  - [ ] "external_bins": []
- [ ] Take screenshot: generated-manifest.png

## Browser Console Tests
Open browser console and run:
```javascript
// Check badges exist
document.querySelectorAll('.runtime-badge').length  // Should be > 0
document.querySelectorAll('.compliance-badge').length  // Should be > 0

// Check styles loaded
getComputedStyle(document.querySelector('.runtime-badge')).background  // Should contain gradient
```

## All Tests Passed?
- [ ] YES - Proceed to create report
- [ ] NO - Document failures and investigate
