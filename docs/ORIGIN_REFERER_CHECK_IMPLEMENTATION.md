# Origin/Referer Same-Origin Check Implementation

## Summary

Successfully implemented Origin/Referer same-origin checking as a second line of defense in the CSRF middleware. This adds a robust two-layer security system to protect against Cross-Site Request Forgery attacks.

## Implementation Date

2026-01-31

## Changes Made

### 1. Modified `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/middleware/csrf.py`

#### Added Configuration Parameter

```python
def __init__(
    self,
    app: FastAPI,
    exempt_paths: Optional[list[str]] = None,
    token_header: str = CSRF_HEADER_NAME,
    cookie_name: str = CSRF_COOKIE_NAME,
    enforce_for_api: bool = True,
    check_origin: bool = True,  # NEW
):
```

- Added `check_origin` parameter (default: `True`)
- Added `/webhook/` to exempt paths for server-to-server webhooks

#### Implemented `_check_origin()` Method

```python
def _check_origin(self, request: Request) -> bool:
    """Check Origin or Referer header for same-origin validation.

    This is the second line of defense against CSRF attacks. Even if CSRF token
    is bypassed, origin checking can block most cross-domain attacks.

    Args:
        request: Current request

    Returns:
        True if same-origin, False if cross-origin or suspicious
    """
```

**Logic Flow:**

1. **Determine Site Origin**:
   - Check `SITE_ORIGIN` environment variable (preferred for production)
   - Fall back to inferring from request scheme and host header

2. **Check Origin Header** (preferred):
   - Parse and compare scheme, domain, and port
   - Return `True` if match, `False` if mismatch

3. **Fallback to Referer Header**:
   - If Origin is missing, check Referer header
   - Parse and compare scheme, domain, and port
   - Return `True` if match, `False` if mismatch

4. **Missing Both Headers**:
   - Return `False` (suspicious, likely attack)

#### Integrated Into `dispatch()` Method

```python
# First line of defense: Origin/Referer same-origin check (if enabled)
if self.check_origin:
    if not self._check_origin(request):
        logger.warning(
            f"Origin/Referer check failed: "
            f"path={request.url.path}, method={request.method}, "
            f"origin={request.headers.get('origin', 'none')}, "
            f"referer={request.headers.get('referer', 'none')}"
        )

        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "error_code": "ORIGIN_CHECK_FAILED",
                "message": "Origin or Referer header check failed",
                "details": {
                    "hint": "Request must originate from the same site",
                    "endpoint": request.url.path,
                    "method": request.method,
                    "origin": request.headers.get("origin"),
                    "referer": request.headers.get("referer")
                },
                "timestamp": _format_timestamp()
            }
        )

# Second line of defense: CSRF token validation (existing logic)
# ...
```

#### Updated `add_csrf_protection()` Function

```python
def add_csrf_protection(
    app: FastAPI,
    exempt_paths: Optional[list[str]] = None,
    token_header: str = CSRF_HEADER_NAME,
    enforce_for_api: bool = True,
    check_origin: bool = True,  # NEW
) -> None:
```

#### Updated Module Docstring

Added information about the two-layer defense system:

```python
"""CSRF Protection Middleware for AgentOS WebUI.

This module provides CSRF (Cross-Site Request Forgery) protection for state-changing
API endpoints. It implements the Double Submit Cookie pattern with session binding,
plus Origin/Referer header validation as a second line of defense.

Key Features:
- Two-layer defense system:
  * Layer 1: Origin/Referer same-origin checking (blocks most cross-domain attacks)
  * Layer 2: CSRF token validation (blocks token-less attacks)
...
"""
```

### 2. Created Test Scripts

#### `/Users/pangge/PycharmProjects/AgentOS/test_origin_check.py`

Full integration test script that requires a running WebUI server.

**Tests:**
- Cross-origin request blocking (Origin header)
- Same-origin request passing Origin check
- Referer header fallback
- Cross-origin Referer blocking
- Missing both headers rejection

#### `/Users/pangge/PycharmProjects/AgentOS/test_origin_logic.py`

Direct logic test script (no external dependencies required).

**Tests:**
- Cross-origin Origin header
- Same-origin Origin header
- Same-origin Referer header (no Origin)
- Cross-origin Referer header
- Missing both headers
- HTTPS same-origin
- Protocol mismatch (HTTP vs HTTPS)
- Port mismatch
- Environment variable `SITE_ORIGIN`

**Test Results:** ✅ All 9/9 tests passed

### 3. Created Documentation

#### `/Users/pangge/PycharmProjects/AgentOS/docs/ORIGIN_REFERER_CHECK_TESTING.md`

Comprehensive testing guide covering:
- Overview of two-layer defense
- Implementation details
- Configuration options
- Test cases and expected results
- Manual testing with curl
- Production configuration
- Security considerations
- Troubleshooting

## Two-Layer Defense System

### Layer 1: Origin/Referer Check (First Line)

**Purpose**: Block cross-domain requests immediately

**Checks**:
- Origin header (preferred)
- Referer header (fallback)
- Scheme, domain, and port must match

**Error Response**: `403 ORIGIN_CHECK_FAILED`

### Layer 2: CSRF Token Validation (Second Line)

**Purpose**: Block requests without valid CSRF tokens

**Checks**:
- X-CSRF-Token header presence
- Token matches session token

**Error Response**: `403 CSRF_TOKEN_REQUIRED` or `403 CSRF_TOKEN_INVALID`

## Configuration

### Environment Variables

```bash
# Explicit site origin (recommended for production)
export SITE_ORIGIN=https://agentos.example.com

# Production environment
export AGENTOS_ENV=production

# Secure cookies
export SESSION_SECURE_ONLY=true
```

### Code Configuration

```python
from agentos.webui.middleware.csrf import add_csrf_protection

# Enable Origin checking (default)
add_csrf_protection(app, check_origin=True)

# Disable Origin checking (not recommended)
add_csrf_protection(app, check_origin=False)
```

## Exempt Paths

The following paths are exempt from Origin/Referer checking:

- `/health` - Health check endpoint
- `/api/health` - API health check
- `/static/` - Static files
- `/ws/` - WebSocket connections
- `/webhook/` - Server-to-Server webhooks (use signature verification)

## Error Responses

### Origin Check Failed

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
    "timestamp": "2026-01-31T12:34:56.789Z"
}
```

### CSRF Token Required (After Passing Origin Check)

```json
{
    "ok": false,
    "error_code": "CSRF_TOKEN_REQUIRED",
    "message": "CSRF token is required for this request",
    "details": {
        "hint": "Include X-CSRF-Token header with a valid token",
        "endpoint": "/api/sessions",
        "method": "POST",
        "reason": "Browser-initiated API requests must include CSRF token"
    },
    "timestamp": "2026-01-31T12:34:56.789Z"
}
```

## Logging

### Debug Level

```
[DEBUG] Origin check passed: http://localhost:8000
[DEBUG] Referer check passed: http://localhost:8000/dashboard
```

### Warning Level

```
[WARNING] Origin mismatch: expected http://localhost:8000, got http://evil.com
[WARNING] Referer mismatch: expected http://localhost:8000, got http://evil.com/attack
[WARNING] Request missing both Origin and Referer headers: path=/api/sessions, method=POST
[WARNING] Origin/Referer check failed: path=/api/sessions, method=POST, origin=http://evil.com, referer=none
```

### Error Level

```
[ERROR] Failed to parse site origin: invalid://url
[ERROR] Failed to parse Origin header: http://[invalid, error: ...
[ERROR] Failed to parse Referer header: http://[invalid, error: ...
```

## Security Benefits

### 1. Defense in Depth

Even if an attacker bypasses the CSRF token (e.g., through XSS), the Origin/Referer check will still block the attack if it originates from a different domain.

### 2. Fail-Safe Protection

If CSRF tokens are accidentally disabled or misconfigured, Origin/Referer checking provides a safety net.

### 3. Complementary Protection

- **CSRF Token**: Protects against same-domain attacks without proper token
- **Origin Check**: Protects against cross-domain attacks

### 4. Browser-Native Security

Modern browsers automatically send Origin headers for cross-origin requests, making it harder for attackers to manipulate.

## Limitations

### 1. Subdomain Attacks

If an attacker controls a subdomain (e.g., `attacker.example.com`), they could potentially craft requests with matching Origin headers.

**Mitigation**: Use separate domains for different trust levels.

### 2. Null Origin

Some browsers send `Origin: null` for certain requests (e.g., from `file://` URLs).

**Current Behavior**: Treats `null` as suspicious and blocks.

### 3. Privacy Extensions

Some browser extensions strip Referer headers for privacy.

**Mitigation**: Origin header is checked first, which is less commonly stripped.

### 4. Server-to-Server Requests

Backend services making API calls may not send Origin/Referer headers.

**Solution**: Use exempt paths (e.g., `/webhook/`) and alternative authentication (e.g., API keys, signatures).

## Testing Results

### Logic Tests

**File**: `test_origin_logic.py`

**Status**: ✅ All 9/9 tests passed

**Tests Covered**:
1. Cross-origin Origin header
2. Same-origin Origin header
3. Same-origin Referer header (no Origin)
4. Cross-origin Referer header
5. Missing both headers
6. HTTPS same-origin
7. Protocol mismatch (HTTP vs HTTPS)
8. Port mismatch
9. Environment variable `SITE_ORIGIN`

### Integration Tests

**File**: `test_origin_check.py`

**Status**: Ready to run (requires WebUI server)

**Tests Covered**:
1. Cross-origin request blocking
2. Same-origin request passing Origin check
3. Referer fallback
4. Cross-origin Referer blocking
5. Missing both headers rejection

## Next Steps

1. **Run Integration Tests**: Start WebUI server and run `test_origin_check.py`
2. **Frontend Integration**: Ensure frontend sends appropriate Origin/Referer headers
3. **Production Deployment**: Set `SITE_ORIGIN` environment variable
4. **Monitoring**: Monitor logs for blocked requests and adjust as needed
5. **Documentation Update**: Update main README with security features

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Verifying Origin With Standard Headers](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#verifying-origin-with-standard-headers)
- [MDN: Origin Header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Origin)
- [MDN: Referer Header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referer)

## Completion Status

- [x] `_check_origin()` method implemented and tested
- [x] Origin/Referer check integrated into `dispatch()` method
- [x] Cross-origin requests correctly rejected (403 ORIGIN_CHECK_FAILED)
- [x] Same-origin requests pass Origin check
- [x] Referer fallback works correctly
- [x] WebSocket and Webhook exempt paths configured
- [x] Configuration option `check_origin` added and working
- [x] Logic test script created and passing (9/9 tests)
- [x] Integration test script created (ready to run)
- [x] Comprehensive documentation created
- [ ] Integration tests executed with live server
- [ ] Frontend integration verified
- [ ] Production deployment tested

## Task Status

**Task #6: 添加 Origin/Referer 同源检查** - ✅ COMPLETED

All implementation requirements have been met. The Origin/Referer same-origin check has been successfully added as a second line of defense in the CSRF middleware.
