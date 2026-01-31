# Memory Capability System - User Guide

## Overview

AgentOS Memory uses an OS-level permission system to control which agents can read, propose, write, or delete memories. This prevents unauthorized access and memory corruption, implementing a principle similar to Linux capabilities (CAP_*).

**Key Benefit**: Prevents AI hallucinations from corrupting your memory system while maintaining auditability and control.

## Capability Levels

AgentOS Memory implements a hierarchical 5-tier capability model:

| Level | Operations | Use Cases | Access Level |
|-------|-----------|-----------|--------------|
| **NONE** | No access | Untrusted agents, disabled agents | ⛔ Complete lockout |
| **READ** | View memories only | Query agents, analysis agents | 🔍 Query-only |
| **PROPOSE** | Suggest memories (requires approval) | Chat agents, extraction agents | 💡 Propose + Read |
| **WRITE** | Direct write access | System config, import agents | ✏️ Write + Propose + Read |
| **ADMIN** | Full control (delete, manage permissions) | Human users, admins | 👑 Full control |

**Hierarchy**: `NONE < READ < PROPOSE < WRITE < ADMIN`

Higher levels inherit all permissions from lower levels (e.g., WRITE can also read and propose).

## Default Capabilities

AgentOS ships with secure defaults based on agent types:

### Tier 1: READ-ONLY Agents
- `query_agent` → **READ**
- `analysis_agent` → **READ**
- `monitoring_agent` → **READ**
- `explanation_agent` → **READ**
- `*_readonly` (pattern) → **READ**

### Tier 2: PROPOSE Agents (Require Approval)
- `chat_agent` → **PROPOSE**
- `extraction_agent` → **PROPOSE**
- `suggestion_agent` → **PROPOSE**
- `learning_agent` → **PROPOSE**

### Tier 3: WRITE Agents (Direct Write)
- `user_explicit_agent` → **WRITE**
- `system_config` → **WRITE**
- `import_agent` → **WRITE**
- `task_artifact_agent` → **WRITE**
- `test_*` (pattern) → **WRITE**

### Tier 4: ADMIN Agents (Full Control)
- `user:*` (pattern) → **ADMIN** (all human users have admin access)
- `system` → **ADMIN**

### Unknown Agents
- **Default → NONE** (deny by default for security)

## Propose Workflow

### Why Propose?

Chat agents with PROPOSE capability cannot directly write memories. This prevents AI hallucinations from corrupting your memory system.

**Example Scenario**:
```
User: "I live in Paris"
Chat Agent: Extracts memory: {"type": "fact", "content": {"key": "user_location", "value": "Paris"}}
```

Without PROPOSE workflow:
- ❌ Memory written immediately (what if agent misunderstood?)
- ❌ Hallucinations can corrupt memory
- ❌ No human verification

With PROPOSE workflow:
- ✅ Memory proposed for review
- ✅ Admin can verify before approval
- ✅ Complete audit trail
- ✅ Hallucinations stay in proposal queue

### How It Works

```
┌────────────────────────────────────────────────────────────┐
│ 1. Agent Proposes Memory                                   │
│    - Agent: chat_agent (PROPOSE capability)                │
│    - Creates proposal in pending state                     │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────┐
│ 2. Admin Reviews in WebUI                                  │
│    - Navigate to "📋 Proposals" page                       │
│    - Review pending proposals                              │
│    - View context: agent, reason, proposed content         │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────┐
│ 3. Admin Approves or Rejects                               │
│    - ✅ Approve: Memory written to memory_items            │
│    - ❌ Reject: Proposal marked rejected (with reason)     │
│    - Full audit trail preserved                            │
└────────────────────────────────────────────────────────────┘
```

### Creating Proposals (Agent Code)

```python
from agentos.core.memory.service import MemoryService

memory_service = MemoryService()

# Chat agent proposes memory
proposal_id = memory_service.propose(
    agent_id="chat_agent",
    memory_item={
        "scope": "global",
        "type": "preference",
        "content": {
            "key": "preferred_name",
            "value": "Alice"
        }
    },
    reason="User said: 'call me Alice'"
)

print(f"Proposal created: {proposal_id}")
# Output: Proposal created: 01HX123ABC...
```

### Reviewing Proposals (WebUI)

**Step 1: Navigate to Proposals**
1. Open AgentOS WebUI
2. Click "📋 Proposals" in the sidebar
3. Filter by "Pending" status

**Step 2: Review Proposal Details**
Each proposal displays:
- **Proposed By**: Agent that created the proposal
- **Proposed At**: Timestamp
- **Memory Type**: preference, fact, preference, etc.
- **Content**: Full memory item content
- **Reason**: Why agent proposed this memory
- **Confidence**: Agent's confidence score (0.0-1.0)

**Step 3: Approve or Reject**
1. Click "✅ Approve" or "❌ Reject"
2. Provide reason (required for rejection, optional for approval)
3. Submission triggers:
   - **Approved**: Memory written to `memory_items` table
   - **Rejected**: Proposal marked rejected, memory NOT written
   - **Audit**: Full audit event logged

### Reviewing Proposals (API)

**List pending proposals:**
```bash
curl http://localhost:5000/api/memory/proposals?status=pending
```

**Approve proposal:**
```bash
curl -X POST http://localhost:5000/api/memory/proposals/{proposal_id}/approve \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "user:alice",
    "reason": "Verified with user context"
  }'
```

**Reject proposal:**
```bash
curl -X POST http://localhost:5000/api/memory/proposals/{proposal_id}/reject \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "user:alice",
    "reason": "Incorrect extraction - user actually meant Berlin"
  }'
```

## Granting Capabilities

### Via Configuration (Recommended)

Create or edit `config/memory_capabilities.yaml`:

```yaml
# Default capabilities for specific agent types
default_capabilities:
  my_custom_agent: write
  data_sync_agent: write
  audit_agent: read

# Pattern-based capability rules
capability_rules:
  - agent_pattern: "audit_*"
    capability: read
    reason: "Audit agents need read access only"

  - agent_pattern: "etl_*"
    capability: write
    reason: "ETL agents need write access for data import"

  - agent_pattern: "reporting_*"
    capability: read
    reason: "Reporting agents are read-only"
```

### Programmatically

```python
from agentos.core.memory.permission import get_permission_service
from agentos.core.memory.capabilities import MemoryCapability

perm_service = get_permission_service()

# Register capability
perm_service.register_agent_capability(
    agent_id="my_custom_agent",
    agent_type="custom",
    capability=MemoryCapability.WRITE,
    granted_by="user:admin",
    reason="Needs write access for data integration"
)

# With expiration (time-limited access)
from agentos.core.time import utc_now_ms

expires_in_7_days = utc_now_ms() + (7 * 24 * 60 * 60 * 1000)

perm_service.register_agent_capability(
    agent_id="temp_import_agent",
    agent_type="import",
    capability=MemoryCapability.WRITE,
    granted_by="user:admin",
    reason="Temporary access for data migration",
    expires_at_ms=expires_in_7_days
)
```

### Via CLI (if available)

```bash
# Grant capability
agentos memory grant-capability my_agent --level write --reason "Data integration needs"

# List agent capabilities
agentos memory list-capabilities

# Revoke capability (set to NONE)
agentos memory revoke-capability my_agent
```

## Checking Current Capabilities

### WebUI

1. Navigate to **Settings > Agents**
2. View "Memory Capability" column in agent list
3. Click agent name to see:
   - Current capability
   - Granted by
   - Granted at timestamp
   - Expiration (if applicable)
   - Grant reason
   - Capability history

### API

**Get agent capability:**
```bash
curl http://localhost:5000/api/memory/capabilities/my_agent
```

**Response:**
```json
{
  "agent_id": "my_agent",
  "agent_type": "custom",
  "memory_capability": "write",
  "granted_by": "user:admin",
  "granted_at_ms": 1704067200000,
  "expires_at_ms": null,
  "reason": "Needs write access for integration"
}
```

### Programmatically

```python
from agentos.core.memory.permission import get_permission_service

service = get_permission_service()

# Get capability
capability = service.get_agent_capability("my_agent")
print(f"Agent has: {capability.value}")
# Output: Agent has: write

# Check if can perform operation
can_write = capability.can_perform("upsert")
print(f"Can write: {can_write}")
# Output: Can write: True
```

## Audit Trail

All capability checks are logged to provide complete visibility into memory access patterns.

### View Audit Events

**Programmatically:**
```python
from agentos.core.audit import get_audit_events

# Get recent capability checks
events = get_audit_events(
    event_type="MEMORY_CAPABILITY_CHECK",
    limit=100
)

for event in events:
    print(f"{event['timestamp']}: {event['agent_id']} "
          f"attempted {event['operation']}: "
          f"{'✅ ALLOWED' if event['allowed'] else '❌ DENIED'}")
```

**Via API:**
```bash
curl "http://localhost:5000/api/audit/events?type=MEMORY_CAPABILITY_CHECK&limit=100"
```

**Sample Output:**
```
2024-01-01 10:23:45: chat_agent attempted list: ✅ ALLOWED
2024-01-01 10:23:50: chat_agent attempted upsert: ❌ DENIED
2024-01-01 10:23:51: chat_agent attempted propose: ✅ ALLOWED
2024-01-01 10:24:10: user:alice attempted delete: ✅ ALLOWED
```

### Audit Event Schema

Each capability check generates an audit event:

```json
{
  "event_type": "MEMORY_CAPABILITY_CHECK",
  "timestamp_ms": 1704067200000,
  "agent_id": "chat_agent",
  "operation": "upsert",
  "capability": "propose",
  "allowed": false,
  "context": {
    "method": "upsert",
    "memory_type": "preference",
    "scope": "global"
  },
  "level": "warning"
}
```

## Troubleshooting

### "Permission Denied" Error

**Error Message:**
```
PermissionDenied: Agent 'my_agent' has capability 'read'
but operation 'upsert' requires capability >= 'write'
```

**Diagnosis:**
- Agent attempted an operation beyond its capability level
- In this example: Agent has READ but tried to WRITE

**Solutions:**

1. **Grant higher capability** (if agent should have write access):
   ```python
   perm_service.register_agent_capability(
       agent_id="my_agent",
       capability=MemoryCapability.WRITE,
       granted_by="user:admin",
       reason="Agent needs write access"
   )
   ```

2. **Use propose() instead** (if agent should go through approval):
   ```python
   # Instead of:
   memory_service.upsert(agent_id="my_agent", memory_item=item)

   # Use:
   proposal_id = memory_service.propose(
       agent_id="my_agent",
       memory_item=item,
       reason="Extracted from user input"
   )
   ```

### Proposal Not Appearing in WebUI

**Symptoms:**
- Created proposal via API
- Not visible in WebUI "Proposals" page

**Checklist:**

1. **Verify agent has PROPOSE capability**:
   ```python
   cap = perm_service.get_agent_capability("my_agent")
   print(cap)  # Should be >= PROPOSE
   ```

2. **Check proposal was created successfully**:
   ```bash
   curl "http://localhost:5000/api/memory/proposals?status=pending"
   ```

3. **Verify filter settings in WebUI**:
   - Ensure "Status" filter is set to "Pending"
   - Check "Proposed By" filter is not excluding your agent

4. **Check logs**:
   ```bash
   grep "Memory proposal created" /var/log/agentos/agentos.log
   ```

### Unknown Agent Getting NONE Capability

**Symptom:**
```
PermissionDenied: Agent 'new_agent' has capability 'none'
```

**Explanation:**
This is **expected behavior**. Unknown agents default to NONE for security (deny by default).

**Solution:**
Register the agent with appropriate capability:

```python
perm_service.register_agent_capability(
    agent_id="new_agent",
    capability=MemoryCapability.PROPOSE,  # Or appropriate level
    granted_by="system",
    reason="Initial registration"
)
```

### Capability Expired

**Symptom:**
```
WARNING: Agent my_agent capability expired, reverting to default
```

**Explanation:**
Agent's time-limited capability has expired.

**Solution:**
Re-grant capability (optionally with new expiration):

```python
perm_service.register_agent_capability(
    agent_id="my_agent",
    capability=MemoryCapability.WRITE,
    granted_by="user:admin",
    reason="Renewed access",
    expires_at_ms=None  # Permanent, or set new expiration
)
```

## Best Practices

### 1. Principle of Least Privilege

Grant the **minimum necessary capability** for each agent:

```python
# ✅ Good: Query agent only needs READ
perm_service.register_agent_capability(
    agent_id="query_agent",
    capability=MemoryCapability.READ,
    granted_by="system",
    reason="Read-only access for queries"
)

# ❌ Bad: Query agent given ADMIN (overprivileged)
perm_service.register_agent_capability(
    agent_id="query_agent",
    capability=MemoryCapability.ADMIN,  # ⚠️ Too much power!
    granted_by="system"
)
```

### 2. Use PROPOSE for AI Agents

AI agents (chat, extraction, learning) should use PROPOSE, not WRITE:

```python
# ✅ Good: Chat agent proposes, human approves
capability=MemoryCapability.PROPOSE

# ❌ Bad: Chat agent writes directly (hallucinations!)
capability=MemoryCapability.WRITE
```

### 3. Regular Audits

Review capability audit log monthly:

```python
# Get denied access attempts
events = get_audit_events(
    event_type="MEMORY_CAPABILITY_CHECK",
    filters={"allowed": False},
    limit=500
)

# Analyze patterns
denied_agents = {}
for event in events:
    agent = event["agent_id"]
    denied_agents[agent] = denied_agents.get(agent, 0) + 1

print("Top denied agents:")
for agent, count in sorted(denied_agents.items(), key=lambda x: -x[1])[:10]:
    print(f"  {agent}: {count} denials")
```

### 4. Document Reasons

Always provide clear reasons when granting capabilities:

```python
# ✅ Good: Clear reason
perm_service.register_agent_capability(
    agent_id="etl_agent",
    capability=MemoryCapability.WRITE,
    granted_by="user:admin",
    reason="ETL agent needs write access for nightly data import from CRM"
)

# ❌ Bad: No reason
perm_service.register_agent_capability(
    agent_id="etl_agent",
    capability=MemoryCapability.WRITE,
    granted_by="user:admin",
    reason=None  # ⚠️ Future admins won't understand why
)
```

### 5. Time-Limited Access

Use expiration for temporary access:

```python
from agentos.core.time import utc_now_ms

# Temporary access for data migration
expires_in_24h = utc_now_ms() + (24 * 60 * 60 * 1000)

perm_service.register_agent_capability(
    agent_id="migration_agent",
    capability=MemoryCapability.WRITE,
    granted_by="user:admin",
    reason="One-time data migration from legacy system",
    expires_at_ms=expires_in_24h
)
```

## FAQ

### Q: Can I bypass capability checks for testing?

**A:** Yes, use the `test_*` agent prefix:

```python
# Test agents automatically get WRITE capability
memory_service.upsert(
    agent_id="test_my_feature",  # Prefix with "test_"
    memory_item={"scope": "global", ...}
)
```

This is safe because test agents are only used in test environments.

### Q: How do I revoke a capability?

**A:** Set capability to NONE or let it expire:

```python
# Method 1: Set to NONE
perm_service.register_agent_capability(
    agent_id="old_agent",
    capability=MemoryCapability.NONE,
    granted_by="user:admin",
    reason="Agent decommissioned"
)

# Method 2: Set short expiration (immediate revocation)
perm_service.register_agent_capability(
    agent_id="old_agent",
    capability=MemoryCapability.READ,
    granted_by="user:admin",
    expires_at_ms=utc_now_ms()  # Expires immediately
)
```

### Q: Can agents change their own capabilities?

**A:** No. Only agents with ADMIN capability can modify capabilities, and agents cannot grant themselves ADMIN.

The only exception is the `system` pseudo-agent, which has permanent ADMIN capability for bootstrapping.

### Q: What happens if an agent's capability expires?

**A:** The system reverts to the default capability for that agent type:

```python
# Before expiration: custom WRITE capability
capability = perm_service.get_agent_capability("my_agent")
# Returns: MemoryCapability.WRITE

# After expiration: reverts to default
capability = perm_service.get_agent_capability("my_agent")
# Returns: MemoryCapability.NONE (or pattern-based default)
```

### Q: How does capability checking impact performance?

**A:** Capability checks are lightweight:

- **Each check**: <10ms (database lookup + audit)
- **Audit logging**: Async, non-blocking (minimal overhead)
- **High throughput**: >50 checks/second verified in performance tests

For high-throughput operations, consider batch processing to amortize the cost.

**Note**: Current implementation queries the database for each capability check to ensure freshness (no caching). Future versions may add optional caching for extreme performance scenarios.

### Q: Can I see who approved a proposal?

**A:** Yes, check the `memory_proposals` table or use the API:

```bash
curl "http://localhost:5000/api/memory/proposals/{proposal_id}"
```

Response includes:
```json
{
  "proposal_id": "01HX123...",
  "proposed_by": "chat_agent",
  "proposed_at_ms": 1704067200000,
  "status": "approved",
  "reviewed_by": "user:alice",
  "reviewed_at_ms": 1704067500000,
  "review_reason": "Verified with user context"
}
```

## Related Documentation

- **[Developer Guide](MEMORY_CAPABILITY_DEVELOPER_GUIDE.md)**: For developers integrating capability checks
- **[Migration Guide](MIGRATION_TO_CAPABILITY_CONTRACT.md)**: For upgrading existing code
- **[ADR-012](adr/ADR-012-memory-capability-contract.md)**: Architecture decision record
- **[Quick Reference](MEMORY_CAPABILITY_QUICK_REF.md)**: Capability matrix and operation reference

## Support

For issues or questions:
1. Check logs: `/var/log/agentos/agentos.log`
2. Review audit trail: `curl http://localhost:5000/api/audit/events?type=MEMORY_CAPABILITY_CHECK`
3. Consult [Troubleshooting](#troubleshooting) section above
4. File issue on GitHub (if public repo) or contact AgentOS support
