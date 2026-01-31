# L-11: Environment-Aware Error Handling - Developer Guide

**Quick Reference for Error Handling in AgentOS**

---

## Overview

AgentOS uses environment-aware error handling to protect sensitive information in production while providing detailed debugging information in development.

---

## Quick Start

### Development Mode (Full Error Details)

```bash
# .env file
AGENTOS_ENV=development
AGENTOS_DEBUG=true
```

**Result**: You'll see full stack traces and error details in API responses.

### Production Mode (Protected Errors)

```bash
# .env file
AGENTOS_ENV=production
AGENTOS_DEBUG=false
```

**Result**: Users see generic errors, full details go to logs and Sentry.

---

## Error Response Format

### Production Response

```json
{
  "ok": false,
  "data": null,
  "error": "Internal server error",
  "hint": "An unexpected error occurred. Please contact support if the issue persists.",
  "reason_code": "INTERNAL_ERROR"
}
```

**✅ Safe for production - no sensitive data exposed**

### Development Response

```json
{
  "ok": false,
  "data": null,
  "error": "ValueError: Database connection failed",
  "hint": "An unexpected error occurred. See details below (DEBUG mode).",
  "reason_code": "INTERNAL_ERROR",
  "debug_info": {
    "exception_type": "ValueError",
    "exception_message": "Database connection failed",
    "traceback": "Traceback (most recent call last):\n  File \"app.py\", line 42...",
    "request_path": "/api/users",
    "request_method": "POST"
  }
}
```

**🔧 Perfect for debugging - all the details you need**

---

## Configuration

### Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `AGENTOS_ENV` | `production`, `staging`, `development` | `development` | Environment mode |
| `AGENTOS_DEBUG` | `true`, `false` | `false` | Enable debug output |

### Behavior Matrix

| AGENTOS_ENV | AGENTOS_DEBUG | Shows Error Details? | Use Case |
|-------------|---------------|----------------------|----------|
| production  | false         | ❌ No                | Production servers |
| production  | true          | ❌ No                | Production (debug overridden) |
| staging     | false         | ❌ No                | Staging environment |
| development | false         | ❌ No                | Test production behavior |
| development | true          | ✅ Yes               | Local development |

**Security Note**: Production environment **always** hides error details, even if DEBUG is true.

---

## How It Works

### 1. Error Occurs

```python
# Somewhere in your code
def process_user(user_id):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")  # Error!
```

### 2. Global Handler Catches It

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Always log full error
    logger.error(f"Unhandled exception in {request.method} {request.url.path}", exc_info=exc)

    # Report to Sentry
    if SENTRY_AVAILABLE and SENTRY_ENABLED:
        sentry_sdk.capture_exception(exc)

    # Check environment
    is_debug = os.getenv("AGENTOS_DEBUG", "false").lower() == "true"
    environment = os.getenv("AGENTOS_ENV", "development").lower()

    # Return appropriate response
    if environment == "production" or not is_debug:
        return generic_error()  # Safe response
    else:
        return detailed_error(exc)  # Debugging info
```

### 3. Response Returned

- **Production**: Generic error to user, full details in logs
- **Development**: Full error details in response

---

## Best Practices

### ✅ DO

1. **Use specific exception types**
   ```python
   raise ValueError("Invalid email format")  # Good
   ```

2. **Add helpful error messages**
   ```python
   raise RuntimeError(f"Failed to connect to database at {db_url}")
   ```

3. **Log context before raising**
   ```python
   logger.error(f"User {user_id} not found in database")
   raise ValueError(f"User {user_id} not found")
   ```

4. **Use environment variables**
   ```python
   if os.getenv("AGENTOS_ENV") == "production":
       # Production-specific logic
   ```

### ❌ DON'T

1. **Don't include sensitive data in error messages**
   ```python
   # BAD - exposes password
   raise ValueError(f"Login failed for user@example.com with password: {password}")

   # GOOD - no sensitive data
   raise ValueError("Login failed: Invalid credentials")
   ```

2. **Don't catch and hide errors silently**
   ```python
   # BAD - errors disappear
   try:
       risky_operation()
   except Exception:
       pass  # Silent failure!

   # GOOD - log and re-raise
   try:
       risky_operation()
   except Exception as e:
       logger.error(f"Operation failed: {e}")
       raise
   ```

3. **Don't return detailed errors manually in production**
   ```python
   # BAD - bypasses global handler
   return {"error": traceback.format_exc()}

   # GOOD - let global handler deal with it
   raise Exception("Something went wrong")
   ```

---

## Testing Error Handling

### Unit Test Example

```python
def test_production_hides_details():
    """Test that production mode hides error details"""
    with patch.dict(os.environ, {
        "AGENTOS_ENV": "production",
        "AGENTOS_DEBUG": "false"
    }):
        from agentos.webui.app import app
        client = TestClient(app)

        # Trigger an error
        response = client.get("/api/trigger-error")

        # Verify generic error
        data = response.json()
        assert data["error"] == "Internal server error"
        assert "debug_info" not in data
        assert "traceback" not in data
```

### Integration Test Example

```python
def test_development_shows_details():
    """Test that development mode shows error details"""
    with patch.dict(os.environ, {
        "AGENTOS_ENV": "development",
        "AGENTOS_DEBUG": "true"
    }):
        from agentos.webui.app import app
        client = TestClient(app)

        # Trigger an error
        response = client.get("/api/trigger-error")

        # Verify detailed error
        data = response.json()
        assert "debug_info" in data
        assert "traceback" in data["debug_info"]
        assert data["debug_info"]["exception_type"] is not None
```

---

## Troubleshooting

### Problem: Not Seeing Error Details in Development

**Solution**: Check environment variables

```bash
# Verify settings
echo $AGENTOS_ENV        # Should be: development
echo $AGENTOS_DEBUG      # Should be: true

# If not set, add to .env
cat >> .env << EOF
AGENTOS_ENV=development
AGENTOS_DEBUG=true
EOF
```

### Problem: Errors Not Being Logged

**Solution**: Check logging configuration

```python
import logging

# Ensure logging is configured
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Verify logger exists
logger = logging.getLogger(__name__)
logger.error("Test log message")
```

### Problem: Sentry Not Receiving Errors

**Solution**: Verify Sentry configuration

```bash
# Check environment variables
echo $SENTRY_ENABLED     # Should be: true
echo $SENTRY_DSN         # Should have your DSN

# Test Sentry
python3 -c "
import sentry_sdk
sentry_sdk.init(dsn='YOUR_DSN')
sentry_sdk.capture_message('Test from AgentOS')
"
```

---

## Advanced Topics

### Custom Error Handlers

You can add custom handlers for specific exceptions:

```python
from fastapi import HTTPException

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with custom logic"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": str(exc.detail),
            "reason_code": "HTTP_ERROR"
        }
    )
```

### Error Context

Add context to errors for better debugging:

```python
try:
    result = complex_operation(user_id, action)
except Exception as e:
    logger.error(
        f"Operation failed",
        extra={
            "user_id": user_id,
            "action": action,
            "error": str(e)
        }
    )
    raise
```

### Monitoring Error Rates

Track error rates with metrics:

```python
from prometheus_client import Counter

error_counter = Counter('api_errors_total', 'Total API errors', ['endpoint', 'error_type'])

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Increment counter
    error_counter.labels(
        endpoint=request.url.path,
        error_type=type(exc).__name__
    ).inc()

    # ... rest of handler
```

---

## Checklist for Production

Before deploying to production, verify:

- [ ] `AGENTOS_ENV=production` is set
- [ ] `AGENTOS_DEBUG=false` is set
- [ ] Sentry DSN is configured
- [ ] Logging is properly configured
- [ ] Error responses are generic (no stack traces)
- [ ] All errors are being logged
- [ ] Monitoring is set up
- [ ] Alerts are configured

---

## References

- **Implementation**: `agentos/webui/app.py`
- **Tests**: `tests/security/test_l11_error_handling_simple.py`
- **Acceptance Report**: `L11_TO_L15_ACCEPTANCE_REPORT.md`
- **Sentry Docs**: https://docs.sentry.io/platforms/python/

---

## Support

If you have questions about error handling:

1. Check this guide first
2. Review the acceptance report
3. Look at test examples
4. Check Sentry dashboard for production errors
5. Contact the security team

---

**Last Updated**: 2026-01-31
**Version**: 1.0
**Status**: ✅ Production Ready
