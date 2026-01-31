# Production Security Checklist

**Version:** 1.0
**Last Updated:** 2026-01-31
**Applies To:** AgentOS WebUI v0.3.2+

This checklist ensures all security controls are properly configured before deploying to production.

---

## Pre-Deployment Security Checklist

### Critical Security Controls

#### 1. HTTPS/TLS Configuration

**Priority:** 🔴 CRITICAL

```bash
□ Valid TLS certificate obtained (Let's Encrypt, DigiCert, etc.)
□ Certificate includes all required domains
□ Certificate is not expired
□ TLS 1.2 or higher enabled
□ Weak ciphers disabled
□ HTTPS redirect configured (HTTP → HTTPS)
```

**Testing:**
```bash
# Test TLS configuration
openssl s_client -connect yourdomain.com:443 -tls1_2

# Verify certificate
curl -vI https://yourdomain.com 2>&1 | grep -i "ssl\|tls"
```

---

#### 2. Enable HSTS

**Priority:** 🔴 CRITICAL (when using HTTPS)

**File:** `agentos/webui/middleware/security.py`

**Action:** Uncomment HSTS header

```python
# Line 92-93
# Before (development):
# response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

# After (production):
response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
```

**Verification:**
```bash
curl -I https://yourdomain.com/ | grep -i strict-transport-security
# Expected: Strict-Transport-Security: max-age=31536000; includeSubDomains
```

**Checklist:**
```bash
□ HSTS header uncommented in security.py
□ max-age set to 31536000 (1 year minimum)
□ includeSubDomains directive present
□ Verified with curl command above
□ (Optional) Submitted to HSTS preload list
```

---

#### 3. Update Session Configuration

**Priority:** 🔴 CRITICAL

**File:** `agentos/webui/app.py`

**Action:** Update session cookie settings for production

```python
# Line 223-230
# Before (development):
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie="agentos_session",
    max_age=86400,  # 24 hours
    same_site="strict",
    https_only=False,  # ⚠️ Set to True in production with HTTPS
)

# After (production):
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie="agentos_session",
    max_age=86400,
    same_site="strict",
    https_only=True,  # ✅ HTTPS only
)
```

**Checklist:**
```bash
□ https_only=True in SessionMiddleware
□ same_site="strict" (already set)
□ SESSION_SECRET_KEY is strong and unique (not default)
□ Session secret stored in environment variable
```

**Generate Strong Secret:**
```bash
# Generate a new session secret
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Set in environment
export SESSION_SECRET_KEY="your-generated-secret-here"
```

---

#### 4. Configure CSRF Protection

**Priority:** 🔴 CRITICAL

**File:** `agentos/webui/middleware/csrf.py`

**Action:** Update CSRF cookie settings

```python
# Line 222-229
# Before (development):
response.set_cookie(
    key=self.cookie_name,
    value=token,
    httponly=False,  # JavaScript needs to read this
    secure=False,     # ⚠️ Set to True in production with HTTPS
    samesite="strict",
    path="/",
)

# After (production):
response.set_cookie(
    key=self.cookie_name,
    value=token,
    httponly=False,
    secure=True,     # ✅ HTTPS only
    samesite="strict",
    path="/",
)
```

**Checklist:**
```bash
□ secure=True in CSRF cookie settings
□ samesite="strict" (already set)
□ CSRF protection tested in production
```

---

#### 5. Security Headers Configuration

**Priority:** 🟡 HIGH

**File:** `agentos/webui/middleware/security.py`

**Current Status:** ✅ Already configured correctly

**Verification:**
```bash
curl -I https://yourdomain.com/ | grep -E "X-Frame-Options|X-Content-Type-Options|X-XSS-Protection|Referrer-Policy|Content-Security-Policy"
```

**Expected Headers:**
```
Content-Security-Policy: default-src 'self'; ...
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

**Checklist:**
```bash
□ All security headers present
□ CSP policy appropriate for application
□ X-Frame-Options: DENY
□ X-Content-Type-Options: nosniff
□ Referrer-Policy configured
```

---

### Environment Configuration

#### 6. Sentry Configuration

**Priority:** 🟡 HIGH (Production Monitoring)

**Environment Variables:**

```bash
# Required
export SENTRY_DSN="https://your-dsn@sentry.io/project"
export SENTRY_ENVIRONMENT="production"
export SENTRY_RELEASE="agentos-webui@$(git rev-parse --short HEAD)"

# Recommended
export SENTRY_ENABLED="true"
export SENTRY_TRACES_SAMPLE_RATE="0.1"  # 10% in production
export SENTRY_PROFILES_SAMPLE_RATE="0.1"  # 10% in production
```

**Checklist:**
```bash
□ Sentry DSN configured
□ Environment set to "production"
□ Release tracking configured
□ Sample rates appropriate for traffic
□ PII scrubbing configured
```

---

#### 7. Database Configuration

**Priority:** 🟡 HIGH

**Environment Variables:**

```bash
# Use production database path
export AGENTOS_DB_PATH="/var/lib/agentos/production.sqlite"

# Or use PostgreSQL (recommended for production)
export DATABASE_URL="postgresql://user:pass@localhost/agentos"
```

**Checklist:**
```bash
□ Database path set to production location
□ Database directory has correct permissions (700)
□ Database backed up regularly
□ Connection pooling configured (if using PostgreSQL)
```

---

#### 8. Logging Configuration

**Priority:** 🟢 MEDIUM

**Environment Variables:**

```bash
export AGENTOS_LOGS_PERSIST="true"
export AGENTOS_LOGS_LEVEL="WARNING"  # Less verbose than ERROR
export AGENTOS_LOGS_MAX_SIZE="10000"
```

**Checklist:**
```bash
□ Log persistence enabled
□ Log level appropriate (WARNING or ERROR)
□ Log rotation configured
□ Sensitive data not logged
```

---

### Advanced Security (Optional)

#### 9. Implement Nonce-Based CSP

**Priority:** 🟢 MEDIUM (Removes unsafe-inline)

**See:** Section 4.2 in Security Audit Report

**Checklist:**
```bash
□ Nonce generation implemented
□ Templates updated to use nonces
□ All inline scripts tagged with nonce
□ CSP updated to use nonces instead of unsafe-inline
□ Tested in staging environment
```

---

#### 10. Add Subresource Integrity (SRI)

**Priority:** 🟢 LOW (Defense in depth)

**File:** `agentos/webui/templates/index.html`

**Action:** Add integrity hashes to external resources

```html
<!-- Before -->
<script src="https://unpkg.com/vis-network@3.23.0/dist/vis-network.min.js"></script>

<!-- After -->
<script
    src="https://unpkg.com/vis-network@3.23.0/dist/vis-network.min.js"
    integrity="sha384-[hash]"
    crossorigin="anonymous"
></script>
```

**Generate Hashes:**
```bash
# Use SRI Hash Generator
# https://www.srihash.org/

# Or generate locally
curl -s https://unpkg.com/vis-network@3.23.0/dist/vis-network.min.js | \
    openssl dgst -sha384 -binary | \
    openssl base64 -A
```

**Checklist:**
```bash
□ SRI hashes added to all external scripts
□ SRI hashes added to all external stylesheets
□ crossorigin="anonymous" attribute present
□ Hashes verified with srihash.org
```

---

#### 11. Configure Rate Limiting

**Priority:** 🟢 MEDIUM

**Current Status:** ✅ Basic rate limiting configured

**File:** `agentos/webui/app.py` (lines 138-140)

**Production Tuning:**

```python
# Adjust rate limits for production traffic
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"]  # Adjust as needed
)
```

**Checklist:**
```bash
□ Rate limits configured for expected traffic
□ Rate limiting tested under load
□ Monitoring alerts for rate limit hits
□ Whitelist configured for trusted IPs (if needed)
```

---

### Testing and Verification

#### 12. Run Security Test Suite

**Priority:** 🔴 CRITICAL

**Command:**
```bash
# Run all security tests
pytest tests/security/ -v

# Specific test suites
pytest tests/security/test_security_headers_comprehensive.py -v
pytest tests/security/test_sessions_api_xss.py -v
pytest tests/unit/webui/test_csrf_middleware.py -v
```

**Checklist:**
```bash
□ All security header tests pass
□ CSRF protection tests pass
□ XSS protection tests pass
□ No test failures or skips (except HSTS in dev mode)
```

---

#### 13. Security Scanning

**Priority:** 🟡 HIGH

**Tools:**

1. **Mozilla Observatory**
   ```bash
   # Visit: https://observatory.mozilla.org/
   # Enter: https://yourdomain.com
   # Target Score: A or A+
   ```

2. **Security Headers Scanner**
   ```bash
   # Visit: https://securityheaders.com/
   # Enter: https://yourdomain.com
   # Target Score: A
   ```

3. **SSL Labs**
   ```bash
   # Visit: https://www.ssllabs.com/ssltest/
   # Enter: yourdomain.com
   # Target Score: A or A+
   ```

**Checklist:**
```bash
□ Mozilla Observatory score: A or better
□ Security Headers score: A or better
□ SSL Labs score: A or better
□ No critical vulnerabilities found
```

---

#### 14. Penetration Testing

**Priority:** 🟡 HIGH (for production)

**Test Areas:**

```bash
□ XSS attempts (reflected, stored, DOM-based)
□ CSRF attacks
□ Clickjacking attempts
□ SQL injection (if applicable)
□ Command injection
□ Path traversal
□ Authentication bypass
□ Session fixation
□ CORS misconfiguration exploitation
```

**Tools:**
- OWASP ZAP
- Burp Suite
- Nikto
- Manual testing

---

### Deployment Configuration

#### 15. Web Server Configuration

**Priority:** 🔴 CRITICAL

**Nginx Configuration Example:**

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # TLS Configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers (redundant with app, but defense in depth)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Checklist:**
```bash
□ HTTP to HTTPS redirect configured
□ TLS 1.2+ enabled
□ Weak ciphers disabled
□ HTTP/2 enabled
□ WebSocket proxying configured
□ Rate limiting configured at web server level
□ Request size limits configured
```

---

#### 16. Firewall Configuration

**Priority:** 🔴 CRITICAL

**UFW Example:**

```bash
# Allow SSH (for management)
sudo ufw allow 22/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Allow HTTP (for redirect)
sudo ufw allow 80/tcp

# Deny all other incoming
sudo ufw default deny incoming

# Allow all outgoing
sudo ufw default allow outgoing

# Enable firewall
sudo ufw enable
```

**Checklist:**
```bash
□ Firewall enabled
□ Only required ports open (80, 443, 22)
□ SSH access restricted to trusted IPs (if possible)
□ DDoS protection configured
```

---

### Monitoring and Incident Response

#### 17. Security Monitoring

**Priority:** 🟡 HIGH

**Metrics to Monitor:**

```bash
□ Failed authentication attempts
□ CSRF token validation failures
□ Rate limit violations
□ Unusual API access patterns
□ Error rate spikes
□ Security header violations (if using CSP reporting)
```

**Tools:**
- Sentry (error tracking)
- Prometheus + Grafana (metrics)
- ELK Stack (log aggregation)
- CloudFlare (DDoS protection)

---

#### 18. Incident Response Plan

**Priority:** 🟢 MEDIUM

**Checklist:**
```bash
□ Security incident contacts identified
□ Incident response procedures documented
□ Backup and restore procedures tested
□ Rollback procedures tested
□ Security patches applied regularly
□ Vulnerability disclosure policy published
```

---

## Quick Reference: Production Environment Variables

```bash
# Copy to .env.production

# Session Security
export SESSION_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"

# Sentry Monitoring
export SENTRY_DSN="https://your-dsn@sentry.io/project"
export SENTRY_ENVIRONMENT="production"
export SENTRY_RELEASE="agentos-webui@0.3.2"
export SENTRY_ENABLED="true"
export SENTRY_TRACES_SAMPLE_RATE="0.1"
export SENTRY_PROFILES_SAMPLE_RATE="0.1"

# Database
export AGENTOS_DB_PATH="/var/lib/agentos/production.sqlite"

# Logging
export AGENTOS_LOGS_PERSIST="true"
export AGENTOS_LOGS_LEVEL="WARNING"
export AGENTOS_LOGS_MAX_SIZE="10000"
```

---

## Deployment Script

```bash
#!/bin/bash
# deploy_production.sh

set -e

echo "🔐 AgentOS Production Deployment Security Checklist"
echo "=================================================="

# Check HTTPS configuration
echo "✓ Checking HTTPS configuration..."
if ! grep -q "https_only=True" agentos/webui/app.py; then
    echo "❌ HTTPS not enforced in session cookies"
    exit 1
fi

# Check HSTS
echo "✓ Checking HSTS configuration..."
if grep -q "# response.headers\[\"Strict-Transport-Security\"\]" agentos/webui/middleware/security.py; then
    echo "❌ HSTS is commented out (required for production)"
    exit 1
fi

# Check session secret
echo "✓ Checking session secret..."
if [ -z "$SESSION_SECRET_KEY" ]; then
    echo "❌ SESSION_SECRET_KEY not set"
    exit 1
fi

# Check Sentry configuration
echo "✓ Checking Sentry configuration..."
if [ -z "$SENTRY_DSN" ]; then
    echo "⚠️  Warning: SENTRY_DSN not set (monitoring disabled)"
fi

# Run security tests
echo "✓ Running security tests..."
pytest tests/security/ -v --tb=short || {
    echo "❌ Security tests failed"
    exit 1
}

echo ""
echo "✅ All security checks passed!"
echo ""
echo "📋 Manual verification required:"
echo "  1. TLS certificate is valid"
echo "  2. Firewall rules configured"
echo "  3. Rate limiting tested"
echo "  4. Security scanning completed"
echo ""
echo "Ready to deploy? (y/N)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "🚀 Proceeding with deployment..."
    # Add your deployment commands here
else
    echo "❌ Deployment cancelled"
    exit 1
fi
```

---

## Support and Documentation

### Additional Resources

- **Security Audit Report:** `/tmp/SECURITY_HEADERS_CORS_AUDIT_REPORT.md`
- **Test Suite:** `tests/security/test_security_headers_comprehensive.py`
- **Middleware Documentation:** `agentos/webui/middleware/`

### Security Contact

For security issues, contact: security@yourdomain.com

### Update Schedule

- Review this checklist: Every release
- Update security headers: Quarterly
- Penetration testing: Annually
- Dependency updates: Monthly

---

**Last Updated:** 2026-01-31
**Document Version:** 1.0
**Reviewed By:** Security Team
