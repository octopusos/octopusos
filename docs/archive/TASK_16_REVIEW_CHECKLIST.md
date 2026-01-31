# Task #16: Review Checklist

## Reviewer Guide for Button Border-Radius Standardization

---

## Overview
This task standardizes all button border-radius values to **4px** across the WebUI.

**Files to Review**: 6 CSS files
**Total Changes**: 15+ border-radius modifications
**Risk Level**: LOW (visual only, no functional changes)

---

## Pre-Review Checklist

### Documentation Review
- [ ] Read `TASK_16_QUICK_REFERENCE.md` for summary
- [ ] Read `TASK_16_BUTTON_RADIUS_STANDARDIZATION_REPORT.md` for full details
- [ ] Review `TASK_16_VISUAL_AUDIT.md` for before/after comparison

---

## Code Review Checklist

### 1. CSS Variable Declaration (main.css)
- [ ] Global variable `--button-border-radius: 4px` added
- [ ] Exception variable `--button-border-radius-circular: 50%` added
- [ ] Variables properly scoped in `:root`
- [ ] Comments explain Task #16

**File**: `agentos/webui/static/css/main.css`
**Lines**: ~3-10

---

### 2. Modal System (modal-unified.css)
- [ ] `.modal-close` button: 6px → 4px
- [ ] `.modal button` (all modal buttons): 6px → 4px
- [ ] `.modal-body input` fields: 6px → 4px
- [ ] All changes marked with `/* Task #16 */` comment

**File**: `agentos/webui/static/css/modal-unified.css`
**Lines**: 138, 234, 270

**Test**: Open any modal dialog, verify button corners

---

### 3. Extension Wizard (extension-wizard.css)
- [ ] `--wizard-radius-md` variable: 6px → 4px
- [ ] Comment explains Task #16 standardization
- [ ] Verify this affects all wizard buttons globally

**File**: `agentos/webui/static/css/extension-wizard.css`
**Line**: 58

**Test**: Open extension wizard, check all step buttons

---

### 4. Extension Management (extensions.css)
- [ ] `.extension-card-actions button`: 8px → 4px
- [ ] `.btn-install-upload, .btn-install-url`: 8px → 4px
- [ ] Changes marked with `/* Task #16 */` comment

**File**: `agentos/webui/static/css/extensions.css`
**Lines**: 261, 330

**Test**: View Extensions page, check card buttons

---

### 5. Project Management (project-v31.css)
- [ ] `.form-control` inputs: 6px → 4px
- [ ] `.criteria-list` container: 6px → 4px
- [ ] Changes marked with `/* Task #16 */` comment

**File**: `agentos/webui/static/css/project-v31.css`
**Lines**: 151, 189

**Test**: Create new project, check form inputs

---

### 6. Universal Components (components.css)
- [ ] `.json-btn`: 3px → 4px
- [ ] `.pagination-btn`: 3px → 4px
- [ ] `.filter-input, .filter-select`: 3px → 4px
- [ ] `.filter-button`: 3px → 4px
- [ ] `.time-range-btn`: 3px → 4px
- [ ] `.time-range-apply`: 3px → 4px
- [ ] All changes marked with `/* Task #16 */` comment

**File**: `agentos/webui/static/css/components.css`
**Lines**: 183, 351, 400, 421, 455, 485

**Test**: Use data tables, filters, pagination

---

## Visual QA Checklist

### Test in Browser
Start the WebUI and verify the following:

#### Modal Dialogs
- [ ] Open "Create Project" modal
  - [ ] Cancel button has subtle rounded corners (4px)
  - [ ] Save button has subtle rounded corners (4px)
  - [ ] Close button (×) maintains circular shape (50%)
- [ ] Open "Delete Confirmation" modal
  - [ ] All buttons consistent with 4px

#### Extension Management
- [ ] Navigate to Extensions view
  - [ ] Extension card buttons (Enable/Disable) have 4px radius
  - [ ] Install buttons have 4px radius
- [ ] Open Extension Wizard
  - [ ] Next/Previous buttons have 4px radius
  - [ ] All form inputs have 4px radius

#### Data Tables
- [ ] Navigate to any view with pagination (Tasks, Projects, etc.)
  - [ ] Pagination buttons (Prev/Next) have 4px radius
  - [ ] Page number buttons have 4px radius

#### Filters
- [ ] Use any filter component
  - [ ] Filter input fields have 4px radius
  - [ ] Filter buttons have 4px radius
  - [ ] Time range buttons have 4px radius

---

## Cross-Browser Testing

### Desktop Browsers
- [ ] **Chrome/Edge** (Latest)
  - [ ] All buttons render correctly
  - [ ] 4px radius visible and consistent
- [ ] **Firefox** (Latest)
  - [ ] All buttons render correctly
  - [ ] 4px radius visible and consistent
- [ ] **Safari** (Latest)
  - [ ] All buttons render correctly
  - [ ] 4px radius visible and consistent

### Mobile Browsers (Optional)
- [ ] iOS Safari
- [ ] Chrome Mobile

---

## Regression Testing

### Ensure No Breakage
- [ ] All modals open and close correctly
- [ ] All buttons remain clickable
- [ ] No layout shifts or overlaps
- [ ] Form inputs still accept text
- [ ] No console errors

### Check Exceptions
- [ ] Circular icon buttons (×, delete) still circular (50%)
- [ ] Nav pills/tabs maintain their design (20px pill shape)
- [ ] Badges maintain full rounding (9999px)
- [ ] Container cards not affected (8px, 12px appropriate)

---

## Code Quality Checklist

### Consistency
- [ ] All button modifications include `/* Task #16 */` comment
- [ ] No hardcoded values mixed with CSS variables
- [ ] Consistent spacing and formatting

### Documentation
- [ ] All changes documented in report files
- [ ] Exceptions clearly documented (50% for icons)
- [ ] Comments explain reasoning

### Maintainability
- [ ] CSS variables established for future use
- [ ] Clear guidelines for new components
- [ ] Rollback plan documented

---

## Acceptance Criteria Verification

### All Must Pass ✅
- [ ] **Criterion 1**: All rectangular buttons have 4px border-radius
- [ ] **Criterion 2**: CSS variable `--button-border-radius: 4px` established
- [ ] **Criterion 3**: extension-wizard.css updated from 6px to 4px
- [ ] **Criterion 4**: No forbidden values (6px, 8px, 5px, 10px) on buttons
- [ ] **Criterion 5**: Circular icon buttons (50%) documented as exceptions
- [ ] **Criterion 6**: Comprehensive modification report created

---

## Automated Verification

Run these commands to verify changes:

```bash
# Verify all Task #16 changes present
grep -rn "Task #16" agentos/webui/static/css/*.css

# Check CSS variable exists
grep "button-border-radius" agentos/webui/static/css/main.css

# Verify modal-unified.css changes
grep "border-radius: 4px" agentos/webui/static/css/modal-unified.css | wc -l
# Expected: 3 occurrences

# Verify extension-wizard.css change
grep "wizard-radius-md: 4px" agentos/webui/static/css/extension-wizard.css
# Expected: 1 occurrence

# Verify extensions.css changes
grep "Task #16" agentos/webui/static/css/extensions.css | wc -l
# Expected: 2 occurrences

# Verify components.css changes
grep "Task #16" agentos/webui/static/css/components.css | wc -l
# Expected: 6+ occurrences

# Check for forbidden button values (should return empty)
grep -rn "border-radius.*[356]px" agentos/webui/static/css/*.css | \
  grep -iE "(button|btn)" | \
  grep -v "50%" | \
  grep -v "Task #16"
# Expected: No results (or only non-button elements)
```

---

## Performance Check

- [ ] No JavaScript changes (no performance impact)
- [ ] Pure CSS changes (browser-native rendering)
- [ ] No additional HTTP requests
- [ ] No increase in CSS file sizes (only value changes)

---

## Final Approval Checklist

### Before Merging
- [ ] All visual QA tests pass
- [ ] All acceptance criteria met
- [ ] No regressions detected
- [ ] Documentation complete
- [ ] Code quality standards met
- [ ] Cross-browser testing complete (or documented exceptions)

### Merge Preparation
- [ ] Changes reviewed by at least one team member
- [ ] All reviewer comments addressed
- [ ] Ready for production deployment

---

## Sign-Off

**Reviewer Name**: _________________
**Date**: _________________
**Status**: [ ] APPROVED / [ ] CHANGES REQUESTED / [ ] REJECTED

**Comments**:
```
[Reviewer notes here]
```

---

## Post-Merge Monitoring

### After Deployment
- [ ] Monitor user feedback for visual issues
- [ ] Check error logs for CSS-related issues
- [ ] Verify production deployment matches staging

### Success Metrics (Week 1)
- [ ] No user complaints about button appearance
- [ ] No CSS-related bug reports
- [ ] Design team approval of visual consistency

---

## Quick Links

- **Full Report**: `TASK_16_BUTTON_RADIUS_STANDARDIZATION_REPORT.md`
- **Quick Reference**: `TASK_16_QUICK_REFERENCE.md`
- **Visual Audit**: `TASK_16_VISUAL_AUDIT.md`
- **This Checklist**: `TASK_16_REVIEW_CHECKLIST.md`

---

**Task #16 Status**: ✅ COMPLETED
**Ready for Review**: YES
**Estimated Review Time**: 30-45 minutes
**Risk Level**: LOW (visual only)
**Rollback Difficulty**: EASY (pure CSS)

---

**Last Updated**: 2026-01-30
