# Memory Capability System - Developer Guide

## Architecture Overview

The Memory Capability System implements OS-level permission control for Memory operations, inspired by Linux capabilities (CAP_*).

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Client Layer                                               │
│  - WebUI (JavaScript)                                       │
│  - CLI (Python)                                             │
│  - Agent Code (Python)                                      │
└────────────────┬────────────────────────────────────────────┘
                 │ agent_id + operation
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  Memory Service (agentos/core/memory/service.py)            │
│                                                              │
│  Methods:                                                    │
│  - list(agent_id, ...)        → READ                        │
│  - get(agent_id, memory_id)   → READ                        │
│  - search(agent_id, ...)      → READ                        │
│  - propose(agent_id, ...)     → PROPOSE                     │
│  - upsert(agent_id, ...)      → WRITE                       │
│  - delete(agent_id, ...)      → ADMIN                       │
└────────────────┬────────────────────────────────────────────┘
                 │ check_capability(agent_id, operation)
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  Permission Service (agentos/core/memory/permission.py)     │
│                                                              │
│  Core Functions:                                             │
│  - check_capability(agent_id, operation) → bool/raises      │
│  - get_agent_capability(agent_id) → MemoryCapability        │
│  - register_agent_capability(...)                           │
│                                                              │
│  Capability Resolution:                                      │
│  1. Check agent_capabilities table                          │
│  2. Check expiration                                         │
│  3. Apply default based on agent_id pattern                 │
│  4. Fall back to NONE (deny by default)                     │
└────────────────┬────────────────────────────────────────────┘
                 │ SQL queries
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  Database (memoryos.db)                                     │
│                                                              │
│  Tables:                                                     │
│  - agent_capabilities: Current capability grants            │
│  - agent_capability_audit: Capability change history        │
│  - memory_proposals: Pending/approved/rejected proposals    │
│  - memory_items: Actual memory storage                      │
└─────────────────────────────────────────────────────────────┘
```

### Capability Matrix

```python
# agentos/core/memory/capabilities.py

CAPABILITY_MATRIX = {
    MemoryCapability.NONE: set(),

    MemoryCapability.READ: {
        "list", "search", "get", "build_context"
    },

    MemoryCapability.PROPOSE: {
        # Inherits READ operations
        "list", "search", "get", "build_context",
        # Plus PROPOSE operations
        "propose"
    },

    MemoryCapability.WRITE: {
        # Inherits READ + PROPOSE operations
        "list", "search", "get", "build_context", "propose",
        # Plus WRITE operations
        "upsert", "update"
    },

    MemoryCapability.ADMIN: {
        # Inherits all above operations
        "list", "search", "get", "build_context", "propose", "upsert", "update",
        # Plus ADMIN operations
        "delete", "set_capability", "approve_proposal", "reject_proposal"
    }
}
```

### Data Flow: Memory Write Operation

```
1. Agent calls MemoryService.upsert(agent_id="chat_agent", memory_item={...})
   │
   ↓
2. MemoryService calls permission_service.check_capability("chat_agent", "upsert")
   │
   ↓
3. PermissionService:
   a. Queries agent_capabilities table for "chat_agent"
   b. Result: capability = PROPOSE
   c. Checks if "upsert" in CAPABILITY_MATRIX[PROPOSE]
   d. Result: False (upsert requires WRITE)
   e. Logs audit event: {agent_id: "chat_agent", operation: "upsert", allowed: false}
   f. Raises PermissionDenied exception
   │
   ↓
4. Exception propagates to agent code
   │
   ↓
5. Agent catches exception and falls back to propose():
   memory_service.propose(agent_id="chat_agent", memory_item={...})
   │
   ↓
6. Proposal created in memory_proposals table
   │
   ↓
7. Admin reviews and approves proposal
   │
   ↓
8. Approved proposal → memory written to memory_items table
```

## Integrating Capability Checks

### New Agent Implementation

Every agent that interacts with Memory must pass `agent_id` to all Memory operations:

```python
from agentos.core.memory.service import MemoryService
from agentos.core.memory.capabilities import PermissionDenied

class MyCustomAgent:
    """Example agent with proper capability handling."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.memory_service = MemoryService()

    def read_memories(self, scope: str) -> list:
        """
        Read memories (requires READ capability).

        Returns:
            List of memory items, or empty list if permission denied
        """
        try:
            memories = self.memory_service.list(
                agent_id=self.agent_id,
                scope=scope
            )
            return memories

        except PermissionDenied as e:
            # Handle permission error gracefully
            print(f"Access denied: {e}")
            return []

    def save_memory(self, memory_item: dict) -> str:
        """
        Save memory with automatic fallback to propose.

        Strategy:
        1. Try direct write (requires WRITE capability)
        2. If denied, fallback to propose (requires PROPOSE capability)
        3. If both fail, raise exception

        Returns:
            memory_id (if written) or proposal_id (if proposed)
        """
        try:
            # Attempt direct write (WRITE capability)
            memory_id = self.memory_service.upsert(
                agent_id=self.agent_id,
                memory_item=memory_item
            )
            print(f"Memory written: {memory_id}")
            return memory_id

        except PermissionDenied as e:
            # Fallback to propose (PROPOSE capability)
            try:
                proposal_id = self.memory_service.propose(
                    agent_id=self.agent_id,
                    memory_item=memory_item,
                    reason=f"Agent {self.agent_id} attempted write but lacks WRITE capability"
                )
                print(f"Memory proposed for review: {proposal_id}")
                return proposal_id

            except PermissionDenied as e2:
                # Agent lacks both WRITE and PROPOSE
                raise ValueError(
                    f"Agent {self.agent_id} cannot save memories: {e2}"
                )

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete memory (requires ADMIN capability).

        Returns:
            True if deleted, False if permission denied
        """
        try:
            self.memory_service.delete(
                agent_id=self.agent_id,
                memory_id=memory_id
            )
            return True

        except PermissionDenied as e:
            print(f"Cannot delete: {e}")
            return False
```

### Registering Agent at Startup

Register custom agents with appropriate capabilities at application startup:

```python
# agentos/core/app_startup.py or similar

from agentos.core.memory.permission import get_permission_service
from agentos.core.memory.capabilities import MemoryCapability
import logging

logger = logging.getLogger(__name__)

def register_custom_agents():
    """Register custom agent capabilities at application startup."""
    perm_service = get_permission_service()

    # Register custom agents
    agents_to_register = [
        {
            "agent_id": "etl_import_agent",
            "agent_type": "import",
            "capability": MemoryCapability.WRITE,
            "reason": "ETL agent needs write access for data import"
        },
        {
            "agent_id": "audit_query_agent",
            "agent_type": "audit",
            "capability": MemoryCapability.READ,
            "reason": "Audit agent needs read-only access"
        },
        {
            "agent_id": "smart_assistant",
            "agent_type": "chat",
            "capability": MemoryCapability.PROPOSE,
            "reason": "Assistant proposes memories for user approval"
        }
    ]

    for agent_config in agents_to_register:
        try:
            perm_service.register_agent_capability(
                agent_id=agent_config["agent_id"],
                agent_type=agent_config["agent_type"],
                capability=agent_config["capability"],
                granted_by="system",
                reason=agent_config["reason"]
            )
            logger.info(f"Registered {agent_config['agent_id']} with {agent_config['capability'].value} capability")

        except Exception as e:
            logger.error(f"Failed to register {agent_config['agent_id']}: {e}")

# Call during application initialization
if __name__ == "__main__":
    register_custom_agents()
```

## Migration Guide

### Breaking Changes (Tasks 15-19)

**All MemoryService methods now require `agent_id` parameter**:

```python
# BEFORE (Tasks 1-14) ❌
memory_service.list(scope="global")
memory_service.upsert(memory_item)
memory_service.delete(memory_id)

# AFTER (Tasks 15+) ✅
memory_service.list(agent_id="my_agent", scope="global")
memory_service.upsert(agent_id="my_agent", memory_item=memory_item)
memory_service.delete(agent_id="my_agent", memory_id=memory_id)
```

### Migration Steps

#### Step 1: Find All MemoryService Calls

```bash
# Find all Memory operation calls
grep -r "memory_service\.\(list\|upsert\|delete\|get\|search\)" . \
    --include="*.py" \
    --exclude-dir=venv \
    --exclude-dir=node_modules
```

#### Step 2: Add agent_id Parameter

For each call, determine the appropriate `agent_id`:

| Context | agent_id Value | Example |
|---------|---------------|---------|
| User action (WebUI) | `f"user:{user_id}"` | `"user:alice"` |
| System operation | `"system"` | `"system"` |
| Chat agent | `"chat_agent"` | `"chat_agent"` |
| Custom agent | Agent identifier | `"etl_agent"` |
| Test code | `"test_*"` | `"test_my_feature"` |

**Example migration:**

```python
# BEFORE ❌
def save_user_preference(preference: dict):
    memory_service = MemoryService()

    memory_item = {
        "scope": "global",
        "type": "preference",
        "content": preference
    }

    memory_id = memory_service.upsert(memory_item)
    return memory_id

# AFTER ✅
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

#### Step 3: Add Exception Handling

Wrap capability-sensitive operations in try-except blocks:

```python
from agentos.core.memory.capabilities import PermissionDenied

try:
    memory_service.upsert(agent_id=agent_id, memory_item=item)

except PermissionDenied as e:
    # Option 1: Log and skip
    logger.warning(f"Memory write denied: {e}")

    # Option 2: Fallback to propose
    proposal_id = memory_service.propose(
        agent_id=agent_id,
        memory_item=item,
        reason="Fallback after write denied"
    )

    # Option 3: Raise user-friendly error
    raise ValueError(f"Cannot save memory: insufficient permissions ({e})")
```

#### Step 4: Register Custom Agents

If you have custom agents not covered by default patterns:

```python
from agentos.core.memory.permission import get_permission_service
from agentos.core.memory.capabilities import MemoryCapability

# At application startup
perm_service = get_permission_service()

perm_service.register_agent_capability(
    agent_id="my_custom_agent",
    agent_type="custom",
    capability=MemoryCapability.PROPOSE,  # Or appropriate level
    granted_by="system",
    reason="Initial registration"
)
```

#### Step 5: Test Thoroughly

```bash
# Run unit tests
pytest tests/unit/core/memory/

# Run integration tests
pytest tests/integration/

# Check for PermissionDenied in logs
grep "PermissionDenied" logs/agentos.log

# Verify audit trail
sqlite3 data/memoryos.db "SELECT * FROM agent_capability_audit ORDER BY changed_at_ms DESC LIMIT 10"
```

### Migration Examples

#### Example 1: WebUI Handler

```python
# BEFORE ❌
@app.route("/api/memory", methods=["POST"])
def create_memory():
    memory_item = request.json
    memory_id = memory_service.upsert(memory_item)
    return {"memory_id": memory_id}

# AFTER ✅
@app.route("/api/memory", methods=["POST"])
def create_memory():
    from flask import session

    memory_item = request.json
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

#### Example 2: Chat Agent

```python
# BEFORE ❌
def extract_and_save_memory(user_message: str):
    extracted = extract_memory_from_message(user_message)
    memory_id = memory_service.upsert(extracted)
    return memory_id

# AFTER ✅
def extract_and_propose_memory(user_message: str):
    extracted = extract_memory_from_message(user_message)

    # Chat agents use PROPOSE capability
    proposal_id = memory_service.propose(
        agent_id="chat_agent",
        memory_item=extracted,
        reason=f"Extracted from: {user_message[:50]}..."
    )

    logger.info(f"Memory proposed for review: {proposal_id}")
    return proposal_id  # Note: returns proposal_id, not memory_id
```

#### Example 3: System Migration Script

```python
# BEFORE ❌
def migrate_legacy_memories(legacy_data: list):
    for item in legacy_data:
        memory_service.upsert(item)

# AFTER ✅
def migrate_legacy_memories(legacy_data: list):
    # Migration scripts use system agent (ADMIN capability)
    for item in legacy_data:
        try:
            memory_service.upsert(
                agent_id="system",
                memory_item=item
            )
        except PermissionDenied as e:
            logger.error(f"Migration failed for item {item.get('id')}: {e}")
            raise  # Migration should fail fast
```

## Testing

### Unit Tests

```python
# tests/unit/core/memory/test_capability_integration.py

import pytest
from pathlib import Path
from agentos.core.memory.permission import MemoryPermissionService
from agentos.core.memory.service import MemoryService
from agentos.core.memory.capabilities import MemoryCapability, PermissionDenied


@pytest.fixture
def test_db(tmp_path):
    """Create temporary test database."""
    return tmp_path / "test.db"


def test_read_agent_can_list_memories(test_db):
    """READ agent can list memories."""
    # Setup
    perm_service = MemoryPermissionService(db_path=test_db)
    perm_service.register_agent_capability(
        "read_agent",
        MemoryCapability.READ,
        "system"
    )

    memory_service = MemoryService(db_path=test_db)

    # Test
    memories = memory_service.list(agent_id="read_agent", scope="global")

    # Should not raise exception
    assert isinstance(memories, list)


def test_read_agent_cannot_write(test_db):
    """READ agent cannot write memories."""
    # Setup
    perm_service = MemoryPermissionService(db_path=test_db)
    perm_service.register_agent_capability(
        "read_agent",
        MemoryCapability.READ,
        "system"
    )

    memory_service = MemoryService(db_path=test_db)

    # Test
    with pytest.raises(PermissionDenied) as exc_info:
        memory_service.upsert(
            agent_id="read_agent",
            memory_item={
                "scope": "global",
                "type": "fact",
                "content": {"key": "test", "value": "data"}
            }
        )

    # Verify exception details
    assert exc_info.value.agent_id == "read_agent"
    assert exc_info.value.operation == "upsert"
    assert exc_info.value.capability == MemoryCapability.READ
    assert exc_info.value.required == MemoryCapability.WRITE


def test_propose_agent_workflow(test_db):
    """PROPOSE agent creates proposal, ADMIN approves."""
    # Setup
    perm_service = MemoryPermissionService(db_path=test_db)
    perm_service.register_agent_capability(
        "propose_agent",
        MemoryCapability.PROPOSE,
        "system"
    )

    memory_service = MemoryService(db_path=test_db)

    # Agent proposes memory
    proposal_id = memory_service.propose(
        agent_id="propose_agent",
        memory_item={
            "scope": "global",
            "type": "preference",
            "content": {"key": "theme", "value": "dark"}
        },
        reason="User preference"
    )

    assert proposal_id is not None
    assert proposal_id.startswith("01")  # ULID format

    # Verify proposal is pending
    from agentos.core.memory.proposals import get_proposal_service
    proposal_service = get_proposal_service()
    proposal = proposal_service.get_proposal(proposal_id)

    assert proposal["status"] == "pending"
    assert proposal["proposed_by"] == "propose_agent"

    # Admin approves proposal
    memory_id = proposal_service.approve_proposal(
        reviewer_id="user:admin",
        proposal_id=proposal_id,
        reason="Verified"
    )

    # Verify memory was written
    memory = memory_service.get(agent_id="user:admin", memory_id=memory_id)
    assert memory is not None
    assert memory["content"]["value"] == "dark"


def test_write_agent_can_write_directly(test_db):
    """WRITE agent can write memories directly (no proposal)."""
    # Setup
    perm_service = MemoryPermissionService(db_path=test_db)
    perm_service.register_agent_capability(
        "write_agent",
        MemoryCapability.WRITE,
        "system"
    )

    memory_service = MemoryService(db_path=test_db)

    # Write directly
    memory_id = memory_service.upsert(
        agent_id="write_agent",
        memory_item={
            "scope": "global",
            "type": "fact",
            "content": {"key": "api_key", "value": "secret"}
        }
    )

    # Verify memory written
    memory = memory_service.get(agent_id="write_agent", memory_id=memory_id)
    assert memory is not None
    assert memory["content"]["value"] == "secret"


def test_unknown_agent_denied(test_db):
    """Unknown agents default to NONE capability (denied)."""
    memory_service = MemoryService(db_path=test_db)

    # Unknown agent
    with pytest.raises(PermissionDenied) as exc_info:
        memory_service.list(agent_id="unknown_agent", scope="global")

    assert exc_info.value.capability == MemoryCapability.NONE
```

### Integration Tests

```python
# tests/integration/test_memory_capability_e2e.py

def test_complete_propose_workflow_e2e(test_db):
    """End-to-end test of propose workflow."""

    # 1. Chat agent proposes memory
    memory_service = MemoryService(db_path=test_db)

    proposal_id = memory_service.propose(
        agent_id="chat_agent",  # Default PROPOSE capability
        memory_item={
            "scope": "project",
            "type": "preference",
            "content": {"key": "language", "value": "Python"},
            "project_id": "proj-123"
        },
        reason="User said: I prefer Python"
    )

    # 2. Verify proposal created
    from agentos.core.memory.proposals import get_proposal_service
    proposal_service = get_proposal_service()

    proposals = proposal_service.list_proposals(status="pending")
    assert len(proposals) == 1
    assert proposals[0]["proposal_id"] == proposal_id

    # 3. Admin approves
    memory_id = proposal_service.approve_proposal(
        reviewer_id="user:admin",  # Default ADMIN capability
        proposal_id=proposal_id,
        reason="Verified from chat context"
    )

    # 4. Verify memory written
    memory = memory_service.get(agent_id="user:admin", memory_id=memory_id)
    assert memory["content"]["value"] == "Python"

    # 5. Verify proposal status updated
    proposal = proposal_service.get_proposal(proposal_id)
    assert proposal["status"] == "approved"
    assert proposal["reviewed_by"] == "user:admin"
    assert proposal["result_memory_id"] == memory_id

    # 6. Verify audit trail
    from agentos.core.audit import get_audit_events

    events = get_audit_events(
        event_type="MEMORY_CAPABILITY_CHECK",
        limit=100
    )

    # Should have audit events for:
    # - propose operation (chat_agent)
    # - approve_proposal operation (user:admin)
    # - get operation (user:admin)
    assert len(events) >= 3
```

## Performance Considerations

### Capability Lookup Performance

Capability lookups query the database for each check to ensure freshness:

```python
# Each call: Database lookup (no caching)
capability = perm_service.get_agent_capability("my_agent")  # <10ms
```

**Performance characteristics:**
- Single lookup: <10ms (p99)
- Concurrent throughput: >50 checks/second
- Consistent latency across repeated lookups

**Design rationale**: Current implementation prioritizes correctness and freshness over caching. This ensures:
- Capability changes take effect immediately
- No cache invalidation complexity
- Predictable performance (no cache misses)

**Future optimization**: For extreme performance scenarios (>1000 checks/second), future versions may add optional in-memory caching with TTL.

### Audit Logging Overhead

Each capability check writes an audit event:

```python
# Single check overhead: ~1-2ms
perm_service.check_capability("my_agent", "list")
```

**To reduce overhead:**

1. **Batch operations** when possible:
   ```python
   # ❌ Bad: Multiple checks
   for memory_id in memory_ids:
       memory = memory_service.get(agent_id="my_agent", memory_id=memory_id)

   # ✅ Good: Single check, batch retrieve
   memories = memory_service.list(agent_id="my_agent", scope="global", filters={"id__in": memory_ids})
   ```

2. **Use async audit logging** (default in production):
   ```python
   # Configured in agentos/core/audit.py
   ASYNC_AUDIT_LOGGING = True  # Non-blocking
   ```

3. **Adjust log levels** in production:
   ```python
   # Only log warnings (denied access)
   logging.getLogger("agentos.core.memory.permission").setLevel(logging.WARNING)
   ```

### Benchmarks

Expected performance (verified in Task #19 tests):

| Operation | Latency (p99) | Throughput |
|-----------|---------------|------------|
| Single capability lookup | <10ms | - |
| Capability check + audit | <10ms | >50 checks/sec |
| Concurrent checks (10 threads, 100 agents) | - | >800 checks/sec |
| Concurrent checks (20 threads, 1000 agents) | <10s total | >100 checks/sec |
| Permission denied check | <10ms | Same as success |
| Capability registration | <20ms | - |

**Test environment**: SQLite on local disk, typical hardware (laptop/workstation)

**Production considerations**:
- Add database connection pooling for high concurrency
- Use SSD storage for sub-millisecond database access
- Monitor audit log table size (grows indefinitely)

## Security Considerations

### 1. Deny by Default

Unknown agents get NONE capability:

```python
capability = perm_service.get_agent_capability("unknown_agent")
# Returns: MemoryCapability.NONE
```

This prevents unauthorized access if agent registration is forgotten.

### 2. Immutable Audit Trail

Audit logs cannot be deleted or modified (append-only):

```sql
-- No DELETE or UPDATE statements on audit tables
CREATE TABLE agent_capability_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    old_capability TEXT,
    new_capability TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    changed_at_ms INTEGER NOT NULL,
    reason TEXT
);
-- No triggers for deletion
```

### 3. Time-Limited Access

Use expiration for temporary privileges:

```python
from agentos.core.time import utc_now_ms

expires_in_24h = utc_now_ms() + (24 * 60 * 60 * 1000)

perm_service.register_agent_capability(
    agent_id="temp_agent",
    capability=MemoryCapability.WRITE,
    granted_by="user:admin",
    reason="Temporary access for migration",
    expires_at_ms=expires_in_24h
)
```

### 4. Separation of Concerns

Only ADMIN capability can modify capabilities:

```python
# Regular agent cannot grant itself higher privileges
perm_service.check_capability("chat_agent", "set_capability")
# Raises: PermissionDenied (requires ADMIN)
```

## Extending the System

### Adding Custom Capability Levels

**⚠️ Not recommended** - use existing 5 levels. If absolutely necessary:

1. **Add to enum**:
   ```python
   # agentos/core/memory/capabilities.py
   class MemoryCapability(str, Enum):
       NONE = "none"
       READ = "read"
       CUSTOM = "custom"  # New level
       PROPOSE = "propose"
       WRITE = "write"
       ADMIN = "admin"
   ```

2. **Update capability matrix**:
   ```python
   CAPABILITY_MATRIX = {
       MemoryCapability.CUSTOM: READ_OPERATIONS | {"custom_operation"},
       # ... other levels
   }
   ```

3. **Update comparison operators**:
   ```python
   def __lt__(self, other):
       levels = [self.NONE, self.READ, self.CUSTOM, self.PROPOSE, self.WRITE, self.ADMIN]
       return levels.index(self) < levels.index(other)
   ```

4. **Add migration** for existing data.

### Custom Permission Logic

Subclass `MemoryPermissionService` for custom logic:

```python
from agentos.core.memory.permission import MemoryPermissionService
from agentos.core.memory.capabilities import PermissionDenied
from datetime import datetime

class TimeRestrictedPermissionService(MemoryPermissionService):
    """Permission service with time-of-day restrictions."""

    def check_capability(self, agent_id, operation, context=None):
        # Custom logic: Restrict delete operations to off-hours
        if operation == "delete":
            hour = datetime.now().hour
            if 9 <= hour < 17:  # Business hours
                raise PermissionDenied(
                    agent_id=agent_id,
                    operation=operation,
                    capability=self.get_agent_capability(agent_id),
                    required=MemoryCapability.ADMIN
                )

        # Call parent implementation
        return super().check_capability(agent_id, operation, context)

# Use custom service
from agentos.core.memory import permission
permission._permission_service = TimeRestrictedPermissionService()
```

## API Reference

### MemoryPermissionService

Located in `agentos/core/memory/permission.py`

#### `check_capability(agent_id, operation, context=None)`

Check if agent has required capability for operation.

**Parameters:**
- `agent_id` (str): Agent identifier
- `operation` (str): Operation name (list|search|get|propose|upsert|delete|etc)
- `context` (dict, optional): Additional context for audit logging

**Returns:**
- `bool`: True if allowed

**Raises:**
- `PermissionDenied`: If agent lacks required capability

#### `get_agent_capability(agent_id)`

Get agent's current Memory capability.

**Parameters:**
- `agent_id` (str): Agent identifier

**Returns:**
- `MemoryCapability`: Current capability enum

#### `register_agent_capability(agent_id, capability, granted_by, ...)`

Register or update agent capability.

**Parameters:**
- `agent_id` (str): Agent identifier
- `capability` (MemoryCapability): Capability level to grant
- `granted_by` (str): Who is granting this (must have ADMIN)
- `agent_type` (str, optional): Type of agent (default: "unknown")
- `reason` (str, optional): Reason for granting
- `expires_at_ms` (int, optional): Expiration timestamp

**Returns:**
- `bool`: True if successful

**Raises:**
- `PermissionDenied`: If granted_by lacks ADMIN capability

### MemoryProposalService

Located in `agentos/core/memory/proposals.py`

#### `propose_memory(agent_id, memory_item, reason=None)`

Create a memory proposal (requires PROPOSE capability).

**Parameters:**
- `agent_id` (str): Agent proposing the memory
- `memory_item` (dict): MemoryItem dict to propose
- `reason` (str, optional): Reason for the proposal

**Returns:**
- `str`: proposal_id (ULID format)

**Raises:**
- `PermissionDenied`: If agent lacks PROPOSE capability

#### `approve_proposal(reviewer_id, proposal_id, reason=None)`

Approve a pending proposal (requires ADMIN capability).

**Parameters:**
- `reviewer_id` (str): Admin approving the proposal
- `proposal_id` (str): Proposal to approve
- `reason` (str, optional): Approval reason

**Returns:**
- `str`: memory_id (ID of written memory)

**Raises:**
- `PermissionDenied`: If reviewer lacks ADMIN capability

#### `reject_proposal(reviewer_id, proposal_id, reason)`

Reject a pending proposal (requires ADMIN capability).

**Parameters:**
- `reviewer_id` (str): Admin rejecting the proposal
- `proposal_id` (str): Proposal to reject
- `reason` (str): Rejection reason (required)

**Returns:**
- `bool`: True if successful

**Raises:**
- `PermissionDenied`: If reviewer lacks ADMIN capability

## Related Documentation

- **[User Guide](MEMORY_CAPABILITY_USER_GUIDE.md)**: For end-users and administrators
- **[Migration Guide](MIGRATION_TO_CAPABILITY_CONTRACT.md)**: For upgrading existing code
- **[ADR-012](adr/ADR-012-memory-capability-contract.md)**: Architecture decision record
- **[Quick Reference](MEMORY_CAPABILITY_QUICK_REF.md)**: Capability matrix and operation reference

## Troubleshooting

### Common Integration Issues

#### Issue: "agent_id parameter missing"

```python
TypeError: list() missing 1 required positional argument: 'agent_id'
```

**Fix:** Add `agent_id` parameter to all Memory operations.

#### Issue: PermissionDenied for system operations

```python
PermissionDenied: Agent 'my_script' has capability 'none'
```

**Fix:** Use `agent_id="system"` for system operations:

```python
memory_service.upsert(agent_id="system", memory_item=item)
```

#### Issue: Proposal ID returned instead of Memory ID

**Expected behavior:** `propose()` returns `proposal_id`, not `memory_id`.

**Fix:** Handle proposals correctly:

```python
result = memory_service.propose(...)

if result.startswith("01"):  # ULID format = proposal_id
    logger.info(f"Awaiting approval: {result}")
else:  # Memory ID
    logger.info(f"Memory written: {result}")
```

## Support

For developer questions:
1. Check inline docstrings in source code
2. Review integration tests: `tests/integration/test_memory_capability_*.py`
3. Consult [Developer Guide](#) (this document)
4. File issue with `[memory-capability]` tag
