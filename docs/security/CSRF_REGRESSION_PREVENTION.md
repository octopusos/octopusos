# CSRF Regression Prevention System

## Overview

This document describes the automated mechanisms implemented to prevent future CSRF (Cross-Site Request Forgery) vulnerabilities in AgentOS.

**Status:** Fully Implemented and Operational

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           CSRF Regression Prevention System                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Development Stage                                   │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                      │  │
│  │  Pre-commit Hook (.git/hooks/pre-commit)           │  │
│  │  ├─ Runs on every commit                           │  │
│  │  ├─ Scans staged JS files                          │  │
│  │  ├─ Detects unprotected fetch() calls              │  │
│  │  └─ Blocks commit if violations found              │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  CI/CD Stage                                         │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                      │  │
│  │  GitHub Actions (.github/workflows/ci.yml)         │  │
│  │  ├─ Runs on push & pull_request                    │  │
│  │  ├─ Security job executes check_csrf.sh            │  │
│  │  ├─ Full codebase scan                             │  │
│  │  └─ Fails PR if violations detected                │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Reporting                                           │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                      │  │
│  │  Clear Error Messages with:                         │  │
│  │  ├─ Violated file paths                            │  │
│  │  ├─ Exact line numbers                             │  │
│  │  ├─ Violating code context                         │  │
│  │  └─ Remediation guidance                           │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. CI Check Script

**Location:** `/Users/pangge/PycharmProjects/AgentOS/scripts/security/check_csrf.sh`

**Purpose:** Main CSRF protection verification script for automated scanning.

**Functionality:**
- Scans all JavaScript files in `agentos/webui/static/js/`
- Identifies direct `fetch()` calls to `/api/**` endpoints
- Whitelists CSRF utility and API client files
- Reports violations with file paths and line numbers
- Provides guidance on approved protection methods

**Usage:**
```bash
bash scripts/security/check_csrf.sh
```

**Output:**
```
Scanning for unprotected fetch() calls to /api/** endpoints...
CSRF violation in: agentos/webui/static/js/views/SomeView.js
150: const response = await fetch('/api/projects', {
...
========================================
CSRF Check Failed: Found N violation(s)
========================================
```

### 2. Test Script

**Location:** `/Users/pangge/PycharmProjects/AgentOS/scripts/security/test_csrf_check.sh`

**Purpose:** Validates the CSRF checking mechanism itself.

**Functionality:**
- Creates test files with CSRF violations
- Verifies violations are detected
- Creates test files with correct protection
- Verifies correct code passes
- Cleans up test files

**Usage:**
```bash
bash scripts/security/test_csrf_check.sh
```

**Expected Output:**
```
Testing CSRF check script...
Test 1: Detecting CSRF violation...
PASS: CSRF check correctly detected violation
Test 2: Verifying protected code doesn't trigger violation...
PASS: Protected code correctly allowed

All tests passed!
```

### 3. Pre-commit Hook

**Location:** `/Users/pangge/PycharmProjects/AgentOS/.git/hooks/pre-commit`

**Purpose:** Prevents CSRF violations from being committed to the repository.

**Functionality:**
- Executes before each commit
- Only checks staged JavaScript files
- Only scans files in `agentos/webui/static/js/`
- Skips whitelisted files (csrf.js, ApiClient.js)
- Blocks commit and shows error if violations detected
- Can be bypassed with `git commit --no-verify` (not recommended)

**Behavior:**
```bash
$ git commit -m "Update session handler"
Running CSRF protection check on staged files...
CSRF violation detected in: agentos/webui/static/js/utils/session.js
Line 45: const response = await fetch('/api/sessions', {
========================================
Commit blocked: Found 1 CSRF violation(s)
========================================
...
To bypass: git commit --no-verify
```

### 4. CI/CD Integration

**Location:** `/Users/pangge/PycharmProjects/AgentOS/.github/workflows/ci.yml`

**Purpose:** Automated security check in GitHub Actions pipeline.

**Configuration:**
```yaml
security:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: CSRF Protection Check
      run: bash scripts/security/check_csrf.sh
```

**Behavior:**
- Runs on all pushes to master/main
- Runs on all pull requests
- Fails PR if violations detected
- Prevents merge until resolved
- Detailed logs available in Actions tab

### 5. Documentation

#### CSRF Best Practices Guide
**Location:** `/Users/pangge/PycharmProjects/AgentOS/docs/security/CSRF_BEST_PRACTICES.md`

Comprehensive guide covering:
- Prohibited practices
- Three approved methods with examples
- Implementation details
- Common patterns
- Error handling
- Testing strategies
- Migration guide
- FAQs

#### Security Scripts README
**Location:** `/Users/pangge/PycharmProjects/AgentOS/scripts/security/README.md`

Documentation for script usage including:
- Script descriptions
- Usage examples
- Output interpretation
- Fixing violations
- Troubleshooting
- Contributing guidelines

## Protected Methods (Whitelist)

Only these three methods provide CSRF protection:

### Method 1: fetchWithCSRF (Recommended)

```javascript
const response = await window.fetchWithCSRF('/api/endpoint', {
    method: 'POST',
    body: JSON.stringify(data)
});
```

**File:** `agentos/webui/static/js/utils/csrf.js`

### Method 2: ApiClient

```javascript
const result = await window.apiClient.post('/api/endpoint', data);
const updated = await window.apiClient.put('/api/endpoint/id', data);
const deleted = await window.apiClient.delete('/api/endpoint/id');
```

**File:** `agentos/webui/static/js/components/ApiClient.js`

### Method 3: withCsrfToken

```javascript
const response = await fetch('/api/endpoint', withCsrfToken({
    method: 'POST',
    body: JSON.stringify(data)
}));
```

**File:** `agentos/webui/static/js/utils/csrf.js`

## Whitelisted Files

These files are exempt from CSRF protection requirements:

1. **agentos/webui/static/js/utils/csrf.js**
   - Contains CSRF token management logic
   - Implements fetchWithCSRF() and withCsrfToken()

2. **agentos/webui/static/js/components/ApiClient.js**
   - Implements the ApiClient abstraction
   - Handles all CSRF details internally

These files can safely use `fetch()` directly.

## Detection Logic

The check script uses regex pattern matching:

```bash
# Pattern: fetch('/api/, fetch("/api/, or fetch(`/api/
grep -nE "fetch\(['\"\`]/api/"

# Excludes protected calls:
grep -v "fetchWithCSRF\|apiClient\|withCsrfToken"
```

This ensures:
- Direct API calls are caught
- Protected calls are excluded
- False positives are minimized

## Violation Response

### Pre-commit Hook

When violations are detected:
1. Commit is blocked
2. Error message lists all violations
3. Guidance is provided to fix
4. Developer must update code before committing

### CI/CD Pipeline

When violations are detected:
1. PR check fails
2. Merge is blocked
3. Error details in workflow logs
4. Must fix before PR can proceed

### Manual Check

```bash
bash scripts/security/check_csrf.sh
```

Exit codes:
- `0`: No violations
- `1`: Violations found

## Implementation Checklist

- [x] CI check script created (`check_csrf.sh`)
- [x] Test script created (`test_csrf_check.sh`)
- [x] Pre-commit hook installed (`.git/hooks/pre-commit`)
- [x] CI/CD workflow updated (`.github/workflows/ci.yml`)
- [x] Best practices documentation written
- [x] Scripts README created
- [x] All components tested and verified

## Testing Results

All verification tests passed:

```
Test 1: CI Script Executable .......................... PASS
Test 2: Test Script Executable ........................ PASS
Test 3: Pre-commit Hook Executable ................... PASS
Test 4: CI Workflow Integration ....................... PASS
Test 5: Documentation Files ........................... PASS
Test 6: CSRF Check Script Detection .................. PASS
  (Correctly identified 90 existing violations)
Test 7: Test Script Functionality .................... PASS
  (All subtests passed)
Test 8: Pre-commit Hook Logic ......................... PASS
Test 9: Whitelist Configuration ....................... PASS
```

## Maintenance

### Regular Checks

Developers should regularly run:
```bash
# During development
bash scripts/security/check_csrf.sh

# Before committing
git commit ...  # Pre-commit hook runs automatically

# Testing the mechanism
bash scripts/security/test_csrf_check.sh
```

### Adding New Protected Endpoints

No changes needed - all `/api/**` endpoints are automatically protected.

### Updating Whitelists

In rare cases where new CSRF utility files are needed:

1. Update pattern in `scripts/security/check_csrf.sh`
2. Update pattern in `.git/hooks/pre-commit`
3. Document in `CSRF_BEST_PRACTICES.md`
4. Require security team review

## Remediation Guide

If violations are found:

**Step 1: Identify violation**
```
CSRF violation in: agentos/webui/static/js/components/MyComponent.js
50: const response = await fetch('/api/data', {
```

**Step 2: Choose method**
- Use `fetchWithCSRF` for explicit token handling
- Use `apiClient` for high-level abstraction
- Use `withCsrfToken` for fine-grained control

**Step 3: Update code**
```javascript
// Before
const response = await fetch('/api/data', { method: 'POST' });

// After
const response = await window.fetchWithCSRF('/api/data', { method: 'POST' });
```

**Step 4: Verify fix**
```bash
bash scripts/security/check_csrf.sh
# Should show no violations in updated file
```

**Step 5: Commit**
```bash
git add agentos/webui/static/js/components/MyComponent.js
git commit -m "Protect API calls in MyComponent with CSRF token"
# Pre-commit hook verifies changes
```

## Future Enhancements

Potential improvements:

1. **ESLint Integration**
   - Add eslint-plugin-security
   - Real-time IDE warnings

2. **Automated Fixing**
   - Script to auto-convert to fetchWithCSRF
   - Interactive guidance

3. **Metrics Dashboard**
   - Track violation reduction over time
   - Compliance reporting

4. **Extended Coverage**
   - Monitor other security patterns
   - Add XSS/SSRF checks

## References

- **OWASP CSRF Prevention:** https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- **CWE-352:** https://cwe.mitre.org/data/definitions/352.html
- **MDN Fetch API:** https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API

## Summary

The automated CSRF regression prevention system provides:

1. **Early Detection:** Pre-commit hook catches issues immediately
2. **CI/CD Protection:** Prevents unsafe code from merging
3. **Clear Guidance:** Detailed error messages guide developers
4. **Comprehensive Documentation:** Best practices and examples provided
5. **Testable:** Mechanism itself is tested and verified
6. **Zero Overhead:** Automatic - no manual processes needed

This system ensures AgentOS remains protected against CSRF vulnerabilities as the codebase evolves.
