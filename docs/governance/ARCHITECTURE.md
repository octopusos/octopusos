# Governance vNext Architecture

## Overview

Governance vNext is a comprehensive governance framework for AgentOS that provides unified control over capability invocations across Extensions and MCP servers.

### Core Subsystems

```
┌─────────────────────────────────────────────────────────────┐
│                   Governance vNext                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Quota      │  │  Trust Tier  │  │  Provenance  │     │
│  │   System     │  │              │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│        │                  │                  │             │
│        └──────────────────┴──────────────────┘             │
│                          │                                 │
│                    ┌─────▼─────┐                          │
│                    │  Policy   │                          │
│                    │  Engine   │                          │
│                    └─────┬─────┘                          │
│                          │                                 │
└──────────────────────────┼─────────────────────────────────┘
                           │
                    ┌──────▼───────┐
                    │ Tool Router  │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
         ┌────▼────┐              ┌────▼────┐
         │Extension│              │   MCP   │
         │  Tools  │              │  Tools  │
         └─────────┘              └─────────┘
```

## Subsystem Descriptions

### 1. Quota System

**Purpose**: Resource management and rate limiting

**Key Features**:
- Calls per minute limiting
- Concurrent execution control
- Runtime duration tracking
- Cost unit management

**Implementation**:
- `agentos/core/capabilities/quota_manager.py`
- `agentos/core/capabilities/governance_models/quota.py`

**Example**:
```python
quota = CapabilityQuota(
    quota_id="mcp:cloud:*",
    limit=QuotaLimit(
        calls_per_minute=100,
        max_concurrent=5,
        runtime_ms_per_minute=60000
    )
)
```

### 2. Trust Tier

**Purpose**: Security classification and policy differentiation

**Trust Levels**:
- **T0**: Local Extension (highest trust)
- **T1**: Local MCP (same host)
- **T2**: Remote MCP (LAN/private network)
- **T3**: Cloud MCP (internet, lowest trust)

**Implementation**:
- `agentos/core/capabilities/trust_tier_defaults.py`
- Integrated into `agentos/core/capabilities/policy.py`

**Automatic Policy Application**:
```python
# T0 Extension
- Risk: LOW
- Quota: 1000 calls/min
- Admin Token: Not required
- Side Effects: Allowed

# T3 Cloud MCP
- Risk: CRITICAL
- Quota: 10 calls/min
- Admin Token: Required for side effects
- Side Effects: Requires explicit approval
```

### 3. Provenance

**Purpose**: Traceability and audit trail

**Tracked Information**:
- Capability identity (source, version)
- Execution environment (host, platform, Python version)
- Invocation context (task, project, spec hash)
- Trust tier classification

**Implementation**:
- `agentos/core/capabilities/governance_models/provenance.py`
- `agentos/core/capabilities/provenance_utils.py`
- `agentos/core/capabilities/provenance_validator.py`

**Usage Scenarios**:
```python
# Replay: Reconstruct execution environment
# Compare: Analyze cross-environment behavior
# Audit: Complete responsibility chain
# Decision: Filter results by trust tier
```

## Integration Architecture

### Policy Engine (7-Layer Gate System)

```
Tool Invocation Request
         │
         ▼
┌────────────────────┐
│ 0. Enabled Gate    │ ◄─── Tool enabled check
└────────┬───────────┘
         ▼
┌────────────────────┐
│ 1. Mode Gate       │ ◄─── Planning blocks side effects
└────────┬───────────┘
         ▼
┌────────────────────┐
│ 2. Spec Frozen     │ ◄─── Execution requires frozen spec
└────────┬───────────┘
         ▼
┌────────────────────┐
│ 3. Project Binding │ ◄─── Requires project_id
└────────┬───────────┘
         ▼
┌────────────────────┐
│ 4. Quota Gate      │ ◄─── [Quota System Integration]
└────────┬───────────┘       Checks: calls, concurrency, runtime, cost
         ▼
┌────────────────────┐
│ 5. Policy Gate     │ ◄─── [Trust Tier Integration]
└────────┬───────────┘       Applies: risk policies, side effects blacklist
         ▼
┌────────────────────┐
│ 6. Admin Token     │ ◄─── [Trust Tier Integration]
└────────┬───────────┘       Requires token for high-risk operations
         ▼
┌────────────────────┐
│ 7. Audit Gate      │ ◄─── Emit audit events
└────────┬───────────┘
         ▼
    Tool Execution
         │
         ▼
┌────────────────────┐
│ Attach Provenance  │ ◄─── [Provenance Integration]
└────────────────────┘       Adds complete traceability info
```

### Data Flow

```
1. Tool Invocation Created
   └─→ ToolInvocation {
         tool_id, mode, spec_frozen,
         project_id, inputs, actor
       }

2. Router Receives Request
   ├─→ Generate ProvenanceStamp
   │   └─→ Capture: source, version, env, trust_tier
   │
   ├─→ Policy Check (7 gates)
   │   ├─→ Gate 4: QuotaManager.check_quota()
   │   ├─→ Gate 5: Apply trust_tier policies
   │   └─→ Gate 6: Check trust_tier admin requirements
   │
   └─→ If allowed:
       ├─→ Update quota (concurrent +1)
       ├─→ Execute tool
       ├─→ Update quota (concurrent -1, add runtime)
       ├─→ Attach provenance to result
       └─→ Emit audit events (with provenance)

3. Result Returned
   └─→ ToolResult {
         success, payload,
         provenance ◄─── Complete traceability
       }
```

## Key Design Principles

### 1. Zero Invasion

**Planner**: Not modified
**MCP/Extension**: No governance awareness required

All governance logic lives in the Capability layer.

### 2. Automatic Application

```python
# Extension automatically gets T0
tool = registry.get_tool("ext:local:cmd")
assert tool.trust_tier == TrustTier.T0

# Cloud MCP automatically gets T3
tool = registry.get_tool("mcp:https://cloud.com:api")
assert tool.trust_tier == TrustTier.T3
```

### 3. Composable Policies

```python
# Each gate is independent
# Gates compose into complete policy
policy_check = (
    enabled_gate and
    mode_gate and
    spec_frozen_gate and
    project_binding_gate and
    quota_gate and        # ← Quota System
    policy_gate and       # ← Trust Tier
    admin_token_gate      # ← Trust Tier
)
```

### 4. Transparent Traceability

```python
# Provenance automatically attached
result = await router.invoke_tool(tool_id, invocation)

# Can immediately trace
assert result.provenance.capability_id == tool_id
assert result.provenance.trust_tier is not None
assert result.provenance.execution_env is not None
```

## Extension Points

### 1. Custom Quota Policies

```python
class CustomQuotaManager(QuotaManager):
    def apply_dynamic_quota(self, tool_id, user_tier):
        # Adjust quota based on user subscription tier
        pass
```

### 2. Custom Trust Tiers

```python
# Define organization-specific tiers
class OrgTrustTier:
    INTERNAL = "internal"
    PARTNER = "partner"
    PUBLIC = "public"
```

### 3. Custom Provenance Validators

```python
class ComplianceValidator(ProvenanceValidator):
    def validate_gdpr_compliance(self, provenance):
        # Ensure GDPR requirements met
        pass
```

## Performance

### Overhead

- **Quota Check**: O(1) memory lookup
- **Trust Tier Application**: O(1) table lookup
- **Provenance Generation**: O(1) data collection

**Total per invocation**: < 1ms

### Scalability

- **In-memory quota state**: Supports thousands of quotas
- **Stateless provenance**: No accumulation overhead
- **Policy caching**: Reuses policy decisions when safe

## Testing

### Test Coverage

- **Quota System**: 10 tests
- **Trust Tier**: 17 tests
- **Provenance**: 8 tests
- **Integration**: 11 tests

**Total**: 46 tests (100% pass rate)

### Verification

```bash
./scripts/verify_governance.sh
# Output: ✅ FINAL RESULT: PASS (46/46 tests)
```

## Related Documents

- [Quota System Design](./QUOTA_SYSTEM.md)
- [Trust Tier Topology](./TRUST_TIER.md)
- [Provenance Tracking](./PROVENANCE.md)
- [Policy Engine Details](./POLICY_ENGINE.md)
- [Integration Guide](./INTEGRATION.md)

## Version

- **Version**: 1.0
- **Status**: Production Ready
- **Last Updated**: 2026-01-31
