# Origin/Referer Same-Origin Check - Testing Guide

## Overview

This document describes the implementation and testing of Origin/Referer same-origin checking as the second line of defense in CSRF protection.

## Two-Layer Defense System

The CSRF middleware now implements a two-layer defense system:

1. **Layer 1: Origin/Referer Check** (First line of defense)
   - Validates that the request originates from the same site
   - Checks `Origin` header (preferred) or falls back to `Referer`
   - Blocks cross-domain requests immediately
   - Returns `403 ORIGIN_CHECK_FAILED` error

2. **Layer 2: CSRF Token Validation** (Second line of defense)
   - Validates CSRF token from session
   - Checks `X-CSRF-Token` header matches session token
   - Returns `403 CSRF_TOKEN_REQUIRED` or `403 CSRF_TOKEN_INVALID` error

## Implementation Details

### Configuration

The Origin/Referer check can be enabled/disabled via the `check_origin` parameter:

```python
from agentos.webui.middleware.csrf import add_csrf_protection

# Enable Origin checking (default)
add_csrf_protection(app, check_origin=True)

# Disable Origin checking (not recommended)
add_csrf_protection(app, check_origin=False)
```

### Site Origin Detection

The middleware determines the site origin in the following order:

1. **Environment Variable**: `SITE_ORIGIN` (e.g., `https://agentos.example.com`)
2. **Request Inference**: Constructed from request scheme and host header

For production deployments, it's recommended to set `SITE_ORIGIN` explicitly:

```bash
export SITE_ORIGIN=https://agentos.example.com
```

### Header Checking Logic

The `_check_origin()` method implements the following logic:

1. **Check Origin header** (preferred):
   - Parse the `Origin` header
   - Compare scheme, domain, and port with site origin
   - Return `True` if same-origin, `False` if cross-origin

2. **Fallback to Referer header**:
   - If `Origin` is missing, parse the `Referer` header
   - Compare scheme, domain, and port with site origin
   - Return `True` if same-origin, `False` if cross-origin

3. **Missing both headers**:
   - If both `Origin` and `Referer` are missing, return `False`
   - This is suspicious and indicates a potential attack

### Exempt Paths

The following paths are exempt from Origin/Referer checking:

- `/health` - Health check endpoint
- `/api/health` - API health check
- `/static/` - Static files
- `/ws/` - WebSocket connections
- `/webhook/` - Server-to-Server webhooks (use signature verification)

## Testing

### Prerequisites

1. Start the AgentOS WebUI server:

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.webui.main
```

The server should be running on `http://localhost:8000`.

### Running the Test Script

The test script `test_origin_check.py` validates all aspects of the Origin/Referer checking:

```bash
python test_origin_check.py
```

### Test Cases

#### Test 1: Cross-Origin Request (Origin Header)

**Scenario**: A request from `http://evil.com` to the API.

**Expected Result**: `403 ORIGIN_CHECK_FAILED`

```python
response = requests.post(
    "http://localhost:8000/api/sessions",
    json={"title": "test"},
    headers={
        "Origin": "http://evil.com",
        "Cookie": "session=test"
    }
)
```

**Expected Response**:
```json
{
    "ok": false,
    "error_code": "ORIGIN_CHECK_FAILED",
    "message": "Origin or Referer header check failed",
    "details": {
        "hint": "Request must originate from the same site",
        "endpoint": "/api/sessions",
        "method": "POST",
        "origin": "http://evil.com",
        "referer": null
    },
    "timestamp": "2024-01-31T12:34:56.789Z"
}
```

#### Test 2: Same-Origin Request (Origin Header)

**Scenario**: A request from `http://localhost:8000` to the API.

**Expected Result**: `403 CSRF_TOKEN_REQUIRED` (passes Origin check, fails CSRF token check)

```python
response = requests.post(
    "http://localhost:8000/api/sessions",
    json={"title": "test"},
    headers={
        "Origin": "http://localhost:8000",
        "Cookie": "session=test"
    }
)
```

#### Test 3: Referer Fallback (Same-Origin)

**Scenario**: A request with `Referer` header but no `Origin` header.

**Expected Result**: `403 CSRF_TOKEN_REQUIRED` (passes Origin check via Referer, fails CSRF token check)

```python
response = requests.post(
    "http://localhost:8000/api/sessions",
    json={"title": "test"},
    headers={
        "Referer": "http://localhost:8000/page",
        "Cookie": "session=test"
    }
)
```

#### Test 4: Cross-Origin Request (Referer Header)

**Scenario**: A request with cross-origin `Referer` header.

**Expected Result**: `403 ORIGIN_CHECK_FAILED`

```python
response = requests.post(
    "http://localhost:8000/api/sessions",
    json={"title": "test"},
    headers={
        "Referer": "http://evil.com/attack",
        "Cookie": "session=test"
    }
)
```

#### Test 5: Missing Both Headers

**Scenario**: A request with neither `Origin` nor `Referer` headers.

**Expected Result**: `403 ORIGIN_CHECK_FAILED`

```python
response = requests.post(
    "http://localhost:8000/api/sessions",
    json={"title": "test"},
    headers={
        "Cookie": "session=test"
    }
)
```

## Manual Testing with curl

### Test Cross-Origin (Should Fail)

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "Origin: http://evil.com" \
  -H "Cookie: session=test" \
  -d '{"title": "test"}' \
  -v
```

**Expected**: `403 ORIGIN_CHECK_FAILED`

### Test Same-Origin (Should Pass Origin Check)

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -H "Cookie: session=test" \
  -d '{"title": "test"}' \
  -v
```

**Expected**: `403 CSRF_TOKEN_REQUIRED` (passes Origin check, fails CSRF token)

### Test with Referer

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "Referer: http://localhost:8000/dashboard" \
  -H "Cookie: session=test" \
  -d '{"title": "test"}' \
  -v
```

**Expected**: `403 CSRF_TOKEN_REQUIRED` (passes Origin check via Referer)

## Production Configuration

### Environment Variables

For production deployments, set the following environment variables:

```bash
# Explicit site origin (recommended)
export SITE_ORIGIN=https://agentos.example.com

# Production environment
export AGENTOS_ENV=production

# Secure cookies (HTTPS only)
export SESSION_SECURE_ONLY=true
```

### HTTPS Enforcement

In production, always use HTTPS to prevent header manipulation:

- Browsers automatically set `Origin` header for cross-origin requests
- HTTPS prevents man-in-the-middle attacks from modifying headers
- Secure cookies prevent cookie theft

### Nginx Configuration Example

```nginx
server {
    listen 443 ssl http2;
    server_name agentos.example.com;

    ssl_certificate /etc/ssl/certs/agentos.crt;
    ssl_certificate_key /etc/ssl/private/agentos.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Security Considerations

### Why Two Layers?

1. **Defense in Depth**: Even if one layer is bypassed, the other still protects
2. **Different Attack Vectors**: Origin checking blocks cross-domain attacks, CSRF tokens block same-domain token-less attacks
3. **Browser Support**: Some browsers may not send Origin header in all scenarios

### When Origin/Referer Might Be Missing

- **Legacy Browsers**: Very old browsers may not send Origin
- **Privacy Extensions**: Some browser extensions strip Referer headers
- **Server-to-Server**: API calls from backend services
- **Mobile Apps**: Native mobile apps making API calls

For these scenarios, the CSRF token validation (Layer 2) still provides protection.

### Limitations

1. **Subdomain Attacks**: If an attacker controls a subdomain, they can set a matching Origin
   - Mitigation: Use separate domains for different trust levels

2. **Null Origin**: Some browsers send `Origin: null` for certain requests
   - Current implementation: Treats `null` as suspicious and blocks

3. **Referer Spoofing**: In theory, attackers could manipulate Referer
   - Mitigation: Origin header is preferred and harder to manipulate

## Monitoring and Logging

The middleware logs the following events:

### Successful Checks

```
[DEBUG] Origin check passed: http://localhost:8000
[DEBUG] Referer check passed: http://localhost:8000/dashboard
```

### Failed Checks

```
[WARNING] Origin mismatch: expected http://localhost:8000, got http://evil.com
[WARNING] Referer mismatch: expected http://localhost:8000, got http://evil.com/attack
[WARNING] Request missing both Origin and Referer headers: path=/api/sessions, method=POST
```

### Blocked Requests

```
[WARNING] Origin/Referer check failed: path=/api/sessions, method=POST, origin=http://evil.com, referer=none
```

## Troubleshooting

### Issue: Legitimate Requests Blocked

**Symptom**: Same-origin requests are being rejected with `ORIGIN_CHECK_FAILED`.

**Possible Causes**:
1. `SITE_ORIGIN` environment variable is set incorrectly
2. Proxy is not forwarding headers correctly
3. Browser is not sending Origin/Referer headers

**Solution**:
1. Check `SITE_ORIGIN` matches your actual domain
2. Verify proxy configuration forwards `Host`, `Origin`, and `Referer` headers
3. Check browser console for header presence

### Issue: Cross-Origin Requests Not Blocked

**Symptom**: Requests from other domains are not being blocked.

**Possible Causes**:
1. `check_origin=False` is set
2. Path is in exempt list
3. Request method is safe (GET, HEAD, OPTIONS)

**Solution**:
1. Verify `check_origin=True` in middleware configuration
2. Review exempt paths list
3. Confirm request method is POST/PUT/PATCH/DELETE

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Verifying Origin With Standard Headers](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#verifying-origin-with-standard-headers)
- [MDN: Origin Header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Origin)
- [MDN: Referer Header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referer)

## Completion Checklist

- [x] `_check_origin()` method implemented
- [x] Origin/Referer checking integrated into `dispatch()`
- [x] Configuration option `check_origin` added
- [x] Exempt paths updated (WebSocket, Webhook)
- [x] Test script created (`test_origin_check.py`)
- [x] Documentation created
- [ ] Test script executed and passing
- [ ] Integration testing with frontend
- [ ] Production deployment verified
