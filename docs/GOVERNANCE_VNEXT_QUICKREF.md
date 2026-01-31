# Governance vNext - Quick Reference

## ⚡ TL;DR

**Status**: ✅ Production Ready
**Tests**: 46/46 passed (100%)
**Verify**: `./scripts/verify_governance.sh`

## 🎯 What It Does

Three governance systems working together:

1. **Quota**: Limits how many times tools can be called
2. **Trust Tier**: Different security for different sources
3. **Provenance**: Complete traceability of results

## 📦 Key Files

```bash
# Implementation
agentos/core/capabilities/quota_manager.py
agentos/core/capabilities/trust_tier_defaults.py
agentos/core/capabilities/governance_models/provenance.py
agentos/core/capabilities/policy.py
agentos/core/capabilities/router.py

# Tests
tests/core/capabilities/test_quota.py              # 10 tests
tests/core/capabilities/test_trust_tier.py         # 17 tests
tests/core/capabilities/test_provenance.py         # 8 tests
tests/integration/governance/test_governance_integration_simple.py  # 11 tests

# Docs
docs/governance/ARCHITECTURE.md
GOVERNANCE_VNEXT_FINAL_REPORT.md
GOVERNANCE_VNEXT_SUMMARY.md
```

## 🚀 Quick Usage

### 1. Limit API Calls

```python
from agentos.core.capabilities.quota_manager import QuotaManager
from agentos.core.capabilities.governance_models.quota import (
    CapabilityQuota, QuotaLimit
)

quota_manager = QuotaManager()

# Limit to 60 calls/minute
quota = CapabilityQuota(
    quota_id="mcp:openai:*",
    limit=QuotaLimit(calls_per_minute=60)
)
quota_manager.register_quota(quota)
```

### 2. Check Tool Trust Level

```python
from agentos.core.capabilities import CapabilityRegistry

registry = CapabilityRegistry(ext_registry)
tool = registry.get_tool("mcp:cloud:api")

# Automatically assigned based on source
print(tool.trust_tier)  # TrustTier.T3 (Cloud MCP)
```

### 3. Trace Results

```python
result = await router.invoke_tool(tool_id, invocation)

# Provenance automatically attached
print(f"Source: {result.provenance.source_id}")
print(f"Version: {result.provenance.source_version}")
print(f"Trust: {result.provenance.trust_tier}")
print(f"Env: {result.provenance.execution_env}")
```

## 🎓 Trust Tier Hierarchy

| Tier | Source | Risk | Quota | Admin Token |
|------|--------|------|-------|-------------|
| **T0** | Local Extension | LOW | 1000/min | No |
| **T1** | Local MCP | LOW | 500/min | No |
| **T2** | Remote MCP | MED | 100/min | For side effects |
| **T3** | Cloud MCP | CRITICAL | 10/min | Yes |

## 🔒 Policy Gates

Every tool invocation passes through 7 gates:

1. **Enabled Gate**: Tool is enabled
2. **Mode Gate**: Planning blocks side effects
3. **Spec Frozen Gate**: Execution requires frozen spec
4. **Project Binding Gate**: Requires project_id
5. **Quota Gate**: Check resource limits ← Quota System
6. **Policy Gate**: Risk & side effects ← Trust Tier
7. **Admin Token Gate**: High-risk approval ← Trust Tier

## 📊 Test Breakdown

```
Quota System:     10 tests  ✅
Trust Tier:       17 tests  ✅
Provenance:        8 tests  ✅
Integration:      11 tests  ✅
──────────────────────────────
TOTAL:            46 tests  ✅
```

## 🔍 Common Queries

### Check if quota exceeded

```python
result = quota_manager.check_quota("tool:my_tool")
if not result.allowed:
    print(f"Quota exceeded: {result.reason}")
```

### Filter results by trust tier

```python
from agentos.core.capabilities.provenance_utils import filter_results_by_trust_tier
from agentos.core.capabilities.capability_models import TrustTier

# Only use high-trust results
high_trust = filter_results_by_trust_tier(results, TrustTier.T1)
```

### Verify result origin

```python
from agentos.core.capabilities.provenance_utils import verify_result_origin

is_valid = verify_result_origin(
    result,
    expected_source_id="local_mcp",
    expected_trust_tier=TrustTier.T1
)
```

## 🐛 Troubleshooting

### Quota exceeded error

```python
# Problem: "Quota exceeded: Calls per minute limit reached"
# Solution: Increase quota or wait for window reset

quota = CapabilityQuota(
    quota_id="tool:my_tool",
    limit=QuotaLimit(calls_per_minute=100)  # Increase
)
```

### Admin token required

```python
# Problem: "requires admin_token for approval"
# Solution: Provide admin token

result = await router.invoke_tool(
    tool_id,
    invocation,
    admin_token="your_token_here"  # Add this
)
```

### Side effects blocked

```python
# Problem: "Cloud MCP (T3) tools with side effects require explicit approval"
# Solution: Either:
# 1. Don't use side effects in planning mode
# 2. Provide admin token
# 3. Use lower trust tier (T0/T1) if possible
```

## 📝 Validation Commands

```bash
# Verify everything works
./scripts/verify_governance.sh

# Run specific subsystem
pytest tests/core/capabilities/test_quota.py -v
pytest tests/core/capabilities/test_trust_tier.py -v
pytest tests/core/capabilities/test_provenance.py -v

# Run integration tests
pytest tests/integration/governance/ -v
```

## 📚 Learn More

- **Complete Report**: `GOVERNANCE_VNEXT_FINAL_REPORT.md`
- **Architecture**: `docs/governance/ARCHITECTURE.md`
- **Summary**: `GOVERNANCE_VNEXT_SUMMARY.md`

## ✅ DoD Checklist

- [x] Quota limits calls correctly
- [x] Trust tier auto-applies policies
- [x] Provenance enables traceability
- [x] Audit contains governance info
- [x] Replay/compare/override possible

## 🎉 Status: READY FOR MERGE

All tests pass, documentation complete, ready for production use!

---

**Version**: 1.0
**Date**: 2026-01-31
**Status**: ✅ Production Ready
