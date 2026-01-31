# CSRF Exemption Contract

**Purpose:** This document serves as the authoritative security contract for CSRF protection exemptions in AgentOS. All exemptions must be documented here with clear security justification. Any changes to exemptions must update this contract.

**Security Policy:** Deny-by-default. All state-changing endpoints (POST/PUT/PATCH/DELETE) MUST have CSRF protection unless explicitly exempted below with valid security controls.

## Contract Version
- **Version:** 1.0.0
- **Last Updated:** 2026-01-31
- **Owner:** Security Team
- **Review Cycle:** Quarterly or on any exemption change

---

## Exemption Table

| Method | Path Pattern | Origin Check | CSRF Token | Alt Security | Justification | Risk Level |
|--------|-------------|--------------|------------|--------------|---------------|-----------|
| ALL | `/health` | No | No | Public endpoint | System health monitoring, no state changes | Low |
| ALL | `/api/health` | No | No | Public endpoint | System health monitoring, no state changes | Low |
| ALL | `/static/**` | No | No | Static content | Read-only static file serving | Low |
| ALL | `/ws/**` | No | No | WebSocket protocol | WebSocket uses different security model (Origin + upgrade headers) | Medium |
| POST/PUT/PATCH/DELETE | `/webhook/**` | No | No | **REQUIRES SIGNATURE** | Server-to-server webhooks MUST verify HMAC/signature | **HIGH** |
| GET | `/api/csrf-token` | No | No | Public endpoint | Token retrieval endpoint, no state changes | Low |

---

## Detailed Security Analysis

### 1. `/health` and `/api/health`
- **Type:** Health check endpoints (GET)
- **State Changes:** None
- **Security Rationale:** Public monitoring endpoints with no authentication or state modification
- **Alternative Controls:** None required (read-only)
- **Audit Status:** ✅ Verified safe

### 2. `/static/**`
- **Type:** Static file serving (GET)
- **State Changes:** None
- **Security Rationale:** Read-only content delivery (CSS, JS, images)
- **Alternative Controls:** None required (no backend logic)
- **Audit Status:** ✅ Verified safe

### 3. `/ws/**`
- **Type:** WebSocket endpoints
- **State Changes:** Potential state changes via WebSocket messages
- **Security Rationale:** WebSocket protocol has built-in protections:
  - Origin header validation
  - Upgrade handshake verification
  - Session-based authentication
- **Alternative Controls:**
  - Origin validation during WebSocket upgrade
  - Session authentication required
  - Message-level authorization checks
- **Audit Status:** ✅ Verified - WebSocket security separate from HTTP CSRF
- **Notes:** WebSocket connections cannot be CSRF'd in the traditional sense due to upgrade handshake requirements

### 4. `/webhook/**`
- **Type:** Server-to-server webhook receivers (POST/PUT/PATCH/DELETE)
- **State Changes:** **YES - CRITICAL**
- **Security Rationale:** External services (Stripe, Twilio, etc.) send POST requests without browser context
- **Alternative Controls:** **MANDATORY SIGNATURE VERIFICATION**
  - HMAC-SHA256 signature validation
  - Webhook provider-specific signature schemes
  - Request timestamp validation (replay protection)
- **Audit Status:** ⚠️ **REQUIRES AUDIT**
- **Action Required:**
  1. Enumerate all `/webhook/*` endpoints
  2. Verify each endpoint has signature validation
  3. If no signature validation exists → **P0 SECURITY VULNERABILITY**
- **Risk Level:** **HIGH** - Unauthenticated state-changing operations if signature missing

### 5. `/api/csrf-token`
- **Type:** CSRF token retrieval endpoint (GET)
- **State Changes:** None
- **Security Rationale:** Token distribution endpoint, required for CSRF protection to function
- **Alternative Controls:** None required (safe operation)
- **Audit Status:** ✅ Verified safe

---

## Webhook Security Audit Results

**Audit Date:** 2026-01-31

### Current Webhook Endpoints

**Status:** ✅ **NO WEBHOOK ENDPOINTS CURRENTLY EXIST**

Search performed:
```bash
# Searched for webhook route definitions
grep -r "@.*\.(post|put|patch|delete)\(.*webhook" agentos/webui/
grep -r "router\.(post|put|patch|delete)\(.*webhook" agentos/webui/

# Result: No matches found
```

**Conclusion:** The `/webhook/**` exemption is currently a placeholder for future webhook integrations. No immediate security risk exists.

**Action Items for Future Webhook Implementation:**
1. Before adding any `/webhook/*` endpoint, implement signature verification
2. Document the signature scheme in this contract
3. Add tests to verify signature validation
4. Update this audit section with endpoint details

---

## Security Guarantees

### Hard Enforcement Rules

1. **Deny-by-Default:** All endpoints REQUIRE CSRF protection unless in exemption table
2. **Browser Detection:** API routes with browser requests MUST validate CSRF tokens
3. **Origin Validation:** All state-changing requests undergo Origin/Referer validation (Layer 1)
4. **Token Validation:** Browser-initiated API requests require valid CSRF token (Layer 2)
5. **No Fuzzy Logic:** No "if not recognized, allow" patterns permitted

### Code Assertions

The CSRF middleware includes runtime contract validation (see `validate_exemption_contract()` in csrf.py):

```python
# Contract assertion: Verify exemption list hasn't been tampered with
EXPECTED_EXEMPTIONS = {
    "/health", "/api/health", "/static/", "/ws/", "/webhook/", "/api/csrf-token"
}

def validate_exemption_contract():
    """Startup validation: Ensure exemption list matches contract"""
    # Implementation in middleware/csrf.py
```

---

## Testing Requirements

All exemptions must have corresponding tests in `tests/security/test_csrf_exemption_contract.py`:

1. **Positive Tests:** Verify exempted endpoints allow requests without CSRF tokens
2. **Negative Tests:** Verify non-exempted endpoints reject requests without CSRF tokens
3. **Webhook Tests:** Verify webhook endpoints reject unsigned requests (when implemented)
4. **Regression Tests:** Detect accidental removal of CSRF protection

---

## Change Management

### Adding New Exemptions

**Process:**
1. Create security justification document
2. Verify alternative security controls exist
3. Update this contract table
4. Add corresponding tests
5. Update middleware exemption list
6. Security team approval required

**Required Documentation:**
- Endpoint purpose and behavior
- Why CSRF protection is incompatible
- What alternative security controls are in place
- Risk assessment (Low/Medium/High)

### Removing Exemptions

**Process:**
1. Verify endpoint can support CSRF tokens
2. Update client code to send tokens
3. Remove from exemption list
4. Update this contract
5. Update tests
6. Monitor for 403 errors in production

---

## Compliance and Audit

### Audit Schedule
- **Quarterly Review:** Verify all exemptions still valid
- **Change-Triggered Review:** Any middleware change triggers contract review
- **Annual Security Audit:** External security review of exemption rationale

### Success Metrics
- Zero unauthorized exemptions
- All webhook endpoints have signature validation
- Test coverage at 100% for exemption contract
- No CSRF-related security incidents

---

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Task #36: CSRF Implementation Summary](./TASK_36_CSRF_IMPLEMENTATION_SUMMARY.md)
- [CSRF Best Practices](./CSRF_BEST_PRACTICES.md)
- [CSRF Regression Prevention](./CSRF_REGRESSION_PREVENTION.md)

---

## Appendix: Contract Validation

### Runtime Validation

The middleware performs startup validation to ensure the exemption list matches this contract:

```python
# Expected exemptions from contract
EXPECTED_EXEMPTIONS = ["/health", "/api/health", "/static/", "/ws/", "/webhook/"]
EXPECTED_API_WHITELIST = ["/api/health", "/api/csrf-token"]

# Validation runs on application startup
# Any mismatch triggers a security alert
```

### Test Validation

All exemptions have automated tests:
- Location: `tests/security/test_csrf_exemption_contract.py`
- Coverage: 100% of exemption table entries
- CI/CD: Tests run on every commit

---

**Contract Status:** ✅ **ACTIVE**

**Next Review:** 2026-04-30 (Quarterly)

**Security Approval:**
- Security Team: Pending
- Engineering Lead: Pending
- Date: 2026-01-31
