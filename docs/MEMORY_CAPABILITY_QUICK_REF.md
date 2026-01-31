# Memory Capability Contract - Quick Reference

**Version**: 1.0
**Date**: 2026-02-01
**Full ADR**: [ADR-012-memory-capability-contract.md](./adr/ADR-012-memory-capability-contract.md)

---

## TL;DR

AgentOS now has a **Linux-inspired permission system** for Memory operations. Every Memory operation requires an `agent_id` parameter for permission checks.

---

## 5 Capability Levels

```python
from agentos.core.memory.capabilities import MemoryCapability

CAP_NONE    = MemoryCapability.NONE      # No access
CAP_READ    = MemoryCapability.READ      # Read-only
CAP_PROPOSE = MemoryCapability.PROPOSE   # Can propose (needs approval)
CAP_WRITE   = MemoryCapability.WRITE     # Direct write
CAP_ADMIN   = MemoryCapability.ADMIN     # Full control
```

---

## Quick Capability Guide

### What can each capability do?

| Capability | list | search | get | propose | upsert | delete |
|------------|------|--------|-----|---------|--------|--------|
| NONE       | ❌    | ❌      | ❌   | ❌       | ❌      | ❌      |
| READ       | ✅    | ✅      | ✅   | ❌       | ❌      | ❌      |
| PROPOSE    | ✅    | ✅      | ✅   | ✅       | ❌      | ❌      |
| WRITE      | ✅    | ✅      | ✅   | ✅       | ✅      | ❌      |
| ADMIN      | ✅    | ✅      | ✅   | ✅       | ✅      | ✅      |

**Hierarchy**: Higher capabilities include all lower operations

---

## Agent Classification (Default Capabilities)

### Tier 1: READ-ONLY (CAP_READ)
```python
"query_agent"       # Search/retrieval
"analysis_agent"    # Data analysis
"monitoring_agent"  # System monitoring
"explanation_agent" # Documentation
```

### Tier 2: PROPOSE (CAP_PROPOSE)
```python
"chat_agent"        # Chat with auto-extraction
"extraction_agent"  # Document parsing
"suggestion_agent"  # Recommendations
"learning_agent"    # Learn from interactions
```

### Tier 3: WRITE (CAP_WRITE)
```python
"user_explicit_agent"  # User commands: "remember this"
"system_config"        # System configuration
"import_agent"         # External data import
"task_artifact_agent"  # Task execution artifacts
```

### Tier 4: ADMIN (CAP_ADMIN)
```python
"user:alice"    # Human users (pattern: user:*)
"user:bob"      # All human users have admin
"system"        # System operations
```

---

## Migration Guide

### Old Code (Before ADR-012)
```python
# ❌ Missing agent_id
memory_service.list(scope="global")
memory_service.upsert(memory_item)
memory_service.delete(memory_id)
```

### New Code (After ADR-012)
```python
# ✅ Include agent_id for all operations
memory_service.list(agent_id="query_agent", scope="global")
memory_service.upsert(agent_id="system_config", memory_item=memory_item)
memory_service.delete(agent_id="user:alice", memory_id=memory_id)
```

**Where to get agent_id?**
- From session context: `session.agent_id`
- From task context: `task.agent_id`
- Hardcoded for system operations: `"system"`
- Human users: `f"user:{username}"`

---

## Common Patterns

### Pattern 1: Read-Only Query Agent

```python
# Query agent only reads, never writes
agent_id = "query_agent"

# ✅ Allowed
results = memory_service.list(agent_id=agent_id, scope="global")
matches = memory_service.search(agent_id=agent_id, query="python")
memory = memory_service.get(agent_id=agent_id, memory_id="mem-123")

# ❌ Denied (PermissionDenied raised)
memory_service.upsert(agent_id=agent_id, memory_item={...})
```

### Pattern 2: Chat Agent with Propose Workflow

```python
# Chat agent extracts preference, but cannot directly write
agent_id = "chat_agent"

# User says: "I prefer Python 3.11"
memory_item = {
    "scope": "project",
    "type": "preference",
    "content": {"key": "python_version", "value": "3.11"}
}

# ✅ Create proposal (goes to admin approval queue)
from agentos.core.memory.proposals import propose_memory

proposal_id = propose_memory(
    agent_id=agent_id,
    memory_item=memory_item,
    reason="User mentioned preference in conversation"
)
# Returns: "prop-abc123" (status=pending)

# ❌ Cannot directly write (denied)
memory_service.upsert(agent_id=agent_id, memory_item=memory_item)
```

### Pattern 3: Admin Approving Proposal

```python
# Admin reviews and approves proposal
admin_id = "user:alice"  # Human user has ADMIN capability
proposal_id = "prop-abc123"

# ✅ Approve proposal
from agentos.core.memory.proposals import approve_proposal

memory_id = approve_proposal(
    reviewer_id=admin_id,
    proposal_id=proposal_id,
    reason="Valid preference, approved"
)
# Returns: "mem-xyz789" (now in memory_items)

# ✅ Or reject proposal
from agentos.core.memory.proposals import reject_proposal

reject_proposal(
    reviewer_id=admin_id,
    proposal_id=proposal_id,
    reason="Hallucinated preference, user never said this"
)
```

### Pattern 4: User Explicit Write (Bypass Approval)

```python
# User explicitly says: "Remember I prefer Python 3.11"
agent_id = "user_explicit_agent"  # Has WRITE capability

memory_item = {
    "scope": "project",
    "type": "preference",
    "content": {"key": "python_version", "value": "3.11"}
}

# ✅ Direct write (no approval needed)
memory_id = memory_service.upsert(
    agent_id=agent_id,
    memory_item=memory_item
)
# Immediately written to memory_items
```

### Pattern 5: Admin Operations

```python
# Admin managing capabilities
admin_id = "user:alice"

# ✅ Set agent capability
from agentos.core.memory.admin import set_agent_capability
from agentos.core.memory.capabilities import MemoryCapability

set_agent_capability(
    admin_id=admin_id,
    agent_id="new_query_agent",
    capability=MemoryCapability.READ,
    reason="New query agent for project X"
)

# ✅ Revoke capability
from agentos.core.memory.admin import revoke_capability

revoke_capability(
    admin_id=admin_id,
    agent_id="compromised_agent",
    reason="Security incident, agent compromised"
)

# ✅ Delete memory
memory_service.delete(
    agent_id=admin_id,
    memory_id="mem-old-data"
)
```

---

## Permission Denied Handling

```python
from agentos.core.memory.permission import PermissionDenied

try:
    memory_service.upsert(
        agent_id="query_agent",  # Has READ
        memory_item=memory_item
    )
except PermissionDenied as e:
    print(f"Permission denied: {e}")
    print(f"Agent: {e.agent_id}")
    print(f"Current capability: {e.capability.value}")
    print(f"Required capability: {e.required.value}")
    print(f"Operation: {e.operation}")

# Output:
# Permission denied: Agent 'query_agent' has capability 'read' but operation 'write' requires 'write'
# Agent: query_agent
# Current capability: read
# Required capability: write
# Operation: write
```

---

## Configuration (config/memory_capabilities.yaml)

```yaml
# Set default capabilities
default_capabilities:
  my_new_agent: read
  my_chat_bot: propose

# Pattern-based rules
capability_rules:
  # All users starting with "user:" get admin
  - agent_pattern: "user:*"
    capability: admin
    reason: "Human users have admin access"

  # Agents ending with "_readonly" get read
  - agent_pattern: "*_readonly"
    capability: read
    reason: "Read-only naming convention"
```

---

## Database Tables

### agent_capabilities (Registry)
```sql
SELECT * FROM agent_capabilities WHERE agent_id = 'chat_agent';

-- Result:
-- agent_id     | memory_capability | granted_by | granted_at_ms
-- chat_agent   | propose           | system     | 1706745600000
```

### memory_proposals (Pending Queue)
```sql
SELECT * FROM memory_proposals WHERE status = 'pending';

-- Result:
-- proposal_id | proposed_by | status  | memory_item
-- prop-abc123 | chat_agent  | pending | {"scope": "project", ...}
```

### Pending Proposals View (UI)
```sql
SELECT * FROM pending_proposals;

-- Result:
-- proposal_id | proposed_by | memory_type | memory_key       | memory_value
-- prop-abc123 | chat_agent  | preference  | python_version   | 3.11
```

---

## Checking Agent Capability

### In Python Code

```python
from agentos.core.memory.permission import get_agent_capability

# Get capability
capability = get_agent_capability("chat_agent")
print(capability)  # MemoryCapability.PROPOSE

# Check if operation is allowed
can_read = capability.allows_operation("read")      # True
can_write = capability.allows_operation("write")    # False
can_delete = capability.allows_operation("delete")  # False
```

### In SQL

```sql
-- Get agent capability
SELECT memory_capability
FROM agent_capabilities
WHERE agent_id = 'chat_agent';

-- List all agents with ADMIN capability
SELECT agent_id, granted_by, granted_at_ms
FROM agent_capabilities
WHERE memory_capability = 'admin';

-- Find expired capabilities
SELECT agent_id, memory_capability, expires_at_ms
FROM agent_capabilities
WHERE expires_at_ms IS NOT NULL
  AND expires_at_ms < (strftime('%s', 'now') * 1000);
```

---

## UI Integration

### Pending Proposals Badge

```javascript
// Fetch pending proposals count
fetch('/api/memory/proposals?status=pending')
    .then(res => res.json())
    .then(data => {
        const count = data.proposals.length;
        document.getElementById('proposals-badge').innerText = count;
    });
```

### Approve/Reject Proposal

```javascript
// Approve proposal
fetch(`/api/memory/proposals/${proposalId}/approve`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        reviewer_id: 'user:alice',
        reason: 'Valid preference'
    })
})
.then(res => res.json())
.then(data => {
    console.log('Approved, memory_id:', data.memory_id);
});

// Reject proposal
fetch(`/api/memory/proposals/${proposalId}/reject`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        reviewer_id: 'user:alice',
        reason: 'Hallucinated preference'
    })
})
.then(res => res.json())
.then(data => {
    console.log('Rejected');
});
```

---

## Audit Trail

Every capability check is logged to audit trail:

```python
from agentos.core.audit import get_audit_events

# Get capability check events
events = get_audit_events(
    event_type="MEMORY_CAPABILITY_CHECK",
    limit=100
)

for event in events:
    print(f"{event['payload']['agent_id']} attempted {event['payload']['operation']}")
    print(f"  Capability: {event['payload']['capability']}")
    print(f"  Allowed: {event['payload']['allowed']}")
    print(f"  Time: {event['created_at']}")
```

**Audit Event Structure**:
```json
{
  "event_type": "MEMORY_CAPABILITY_CHECK",
  "level": "info",
  "payload": {
    "agent_id": "query_agent",
    "operation": "write",
    "capability": "read",
    "allowed": false,
    "context": {
      "method": "upsert",
      "memory_type": "preference"
    }
  },
  "created_at": 1706745600
}
```

---

## Testing

### Unit Test Example

```python
import pytest
from agentos.core.memory.permission import check_capability, PermissionDenied
from agentos.core.memory.capabilities import MemoryCapability

def test_read_only_agent_cannot_write():
    """Query agent with READ capability cannot write"""
    with pytest.raises(PermissionDenied) as exc_info:
        check_capability("query_agent", "write")

    assert exc_info.value.agent_id == "query_agent"
    assert exc_info.value.capability == MemoryCapability.READ
    assert exc_info.value.required == MemoryCapability.WRITE

def test_admin_can_delete():
    """Human user with ADMIN capability can delete"""
    result = check_capability("user:alice", "delete")
    assert result is True
```

---

## Troubleshooting

### PermissionDenied Error

**Problem**: `PermissionDenied: Agent 'my_agent' has capability 'read' but operation 'write' requires 'write'`

**Solution**:
1. Check agent's capability: `get_agent_capability("my_agent")`
2. Set correct capability: `set_agent_capability(admin_id, "my_agent", MemoryCapability.WRITE, reason)`
3. Or use correct agent_id for this operation

### Missing agent_id Parameter

**Problem**: `TypeError: list() missing 1 required positional argument: 'agent_id'`

**Solution**: Add `agent_id` parameter to all Memory operations
```python
# Before
memory_service.list(scope="global")

# After
memory_service.list(agent_id="query_agent", scope="global")
```

### Proposal Not Approved

**Problem**: Chat agent proposed memory but it's not showing up in queries

**Reason**: Proposals require admin approval before being written to memory_items

**Solution**:
1. Check pending proposals: `SELECT * FROM pending_proposals`
2. Approve proposal: `approve_proposal(admin_id, proposal_id)`
3. Or use WRITE capability agent to bypass approval

### Unknown Agent Gets NONE

**Problem**: New agent gets NONE capability by default, cannot do anything

**Solution**: Configure default capability in `config/memory_capabilities.yaml`
```yaml
default_capabilities:
  my_new_agent: read  # Or propose/write/admin
```

Or set capability explicitly:
```python
set_agent_capability(
    admin_id="user:admin",
    agent_id="my_new_agent",
    capability=MemoryCapability.READ,
    reason="New agent deployment"
)
```

---

## FAQ

### Q: Do I need to add agent_id to every Memory call?
**A**: Yes. This is a breaking change but necessary for permission control and audit trail.

### Q: What happens if I don't provide agent_id?
**A**: TypeError in strict mode. During migration phase, may fall back to "system" with deprecation warning.

### Q: Can I bypass the permission check?
**A**: No. All operations go through `check_capability()`. Use ADMIN capability for full access.

### Q: How do I get user-explicit memories without approval?
**A**: Use agent_id with WRITE capability (e.g., "user_explicit_agent"). These bypass the proposal workflow.

### Q: Can agents change their own capability?
**A**: No. Only agents with ADMIN capability can modify capabilities (set_agent_capability).

### Q: What if multiple agents have the same agent_id?
**A**: agent_id should be unique per agent instance. If needed, use namespacing: "chat_agent:session-123".

### Q: How long do capabilities last?
**A**: By default, forever. Use `expires_at_ms` for time-limited access.

### Q: Can I have per-scope capabilities?
**A**: Not in v1.0. Future enhancement: scope-based capability overrides.

---

## Best Practices

### ✅ DO

1. **Always provide agent_id** for all Memory operations
2. **Use specific agent IDs** (not generic "agent")
3. **Follow naming conventions**: `user:*` for humans, descriptive names for agents
4. **Configure defaults** in `memory_capabilities.yaml` for new agent types
5. **Review proposals regularly** to prevent queue buildup
6. **Set expiration** for temporary elevated privileges
7. **Check audit trail** when debugging permission issues

### ❌ DON'T

1. **Don't hardcode "system"** everywhere (use specific agent IDs)
2. **Don't skip permission checks** (no direct DB writes)
3. **Don't give everyone ADMIN** (principle of least privilege)
4. **Don't ignore PermissionDenied** (fix capability or use correct agent)
5. **Don't auto-approve proposals** without review (defeats the purpose)
6. **Don't use same agent_id** for different agent instances
7. **Don't bypass audit logging** (always use MemoryService API)

---

## Quick Commands

```bash
# Apply schema migration
agentos db migrate --version 46

# List agent capabilities
sqlite3 ~/.agentos/store/memoryos/db.sqlite \
  "SELECT agent_id, memory_capability FROM agent_capabilities;"

# List pending proposals
sqlite3 ~/.agentos/store/memoryos/db.sqlite \
  "SELECT * FROM pending_proposals;"

# Check audit trail for permission denials
sqlite3 ~/.agentos/store/agentos/db.sqlite \
  "SELECT * FROM task_audits WHERE event_type='MEMORY_CAPABILITY_CHECK' AND level='warning';"
```

---

## Links

- **Full ADR**: [ADR-012-memory-capability-contract.md](./adr/ADR-012-memory-capability-contract.md)
- **Completion Summary**: [TASK_15_COMPLETION_SUMMARY.md](../TASK_15_COMPLETION_SUMMARY.md)
- **Implementation**: Tasks #16-19

---

**Last Updated**: 2026-02-01
**Version**: 1.0
**Status**: Design Complete, Implementation Pending
