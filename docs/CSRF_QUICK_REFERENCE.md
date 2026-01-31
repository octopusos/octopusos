# CSRF Protection Quick Reference

## TL;DR

AgentOS WebUI now has **two-layer CSRF protection**:

1. **Layer 1**: Origin/Referer same-origin check
2. **Layer 2**: CSRF token validation

Both layers are **enabled by default**. No action required for basic protection.

---

## For Frontend Developers

### What You Need to Do

**Option A: Use fetch() with credentials**

```javascript
// Browser automatically sends Origin header
fetch('/api/sessions', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': getCsrfToken()  // Read from cookie
    },
    credentials: 'include',  // Send cookies
    body: JSON.stringify({title: 'My Session'})
});
```

**Option B: Use XMLHttpRequest**

```javascript
var xhr = new XMLHttpRequest();
xhr.open('POST', '/api/sessions');
xhr.setRequestHeader('Content-Type', 'application/json');
xhr.setRequestHeader('X-CSRF-Token', getCsrfToken());
xhr.withCredentials = true;
xhr.send(JSON.stringify({title: 'My Session'}));
```

### Get CSRF Token

```javascript
function getCsrfToken() {
    // Read from cookie
    const match = document.cookie.match(/csrf_token=([^;]+)/);
    return match ? match[1] : null;
}
```

### What Happens If You Forget

```json
{
    "ok": false,
    "error_code": "CSRF_TOKEN_REQUIRED",
    "message": "CSRF token is required for this request"
}
```

**Fix**: Add `X-CSRF-Token` header to your request.

---

## For Backend Developers

### Enable CSRF Protection

```python
from agentos.webui.middleware.csrf import add_csrf_protection

# Enable both layers (recommended)
add_csrf_protection(app)

# Custom configuration
add_csrf_protection(
    app,
    check_origin=True,      # Layer 1: Origin/Referer check
    enforce_for_api=True,   # Layer 2: CSRF token validation
    exempt_paths=[          # Additional exempt paths
        "/my-webhook",
    ]
)
```

### Exempt a Path from CSRF

```python
# Method 1: Add to exempt_paths
add_csrf_protection(
    app,
    exempt_paths=[
        "/webhook/github",
        "/api/public",
    ]
)

# Method 2: Use default exemptions
# /health, /api/health, /static/*, /ws/*, /webhook/*
```

### Get CSRF Token in View

```python
from agentos.webui.middleware.csrf import get_csrf_token

@app.get("/form")
async def show_form(request: Request):
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse("form.html", {
        "request": request,
        "csrf_token": csrf_token
    })
```

### What Happens When Request is Blocked

**Cross-Origin Request:**

```json
{
    "ok": false,
    "error_code": "ORIGIN_CHECK_FAILED",
    "message": "Origin or Referer header check failed",
    "details": {
        "hint": "Request must originate from the same site",
        "origin": "http://evil.com"
    }
}
```

**Missing CSRF Token:**

```json
{
    "ok": false,
    "error_code": "CSRF_TOKEN_REQUIRED",
    "message": "CSRF token is required for this request",
    "details": {
        "hint": "Include X-CSRF-Token header with a valid token"
    }
}
```

---

## For DevOps/SRE

### Production Configuration

```bash
# Set explicit site origin (recommended)
export SITE_ORIGIN=https://agentos.example.com

# Enable production mode
export AGENTOS_ENV=production

# Secure cookies (HTTPS only)
export SESSION_SECURE_ONLY=true
```

### Nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name agentos.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Monitoring

```bash
# Check for blocked requests
tail -f /var/log/agentos/webui.log | grep "ORIGIN_CHECK_FAILED\|CSRF_TOKEN"

# Count blocked requests
grep "ORIGIN_CHECK_FAILED" /var/log/agentos/webui.log | wc -l
```

### Health Check

```bash
# Should NOT require CSRF token
curl http://localhost:8000/api/health
```

---

## Error Codes Reference

| Error Code | Layer | Meaning | Fix |
|------------|-------|---------|-----|
| `ORIGIN_CHECK_FAILED` | 1 | Cross-origin request | Check Origin/Referer headers |
| `CSRF_TOKEN_REQUIRED` | 2 | Missing CSRF token | Add X-CSRF-Token header |
| `CSRF_TOKEN_INVALID` | 2 | Invalid CSRF token | Get fresh token from cookie |

---

## HTTP Methods Protected

| Method | Protected? | Reason |
|--------|------------|--------|
| `POST` | ✅ Yes | State-changing |
| `PUT` | ✅ Yes | State-changing |
| `PATCH` | ✅ Yes | State-changing |
| `DELETE` | ✅ Yes | State-changing |
| `GET` | ❌ No | Safe/idempotent |
| `HEAD` | ❌ No | Safe/idempotent |
| `OPTIONS` | ❌ No | Safe/idempotent |

---

## Testing

### Test Origin Check

```bash
# Should be blocked (cross-origin)
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "Origin: http://evil.com" \
  -d '{"title": "test"}'

# Should pass Origin check (same-origin)
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -d '{"title": "test"}'
```

### Test CSRF Token

```bash
# Get CSRF token
TOKEN=$(curl -s http://localhost:8000/api/csrf-token | jq -r .token)

# Use token in request
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:8000" \
  -H "X-CSRF-Token: $TOKEN" \
  -H "Cookie: session=your_session_id" \
  -d '{"title": "test"}'
```

### Run Test Suite

```bash
# Logic tests (no dependencies)
python3 test_origin_logic.py

# Integration tests (requires live server)
python3 test_origin_check.py
```

---

## Troubleshooting

### Problem: "ORIGIN_CHECK_FAILED" on legitimate requests

**Possible Causes:**

1. `SITE_ORIGIN` env var is wrong
2. Proxy not forwarding headers
3. Browser not sending Origin/Referer

**Solutions:**

```bash
# Check current origin
curl -v http://localhost:8000 2>&1 | grep -i origin

# Set explicit origin
export SITE_ORIGIN=http://localhost:8000

# Check proxy config
nginx -T | grep proxy_set_header
```

### Problem: "CSRF_TOKEN_REQUIRED" on all requests

**Possible Causes:**

1. Frontend not sending token
2. Session not persisting
3. Cookie not being set

**Solutions:**

```javascript
// Check if token exists
console.log('CSRF Token:', getCsrfToken());

// Check cookies
console.log('Cookies:', document.cookie);

// Check if token is sent
fetch('/api/test', {
    method: 'POST',
    headers: {
        'X-CSRF-Token': getCsrfToken()
    }
});
```

### Problem: Token validation always fails

**Possible Causes:**

1. Session middleware not configured
2. Token expired
3. Token from different session

**Solutions:**

```python
# Check session middleware order (must be before CSRF)
app.add_middleware(SessionMiddleware, secret_key="...")
app.add_middleware(CSRFProtectionMiddleware, ...)

# Check token in session
print(request.session.get("_csrf_token"))
```

---

## Security Best Practices

### ✅ DO

- Enable both layers (`check_origin=True`, `enforce_for_api=True`)
- Set `SITE_ORIGIN` explicitly in production
- Use HTTPS in production
- Send Origin header from frontend
- Include CSRF token in all state-changing requests
- Monitor blocked requests for potential attacks

### ❌ DON'T

- Disable CSRF protection without good reason
- Exempt sensitive endpoints from protection
- Store CSRF tokens in localStorage (use cookies)
- Send CSRF tokens in URL parameters
- Ignore "ORIGIN_CHECK_FAILED" errors in logs

---

## FAQ

### Q: Do I need both layers?

**A:** Yes. Layer 1 blocks cross-domain attacks, Layer 2 blocks same-domain attacks without tokens. Together they provide defense in depth.

### Q: What if my API is called from mobile apps?

**A:** Mobile apps won't send Origin/Referer headers. Either:
1. Exempt the mobile API paths
2. Use a different authentication method (API keys, JWT)
3. Disable `check_origin` for those paths

### Q: What about WebSocket connections?

**A:** WebSocket upgrade requests are automatically exempt (`/ws/*` path prefix).

### Q: What about webhooks from external services?

**A:** Webhook paths (`/webhook/*`) are automatically exempt. Use signature verification instead.

### Q: Can I disable Origin checking but keep CSRF tokens?

**A:** Yes, but not recommended. Set `check_origin=False` when calling `add_csrf_protection()`.

### Q: What if a browser doesn't send Origin/Referer?

**A:** Very rare with modern browsers. If needed, CSRF token (Layer 2) still protects. Consider exempting specific paths for old browsers.

### Q: How do I test in development without HTTPS?

**A:** Works fine with HTTP. Origin checking compares the full origin including protocol.

### Q: What's the performance impact?

**A:** Negligible. Origin checking is a simple string comparison. CSRF token validation is a constant-time comparison.

---

## Quick Commands

```bash
# Start WebUI
python -m agentos.webui.main

# Run tests
python3 test_origin_logic.py
python3 test_origin_check.py

# Check logs
tail -f logs/webui.log | grep -i csrf

# Test endpoint
curl -X POST http://localhost:8000/api/sessions \
  -H "Origin: http://localhost:8000" \
  -H "X-CSRF-Token: $(curl -s http://localhost:8000/api/csrf-token | jq -r .token)" \
  -d '{"title":"test"}'
```

---

## Further Reading

- [Full Implementation Guide](./ORIGIN_REFERER_CHECK_IMPLEMENTATION.md)
- [Testing Guide](./ORIGIN_REFERER_CHECK_TESTING.md)
- [Two-Layer Defense Architecture](./CSRF_TWO_LAYER_DEFENSE.md)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

---

**Last Updated:** 2026-01-31
**Version:** 1.0
**Status:** ✅ Production Ready
