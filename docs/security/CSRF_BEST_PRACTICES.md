# CSRF Protection - Development Standards

## Overview

This document outlines the mandatory CSRF protection standards for AgentOS WebUI development. All API calls to `/api/**` endpoints must use explicit CSRF protection to prevent Cross-Site Request Forgery attacks.

## Mandatory Requirements

### Prohibited Practices

Direct use of `fetch()` to call API endpoints is **strictly prohibited**:

```javascript
// WRONG - No CSRF protection
const response = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'test' })
});
```

```javascript
// WRONG - No CSRF protection
const data = await fetch('/api/projects', {
    method: 'PUT',
    body: JSON.stringify({ name: 'updated' })
});
```

### Correct Practices

All API calls must use one of the three approved methods:

#### Method 1: fetchWithCSRF (Recommended)

Use `window.fetchWithCSRF()` for maximum clarity and explicit CSRF token handling:

```javascript
const response = await window.fetchWithCSRF('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'test' })
});

const data = await response.json();
```

**Advantages:**
- Most explicit and readable
- Clear intent that CSRF protection is applied
- Identical API to native `fetch()`
- Easy to audit and review

#### Method 2: ApiClient (Recommended for Complex Operations)

Use `window.apiClient` for a higher-level abstraction with automatic header management:

```javascript
// POST request
const result = await window.apiClient.post('/api/sessions', {
    title: 'test'
});

// PUT request
const updated = await window.apiClient.put('/api/projects/123', {
    name: 'updated'
});

// PATCH request
const patched = await window.apiClient.patch('/api/projects/123', {
    status: 'active'
});

// DELETE request
await window.apiClient.delete('/api/sessions/456');
```

**Advantages:**
- Higher-level abstraction
- Automatic JSON serialization/deserialization
- Consistent error handling
- Automatic CSRF token injection

#### Method 3: withCsrfToken Helper

Use `withCsrfToken()` for fine-grained control over fetch options:

```javascript
const response = await fetch('/api/sessions', withCsrfToken({
    method: 'POST',
    body: JSON.stringify({ title: 'test' }),
    // Other fetch options as needed
}));

const data = await response.json();
```

**Advantages:**
- Flexible - works with any fetch options
- Lower-level control
- Can be used with middleware

## Implementation Details

### SafeList Files

Only these files are permitted to directly use `fetch()` without CSRF protection:

1. **agentos/webui/static/js/utils/csrf.js**
   - Implements CSRF protection mechanisms
   - Provides `fetchWithCSRF()` and `withCsrfToken()` exports

2. **agentos/webui/static/js/components/ApiClient.js**
   - Implements the ApiClient wrapper class
   - Handles all API communication abstraction

All other JavaScript files **must** use the three approved methods.

## Automated Enforcement

CSRF protection is enforced through multiple mechanisms:

### 1. Pre-commit Hook

Runs automatically before each commit to prevent violations from being committed:

```bash
bash .git/hooks/pre-commit
```

If violations are detected:
- Commit is blocked with detailed error message
- Specific files and line numbers are reported
- Instructions for fixing violations are provided

To bypass (not recommended):
```bash
git commit --no-verify
```

### 2. CI/CD Pipeline Check

All pull requests must pass the CSRF check:

```bash
bash scripts/security/check_csrf.sh
```

Violations in PR code will fail CI and block merging.

### 3. Development Environment

Developers can manually verify compliance:

```bash
# Run full CSRF check
bash scripts/security/check_csrf.sh

# Run tests for check script
bash scripts/security/test_csrf_check.sh
```

## Migration Guide

### Converting Existing Code

If you're modifying existing code with unprotected `fetch()` calls:

**Before:**
```javascript
async function loadSessions() {
    const response = await fetch('/api/sessions', {
        method: 'GET'
    });
    return response.json();
}
```

**After (Option 1 - fetchWithCSRF):**
```javascript
async function loadSessions() {
    const response = await window.fetchWithCSRF('/api/sessions', {
        method: 'GET'
    });
    return response.json();
}
```

**After (Option 2 - ApiClient):**
```javascript
async function loadSessions() {
    return window.apiClient.get('/api/sessions');
}
```

## Common Patterns

### GET Requests

```javascript
// Method 1: fetchWithCSRF
const data = await window.fetchWithCSRF('/api/projects').then(r => r.json());

// Method 2: ApiClient (if using read-through cache)
const data = await window.apiClient.get('/api/projects');

// Note: GET requests don't strictly need CSRF tokens, but using these methods
// ensures consistency and future-proofs the code if endpoints change to POST
```

### POST with JSON Body

```javascript
// Method 1: fetchWithCSRF (explicit)
const response = await window.fetchWithCSRF('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'Meeting' })
});

// Method 2: ApiClient (recommended)
const result = await window.apiClient.post('/api/sessions', {
    title: 'Meeting'
});
```

### Form Data Upload

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('description', 'My upload');

// Method 1: fetchWithCSRF (handles multipart/form-data)
const response = await window.fetchWithCSRF('/api/uploads', {
    method: 'POST',
    body: formData
});

// Don't set Content-Type header with FormData - let the browser set it
```

### Error Handling

```javascript
try {
    const response = await window.fetchWithCSRF('/api/projects', {
        method: 'POST',
        body: JSON.stringify({ name: 'new' })
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
} catch (error) {
    console.error('Request failed:', error);
    throw error;
}
```

## Testing

### Unit Tests

When writing tests, use appropriate mocking:

```javascript
// With mock fetch
global.fetch = jest.fn(() =>
    Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ id: 1 })
    })
);

// fetchWithCSRF should be available globally
global.fetchWithCSRF = global.fetch;

// Test your code
await myFunction();
```

### Integration Tests

For integration tests, the CSRF protection should work transparently:

```javascript
// Load the CSRF utility
import { fetchWithCSRF } from '/js/utils/csrf.js';

// Use it directly in tests
const response = await fetchWithCSRF('/api/test', { method: 'POST' });
```

## Troubleshooting

### "fetch is not CSRF protected" Error

This error appears when the check script detects unprotected fetch calls. Fix it by:

1. Replacing `fetch()` with `window.fetchWithCSRF()`
2. Or using `window.apiClient.post/put/patch/delete()`
3. Or wrapping fetch options with `withCsrfToken()`

### "CSRF token not found" Error at Runtime

This usually means:

1. CSRF utility is not loaded - ensure `csrf.js` is included in the page
2. Token cookie is missing - check browser cookies for `csrf_token`
3. Wrong request method - ensure you're using POST/PUT/PATCH/DELETE

### Pre-commit Hook Not Running

Ensure the hook is executable:

```bash
chmod +x .git/hooks/pre-commit
```

## FAQs

**Q: Do GET requests need CSRF protection?**
A: Technically no, but we enforce it for consistency and to catch refactoring errors.

**Q: Can I bypass the pre-commit hook?**
A: Yes, with `git commit --no-verify`, but this is not recommended and will fail CI.

**Q: What about external API calls?**
A: Only internal `/api/**` calls need CSRF protection. External APIs use different auth.

**Q: Can I modify the whitelist?**
A: Only in exceptional circumstances, and only after peer review. Contact the security team.

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [CSRF Utility Implementation](../../../agentos/webui/static/js/utils/csrf.js)
- [API Client Implementation](../../../agentos/webui/static/js/components/ApiClient.js)

## Questions?

For CSRF protection questions or to request whitelist additions, contact the security team.
