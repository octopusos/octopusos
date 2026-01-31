# ADR-012: Memory Capability Contract

## Status
**Proposed**

**Date**: 2026-02-01
**Authors**: AgentOS Architecture Team
**Semantic Freeze**: YES - This is a system-wide contract for memory access control
**Related**: ADR-011-time-timestamp-contract.md (System contracts), ADR-CHAT-003-InfoNeed-Classification.md (Permission patterns)

---

## Context

### Problem Statement

AgentOS currently lacks a permission system for Memory operations. Any agent can read, write, or delete memories without restriction. This creates several critical problems:

#### 1. **Security Risks**
- Malicious agents can corrupt the Memory system
- Buggy agents can accidentally overwrite critical memories
- No audit trail of who modified what

#### 2. **Multi-Tenancy Challenges**
- Cannot deploy AgentOS in enterprise environments
- No way to isolate agent access to memories
- No support for user-specific or project-specific memory boundaries

#### 3. **System Integrity**
- Chat agents can directly write to Memory during extraction
- No review process for auto-extracted memories
- Cannot differentiate between user-explicit vs auto-generated memories

#### 4. **Lack of OS-Like Architecture**
- AgentOS claims to be an "OS for AI Agents"
- Real operating systems have permission models (Linux: chmod, ACL, capabilities)
- Without permissions, AgentOS is just a framework, not an OS

### Current State

```python
# Current API (no permission checks)
memory_service.upsert(memory_item)  # Anyone can write
memory_service.delete(memory_id)    # Anyone can delete
memory_service.list()               # Anyone can read
```

Problems with current approach:
- No agent identification
- No permission checks
- No differentiation between agents
- No approval workflow

### Real-World Scenarios

**Scenario 1: Chat Agent Auto-Extraction Gone Wrong**
- User: "I like Python 2.7"
- Chat Agent extracts: `{"key": "preferred_python_version", "value": "2.7"}`
- Memory corrupted with outdated preference
- No way to prevent or review this

**Scenario 2: Enterprise Multi-Project Isolation**
- Project A agent reads memories from Project B
- Privacy violation, data leak risk
- Cannot deploy in enterprise environments

**Scenario 3: Malicious Agent**
- Rogue agent deletes all user memories
- No permission check, no audit trail
- System becomes unusable

**Scenario 4: Read-Only Query Agent**
- Search/analysis agent should only READ memories
- Currently can accidentally write during execution
- Violates principle of least privilege

---

## Decision

### Core Principle: OS-Like Capability System

AgentOS adopts a **Linux capabilities-inspired** permission model for Memory operations:

```
┌────────────────────────────────────────────────────┐
│        Linux Capabilities Analogy                  │
├────────────────────────────────────────────────────┤
│  CAP_READ       →  MemoryCapability.READ           │
│  CAP_WRITE      →  MemoryCapability.WRITE          │
│  CAP_DAC_OVERRIDE → MemoryCapability.ADMIN         │
│  (no capability) →  MemoryCapability.NONE          │
└────────────────────────────────────────────────────┘
```

Key insight: Instead of complex RBAC (role-based access control), use **capability-based** security:
- Simpler than RBAC (no roles, groups, inheritance)
- More flexible than ACLs (capabilities are composable)
- Proven model from Linux kernel security

---

## Architecture Design

### 1. Capability Enumeration

```python
# agentos/core/memory/capabilities.py

from enum import Enum

class MemoryCapability(str, Enum):
    """
    Memory operation capability levels.

    Inspired by Linux capabilities (CAP_*), this defines what operations
    an agent can perform on the Memory system.

    Design Principle:
    - NONE: Complete lockout (for untrusted agents)
    - READ: Query-only access (for search/analysis agents)
    - PROPOSE: Can suggest memories but requires approval (for chat agents)
    - WRITE: Can directly write memories (for user-explicit agents)
    - ADMIN: Full control including deletion and capability management (for users/admins)
    """

    NONE = "none"           # Completely prohibited from accessing Memory
    READ = "read"           # Read-only: list_memory, search_memory, get_memory, build_context
    PROPOSE = "propose"     # Propose + Read: can create proposals but needs approval
    WRITE = "write"         # Write + Propose + Read: can directly upsert/update memories
    ADMIN = "admin"         # Admin + Write + Propose + Read: full control (delete, set_capability)

    def allows_operation(self, operation: str) -> bool:
        """
        Check if this capability allows the given operation.

        Args:
            operation: Operation name (read|propose|write|delete|admin)

        Returns:
            True if capability level allows the operation

        Example:
            >>> MemoryCapability.READ.allows_operation("read")
            True
            >>> MemoryCapability.READ.allows_operation("write")
            False
            >>> MemoryCapability.WRITE.allows_operation("read")
            True
        """
        capability_hierarchy = {
            "none": set(),
            "read": {"read"},
            "propose": {"read", "propose"},
            "write": {"read", "propose", "write"},
            "admin": {"read", "propose", "write", "delete", "admin"}
        }
        return operation in capability_hierarchy.get(self.value, set())


# Convenience constants
CAP_NONE = MemoryCapability.NONE
CAP_READ = MemoryCapability.READ
CAP_PROPOSE = MemoryCapability.PROPOSE
CAP_WRITE = MemoryCapability.WRITE
CAP_ADMIN = MemoryCapability.ADMIN
```

---

### 2. Agent Classification by Default Capability

Agents are classified into 4 tiers based on their default memory access needs:

#### Tier 1: READ-ONLY Agents (CAP_READ)

**Principle**: These agents only need to query existing knowledge, never modify it.

**Agent Types**:
- `query_agent` - Search and retrieval operations
- `analysis_agent` - Data analysis and reporting
- `monitoring_agent` - System health monitoring and alerts
- `explanation_agent` - Documentation generation and explanations

**Allowed Operations**:
```python
✅ list_memory(scope="global")
✅ search_memory(query="python best practices")
✅ get_memory(memory_id="mem-123")
✅ build_context(project_id="proj-456", agent_type="query_agent")

❌ upsert_memory(...)  # Forbidden
❌ delete_memory(...)  # Forbidden
```

**Rationale**: Query agents should never modify data. This follows the **principle of least privilege**.

---

#### Tier 2: PROPOSE Agents (CAP_PROPOSE)

**Principle**: These agents can extract/suggest memories but cannot directly write without approval.

**Agent Types**:
- `chat_agent` - Conversational agents that auto-extract user preferences
- `extraction_agent` - Document/log parsing agents
- `suggestion_agent` - Recommendation systems
- `learning_agent` - Agents that learn from interactions

**Allowed Operations**:
```python
✅ All READ operations (inherited)
✅ propose_memory(memory_item={...}, reason="User mentioned preference")

⚠️  Proposed memories go into pending queue
⚠️  Requires human/admin approval before writing to memory_items

❌ upsert_memory(...)  # Cannot directly write
❌ delete_memory(...)  # Cannot delete
```

**Workflow**:
```
Chat Agent extracts preference
    ↓
propose_memory(memory_item)
    ↓
Insert into memory_proposals (status=pending)
    ↓
Notify admin/user via UI badge or email
    ↓
Human reviews proposal
    ↓
approve_proposal(proposal_id) → Writes to memory_items
```

**Rationale**: Auto-extracted memories need review to prevent:
- Hallucinated preferences
- Outdated information
- Misinterpreted context

---

#### Tier 3: WRITE Agents (CAP_WRITE)

**Principle**: These agents have direct write access, used for explicit user commands or system configuration.

**Agent Types**:
- `user_explicit_agent` - Handles explicit user commands like "remember this"
- `system_config_agent` - System configuration management
- `import_agent` - External data import operations
- `task_artifact_agent` - Task execution artifacts

**Allowed Operations**:
```python
✅ All READ + PROPOSE operations (inherited)
✅ upsert_memory(memory_item={...})
✅ update_memory(memory_id="mem-123", updates={...})

❌ delete_memory(...)  # Cannot delete (requires ADMIN)
❌ set_capability(...)  # Cannot manage permissions
```

**Rationale**: User-explicit operations should bypass approval workflow for better UX.

---

#### Tier 4: ADMIN Agents (CAP_ADMIN)

**Principle**: Full control over Memory system, including destructive operations and permission management.

**Agent Types**:
- `human_user` - Human users via WebUI
- `system_admin` - System administrators
- `maintenance_agent` - System maintenance operations (with explicit approval)

**Allowed Operations**:
```python
✅ All READ + PROPOSE + WRITE operations (inherited)
✅ delete_memory(memory_id="mem-123")
✅ set_capability(agent_id="chat_agent", capability=CAP_PROPOSE)
✅ approve_proposal(proposal_id="prop-456")
✅ reject_proposal(proposal_id="prop-789", reason="hallucination")
```

**Rationale**: Only trusted entities should have destructive capabilities.

---

### 3. Permission Matrix

Complete mapping of operations to required capabilities:

| Operation               | NONE | READ | PROPOSE | WRITE | ADMIN |
|-------------------------|------|------|---------|-------|-------|
| `list_memory()`         | ❌    | ✅    | ✅       | ✅     | ✅     |
| `search_memory()`       | ❌    | ✅    | ✅       | ✅     | ✅     |
| `get_memory()`          | ❌    | ✅    | ✅       | ✅     | ✅     |
| `build_context()`       | ❌    | ✅    | ✅       | ✅     | ✅     |
| `propose_memory()`      | ❌    | ❌    | ✅       | ✅     | ✅     |
| `upsert_memory()`       | ❌    | ❌    | ❌       | ✅     | ✅     |
| `update_memory()`       | ❌    | ❌    | ❌       | ✅     | ✅     |
| `delete_memory()`       | ❌    | ❌    | ❌       | ❌     | ✅     |
| `set_capability()`      | ❌    | ❌    | ❌       | ❌     | ✅     |
| `approve_proposal()`    | ❌    | ❌    | ❌       | ❌     | ✅     |
| `reject_proposal()`     | ❌    | ❌    | ❌       | ❌     | ✅     |

**Design Principle**: Capabilities are hierarchical. Higher capabilities inherit all operations from lower levels.

---

### 4. Database Schema Design

#### 4.1 Agent Capabilities Registry

```sql
-- schema_v46_memory_capabilities.sql
-- Migration for Memory Capability Contract
-- Task #15: Design Memory Capability Contract

-- Agent capability registry
CREATE TABLE IF NOT EXISTS agent_capabilities (
    agent_id TEXT PRIMARY KEY,           -- Agent identifier (e.g., "chat_agent", "user:alice")
    agent_type TEXT NOT NULL,            -- Agent type classification (tier 1-4)
    memory_capability TEXT NOT NULL,     -- Capability level: none|read|propose|write|admin
    granted_by TEXT NOT NULL,            -- Who granted this capability (user_id or "system")
    granted_at_ms INTEGER NOT NULL,      -- When capability was granted (epoch milliseconds)
    reason TEXT,                         -- Human-readable reason for granting this capability
    expires_at_ms INTEGER,               -- Optional expiration time (epoch milliseconds, NULL = never expires)
    metadata TEXT,                       -- JSON: Additional metadata (e.g., scope restrictions)

    -- Constraints
    CHECK (memory_capability IN ('none', 'read', 'propose', 'write', 'admin')),
    CHECK (granted_at_ms > 0),
    CHECK (expires_at_ms IS NULL OR expires_at_ms > granted_at_ms)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_cap_type
    ON agent_capabilities(agent_type);

CREATE INDEX IF NOT EXISTS idx_agent_cap_capability
    ON agent_capabilities(memory_capability);

CREATE INDEX IF NOT EXISTS idx_agent_cap_expires
    ON agent_capabilities(expires_at_ms)
    WHERE expires_at_ms IS NOT NULL;

-- Audit trail for capability changes
CREATE TABLE IF NOT EXISTS agent_capability_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    old_capability TEXT,                 -- Previous capability (NULL if first grant)
    new_capability TEXT NOT NULL,        -- New capability
    changed_by TEXT NOT NULL,            -- Who made the change
    changed_at_ms INTEGER NOT NULL,      -- When change occurred
    reason TEXT,                         -- Reason for change
    metadata TEXT                        -- JSON: Additional context
);

CREATE INDEX IF NOT EXISTS idx_cap_audit_agent
    ON agent_capability_audit(agent_id, changed_at_ms DESC);
```

**Design Notes**:
- `agent_id` format:
  - Agents: `"chat_agent"`, `"query_agent"`, `"system_config"`
  - Human users: `"user:alice"`, `"user:bob"`
  - Special: `"system"` (system operations)
- `metadata` JSON examples:
  ```json
  {
    "scope_restrictions": ["project:proj-123"],
    "max_memories_per_day": 10,
    "requires_2fa": true
  }
  ```

#### 4.2 Memory Proposals Table

```sql
-- Memory proposals (pending approval queue)
CREATE TABLE IF NOT EXISTS memory_proposals (
    proposal_id TEXT PRIMARY KEY,        -- Unique proposal ID (ulid)
    proposed_by TEXT NOT NULL,           -- Agent ID who proposed
    proposed_at_ms INTEGER NOT NULL,     -- When proposed (epoch milliseconds)
    memory_item TEXT NOT NULL,           -- JSON: Complete MemoryItem to be written
    status TEXT NOT NULL DEFAULT 'pending', -- pending|approved|rejected
    reviewed_by TEXT,                    -- Who reviewed (NULL if pending)
    reviewed_at_ms INTEGER,              -- When reviewed (NULL if pending)
    review_reason TEXT,                  -- Why approved/rejected
    resulting_memory_id TEXT,            -- Memory ID after approval (NULL if rejected)
    metadata TEXT,                       -- JSON: Additional context

    -- Constraints
    CHECK (status IN ('pending', 'approved', 'rejected')),
    CHECK (proposed_at_ms > 0),
    CHECK (
        (status = 'pending' AND reviewed_by IS NULL AND reviewed_at_ms IS NULL) OR
        (status IN ('approved', 'rejected') AND reviewed_by IS NOT NULL AND reviewed_at_ms IS NOT NULL)
    ),

    -- Foreign key to agent_capabilities
    FOREIGN KEY (proposed_by) REFERENCES agent_capabilities(agent_id)
);

-- Indexes for proposal management
CREATE INDEX IF NOT EXISTS idx_proposal_status
    ON memory_proposals(status, proposed_at_ms DESC);

CREATE INDEX IF NOT EXISTS idx_proposal_agent
    ON memory_proposals(proposed_by, proposed_at_ms DESC);

CREATE INDEX IF NOT EXISTS idx_proposal_reviewed
    ON memory_proposals(reviewed_at_ms DESC)
    WHERE reviewed_at_ms IS NOT NULL;

-- View for pending proposals (UI convenience)
CREATE VIEW IF NOT EXISTS pending_proposals AS
SELECT
    proposal_id,
    proposed_by,
    proposed_at_ms,
    json_extract(memory_item, '$.type') as memory_type,
    json_extract(memory_item, '$.scope') as memory_scope,
    json_extract(memory_item, '$.content.key') as memory_key,
    json_extract(memory_item, '$.content.value') as memory_value
FROM memory_proposals
WHERE status = 'pending'
ORDER BY proposed_at_ms DESC;
```

---

### 5. Permission Check Flow

```python
# agentos/core/memory/permission.py

from typing import Optional
from agentos.core.memory.capabilities import MemoryCapability
from agentos.core.audit import log_audit_event
from agentos.core.time import utc_now_ms

class PermissionDenied(Exception):
    """
    Memory permission denied exception.

    Raised when an agent attempts an operation that exceeds its capability level.
    """

    def __init__(
        self,
        agent_id: str,
        capability: MemoryCapability,
        required: MemoryCapability,
        operation: str
    ):
        self.agent_id = agent_id
        self.capability = capability
        self.required = required
        self.operation = operation

        super().__init__(
            f"Permission denied: Agent '{agent_id}' has capability '{capability.value}' "
            f"but operation '{operation}' requires '{required.value}'"
        )


def check_capability(
    agent_id: str,
    operation: str,
    context: Optional[dict] = None
) -> bool:
    """
    Check if agent has permission to perform operation.

    This is the central permission check function. All Memory operations
    MUST call this before executing.

    Args:
        agent_id: Agent identifier (e.g., "chat_agent", "user:alice")
        operation: Operation name (read|propose|write|delete|admin)
        context: Optional context for audit logging

    Returns:
        True if allowed

    Raises:
        PermissionDenied: If agent lacks required capability

    Example:
        >>> check_capability("query_agent", "read")
        True
        >>> check_capability("query_agent", "write")
        PermissionDenied: ...

    Design Notes:
    - ALWAYS logs to audit trail (even on success)
    - Checks capability expiration
    - Handles special cases (system operations, fallback)
    """
    # Step 1: Get agent's capability
    capability = get_agent_capability(agent_id)

    # Step 2: Check if operation is allowed
    allowed = capability.allows_operation(operation)

    # Step 3: Audit log (ALWAYS log, success or failure)
    audit_capability_check(
        agent_id=agent_id,
        operation=operation,
        capability=capability,
        allowed=allowed,
        context=context or {}
    )

    # Step 4: Raise exception if not allowed
    if not allowed:
        raise PermissionDenied(
            agent_id=agent_id,
            capability=capability,
            required=_required_capability_for_operation(operation),
            operation=operation
        )

    return True


def get_agent_capability(agent_id: str) -> MemoryCapability:
    """
    Get agent's current memory capability.

    Resolution order:
    1. Check agent_capabilities table
    2. Check capability expiration
    3. Apply default capability based on agent_id pattern
    4. Fall back to NONE (safe default)

    Args:
        agent_id: Agent identifier

    Returns:
        MemoryCapability enum

    Example:
        >>> get_agent_capability("chat_agent")
        MemoryCapability.PROPOSE
        >>> get_agent_capability("user:alice")
        MemoryCapability.ADMIN
        >>> get_agent_capability("unknown_agent")
        MemoryCapability.NONE
    """
    from agentos.store import get_db

    conn = get_db()
    cursor = conn.cursor()

    # Query agent_capabilities table
    cursor.execute(
        """
        SELECT memory_capability, expires_at_ms
        FROM agent_capabilities
        WHERE agent_id = ?
        """,
        (agent_id,)
    )

    row = cursor.fetchone()

    if row:
        capability_str, expires_at_ms = row

        # Check expiration
        if expires_at_ms is not None and expires_at_ms < utc_now_ms():
            # Capability expired, fall through to default
            pass
        else:
            return MemoryCapability(capability_str)

    # No explicit capability set, use defaults
    return _get_default_capability(agent_id)


def _get_default_capability(agent_id: str) -> MemoryCapability:
    """
    Get default capability based on agent_id pattern.

    Default rules (from config/memory_capabilities.yaml):
    - user:* → ADMIN (all human users have admin access)
    - system → ADMIN (system operations)
    - *_readonly → READ (naming convention)
    - chat_agent → PROPOSE
    - query_agent → READ
    - analysis_agent → READ
    - extraction_agent → PROPOSE
    - system_config → WRITE
    - test_* → WRITE (test agents)
    - unknown → NONE (fail-safe)

    Args:
        agent_id: Agent identifier

    Returns:
        Default MemoryCapability
    """
    # Load default rules from config
    import yaml
    from pathlib import Path

    config_path = Path(__file__).parent.parent.parent / "config" / "memory_capabilities.yaml"

    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Check default_capabilities
        defaults = config.get("default_capabilities", {})
        if agent_id in defaults:
            return MemoryCapability(defaults[agent_id])

        # Check pattern rules
        import fnmatch
        for rule in config.get("capability_rules", []):
            pattern = rule["agent_pattern"]
            if fnmatch.fnmatch(agent_id, pattern):
                return MemoryCapability(rule["capability"])

    # Built-in defaults (if no config file)
    if agent_id.startswith("user:"):
        return MemoryCapability.ADMIN
    elif agent_id == "system":
        return MemoryCapability.ADMIN
    elif agent_id.endswith("_readonly"):
        return MemoryCapability.READ
    elif agent_id == "chat_agent":
        return MemoryCapability.PROPOSE
    elif agent_id in ["query_agent", "analysis_agent", "monitoring_agent"]:
        return MemoryCapability.READ
    elif agent_id in ["extraction_agent", "suggestion_agent"]:
        return MemoryCapability.PROPOSE
    elif agent_id in ["system_config", "import_agent"]:
        return MemoryCapability.WRITE
    elif agent_id.startswith("test_"):
        return MemoryCapability.WRITE
    else:
        # Unknown agent: fail-safe to NONE
        return MemoryCapability.NONE


def _required_capability_for_operation(operation: str) -> MemoryCapability:
    """Get minimum required capability for operation."""
    operation_requirements = {
        "read": MemoryCapability.READ,
        "propose": MemoryCapability.PROPOSE,
        "write": MemoryCapability.WRITE,
        "delete": MemoryCapability.ADMIN,
        "admin": MemoryCapability.ADMIN,
    }
    return operation_requirements.get(operation, MemoryCapability.ADMIN)


def audit_capability_check(
    agent_id: str,
    operation: str,
    capability: MemoryCapability,
    allowed: bool,
    context: dict
):
    """
    Audit log capability check.

    This function records EVERY capability check to the audit trail,
    whether successful or denied. This provides complete visibility
    into memory access patterns.

    Args:
        agent_id: Agent identifier
        operation: Operation attempted
        capability: Agent's current capability
        allowed: Whether operation was allowed
        context: Additional context
    """
    log_audit_event(
        event_type="MEMORY_CAPABILITY_CHECK",
        level="info" if allowed else "warning",
        metadata={
            "agent_id": agent_id,
            "operation": operation,
            "capability": capability.value,
            "allowed": allowed,
            "context": context,
        }
    )
```

---

### 6. Modified Memory Service API

All Memory operations now require `agent_id` parameter:

```python
# agentos/core/memory/service.py (MODIFIED)

from agentos.core.memory.permission import check_capability, PermissionDenied
from agentos.core.memory.capabilities import MemoryCapability

class MemoryService:
    """
    External memory service with capability-based access control.

    BREAKING CHANGE: All methods now require agent_id parameter for permission checks.
    """

    def list(
        self,
        agent_id: str,  # NEW: Required
        scope: Optional[str] = None,
        project_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        mem_type: Optional[str] = None,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[dict]:
        """
        List memory items with filters (requires READ capability).

        Args:
            agent_id: Agent performing the operation (NEW)
            scope: Filter by scope
            project_id: Filter by project
            tags: Filter by tags
            mem_type: Filter by memory type
            limit: Max results
            include_inactive: Include superseded memories

        Returns:
            List of memory items

        Raises:
            PermissionDenied: If agent lacks READ capability

        Example:
            >>> service.list(agent_id="query_agent", scope="global")
            [...]
            >>> service.list(agent_id="unknown_agent", scope="global")
            PermissionDenied: ...
        """
        # Permission check
        check_capability(
            agent_id=agent_id,
            operation="read",
            context={
                "method": "list",
                "scope": scope,
                "project_id": project_id
            }
        )

        # Original implementation continues...
        conn = self._get_connection()
        # ... (existing code unchanged)

    def upsert(
        self,
        agent_id: str,  # NEW: Required
        memory_item: dict
    ) -> str:
        """
        Insert or update memory (requires WRITE capability).

        Args:
            agent_id: Agent performing the operation (NEW)
            memory_item: Memory item to upsert

        Returns:
            memory_id

        Raises:
            PermissionDenied: If agent lacks WRITE capability

        Example:
            >>> service.upsert(agent_id="system_config", memory_item={...})
            "mem-abc123"
            >>> service.upsert(agent_id="query_agent", memory_item={...})
            PermissionDenied: query_agent has READ, requires WRITE
        """
        # Permission check
        check_capability(
            agent_id=agent_id,
            operation="write",
            context={
                "method": "upsert",
                "memory_type": memory_item.get("type"),
                "scope": memory_item.get("scope")
            }
        )

        # Original implementation continues...
        # ... (existing code unchanged)

    def delete(
        self,
        agent_id: str,  # NEW: Required
        memory_id: str
    ) -> bool:
        """
        Delete memory (requires ADMIN capability).

        Args:
            agent_id: Agent performing the operation (NEW)
            memory_id: Memory ID to delete

        Returns:
            True if deleted

        Raises:
            PermissionDenied: If agent lacks ADMIN capability

        Example:
            >>> service.delete(agent_id="user:alice", memory_id="mem-123")
            True
            >>> service.delete(agent_id="chat_agent", memory_id="mem-123")
            PermissionDenied: chat_agent has PROPOSE, requires ADMIN
        """
        # Permission check
        check_capability(
            agent_id=agent_id,
            operation="delete",
            context={
                "method": "delete",
                "memory_id": memory_id
            }
        )

        # Original implementation continues...
        # ... (existing code unchanged)
```

---

### 7. Propose Workflow Implementation

```python
# agentos/core/memory/proposals.py (NEW)

from typing import Optional
from agentos.core.time import utc_now_ms, utc_now_iso
from agentos.core.memory.permission import check_capability
from agentos.store import get_db
import json

def propose_memory(
    agent_id: str,
    memory_item: dict,
    reason: Optional[str] = None
) -> str:
    """
    Propose a memory for approval (requires PROPOSE capability).

    This function creates a proposal that enters the approval queue.
    The memory is NOT written to memory_items until approved by an admin.

    Workflow:
    1. Check agent has PROPOSE capability
    2. Generate proposal_id (ulid)
    3. Insert into memory_proposals (status=pending)
    4. Notify admins via notification system
    5. Return proposal_id

    Args:
        agent_id: Agent proposing the memory
        memory_item: Complete MemoryItem dict to be written
        reason: Human-readable reason for proposal

    Returns:
        proposal_id: Unique proposal identifier

    Raises:
        PermissionDenied: If agent lacks PROPOSE capability

    Example:
        >>> propose_memory(
        ...     agent_id="chat_agent",
        ...     memory_item={
        ...         "scope": "project",
        ...         "type": "preference",
        ...         "content": {"key": "preferred_language", "value": "python"}
        ...     },
        ...     reason="User mentioned preference in conversation"
        ... )
        "prop-abc123"
    """
    # Permission check
    check_capability(
        agent_id=agent_id,
        operation="propose",
        context={
            "method": "propose_memory",
            "memory_type": memory_item.get("type"),
            "scope": memory_item.get("scope")
        }
    )

    # Generate proposal ID
    from ulid import ulid
    proposal_id = f"prop-{ulid()}"

    # Prepare proposal
    now_ms = utc_now_ms()
    memory_item_json = json.dumps(memory_item, ensure_ascii=False)

    # Insert proposal
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO memory_proposals (
            proposal_id, proposed_by, proposed_at_ms, memory_item,
            status, reviewed_by, reviewed_at_ms, review_reason,
            resulting_memory_id, metadata
        )
        VALUES (?, ?, ?, ?, 'pending', NULL, NULL, NULL, NULL, ?)
        """,
        (
            proposal_id,
            agent_id,
            now_ms,
            memory_item_json,
            json.dumps({"reason": reason} if reason else {})
        )
    )

    conn.commit()

    # Notify admins (placeholder for notification system)
    _notify_admins_of_proposal(proposal_id, agent_id, memory_item)

    return proposal_id


def approve_proposal(
    reviewer_id: str,
    proposal_id: str,
    reason: Optional[str] = None
) -> str:
    """
    Approve a memory proposal (requires ADMIN capability).

    This function:
    1. Checks reviewer has ADMIN capability
    2. Retrieves proposal from memory_proposals
    3. Writes memory to memory_items using reviewer's capability
    4. Updates proposal status to 'approved'
    5. Records resulting_memory_id

    Args:
        reviewer_id: Admin approving the proposal
        proposal_id: Proposal ID to approve
        reason: Optional reason for approval

    Returns:
        memory_id: ID of the created memory in memory_items

    Raises:
        PermissionDenied: If reviewer lacks ADMIN capability
        ValueError: If proposal not found or already reviewed

    Example:
        >>> approve_proposal(
        ...     reviewer_id="user:alice",
        ...     proposal_id="prop-abc123",
        ...     reason="Valid preference, approved"
        ... )
        "mem-xyz789"
    """
    # Permission check
    check_capability(
        reviewer_id=reviewer_id,
        operation="admin",
        context={
            "method": "approve_proposal",
            "proposal_id": proposal_id
        }
    )

    conn = get_db()
    cursor = conn.cursor()

    # Retrieve proposal
    cursor.execute(
        """
        SELECT memory_item, status, proposed_by
        FROM memory_proposals
        WHERE proposal_id = ?
        """,
        (proposal_id,)
    )

    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Proposal not found: {proposal_id}")

    memory_item_json, status, proposed_by = row

    if status != "pending":
        raise ValueError(f"Proposal already reviewed with status: {status}")

    # Parse memory item
    memory_item = json.loads(memory_item_json)

    # Write memory using MemoryService (with reviewer's ADMIN capability)
    from agentos.core.memory.service import MemoryService
    service = MemoryService()
    memory_id = service.upsert(
        agent_id=reviewer_id,  # Use reviewer's capability
        memory_item=memory_item
    )

    # Update proposal status
    now_ms = utc_now_ms()
    cursor.execute(
        """
        UPDATE memory_proposals
        SET status = 'approved',
            reviewed_by = ?,
            reviewed_at_ms = ?,
            review_reason = ?,
            resulting_memory_id = ?
        WHERE proposal_id = ?
        """,
        (reviewer_id, now_ms, reason, memory_id, proposal_id)
    )

    conn.commit()

    # Notify proposer (placeholder)
    _notify_proposal_decision(proposal_id, proposed_by, "approved", reason)

    return memory_id


def reject_proposal(
    reviewer_id: str,
    proposal_id: str,
    reason: str
) -> bool:
    """
    Reject a memory proposal (requires ADMIN capability).

    Args:
        reviewer_id: Admin rejecting the proposal
        proposal_id: Proposal ID to reject
        reason: Required reason for rejection

    Returns:
        True if rejected successfully

    Raises:
        PermissionDenied: If reviewer lacks ADMIN capability
        ValueError: If proposal not found or already reviewed

    Example:
        >>> reject_proposal(
        ...     reviewer_id="user:alice",
        ...     proposal_id="prop-abc123",
        ...     reason="Hallucinated preference, user never said this"
        ... )
        True
    """
    # Permission check
    check_capability(
        reviewer_id=reviewer_id,
        operation="admin",
        context={
            "method": "reject_proposal",
            "proposal_id": proposal_id
        }
    )

    conn = get_db()
    cursor = conn.cursor()

    # Check proposal exists and is pending
    cursor.execute(
        """
        SELECT status, proposed_by
        FROM memory_proposals
        WHERE proposal_id = ?
        """,
        (proposal_id,)
    )

    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Proposal not found: {proposal_id}")

    status, proposed_by = row

    if status != "pending":
        raise ValueError(f"Proposal already reviewed with status: {status}")

    # Update proposal status
    now_ms = utc_now_ms()
    cursor.execute(
        """
        UPDATE memory_proposals
        SET status = 'rejected',
            reviewed_by = ?,
            reviewed_at_ms = ?,
            review_reason = ?
        WHERE proposal_id = ?
        """,
        (reviewer_id, now_ms, reason, proposal_id)
    )

    conn.commit()

    # Notify proposer
    _notify_proposal_decision(proposal_id, proposed_by, "rejected", reason)

    return True


def _notify_admins_of_proposal(proposal_id: str, agent_id: str, memory_item: dict):
    """
    Notify admins of new proposal (placeholder for notification system).

    Future implementation:
    - Send email to admin email addresses
    - Show UI badge with pending count
    - Slack/webhook notification
    """
    # TODO: Implement notification system
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"New memory proposal: {proposal_id} from {agent_id} "
        f"(type: {memory_item.get('type')}, scope: {memory_item.get('scope')})"
    )


def _notify_proposal_decision(
    proposal_id: str,
    proposer_id: str,
    decision: str,
    reason: Optional[str]
):
    """
    Notify proposer of approval/rejection decision.

    Future implementation:
    - Log to proposer's notification inbox
    - Show in agent's dashboard
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"Proposal {proposal_id} {decision} "
        f"(proposer: {proposer_id}, reason: {reason})"
    )
```

---

### 8. Configuration File Format

```yaml
# config/memory_capabilities.yaml

# Default capabilities for common agent types
default_capabilities:
  # Tier 1: READ-ONLY
  query_agent: read
  analysis_agent: read
  monitoring_agent: read
  explanation_agent: read

  # Tier 2: PROPOSE
  chat_agent: propose
  extraction_agent: propose
  suggestion_agent: propose
  learning_agent: propose

  # Tier 3: WRITE
  user_explicit_agent: write
  system_config: write
  import_agent: write
  task_artifact_agent: write

  # Tier 4: ADMIN
  system: admin

# Pattern-based rules (applied in order)
capability_rules:
  # Human users always have admin access
  - agent_pattern: "user:*"
    capability: admin
    reason: "All human users have admin access by default"

  # Read-only naming convention
  - agent_pattern: "*_readonly"
    capability: read
    reason: "Read-only agents by naming convention"

  # Test agents get write access
  - agent_pattern: "test_*"
    capability: write
    reason: "Test agents need write access for integration tests"

  # Monitoring/observability agents
  - agent_pattern: "monitor_*"
    capability: read
    reason: "Monitoring agents only need read access"

# Scope-based overrides (optional future feature)
scope_overrides:
  global:
    # Global scope requires higher privilege to prevent pollution
    min_capability: write
    reason: "Global memories affect all projects"

  project:
    # Project scope allows propose
    min_capability: propose
    reason: "Project memories can be proposed by chat agents"

  task:
    # Task scope is most permissive
    min_capability: propose
    reason: "Task-specific memories are ephemeral"

# Capability expiration policies (optional)
expiration_policies:
  # Temporary elevated privileges
  temporary_admin:
    default_duration_hours: 24
    requires_justification: true

  # Time-limited access for external agents
  external_agent:
    default_duration_hours: 168  # 1 week
    max_duration_hours: 720      # 30 days

# Notification settings
notifications:
  # Notify admins of proposals
  proposal_notification:
    enabled: true
    methods: ["ui_badge", "email"]
    batch_interval_minutes: 15  # Batch notifications every 15 min

  # Notify on permission denials
  permission_denied_notification:
    enabled: true
    threshold: 3  # Notify after 3 denials in 1 hour
    methods: ["log"]
```

---

### 9. Admin API for Capability Management

```python
# agentos/core/memory/admin.py (NEW)

from agentos.core.memory.capabilities import MemoryCapability
from agentos.core.memory.permission import check_capability
from agentos.core.time import utc_now_ms
from agentos.store import get_db
import json

def set_agent_capability(
    admin_id: str,
    agent_id: str,
    capability: MemoryCapability,
    reason: str,
    expires_at_ms: Optional[int] = None
) -> bool:
    """
    Set or update agent's memory capability (requires ADMIN).

    Args:
        admin_id: Admin performing the operation
        agent_id: Agent whose capability to set
        capability: New capability level
        reason: Required reason for change
        expires_at_ms: Optional expiration timestamp (epoch ms)

    Returns:
        True if updated successfully

    Raises:
        PermissionDenied: If admin_id lacks ADMIN capability

    Example:
        >>> set_agent_capability(
        ...     admin_id="user:alice",
        ...     agent_id="new_chat_agent",
        ...     capability=MemoryCapability.PROPOSE,
        ...     reason="New chat agent deployment"
        ... )
        True
    """
    # Permission check
    check_capability(
        agent_id=admin_id,
        operation="admin",
        context={
            "method": "set_agent_capability",
            "target_agent_id": agent_id,
            "new_capability": capability.value
        }
    )

    conn = get_db()
    cursor = conn.cursor()

    # Get old capability for audit
    cursor.execute(
        "SELECT memory_capability FROM agent_capabilities WHERE agent_id = ?",
        (agent_id,)
    )
    row = cursor.fetchone()
    old_capability = row[0] if row else None

    # Upsert capability
    now_ms = utc_now_ms()
    cursor.execute(
        """
        INSERT INTO agent_capabilities (
            agent_id, agent_type, memory_capability,
            granted_by, granted_at_ms, reason, expires_at_ms, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(agent_id) DO UPDATE SET
            memory_capability = excluded.memory_capability,
            granted_by = excluded.granted_by,
            granted_at_ms = excluded.granted_at_ms,
            reason = excluded.reason,
            expires_at_ms = excluded.expires_at_ms
        """,
        (
            agent_id,
            _infer_agent_type(agent_id, capability),
            capability.value,
            admin_id,
            now_ms,
            reason,
            expires_at_ms,
            None  # metadata
        )
    )

    # Audit log
    cursor.execute(
        """
        INSERT INTO agent_capability_audit (
            agent_id, old_capability, new_capability,
            changed_by, changed_at_ms, reason, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_id,
            old_capability,
            capability.value,
            admin_id,
            now_ms,
            reason,
            None  # metadata
        )
    )

    conn.commit()

    return True


def revoke_capability(
    admin_id: str,
    agent_id: str,
    reason: str
) -> bool:
    """
    Revoke agent's capability (set to NONE).

    Args:
        admin_id: Admin performing revocation
        agent_id: Agent whose capability to revoke
        reason: Required reason for revocation

    Returns:
        True if revoked

    Raises:
        PermissionDenied: If admin_id lacks ADMIN capability

    Example:
        >>> revoke_capability(
        ...     admin_id="user:alice",
        ...     agent_id="compromised_agent",
        ...     reason="Security incident, agent compromised"
        ... )
        True
    """
    return set_agent_capability(
        admin_id=admin_id,
        agent_id=agent_id,
        capability=MemoryCapability.NONE,
        reason=reason
    )


def list_agent_capabilities(
    admin_id: str,
    capability_filter: Optional[MemoryCapability] = None,
    include_expired: bool = False
) -> list[dict]:
    """
    List all agent capabilities (requires ADMIN).

    Args:
        admin_id: Admin querying capabilities
        capability_filter: Optional filter by capability level
        include_expired: Include expired capabilities

    Returns:
        List of capability records

    Example:
        >>> list_agent_capabilities(
        ...     admin_id="user:alice",
        ...     capability_filter=MemoryCapability.PROPOSE
        ... )
        [
            {
                "agent_id": "chat_agent",
                "capability": "propose",
                "granted_by": "system",
                "granted_at_ms": 1706745600000,
                "expires_at_ms": null
            },
            ...
        ]
    """
    # Permission check
    check_capability(
        agent_id=admin_id,
        operation="admin",
        context={"method": "list_agent_capabilities"}
    )

    conn = get_db()
    cursor = conn.cursor()

    # Build query
    query = """
        SELECT agent_id, agent_type, memory_capability,
               granted_by, granted_at_ms, reason, expires_at_ms
        FROM agent_capabilities
        WHERE 1=1
    """
    params = []

    if capability_filter:
        query += " AND memory_capability = ?"
        params.append(capability_filter.value)

    if not include_expired:
        now_ms = utc_now_ms()
        query += " AND (expires_at_ms IS NULL OR expires_at_ms > ?)"
        params.append(now_ms)

    query += " ORDER BY agent_id"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    return [
        {
            "agent_id": row[0],
            "agent_type": row[1],
            "capability": row[2],
            "granted_by": row[3],
            "granted_at_ms": row[4],
            "reason": row[5],
            "expires_at_ms": row[6]
        }
        for row in rows
    ]


def _infer_agent_type(agent_id: str, capability: MemoryCapability) -> str:
    """Infer agent_type from agent_id and capability."""
    if agent_id.startswith("user:"):
        return "human_user"
    elif agent_id == "system":
        return "system"
    elif capability == MemoryCapability.READ:
        return "readonly_agent"
    elif capability == MemoryCapability.PROPOSE:
        return "propose_agent"
    elif capability == MemoryCapability.WRITE:
        return "write_agent"
    elif capability == MemoryCapability.ADMIN:
        return "admin_agent"
    else:
        return "unknown"
```

---

## Consequences

### Positive ✅

1. **OS-Like Architecture**
   - AgentOS now has a true permission system like Linux
   - Differentiates AgentOS from other frameworks
   - Makes "OS" in AgentOS meaningful

2. **Security & Safety**
   - Malicious agents cannot corrupt Memory
   - Buggy agents have limited blast radius
   - Principle of least privilege enforced

3. **Enterprise-Ready**
   - Multi-tenancy support via capability isolation
   - Audit trail for compliance (SOC 2, GDPR)
   - Fine-grained access control

4. **Memory Quality Improvement**
   - Chat agents require approval (prevents hallucinated memories)
   - User-explicit memories bypass approval (better UX)
   - Admins can review and reject bad proposals

5. **Clear Responsibility Model**
   - Every memory operation has an agent_id
   - Audit trail shows who did what
   - Easier debugging and accountability

6. **Extensibility**
   - Configuration-based capability rules
   - Easy to add new agent types
   - Pattern-based defaults

### Negative ⚠️

1. **Breaking API Change**
   - All Memory operations now require `agent_id` parameter
   - Existing code needs migration
   - Risk: Forgot to add `agent_id` = runtime error

2. **Implementation Complexity**
   - New tables (agent_capabilities, memory_proposals)
   - Permission check on every operation
   - Audit logging overhead

3. **Performance Overhead**
   - Database lookup for capability on each operation
   - Audit logging I/O
   - Proposal workflow adds latency

4. **Configuration Burden**
   - Need to configure default capabilities
   - Pattern rules can be confusing
   - Risk: Misconfigured permissions

5. **User Experience Impact**
   - Proposal workflow adds friction
   - Users need to review pending proposals
   - UI complexity (approval queue)

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Breaking API change breaks existing agents | High | Gradual migration with fallback, clear migration guide |
| Performance regression on Memory operations | Medium | Cache capability lookups, async audit logging |
| Misconfigured permissions lock out agents | High | Safe defaults (fail to NONE), admin override tool |
| Proposal queue gets clogged | Medium | Auto-approve low-risk proposals, batch notifications |
| Agent spoofing (fake agent_id) | High | Enforce agent_id from trusted source (session context) |

---

## Migration Strategy

### Phase 1: Schema Migration (v46)

```bash
# Apply schema migration
agentos db migrate --version 46
```

### Phase 2: Add agent_id to Existing Calls (Gradual)

```python
# OLD (before ADR-012)
memory_service.upsert(memory_item)

# NEW (after ADR-012)
memory_service.upsert(agent_id="chat_agent", memory_item=memory_item)
```

**Migration Script**:
```python
# scripts/migrate_memory_api.py
# Automated search-and-replace for common patterns
import re
from pathlib import Path

patterns = [
    (r'memory_service\.upsert\(', r'memory_service.upsert(agent_id=AGENT_ID, '),
    (r'memory_service\.list\(', r'memory_service.list(agent_id=AGENT_ID, '),
    # ... more patterns
]

for py_file in Path("agentos").rglob("*.py"):
    content = py_file.read_text()
    for old, new in patterns:
        content = re.sub(old, new, content)
    py_file.write_text(content)
```

### Phase 3: Backward Compatibility (Temporary)

```python
# Temporary fallback for agent_id
def list(
    self,
    agent_id: Optional[str] = None,  # Optional during migration
    scope: Optional[str] = None,
    **kwargs
) -> list[dict]:
    if agent_id is None:
        # Fallback: Use "system" capability
        import warnings
        warnings.warn(
            "agent_id not provided, using 'system'. "
            "This fallback will be removed in v1.0",
            DeprecationWarning
        )
        agent_id = "system"

    # Rest of implementation...
```

### Phase 4: Enforce agent_id (v1.0)

```python
# Remove optional agent_id, make it required
def list(
    self,
    agent_id: str,  # Required (no default)
    scope: Optional[str] = None,
    **kwargs
) -> list[dict]:
    # agent_id is now mandatory
    ...
```

---

## Testing Requirements

### Unit Tests (Minimum 50 Tests)

**Capability System Tests (15 tests)**:
1. ✅ Test MemoryCapability.allows_operation() for all capability levels
2. ✅ Test capability hierarchy (ADMIN can do everything)
3. ✅ Test get_agent_capability() with explicit grants
4. ✅ Test get_agent_capability() with default patterns
5. ✅ Test get_agent_capability() with expired capabilities
6. ✅ Test check_capability() success path
7. ✅ Test check_capability() raises PermissionDenied
8. ✅ Test audit logging on capability check
9. ✅ Test _get_default_capability() patterns
10. ✅ Test config file loading for capabilities
11. ✅ Test user:* pattern → ADMIN
12. ✅ Test *_readonly pattern → READ
13. ✅ Test unknown agent → NONE
14. ✅ Test system agent → ADMIN
15. ✅ Test test_* pattern → WRITE

**Memory Service Integration Tests (15 tests)**:
16. ✅ Test list() with READ capability
17. ✅ Test list() with NONE capability (denied)
18. ✅ Test upsert() with WRITE capability
19. ✅ Test upsert() with READ capability (denied)
20. ✅ Test delete() with ADMIN capability
21. ✅ Test delete() with WRITE capability (denied)
22. ✅ Test search() with READ capability
23. ✅ Test build_context() with READ capability
24. ✅ Test upsert() without agent_id (DeprecationWarning in migration phase)
25. ✅ Test audit trail records agent_id
26. ✅ Test permission denied logs warning
27. ✅ Test capability expiration prevents operations
28. ✅ Test capability inheritance (WRITE can READ)
29. ✅ Test capability non-inheritance (READ cannot WRITE)
30. ✅ Test agent_id spoofing protection (future)

**Proposal Workflow Tests (10 tests)**:
31. ✅ Test propose_memory() with PROPOSE capability
32. ✅ Test propose_memory() with READ capability (denied)
33. ✅ Test propose_memory() creates pending proposal
34. ✅ Test approve_proposal() writes to memory_items
35. ✅ Test approve_proposal() updates proposal status
36. ✅ Test approve_proposal() requires ADMIN
37. ✅ Test reject_proposal() does not write memory
38. ✅ Test reject_proposal() updates proposal status
39. ✅ Test reject_proposal() requires reason
40. ✅ Test cannot approve already-reviewed proposal

**Admin API Tests (10 tests)**:
41. ✅ Test set_agent_capability() with ADMIN
42. ✅ Test set_agent_capability() with WRITE (denied)
43. ✅ Test set_agent_capability() creates audit record
44. ✅ Test revoke_capability() sets to NONE
45. ✅ Test list_agent_capabilities() returns all agents
46. ✅ Test list_agent_capabilities() filters by capability
47. ✅ Test list_agent_capabilities() excludes expired
48. ✅ Test capability update triggers audit log
49. ✅ Test capability expiration enforcement
50. ✅ Test set_agent_capability() upsert semantics

### Integration Tests (5 scenarios)

51. ✅ Full propose workflow: chat agent → proposal → admin approval → memory created
52. ✅ Permission denied scenario: query agent tries to write → PermissionDenied → audit log
53. ✅ Capability expiration: grant temporary WRITE → wait for expiry → operation denied
54. ✅ Multi-agent isolation: agent A cannot access agent B's scoped memories
55. ✅ Human user admin flow: user creates agent → sets capability → agent operates

---

## Implementation Checklist

**Phase 1: Core Implementation (Tasks #16-17)**
- [ ] Create `agentos/core/memory/capabilities.py` (Capability enum)
- [ ] Create `agentos/core/memory/permission.py` (Permission checks)
- [ ] Create `agentos/core/memory/proposals.py` (Propose workflow)
- [ ] Create `agentos/core/memory/admin.py` (Admin API)
- [ ] Apply schema migration v46 (SQL files)
- [ ] Write 50+ unit tests

**Phase 2: Memory Service Integration (Task #16)**
- [ ] Modify `MemoryService.list()` to require agent_id
- [ ] Modify `MemoryService.upsert()` to require agent_id
- [ ] Modify `MemoryService.delete()` to require agent_id
- [ ] Modify `MemoryService.search()` to require agent_id
- [ ] Modify `MemoryService.build_context()` to require agent_id
- [ ] Add backward compatibility fallback (temporary)
- [ ] Update all existing Memory API callers with agent_id

**Phase 3: Configuration & Documentation (Task #19)**
- [ ] Create `config/memory_capabilities.yaml`
- [ ] Write migration guide for existing code
- [ ] Write ADR-012 (this document)
- [ ] Write API documentation
- [ ] Write admin guide (capability management)
- [ ] Create example scripts

**Phase 4: UI Integration (Task #18)**
- [ ] Add pending proposals view to WebUI
- [ ] Add approve/reject buttons
- [ ] Add capability management UI (admin panel)
- [ ] Add badge notification for pending proposals
- [ ] Add audit trail viewer (who did what)

**Phase 5: Testing & Validation**
- [ ] Run full test suite (50+ tests)
- [ ] Performance testing (capability lookup overhead)
- [ ] Security audit (permission bypass attempts)
- [ ] End-to-end testing with real agents
- [ ] Load testing (proposal queue)

**Phase 6: Migration & Deployment**
- [ ] Run automated migration script on codebase
- [ ] Manual review of agent_id additions
- [ ] Deploy schema migration v46
- [ ] Deploy code with backward compatibility
- [ ] Monitor for PermissionDenied errors
- [ ] Remove backward compatibility (v1.0)

---

## Future Enhancements

### Potential Features (Post-v1.0)

1. **Scope-Based Capabilities**
   - Fine-grained control: agent can WRITE to project scope but only READ global scope
   - Example: `agent_capabilities` adds `scope_restrictions` JSON field

2. **Time-Based Capabilities**
   - Temporary elevated privileges
   - Example: Grant WRITE for 24 hours

3. **Rate Limiting**
   - Limit number of proposals per agent per day
   - Prevent proposal spam

4. **Auto-Approval Rules**
   - Low-risk proposals auto-approve
   - Example: Task-scoped memories auto-approve

5. **Capability Delegation**
   - Agent can delegate subset of its capability to sub-agents
   - Example: Parent agent grants READ to child agents

6. **Multi-Signature Approval**
   - High-risk proposals require 2+ admin approvals
   - Example: Delete global memory requires 2 approvals

7. **Audit Trail Analytics**
   - Dashboard showing capability usage patterns
   - Anomaly detection (unusual access patterns)

---

## References

### Internal Documentation

- **Memory Service**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/memory/service.py`
- **Memory Schema**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/memory/schema.py`
- **Audit System**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/audit.py`
- **Time Contract**: `/Users/pangge/PycharmProjects/AgentOS/docs/adr/ADR-011-time-timestamp-contract.md`
- **InfoNeed Classification**: `/Users/pangge/PycharmProjects/AgentOS/docs/adr/ADR-CHAT-003-InfoNeed-Classification.md`

### External References

- [Linux Capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html) - Inspiration for capability model
- [Principle of Least Privilege](https://en.wikipedia.org/wiki/Principle_of_least_privilege) - Security principle
- [RBAC vs ABAC vs Capabilities](https://www.osohq.com/academy/rbac-vs-abac) - Access control models comparison
- [OWASP Access Control](https://owasp.org/www-community/Access_Control) - Security best practices

---

## Appendix A: Example Workflows

### Example 1: Chat Agent Auto-Extraction

**Scenario**: User says "I prefer Python 3.11" in chat.

```
User message: "I prefer Python 3.11"
    ↓
ChatEngine extracts preference
    ↓
chat_agent calls propose_memory(
    agent_id="chat_agent",
    memory_item={
        "scope": "project",
        "type": "preference",
        "content": {"key": "python_version", "value": "3.11"}
    },
    reason="User explicitly mentioned preference"
)
    ↓
Check: chat_agent has PROPOSE capability ✅
    ↓
Insert into memory_proposals (status=pending)
    ↓
Notify admin via UI badge: "1 pending proposal"
    ↓
Admin reviews proposal in WebUI
    ↓
Admin clicks "Approve" with reason "Valid preference"
    ↓
approve_proposal(
    reviewer_id="user:alice",
    proposal_id="prop-abc123",
    reason="Valid preference"
)
    ↓
Check: user:alice has ADMIN capability ✅
    ↓
Write memory to memory_items (memory_id="mem-xyz789")
    ↓
Update proposal: status=approved, resulting_memory_id="mem-xyz789"
    ↓
Notify chat_agent: "Proposal approved"
```

---

### Example 2: Query Agent Read-Only

**Scenario**: Query agent searches for Python knowledge.

```
User: "Search memories for Python best practices"
    ↓
query_agent calls list_memory(
    agent_id="query_agent",
    scope="global",
    tags=["python", "best_practices"]
)
    ↓
Check: query_agent has READ capability ✅
    ↓
Query memory_items table
    ↓
Return results to query_agent
    ↓
Agent formats and displays results
```

**If query agent tries to write**:

```
query_agent calls upsert_memory(
    agent_id="query_agent",
    memory_item={...}
)
    ↓
Check: query_agent has READ capability
Required: WRITE capability
    ↓
PermissionDenied raised ❌
    ↓
Audit log: "query_agent attempted WRITE with READ capability"
    ↓
Error returned to query_agent
```

---

### Example 3: Human User Admin Operations

**Scenario**: User Alice creates new agent and sets capability.

```
User Alice clicks "Create Agent" in WebUI
    ↓
WebUI calls create_agent(name="new_analysis_agent")
    ↓
Admin calls set_agent_capability(
    admin_id="user:alice",
    agent_id="new_analysis_agent",
    capability=READ,
    reason="Analysis agent for project X"
)
    ↓
Check: user:alice has ADMIN capability ✅
    ↓
Insert into agent_capabilities:
    agent_id="new_analysis_agent"
    capability="read"
    granted_by="user:alice"
    ↓
Insert audit record into agent_capability_audit
    ↓
Success: Agent created with READ capability
    ↓
new_analysis_agent can now list_memory() ✅
```

---

### Example 4: Permission Denied Flow

**Scenario**: Malicious agent tries to delete memories.

```
rogue_agent calls delete_memory(
    agent_id="rogue_agent",
    memory_id="mem-important"
)
    ↓
Check: rogue_agent has NONE capability (default for unknown)
Required: ADMIN capability
    ↓
PermissionDenied raised ❌
    ↓
Audit log (level=warning):
    "rogue_agent attempted DELETE with NONE capability"
    ↓
Error message: "Permission denied: rogue_agent has none, requires admin"
    ↓
Memory not deleted (safe) ✅
    ↓
Admin receives alert: "3 permission denials from rogue_agent"
    ↓
Admin investigates and revokes rogue_agent
```

---

## Appendix B: Database Schema Reference

### Complete Schema DDL

```sql
-- schema_v46_memory_capabilities.sql
-- Complete schema for Memory Capability Contract

-- Agent capability registry
CREATE TABLE IF NOT EXISTS agent_capabilities (
    agent_id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL,
    memory_capability TEXT NOT NULL CHECK (memory_capability IN ('none', 'read', 'propose', 'write', 'admin')),
    granted_by TEXT NOT NULL,
    granted_at_ms INTEGER NOT NULL CHECK (granted_at_ms > 0),
    reason TEXT,
    expires_at_ms INTEGER CHECK (expires_at_ms IS NULL OR expires_at_ms > granted_at_ms),
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_cap_type ON agent_capabilities(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_cap_capability ON agent_capabilities(memory_capability);
CREATE INDEX IF NOT EXISTS idx_agent_cap_expires ON agent_capabilities(expires_at_ms) WHERE expires_at_ms IS NOT NULL;

-- Capability audit trail
CREATE TABLE IF NOT EXISTS agent_capability_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    old_capability TEXT,
    new_capability TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    changed_at_ms INTEGER NOT NULL,
    reason TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_cap_audit_agent ON agent_capability_audit(agent_id, changed_at_ms DESC);

-- Memory proposals (pending approval queue)
CREATE TABLE IF NOT EXISTS memory_proposals (
    proposal_id TEXT PRIMARY KEY,
    proposed_by TEXT NOT NULL,
    proposed_at_ms INTEGER NOT NULL CHECK (proposed_at_ms > 0),
    memory_item TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT,
    reviewed_at_ms INTEGER,
    review_reason TEXT,
    resulting_memory_id TEXT,
    metadata TEXT,

    CHECK (
        (status = 'pending' AND reviewed_by IS NULL AND reviewed_at_ms IS NULL) OR
        (status IN ('approved', 'rejected') AND reviewed_by IS NOT NULL AND reviewed_at_ms IS NOT NULL)
    ),

    FOREIGN KEY (proposed_by) REFERENCES agent_capabilities(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_proposal_status ON memory_proposals(status, proposed_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_proposal_agent ON memory_proposals(proposed_by, proposed_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_proposal_reviewed ON memory_proposals(reviewed_at_ms DESC) WHERE reviewed_at_ms IS NOT NULL;

-- Pending proposals view (UI convenience)
CREATE VIEW IF NOT EXISTS pending_proposals AS
SELECT
    proposal_id,
    proposed_by,
    proposed_at_ms,
    json_extract(memory_item, '$.type') as memory_type,
    json_extract(memory_item, '$.scope') as memory_scope,
    json_extract(memory_item, '$.content.key') as memory_key,
    json_extract(memory_item, '$.content.value') as memory_value
FROM memory_proposals
WHERE status = 'pending'
ORDER BY proposed_at_ms DESC;

-- Update schema version
INSERT INTO schema_version (version, applied_at, description)
VALUES (
    '0.46.0',
    CURRENT_TIMESTAMP,
    'Memory Capability Contract (ADR-012): agent_capabilities, memory_proposals'
);
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-01 | AgentOS Team | Initial version (Task #15) |

---

**Semantic Freeze Notice**: This ADR defines a system-wide contract for memory access control. Any changes require team consensus and must be documented as a new ADR revision.

**Implementation Status**: Proposed (Tasks #16-19 pending implementation)
