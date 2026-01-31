# Security Governance System

## Overview

AgentOS implements a comprehensive 6-layer security governance system for all tool invocations (both Extension and MCP tools). This system ensures that every operation is properly vetted, authorized, and audited.

## Design Philosophy

### Core Principles

1. **Security First**: No tool can execute without passing through all security gates
2. **Complete Audit Trail**: Every invocation attempt (success or failure) is logged
3. **Clear Error Messages**: Denials provide actionable reasons
4. **Performance**: Gate checks complete in <10ms
5. **Backward Compatible**: Existing extensions work without modification

### Red Lines (Non-Negotiable)

- ❌ MCP/Extension tools MUST NOT bypass `spec_frozen` gate
- ❌ Direct TaskDB writes/task state changes are FORBIDDEN
- ✅ ALL executions MUST appear in unified audit event stream
- ✅ High-risk tools MUST require Admin Token verification

## The 6-Layer Security Gate System

### Gate 1: Mode Gate

**Purpose**: Prevent side effects during planning phase

**Rules**:
- If `mode == "planning"` AND tool has `side_effect_tags` → **DENY**
- If `mode == "execution"` → **ALLOW** (continue to next gate)

**Example**:
```python
# This will be blocked
invocation = ToolInvocation(
    mode=ExecutionMode.PLANNING,
    # ... other fields
)
# Tool with side_effect_tags=["fs.write"] → DENIED
```

**Rationale**: During planning, agents should only read and analyze, never modify state.

### Gate 2: Spec Frozen Gate

**Purpose**: Ensure execution follows immutable plan

**Rules**:
- If `mode == "execution"`:
  - `spec_frozen` must be `True` → else **DENY**
  - `spec_hash` must exist → else **DENY**
  - If `task_id` exists → verify `spec_frozen=1` in TaskDB → else **DENY**

**Example**:
```python
# This will be blocked
invocation = ToolInvocation(
    mode=ExecutionMode.EXECUTION,
    spec_frozen=False,  # Not frozen!
    # ... other fields
)
# DENIED: "Execution mode requires spec_frozen=True"
```

**Rationale**: Prevents plan tampering during execution (critical for security and reproducibility).

### Gate 3: Project Binding Gate

**Purpose**: Ensure tool execution is associated with a project

**Rules**:
- `project_id` must be set → else **DENY**

**Example**:
```python
# This will be blocked
invocation = ToolInvocation(
    project_id=None,  # No project!
    # ... other fields
)
# DENIED: "Tool invocation must be bound to a project_id"
```

**Rationale**: Enables project-level access control and audit trails.

### Gate 4: Policy Gate

**Purpose**: Enforce organizational policies based on side effects and risk

**Rules**:
- Check side effects against blacklist → if blacklisted → **DENY**
- Default blacklist: `["payments", "cloud.key_delete"]`
- Extensible for custom policies

**Example**:
```python
# This will be blocked
tool = ToolDescriptor(
    side_effect_tags=["payments"],  # Blacklisted!
    # ... other fields
)
# DENIED: "Side effect 'payments' is blacklisted by policy"
```

**Rationale**: Prevent high-consequence operations without explicit approval.

### Gate 5: Admin Token Gate

**Purpose**: Require human approval for critical operations

**Rules**:
- If `tool.risk_level == RiskLevel.CRITICAL` OR `tool.requires_admin_token == True`:
  - `admin_token` must be provided → else **DENY**
  - Token must be valid (validated by `AdminTokenManager`) → else **DENY**

**Example**:
```python
# This will be blocked
tool = ToolDescriptor(
    risk_level=RiskLevel.CRITICAL,  # Requires admin!
    # ... other fields
)

result = router.invoke_tool(
    tool_id,
    invocation,
    admin_token=None  # No token!
)
# DENIED: "Tool requires admin_token for approval"
```

**Rationale**: High-risk operations require explicit human authorization.

### Gate 6: Audit Gate

**Purpose**: Ensure complete audit trail

**Implementation**:
- Before execution: `emit_tool_invocation_start(invocation, tool)`
- After execution: `emit_tool_invocation_end(result, tool, task_id)`
- On policy violation: `emit_policy_violation(invocation, tool, decision, reason)`

**Audit Destinations**:
1. **Python Logger** (structured logging)
2. **task_audits Table** (persistent, queryable)

**Rationale**: Every operation must be traceable for security, compliance, and debugging.

## Admin Token System

### PR-3 Implementation (Simple)

Environment variable-based token validation:

```bash
# Set admin token
export AGENTOS_ADMIN_TOKEN="your-secure-token-here"
```

```python
from agentos.core.capabilities.admin_token import AdminTokenManager

manager = AdminTokenManager()

# Validate token
if manager.validate_token(token):
    print("Authorized!")
```

### Security Features

- **Constant-time comparison**: Prevents timing attacks
- **Simple setup**: Single environment variable
- **No persistence**: Token stored only in memory

### Future Enhancements (PR-4+)

- JWT with expiry
- Token claims (user_id, permissions)
- Token revocation
- Audit trail for token usage

## Audit Trail

### Audit Events

All tool invocations generate the following events:

1. **tool_invocation_start**
   - Timestamp
   - Tool ID and name
   - Actor
   - Mode (planning/execution)
   - Risk level
   - Side effects

2. **tool_invocation_end**
   - Success/failure
   - Duration
   - Actual side effects
   - Error message (if failed)

3. **policy_violation** (HIGH PRIORITY)
   - Tool ID and name
   - Actor
   - Denial reason
   - Risk level
   - Approval context (if applicable)

### Querying Audit Trail

```sql
-- All tool invocations for a task
SELECT * FROM task_audits
WHERE task_id = 'task_123'
AND event_type IN ('tool_invocation_start', 'tool_invocation_end')
ORDER BY created_at;

-- All policy violations
SELECT * FROM task_audits
WHERE event_type = 'policy_violation'
ORDER BY created_at DESC;

-- High-risk tool usage
SELECT * FROM task_audits
WHERE event_type = 'tool_invocation_start'
AND json_extract(payload, '$.risk_level') = 'CRITICAL'
ORDER BY created_at DESC;
```

## Configuration

### Policy Engine Configuration

```python
from agentos.core.capabilities.policy import ToolPolicyEngine
from agentos.core.capabilities.admin_token import validate_admin_token

# Create policy engine with custom settings
policy = ToolPolicyEngine(
    task_db_path=Path("/path/to/taskdb.sqlite"),
    admin_token_validator=validate_admin_token
)

# Customize blacklist
policy.blacklisted_effects = [
    "payments",
    "cloud.key_delete",
    "cloud.resource_delete",  # Add custom
]
```

### Tool Risk Levels

When defining tools, use appropriate risk levels:

```python
from agentos.core.capabilities.capability_models import (
    ToolDescriptor,
    RiskLevel
)

# Low risk: Read-only, no side effects
low_risk_tool = ToolDescriptor(
    risk_level=RiskLevel.LOW,
    side_effect_tags=[],
    # ...
)

# Medium risk: Limited side effects, reversible
med_risk_tool = ToolDescriptor(
    risk_level=RiskLevel.MED,
    side_effect_tags=["fs.write"],
    # ...
)

# High risk: Significant side effects
high_risk_tool = ToolDescriptor(
    risk_level=RiskLevel.HIGH,
    side_effect_tags=["fs.delete", "network.http"],
    # ...
)

# Critical risk: Dangerous operations
critical_tool = ToolDescriptor(
    risk_level=RiskLevel.CRITICAL,
    side_effect_tags=["cloud.resource_delete"],
    requires_admin_token=True,
    # ...
)
```

## Usage Examples

### Basic Tool Invocation

```python
from agentos.core.capabilities import ToolRouter, CapabilityRegistry
from agentos.core.capabilities.policy import ToolPolicyEngine
from agentos.core.capabilities.capability_models import (
    ToolInvocation,
    ExecutionMode
)

# Setup
registry = CapabilityRegistry(ext_registry)
policy = ToolPolicyEngine()
router = ToolRouter(registry, policy_engine=policy)

# Create invocation
invocation = ToolInvocation(
    invocation_id="inv_123",
    tool_id="ext:tools.postman:get",
    task_id="task_456",
    project_id="proj_789",
    spec_hash="abc123",
    spec_frozen=True,
    mode=ExecutionMode.EXECUTION,
    inputs={"url": "https://api.example.com"},
    actor="user@example.com"
)

# Invoke tool (all gates checked automatically)
result = await router.invoke_tool(
    "ext:tools.postman:get",
    invocation
)

if result.success:
    print(f"Success: {result.payload}")
else:
    print(f"Failed: {result.error}")
```

### Critical Tool with Admin Token

```python
import os

# Set admin token (in production, use secure secret management)
os.environ["AGENTOS_ADMIN_TOKEN"] = "admin-secret-token"

# Create invocation for critical tool
invocation = ToolInvocation(
    invocation_id="inv_789",
    tool_id="ext:cloud.manager:delete_resource",
    task_id="task_critical",
    project_id="proj_789",
    spec_hash="def456",
    spec_frozen=True,
    mode=ExecutionMode.EXECUTION,
    inputs={"resource_id": "res_123"},
    actor="admin@example.com"
)

# Invoke with admin token
result = await router.invoke_tool(
    "ext:cloud.manager:delete_resource",
    invocation,
    admin_token="admin-secret-token"  # Required!
)
```

### Planning Mode (Safe Exploration)

```python
# Planning mode - only read-only tools allowed
invocation = ToolInvocation(
    invocation_id="inv_plan",
    tool_id="ext:tools.reader:read_file",
    task_id="task_planning",
    project_id="proj_789",
    spec_hash="",  # No spec hash in planning
    spec_frozen=False,  # Not frozen in planning
    mode=ExecutionMode.PLANNING,  # Planning mode
    inputs={"path": "/data/file.txt"},
    actor="agent"
)

# This will succeed (read-only tool)
result = await router.invoke_tool("ext:tools.reader:read_file", invocation)

# This will fail (has side effects)
invocation.tool_id = "ext:tools.writer:write_file"
result = await router.invoke_tool("ext:tools.writer:write_file", invocation)
# Error: "Tool has side effects and cannot be executed in planning mode"
```

## Troubleshooting

### Common Errors

#### "Execution mode requires spec_frozen=True"

**Cause**: Trying to execute without frozen spec

**Solution**:
```python
# Freeze spec before execution
invocation.spec_frozen = True
invocation.spec_hash = compute_spec_hash(spec)
```

#### "Tool requires admin_token for approval"

**Cause**: Critical tool invoked without admin token

**Solution**:
```python
# Provide admin token
result = await router.invoke_tool(
    tool_id,
    invocation,
    admin_token=os.environ["AGENTOS_ADMIN_TOKEN"]
)
```

#### "Side effect 'X' is blacklisted by policy"

**Cause**: Tool uses blacklisted side effect

**Solution**:
1. Review if operation is truly necessary
2. If necessary, modify policy blacklist:
```python
policy.blacklisted_effects.remove("X")
```

#### "Tool invocation must be bound to a project_id"

**Cause**: Missing project_id

**Solution**:
```python
invocation.project_id = "proj_123"
```

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("agentos.core.capabilities").setLevel(logging.DEBUG)
```

Check audit trail:
```sql
SELECT * FROM task_audits
WHERE task_id = 'your_task_id'
ORDER BY created_at DESC
LIMIT 10;
```

## Best Practices

1. **Always set appropriate risk levels** when defining tools
2. **Use planning mode for exploration**, execution mode for real operations
3. **Freeze specs before execution** to ensure reproducibility
4. **Review audit trail** regularly for security monitoring
5. **Rotate admin tokens** periodically
6. **Test gate behavior** with unit tests when adding new tools
7. **Document side effects** clearly in tool descriptors

## Performance Considerations

- Gate checks: <10ms per invocation
- Audit writes: Async, non-blocking
- Cache: 60-second TTL for tool discovery
- Database: SQLite with WAL mode for concurrent reads

## Future Enhancements

- **PR-4**: JWT-based admin tokens with expiry
- **PR-5**: Per-project policy customization
- **PR-6**: Rate limiting for high-frequency tools
- **PR-7**: Real-time policy violation alerts
- **PR-8**: Automated security reports

## References

- [Capability Models](../core/capabilities/capability_models.py)
- [Policy Engine](../core/capabilities/policy.py)
- [Audit System](../core/capabilities/audit.py)
- [Tool Router](../core/capabilities/router.py)
- [Admin Token Manager](../core/capabilities/admin_token.py)
