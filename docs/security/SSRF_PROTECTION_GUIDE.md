# SSRF Protection Quick Reference Guide

## Overview

The Web Fetch Connector now includes built-in SSRF (Server-Side Request Forgery) protection that automatically validates all URLs before making requests.

## What is Blocked?

### 🚫 Blocked URLs

| Category | Examples | Reason |
|----------|----------|--------|
| **Localhost** | `http://localhost/`, `http://127.0.0.1/` | Internal service access |
| **Private Networks** | `http://192.168.1.1/`, `http://10.0.0.1/` | Internal network access |
| **Cloud Metadata** | `http://169.254.169.254/` | Credential theft |
| **IPv6 Private** | `http://[::1]/`, `http://[fc00::1]/` | IPv6 internal access |
| **Invalid Protocols** | `file:///etc/passwd`, `ftp://internal/` | Protocol smuggling |

### ✅ Allowed URLs

| Type | Examples |
|------|----------|
| **Public HTTP** | `http://example.com/` |
| **Public HTTPS** | `https://api.github.com/` |
| **Public IPs** | `http://8.8.8.8/` (Google DNS) |

## Usage

### Basic Usage (No Changes Required)

```python
from agentos.core.communication.connectors.web_fetch import WebFetchConnector

connector = WebFetchConnector()

# This just works - public URLs are allowed
result = await connector.execute("fetch", {
    "url": "https://example.com"
})
```

### Error Handling

```python
try:
    result = await connector.execute("fetch", {
        "url": "http://localhost:8080/admin"
    })
except ValueError as e:
    # Handle SSRF protection error
    print(f"URL blocked: {e}")
    # Output: "Access to loopback addresses is forbidden: 127.0.0.1"
```

## Common Error Messages

### Loopback Blocked
```
ValueError: Access to loopback addresses is forbidden: 127.0.0.1 (hostname: localhost)
```
**Cause**: Attempting to access localhost or 127.0.0.0/8 range

### Private Network Blocked
```
ValueError: Access to private IP addresses is forbidden: 192.168.1.1 (hostname: 192.168.1.1)
```
**Cause**: Attempting to access private network (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)

### Cloud Metadata Blocked
```
ValueError: Access to link-local addresses is forbidden: 169.254.169.254 (hostname: 169.254.169.254).
This includes cloud metadata endpoints like 169.254.169.254
```
**Cause**: Attempting to access cloud metadata service

### Protocol Blocked
```
ValueError: Invalid URL scheme: file. Only http and https are allowed
```
**Cause**: Using non-HTTP/HTTPS protocol

### DNS Rebinding Blocked
```
ValueError: Hostname 'evil-domain.com' resolves to forbidden IP 127.0.0.1:
Access to loopback addresses is forbidden: 127.0.0.1 (hostname: evil-domain.com)
```
**Cause**: Domain resolves to a blocked IP address

## Testing Your Code

### Test with Mocked DNS

When testing code that uses the Web Fetch Connector, mock DNS resolution:

```python
import pytest
from unittest.mock import patch
import socket

@pytest.mark.asyncio
@patch("socket.getaddrinfo")
async def test_my_fetch_function(mock_getaddrinfo):
    # Mock DNS to return a public IP
    mock_getaddrinfo.return_value = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))
    ]

    # Your test code here
    result = await my_function_that_uses_web_fetch()
    assert result["status_code"] == 200
```

### Test SSRF Protection

```python
import pytest

@pytest.mark.asyncio
async def test_ssrf_protection():
    connector = WebFetchConnector()

    # Verify localhost is blocked
    with pytest.raises(ValueError, match="loopback.*forbidden"):
        await connector.execute("fetch", {"url": "http://localhost/"})

    # Verify private IPs are blocked
    with pytest.raises(ValueError, match="private.*forbidden"):
        await connector.execute("fetch", {"url": "http://192.168.1.1/"})
```

## Performance Notes

### DNS Caching

The connector caches DNS results for better performance:
- **First request**: ~50-100ms (includes DNS resolution)
- **Subsequent requests**: ~1-5ms (cached)

### Cache Behavior

```python
connector = WebFetchConnector()

# First request - resolves DNS
await connector.execute("fetch", {"url": "http://example.com/page1"})  # ~100ms

# Second request - uses cache
await connector.execute("fetch", {"url": "http://example.com/page2"})  # ~5ms
```

To clear DNS cache, create a new connector instance:
```python
connector = WebFetchConnector()  # Fresh DNS cache
```

## Configuration

### Default Settings

```python
connector = WebFetchConnector({
    "timeout": 30,          # Request timeout in seconds
    "max_size": 10485760,   # Max content size (10MB)
    "follow_redirects": True,
    "user_agent": "AgentOS/1.0"
})
```

### Custom Configuration

```python
# Stricter timeout
connector = WebFetchConnector({
    "timeout": 10,
    "max_size": 5 * 1024 * 1024  # 5MB
})
```

## Security Best Practices

### ✅ Do's

1. **Always validate user input** before passing to web_fetch
2. **Use HTTPS** whenever possible
3. **Handle errors gracefully** with try-except
4. **Log blocked attempts** for security monitoring
5. **Test with various URL patterns**

### ❌ Don'ts

1. **Don't bypass validation** - there's no override flag for security reasons
2. **Don't trust user-provided URLs** - always validate
3. **Don't use file:// or ftp://** - only HTTP/HTTPS allowed
4. **Don't ignore ValueError exceptions** - they indicate security issues

## Troubleshooting

### Problem: Legitimate URL is blocked

**Symptom**: Public URL throws "Cannot resolve hostname" error

**Cause**: DNS resolution failure (network issue, not security)

**Solution**:
```python
try:
    result = await connector.execute("fetch", {"url": url})
except ValueError as e:
    if "Cannot resolve hostname" in str(e):
        # DNS issue - retry or log
        logger.warning(f"DNS resolution failed for {url}")
    else:
        # Security block - do not retry
        logger.error(f"SSRF protection blocked {url}")
```

### Problem: Tests failing after SSRF implementation

**Symptom**: Tests that mock httpx.AsyncClient now fail

**Solution**: Also mock socket.getaddrinfo:
```python
@patch("socket.getaddrinfo")
@patch("httpx.AsyncClient")
async def test_function(mock_client, mock_getaddrinfo):
    mock_getaddrinfo.return_value = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))
    ]
    # ... rest of test
```

## Migration Guide

### Before (No SSRF Protection)
```python
# Old code - vulnerable to SSRF
result = await connector.execute("fetch", {
    "url": user_provided_url  # ⚠️ Dangerous
})
```

### After (With SSRF Protection)
```python
# New code - automatically protected
try:
    result = await connector.execute("fetch", {
        "url": user_provided_url  # ✅ Safe
    })
except ValueError as e:
    # Handle blocked URLs
    return {"error": "Invalid URL", "details": str(e)}
```

**No code changes required** - protection is automatic!

## Support

### For Security Issues
- Report vulnerabilities to security team
- Do not disclose publicly until patched

### For Questions
- Check test file: `tests/unit/core/communication/test_ssrf_protection.py`
- Review implementation: `agentos/core/communication/connectors/web_fetch.py`

## Version History

- **v1.0.0** (2026-01-31): Initial SSRF protection implementation
  - Added URL validation
  - Added DNS rebinding protection
  - Added IPv6 support
  - Added DNS caching
  - 34 test cases
  - Backward compatible

---

**Last Updated**: 2026-01-31
**Author**: AgentOS Security Team
