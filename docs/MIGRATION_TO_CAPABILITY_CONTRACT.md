# Migration Guide: Memory Capability Contract

## Overview

Tasks 15-19 introduce breaking API changes to MemoryService to implement OS-level permission controls. This guide helps you migrate existing code to the new Memory Capability Contract.

**Timeline Estimate**: 1-2 weeks for full migration and testing

## What Changed?

### API Changes

**Before (Tasks 1-14)**:
```python
memory_service.list(scope="global")
memory_service.upsert(memory_item)
memory_service.delete(memory_id)
```

**After (Tasks 15+)**:
```python
memory_service.list(agent_id="my_agent", scope="global")
memory_service.upsert(agent_id="my_agent", memory_item=memory_item)
memory_service.delete(agent_id="my_agent", memory_id=memory_id)
```

### New Features

1. **Capability-Based Access Control**: 5-tier permission model (NONE < READ < PROPOSE < WRITE < ADMIN)
2. **PermissionDenied Exception**: Raised when agent lacks required capability
3. **Propose Workflow**: New `propose()` method for agents with PROPOSE capability
4. **Audit Trail**: Every capability check is logged
5. **Default Capabilities**: Pattern-based defaults for common agent types

### Why This Change?

**Security**: Prevents unauthorized memory access and corruption
**Accountability**: Complete audit trail of who did what
**Anti-Hallucination**: PROPOSE workflow prevents AI hallucinations from corrupting memory
**Compliance**: Enterprise-grade permission tracking

## Quick Summary

| Change | Impact | Migration Effort |
|--------|--------|------------------|
| `agent_id` parameter required | 🔴 Breaking | Medium - Find and update all calls |
| `PermissionDenied` exception | 🟡 New error type | Low - Add exception handling |
| `propose()` method | 🟢 New feature | Optional - Use for chat agents |
| Agent capability registration | 🟡 New requirement | Low - One-time setup |

## Step-by-Step Migration

### Step 1: Update Method Signatures

**Find and replace pattern** (use your IDE's find-replace with regex):

#### Pattern 1: list()

```regex
# Find:
memory_service\.list\(

# Replace with:
memory_service.list(agent_id="YOUR_AGENT_ID",
```

#### Pattern 2: upsert()

```regex
# Find:
memory_service\.upsert\(

# Replace with:
memory_service.upsert(agent_id="YOUR_AGENT_ID",
```

#### Pattern 3: delete()

```regex
# Find:
memory_service\.delete\(

# Replace with:
memory_service.delete(agent_id="YOUR_AGENT_ID",
```

#### Pattern 4: get()

```regex
# Find:
memory_service\.get\(

# Replace with:
memory_service.get(agent_id="YOUR_AGENT_ID",
```

#### Pattern 5: search()

```regex
# Find:
memory_service\.search\(

# Replace with:
memory_service.search(agent_id="YOUR_AGENT_ID",
```

### Step 2: Determine Appropriate agent_id

For each call, determine the appropriate `agent_id` based on context:

| Context | agent_id Value | Capability | Example |
|---------|---------------|------------|---------|
| **User action (WebUI)** | `f"user:{user_id}"` | ADMIN | `"user:alice"` |
| **System operation** | `"system"` | ADMIN | `"system"` |
| **Chat agent** | `"chat_agent"` | PROPOSE | `"chat_agent"` |
| **Query agent** | `"query_agent"` | READ | `"query_agent"` |
| **Custom agent** | Agent identifier | (varies) | `"etl_agent"` |
| **Test code** | `"test_*"` | WRITE | `"test_my_feature"` |
| **Unknown context** | `"system"` (temporary) | ADMIN | Use during migration only |

### Step 3: Add Exception Handling

Wrap capability-sensitive operations in try-except blocks:

```python
from agentos.core.memory.capabilities import PermissionDenied

# Option 1: Log and skip
try:
    memory_service.upsert(agent_id=agent_id, memory_item=item)
except PermissionDenied as e:
    logger.warning(f"Memory write denied: {e}")

# Option 2: Fallback to propose
try:
    memory_service.upsert(agent_id=agent_id, memory_item=item)
except PermissionDenied:
    proposal_id = memory_service.propose(
        agent_id=agent_id,
        memory_item=item,
        reason="Fallback after write denied"
    )
    logger.info(f"Memory proposed for review: {proposal_id}")

# Option 3: Raise user-friendly error
try:
    memory_service.upsert(agent_id=agent_id, memory_item=item)
except PermissionDenied as e:
    raise ValueError(f"Cannot save memory: {e}")
```

### Step 4: Register Custom Agents

If you have custom agents not covered by default patterns, register them at startup:

```python
# In application initialization (e.g., agentos/core/app_startup.py)

from agentos.core.memory.permission import get_permission_service
from agentos.core.memory.capabilities import MemoryCapability

def register_custom_agents():
    """Register custom agent capabilities at startup."""
    perm_service = get_permission_service()

    # Register your custom agents
    perm_service.register_agent_capability(
        agent_id="etl_agent",
        agent_type="import",
        capability=MemoryCapability.WRITE,
        granted_by="system",
        reason="ETL agent needs write access for data import"
    )

    perm_service.register_agent_capability(
        agent_id="audit_agent",
        agent_type="audit",
        capability=MemoryCapability.READ,
        granted_by="system",
        reason="Audit agent needs read-only access"
    )

# Call during startup
register_custom_agents()
```

### Step 5: Test Thoroughly

```bash
# Run unit tests
pytest tests/unit/core/memory/ -v

# Run integration tests
pytest tests/integration/ -k memory -v

# Check for PermissionDenied in logs
grep "PermissionDenied" logs/agentos.log

# Verify audit trail
sqlite3 data/memoryos.db \
  "SELECT * FROM agent_capability_audit ORDER BY changed_at_ms DESC LIMIT 10"
```

## Code Migration Examples

### Example 1: Simple CRUD Operation

**Before:**
```python
def save_user_preference(preference: dict):
    memory_service = MemoryService()

    memory_item = {
        "scope": "global",
        "type": "preference",
        "content": preference
    }

    memory_id = memory_service.upsert(memory_item)
    return memory_id
```

**After:**
```python
def save_user_preference(user_id: str, preference: dict):
    memory_service = MemoryService()

    memory_item = {
        "scope": "global",
        "type": "preference",
        "content": preference
    }

    try:
        # user:* has ADMIN capability by default
        memory_id = memory_service.upsert(
            agent_id=f"user:{user_id}",
            memory_item=memory_item
        )
        return memory_id

    except PermissionDenied as e:
        logger.error(f"Failed to save preference: {e}")
        raise
```

### Example 2: Chat Agent (Propose Workflow)

**Before:**
```python
def extract_and_save_memory(user_message: str):
    """Extract memory from user message and save."""
    extracted = extract_memory_from_message(user_message)

    memory_id = memory_service.upsert(extracted)

    logger.info(f"Memory saved: {memory_id}")
    return memory_id
```

**After:**
```python
def extract_and_propose_memory(user_message: str):
    """Extract memory from user message and propose for review."""
    extracted = extract_memory_from_message(user_message)

    # Chat agents have PROPOSE capability (requires approval)
    proposal_id = memory_service.propose(
        agent_id="chat_agent",
        memory_item=extracted,
        reason=f"Extracted from: {user_message[:50]}..."
    )

    logger.info(f"Memory proposed for review: {proposal_id}")
    return proposal_id  # ⚠️ Note: returns proposal_id, not memory_id
```

**Important**: Update callers to handle proposal_id:

```python
# Before
memory_id = extract_and_save_memory(message)
print(f"Saved: {memory_id}")

# After
proposal_id = extract_and_propose_memory(message)
print(f"Proposed for review: {proposal_id}")
print("Admin will approve in WebUI")
```

### Example 3: WebUI Handler

**Before:**
```python
@app.route("/api/memory", methods=["POST"])
def create_memory():
    memory_item = request.json

    memory_id = memory_service.upsert(memory_item)

    return {"memory_id": memory_id}
```

**After:**
```python
from flask import session
from agentos.core.memory.capabilities import PermissionDenied

@app.route("/api/memory", methods=["POST"])
def create_memory():
    memory_item = request.json

    # Get user from session
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Not authenticated"}, 401

    try:
        memory_id = memory_service.upsert(
            agent_id=f"user:{user_id}",
            memory_item=memory_item
        )
        return {"memory_id": memory_id}

    except PermissionDenied as e:
        return {"error": str(e)}, 403
```

### Example 4: System Migration Script

**Before:**
```python
def migrate_legacy_memories(legacy_data: list):
    """Migrate legacy memory data."""
    for item in legacy_data:
        memory_service.upsert(item)
        print(f"Migrated: {item['id']}")
```

**After:**
```python
def migrate_legacy_memories(legacy_data: list):
    """Migrate legacy memory data."""
    # Migration scripts use system agent (ADMIN capability)
    for item in legacy_data:
        try:
            memory_service.upsert(
                agent_id="system",
                memory_item=item
            )
            print(f"Migrated: {item['id']}")

        except PermissionDenied as e:
            # Migration should fail fast on permission errors
            logger.error(f"Migration failed for {item['id']}: {e}")
            raise
```

### Example 5: Background Job

**Before:**
```python
def cleanup_old_memories():
    """Background job to cleanup old memories."""
    old_memories = memory_service.list(
        scope="global",
        filters={"created_before": cutoff_date}
    )

    for memory in old_memories:
        memory_service.delete(memory["id"])
```

**After:**
```python
def cleanup_old_memories():
    """Background job to cleanup old memories."""
    # Background jobs use system agent
    old_memories = memory_service.list(
        agent_id="system",
        scope="global",
        filters={"created_before": cutoff_date}
    )

    for memory in old_memories:
        memory_service.delete(
            agent_id="system",
            memory_id=memory["id"]
        )
```

### Example 6: Agent with Fallback Strategy

**Before:**
```python
class SmartAgent:
    def save_insight(self, insight: dict):
        memory_service.upsert(insight)
```

**After:**
```python
class SmartAgent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def save_insight(self, insight: dict):
        """Save insight with automatic fallback to propose."""
        try:
            # Try direct write
            memory_id = memory_service.upsert(
                agent_id=self.agent_id,
                memory_item=insight
            )
            logger.info(f"Insight written: {memory_id}")
            return memory_id

        except PermissionDenied:
            # Fallback to propose
            proposal_id = memory_service.propose(
                agent_id=self.agent_id,
                memory_item=insight,
                reason="Agent insight requires approval"
            )
            logger.info(f"Insight proposed: {proposal_id}")
            return proposal_id
```

## Common Migration Issues

### Issue 1: "agent_id parameter missing"

**Error:**
```python
TypeError: list() missing 1 required positional argument: 'agent_id'
```

**Root Cause:** Old code calling Memory methods without `agent_id` parameter.

**Fix:**
```python
# Before
memories = memory_service.list(scope="global")

# After
memories = memory_service.list(agent_id="system", scope="global")
```

### Issue 2: "PermissionDenied for unknown agent"

**Error:**
```python
PermissionDenied: Agent 'my_new_agent' has capability 'none'
but operation 'list' requires capability >= 'read'
```

**Root Cause:** Agent not registered, defaults to NONE capability.

**Fix:** Register the agent:
```python
from agentos.core.memory.permission import get_permission_service
from agentos.core.memory.capabilities import MemoryCapability

perm_service = get_permission_service()
perm_service.register_agent_capability(
    agent_id="my_new_agent",
    capability=MemoryCapability.READ,  # Or appropriate level
    granted_by="system",
    reason="Initial registration"
)
```

### Issue 3: "Proposal ID returned instead of Memory ID"

**Symptom:** Code expects memory_id but receives proposal_id format.

**Root Cause:** Using `propose()` method (for PROPOSE agents) but expecting immediate write.

**Expected Behavior:** `propose()` returns `proposal_id` (ULID format), not `memory_id`.

**Fix Option 1:** Handle proposals correctly:
```python
result = memory_service.propose(...)

if result.startswith("01"):  # ULID format = proposal_id
    logger.info(f"Awaiting approval: {result}")
else:  # Memory ID
    logger.info(f"Memory written: {result}")
```

**Fix Option 2:** Grant WRITE capability if agent should write directly:
```python
perm_service.register_agent_capability(
    agent_id="my_agent",
    capability=MemoryCapability.WRITE,  # Upgraded from PROPOSE
    granted_by="user:admin",
    reason="Agent needs direct write access"
)
```

### Issue 4: "Tests failing with PermissionDenied"

**Symptom:** Unit tests failing after migration.

**Root Cause:** Test code not using test agent pattern.

**Fix:** Use `test_*` prefix for test agents:
```python
# Before
def test_memory_creation():
    memory_id = memory_service.upsert(
        agent_id="my_agent",
        memory_item={...}
    )

# After
def test_memory_creation():
    memory_id = memory_service.upsert(
        agent_id="test_my_agent",  # ✅ test_* prefix = WRITE capability
        memory_item={...}
    )
```

Or use fixtures to register test agents:

```python
@pytest.fixture
def test_agent_with_write():
    perm_service = get_permission_service()
    perm_service.register_agent_capability(
        agent_id="test_agent",
        capability=MemoryCapability.WRITE,
        granted_by="system"
    )
    return "test_agent"

def test_memory_creation(test_agent_with_write):
    memory_id = memory_service.upsert(
        agent_id=test_agent_with_write,
        memory_item={...}
    )
```

### Issue 5: "Import errors after migration"

**Error:**
```python
ImportError: cannot import name 'PermissionDenied'
```

**Root Cause:** Missing import statement.

**Fix:**
```python
from agentos.core.memory.capabilities import PermissionDenied
```

## Backward Compatibility Strategy

For gradual migration, you can add temporary defaults (⚠️ not recommended for production):

```python
# Temporary wrapper for gradual migration
class BackwardCompatibleMemoryService(MemoryService):
    """
    TEMPORARY: Provides backward compatibility during migration.

    WARNING: This should be removed after migration is complete.
    """

    def upsert(self, agent_id: str = "system", memory_item: dict = None, **kwargs):
        if agent_id == "system" and not kwargs.get("_explicit_system"):
            logger.warning(
                "DEPRECATED: Calling upsert() without explicit agent_id. "
                "This will fail in future versions. "
                f"Caller: {inspect.stack()[1].function}"
            )

        return super().upsert(agent_id=agent_id, memory_item=memory_item, **kwargs)

    # Similar for other methods...

# Use during migration (TEMPORARY)
memory_service = BackwardCompatibleMemoryService()
```

**⚠️ Important**: Remove this wrapper after migration is complete. It bypasses security controls.

## Rollback Plan

If you need to temporarily rollback:

### Option 1: Code Rollback (Recommended)

```bash
# Rollback to pre-capability commit
git revert <task-15-commit>..HEAD

# Or revert specific commits
git revert <task-15-commit> <task-16-commit> <task-17-commit>
```

**Note**: This loses all capability configuration and audit trail.

### Option 2: Database-Only Rollback

Capability tables are separate from memory_items, so you can ignore them temporarily:

```python
# Temporarily bypass capability checks (DANGEROUS)
from agentos.core.memory import permission

class NoOpPermissionService:
    """TEMPORARY: Bypass capability checks."""
    def check_capability(self, *args, **kwargs):
        return True  # Always allow

# Replace global service (TEMPORARY)
permission._permission_service = NoOpPermissionService()
```

**⚠️ DANGER**: This disables all security controls. Only use for emergency rollback.

### Option 3: Grant Universal ADMIN (Not Recommended)

```python
# Grant ADMIN to all agents (DANGEROUS)
perm_service.register_agent_capability(
    agent_id="*",  # Wildcard (if implemented)
    capability=MemoryCapability.ADMIN,
    granted_by="system",
    reason="Emergency rollback"
)
```

**⚠️ DANGER**: This defeats the purpose of capability control.

## Testing Your Migration

### Checklist

- [ ] All Memory operations have `agent_id` parameter
- [ ] Exception handling added for `PermissionDenied`
- [ ] Custom agents registered with appropriate capabilities
- [ ] Chat agents use `propose()` instead of `upsert()`
- [ ] WebUI handlers check user authentication
- [ ] Unit tests updated with test agent IDs
- [ ] Integration tests pass
- [ ] No `PermissionDenied` errors in logs (except expected ones)
- [ ] Audit trail shows capability checks

### Test Commands

```bash
# 1. Run unit tests
pytest tests/unit/core/memory/ -v

# 2. Run integration tests
pytest tests/integration/ -k memory -v

# 3. Check for errors
grep -i "permissiondenied\|missing.*agent_id" logs/agentos.log

# 4. Verify capability registrations
sqlite3 data/memoryos.db \
  "SELECT agent_id, memory_capability, granted_by, reason
   FROM agent_capabilities
   ORDER BY granted_at_ms DESC"

# 5. Check audit trail
sqlite3 data/memoryos.db \
  "SELECT COUNT(*) as total_checks,
          SUM(CASE WHEN allowed THEN 1 ELSE 0 END) as allowed,
          SUM(CASE WHEN allowed THEN 0 ELSE 1 END) as denied
   FROM agent_capability_audit"

# 6. Test propose workflow (if applicable)
pytest tests/integration/test_memory_proposal_workflow.py -v
```

### Manual Testing

**Test 1: User can write memories**
```bash
curl -X POST http://localhost:5000/api/memory \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{
    "scope": "global",
    "type": "fact",
    "content": {"key": "test", "value": "migration_test"}
  }'

# Expected: 200 OK with memory_id
```

**Test 2: Chat agent proposes memory**
```python
from agentos.core.memory.service import MemoryService

memory_service = MemoryService()

proposal_id = memory_service.propose(
    agent_id="chat_agent",
    memory_item={
        "scope": "global",
        "type": "preference",
        "content": {"key": "theme", "value": "dark"}
    },
    reason="Test proposal"
)

print(f"Proposal created: {proposal_id}")
# Expected: proposal_id in ULID format (01HX...)
```

**Test 3: Unknown agent denied**
```python
try:
    memory_service.list(agent_id="unknown_agent", scope="global")
    print("ERROR: Should have been denied")
except PermissionDenied:
    print("✅ Correctly denied unknown agent")
```

## Timeline

**Recommended migration timeline**:

| Week | Activities |
|------|-----------|
| **Week 1** | • Update code (add agent_id parameters)<br>• Add exception handling<br>• Register custom agents |
| **Week 2** | • Update tests<br>• Run test suite<br>• Fix issues |
| **Week 3** | • Deploy to staging<br>• Manual testing<br>• Load testing |
| **Week 4** | • Deploy to production<br>• Monitor logs<br>• Review audit trail |
| **Week 5+** | • Monitor performance<br>• Adjust capabilities as needed<br>• Remove temporary workarounds |

## Getting Help

**If you encounter issues during migration**:

1. **Check logs**:
   ```bash
   tail -f logs/agentos.log | grep -i "permission\|capability"
   ```

2. **Review audit trail**:
   ```bash
   sqlite3 data/memoryos.db \
     "SELECT * FROM agent_capability_audit
      WHERE allowed = 0
      ORDER BY changed_at_ms DESC LIMIT 20"
   ```

3. **Consult documentation**:
   - [User Guide](MEMORY_CAPABILITY_USER_GUIDE.md)
   - [Developer Guide](MEMORY_CAPABILITY_DEVELOPER_GUIDE.md)
   - [ADR-012](adr/ADR-012-memory-capability-contract.md)

4. **Enable debug logging**:
   ```python
   import logging
   logging.getLogger("agentos.core.memory").setLevel(logging.DEBUG)
   ```

5. **File issue** with:
   - Error message and stack trace
   - Relevant code snippet
   - Output of: `sqlite3 data/memoryos.db "SELECT * FROM agent_capabilities WHERE agent_id='your_agent'"`

## Related Documentation

- **[User Guide](MEMORY_CAPABILITY_USER_GUIDE.md)**: End-user documentation
- **[Developer Guide](MEMORY_CAPABILITY_DEVELOPER_GUIDE.md)**: Integration guide for developers
- **[ADR-012](adr/ADR-012-memory-capability-contract.md)**: Architecture decision record
- **[Quick Reference](MEMORY_CAPABILITY_QUICK_REF.md)**: Capability matrix reference

---

**Migration Checklist Summary**:

- [ ] Update all MemoryService calls to include `agent_id`
- [ ] Add `PermissionDenied` exception handling
- [ ] Register custom agents with appropriate capabilities
- [ ] Update chat agents to use `propose()` workflow
- [ ] Update tests with test agent IDs
- [ ] Run full test suite
- [ ] Deploy to staging and test
- [ ] Monitor audit logs
- [ ] Deploy to production
- [ ] Remove temporary workarounds

**Estimated Effort**: 5-10 days for medium-sized codebase
