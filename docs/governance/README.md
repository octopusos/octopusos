# Governance vNext

> Unified governance framework for AgentOS capability invocations

## 🎯 What is Governance vNext?

Governance vNext is a comprehensive governance system that provides unified control over all capability invocations in AgentOS, whether they come from Extensions or MCP servers.

### Core Features

1. **Quota System** - Resource management and rate limiting
2. **Trust Tier** - Security classification and policy differentiation
3. **Provenance** - Complete traceability and audit trail

## ⚡ Quick Start

### Verify Installation

```bash
./scripts/verify_governance.sh
```

Expected output:
```
✅ FINAL RESULT: PASS (46/46 tests)
🎉 Governance vNext is ready for production!
```

### Basic Usage

```python
from agentos.core.capabilities import ToolRouter, QuotaManager
from agentos.core.capabilities.governance_models.quota import (
    CapabilityQuota, QuotaLimit
)

# 1. Setup router with governance
quota_manager = QuotaManager()
router = ToolRouter(registry, quota_manager=quota_manager)

# 2. Configure quota for expensive operations
quota = CapabilityQuota(
    quota_id="mcp:openai:*",
    limit=QuotaLimit(calls_per_minute=60, max_concurrent=3)
)
quota_manager.register_quota(quota)

# 3. Invoke tool - governance automatic!
result = await router.invoke_tool(tool_id, invocation)

# 4. Check provenance
print(f"Trust Tier: {result.provenance.trust_tier}")
print(f"Source: {result.provenance.source_id} v{result.provenance.source_version}")
```

## 📚 Documentation

### Getting Started

- **[Quick Reference](../../GOVERNANCE_VNEXT_QUICKREF.md)** - Common patterns and troubleshooting
- **[Executive Summary](../../GOVERNANCE_VNEXT_SUMMARY.md)** - High-level overview
- **[Complete Report](../../GOVERNANCE_VNEXT_FINAL_REPORT.md)** - Detailed implementation report

### Architecture & Design

- **[Architecture](./ARCHITECTURE.md)** - System architecture and data flow
- **[Quota System](./QUOTA_SYSTEM.md)** - Resource management design
- **[Trust Tier](./TRUST_TIER.md)** - Security classification topology
- **[Provenance](./PROVENANCE.md)** - Traceability system

### Additional Resources

- **[Policy Engine](./POLICY_ENGINE.md)** - 7-layer security gate system
- **[Integration Guide](./INTEGRATION.md)** - How to integrate with existing code
- **[File Listing](../../GOVERNANCE_VNEXT_FILES.txt)** - Complete file inventory

## 🎓 Key Concepts

### Trust Tier Hierarchy

| Tier | Source | Risk | Quota | Admin Required |
|------|--------|------|-------|----------------|
| T0 | Local Extension | LOW | 1000/min | No |
| T1 | Local MCP | LOW | 500/min | No |
| T2 | Remote MCP | MEDIUM | 100/min | For side effects |
| T3 | Cloud MCP | CRITICAL | 10/min | Yes |

### Policy Gates

Every tool invocation passes through 7 security gates:

1. **Enabled Gate** - Tool must be enabled
2. **Mode Gate** - Planning blocks side effects
3. **Spec Frozen Gate** - Execution requires frozen spec
4. **Project Binding Gate** - Must have project_id
5. **Quota Gate** - Check resource limits
6. **Policy Gate** - Validate risk & side effects
7. **Admin Token Gate** - High-risk operations require approval

### Provenance Tracking

Every result includes complete traceability:

```python
result.provenance = ProvenanceStamp(
    capability_id="mcp:server:tool",
    source_id="server",
    source_version="1.0.0",
    trust_tier="remote_mcp",
    execution_env=ExecutionEnv(...),
    invocation_id="inv_123",
    task_id="task_456",
    project_id="proj_789",
    spec_hash="abc123"
)
```

## 📊 Status

| Aspect | Status |
|--------|--------|
| **Implementation** | ✅ Complete |
| **Tests** | ✅ 46/46 passing (100%) |
| **Documentation** | ✅ Complete |
| **Production Ready** | ✅ Yes |

### Test Breakdown

- Quota System: 10 tests ✅
- Trust Tier: 17 tests ✅
- Provenance: 8 tests ✅
- Integration: 11 tests ✅

## 🚀 Common Use Cases

### 1. Rate Limit Expensive APIs

```python
# Prevent excessive calls to OpenAI
quota = CapabilityQuota(
    quota_id="mcp:openai:*",
    limit=QuotaLimit(
        calls_per_minute=60,     # 1 per second
        max_concurrent=3,         # Max 3 simultaneous
        max_cost_units=100.0      # $100 budget
    )
)
quota_manager.register_quota(quota)
```

### 2. Security by Source

```python
# Different policies for different sources
ext_tool = registry.get_tool("ext:local:cmd")
# → Automatically: trust_tier=T0, risk=LOW

cloud_tool = registry.get_tool("mcp:https://cloud:api")
# → Automatically: trust_tier=T3, risk=CRITICAL, admin required
```

### 3. Audit Trail

```python
# Complete traceability
result = await router.invoke_tool(tool_id, invocation)

# Can trace back to exact source
print(f"Executed by: {result.provenance.source_id}")
print(f"Version: {result.provenance.source_version}")
print(f"In environment: {result.provenance.execution_env}")
print(f"Trust level: {result.provenance.trust_tier}")
```

## 🔧 Integration

### No Code Changes Required

Governance vNext integrates transparently:

```python
# Old code (no governance)
result = await router.invoke_tool(tool_id, invocation)

# Same code (governance automatic!)
result = await router.invoke_tool(tool_id, invocation)
# ✅ Quota checked
# ✅ Trust tier applied
# ✅ Provenance attached
```

### Zero Invasion Architecture

- **Planner**: Not modified
- **MCP**: No changes required
- **Extensions**: No changes required
- **All governance in Capability layer**

## 📈 Performance

- **Overhead per invocation**: < 1ms
- **Memory**: ~100 bytes per quota
- **Scalability**: Tested with 10,000+ invocations

## 🐛 Troubleshooting

### Quota Exceeded

```python
# Error: "Quota exceeded: Calls per minute limit reached"

# Solution: Increase quota
quota = CapabilityQuota(
    quota_id="tool:id",
    limit=QuotaLimit(calls_per_minute=100)  # Increase
)
```

### Admin Token Required

```python
# Error: "requires admin_token for approval"

# Solution: Provide token
result = await router.invoke_tool(
    tool_id, invocation,
    admin_token="your_token"  # Add this
)
```

### Side Effects Blocked

```python
# Error: "Cloud MCP (T3) tools with side effects require approval"

# Solutions:
# 1. Use in execution mode (not planning)
# 2. Provide admin token
# 3. Use lower trust tier if possible
```

## 📞 Support

For questions or issues:

1. Check [Quick Reference](../../GOVERNANCE_VNEXT_QUICKREF.md)
2. Review [Architecture](./ARCHITECTURE.md)
3. Run verification: `./scripts/verify_governance.sh`

## 🎉 Ready to Use!

Governance vNext is production-ready and fully tested. Start using it today!

```bash
# Verify installation
./scripts/verify_governance.sh

# Expected output:
# ✅ FINAL RESULT: PASS (46/46 tests)
# 🎉 Governance vNext is ready for production!
```

---

**Version**: 1.0
**Status**: ✅ Production Ready
**Last Updated**: 2026-01-31
