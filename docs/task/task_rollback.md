# Task Rollback Strategy

## Overview

This document defines the minimal viable rollback/undo strategy for AgentOS tasks. The strategy prioritizes **safety over convenience**, preventing history tampering while providing essential undo capabilities.

Created for: Task #6: S6 - Implement minimal rollback/undo strategy

## Core Principles

### 1. Safety First - No History Tampering

- **Immutable History**: Completed tasks (DONE, VERIFIED) cannot be rolled back
- **Audit Trail**: All rollback operations are fully audited
- **New Task IDs**: Restarting a task creates a new task_id (prevents history modification)

### 2. Limited Rollback Scope

Only the following rollback operations are allowed:

1. **Cancel Draft** (DRAFT → CANCELED)
2. **Cancel Approved** (APPROVED → CANCELED)
3. **Cancel Queued** (QUEUED → CANCELED)
4. **Restart as New Draft** (creates new task_id)

### 3. No Arbitrary Rollback

The following operations are **NOT ALLOWED**:

- Rollback from DONE → any previous state
- Rollback from VERIFIED → any previous state
- Rollback from FAILED → DRAFT (use retry instead)
- Direct state modification (must go through state machine)
- Modifying historical records

## Allowed Rollback Operations

### 1. Cancel Draft (DRAFT → CANCELED)

**Use Case**: Discard a task that was created but is no longer needed.

**Safety**: ✅ Safe - no approval or execution has occurred

```python
from agentos.core.task.rollback import TaskRollbackService

rollback_service = TaskRollbackService()

# Cancel a draft task
task = rollback_service.cancel_draft(
    task_id="task_xyz",
    actor="user@example.com",
    reason="Task is no longer needed"
)

print(f"Task canceled: {task.status}")  # canceled
```

**Audit Trail**:
- Event: `ROLLBACK_CANCEL_DRAFT`
- Payload includes: operation, actor, reason, timestamp

### 2. Cancel Approved (APPROVED → CANCELED)

**Use Case**: Cancel a task that was approved but should not be executed.

**Safety**: ✅ Safe - approval granted but no execution started

```python
# Cancel an approved task
task = rollback_service.cancel_approved(
    task_id="task_xyz",
    actor="product_owner",
    reason="Requirements changed - feature no longer needed",
    metadata={"change_request": "CR-123"}
)
```

**Requirements**:
- Task must be in APPROVED state
- Reason is REQUIRED (for audit)
- Actor must be identified

**Audit Trail**:
- Event: `ROLLBACK_CANCEL_APPROVED`
- Includes reason and metadata

### 3. Cancel Queued (QUEUED → CANCELED)

**Use Case**: Cancel a task before execution starts.

**Safety**: ✅ Safe - queued but not yet executing

```python
# Cancel a queued task
task = rollback_service.cancel_queued(
    task_id="task_xyz",
    actor="system",
    reason="System maintenance scheduled - canceling queued tasks",
    metadata={"maintenance_window": "2024-01-15 02:00-04:00"}
)
```

**Requirements**:
- Task must be in QUEUED state
- Reason is REQUIRED
- Cannot cancel once execution starts (RUNNING state)

### 4. Restart as New Draft

**Use Case**: Retry or restart a task with a fresh start.

**Safety**: ✅ Safe - creates NEW task, preserves original history

**Key Feature**: This is the ONLY way to "restart" a task. It creates a completely new task with a new task_id, avoiding any history tampering.

```python
# Create new draft from existing task
new_task = rollback_service.create_new_draft_from_task(
    source_task_id="task_xyz",
    actor="user@example.com",
    reason="Retrying with updated requirements",
    title_override="[Retry] Implement Feature X",  # Optional
    metadata={"retry_count": 1}  # Optional
)

print(f"New task created: {new_task.task_id}")  # New ULID
print(f"Status: {new_task.status}")  # draft
print(f"Source: {new_task.metadata['source_task']['task_id']}")  # task_xyz
```

**Behavior**:
- Creates new task with new task_id
- Copies title, metadata, routing info from source
- Adds `source_task` to metadata with link to original
- Records audit in BOTH tasks (source and new)
- Creates lineage entry linking new task to source

**Metadata Added**:
```json
{
  "source_task": {
    "task_id": "01HN2KX...",
    "title": "Original Task Title",
    "original_status": "failed",
    "restart_reason": "Retrying with updated requirements",
    "restarted_by": "user@example.com",
    "restarted_at": "2024-01-15T10:30:00Z"
  },
  "source_metadata": { /* Original task metadata */ }
}
```

## Operations NOT Allowed

### ❌ Rollback Completed Tasks

```python
# This will raise RollbackNotAllowedError
task = rollback_service.cancel_draft(
    task_id="completed_task",
    actor="user",
    reason="Undo completion"
)
# Error: Cannot cancel task in 'done' state
```

**Why**: Completed tasks represent historical facts. Modifying them would break audit trails and create confusion.

**Alternative**: Use `create_new_draft_from_task()` to create a corrective task.

### ❌ Direct State Rollback

```python
# This is NOT available - no arbitrary rollback
task = rollback_service.rollback_to_state(
    task_id="task_xyz",
    target_state="draft"
)
# Method does not exist
```

**Why**: Arbitrary rollback violates the state machine rules and could create invalid state transitions.

**Alternative**: Use state machine transitions or create new draft.

### ❌ Modify Historical Records

```python
# This is NOT allowed
task.status = "draft"  # Direct modification
task_manager.update_task_status(task_id, "draft")  # Bypass state machine
```

**Why**: All state changes must go through the state machine to ensure validation and audit logging.

## Query Operations

### Check Rollback Options

```python
# Get available rollback options for a task
options = rollback_service.get_rollback_options("task_xyz")

print(options)
# {
#   "task_id": "task_xyz",
#   "current_state": "approved",
#   "can_cancel": True,
#   "can_restart_as_new_draft": True,
#   "allowed_operations": ["cancel_approved", "restart_as_new_draft"],
#   "reasoning": "Approved task can be canceled or restarted as new draft"
# }
```

### Check if Task Can Be Canceled

```python
# Quick check
can_cancel = rollback_service.can_cancel("task_xyz")
can_restart = rollback_service.can_restart("task_xyz")
```

## Rollback Decision Matrix

| Current State | Cancel Draft | Cancel Approved | Cancel Queued | Restart as New |
|---------------|--------------|-----------------|---------------|----------------|
| DRAFT         | ✅           | ❌              | ❌            | ✅             |
| APPROVED      | ❌           | ✅              | ❌            | ✅             |
| QUEUED        | ❌           | ❌              | ✅            | ✅             |
| RUNNING       | ❌           | ❌              | ❌            | ✅             |
| VERIFYING     | ❌           | ❌              | ❌            | ✅             |
| VERIFIED      | ❌           | ❌              | ❌            | ✅             |
| DONE          | ❌           | ❌              | ❌            | ✅             |
| FAILED        | ❌           | ❌              | ❌            | ✅             |
| CANCELED      | ❌           | ❌              | ❌            | ✅             |

**Key Insights**:
- Only pre-execution states (DRAFT, APPROVED, QUEUED) can be canceled
- Restart as new draft is ALWAYS available (creates new task)
- Terminal states (DONE, FAILED, CANCELED) cannot be canceled

## Error Handling

### RollbackNotAllowedError

```python
from agentos.core.task.rollback import RollbackNotAllowedError

try:
    task = rollback_service.cancel_draft("completed_task", "user", "Undo")
except RollbackNotAllowedError as e:
    print(f"Rollback not allowed: {e}")
    # Get valid options instead
    options = rollback_service.get_rollback_options("completed_task")
    print(f"Available operations: {options['allowed_operations']}")
```

### TaskNotFoundError

```python
from agentos.core.task.errors import TaskNotFoundError

try:
    task = rollback_service.cancel_draft("nonexistent", "user", "Cancel")
except TaskNotFoundError as e:
    print(f"Task not found: {e}")
```

## Audit Trail

All rollback operations are fully audited in the `task_audits` table:

### Cancel Operations

```json
{
  "event_type": "ROLLBACK_CANCEL_DRAFT",
  "level": "info",
  "payload": {
    "operation": "cancel_draft",
    "actor": "user@example.com",
    "reason": "Task no longer needed",
    "rollback_metadata": {},
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Restart Operations

```json
{
  "event_type": "ROLLBACK_RESTART_AS_NEW_DRAFT",
  "level": "info",
  "payload": {
    "operation": "restart_as_new_draft",
    "actor": "user@example.com",
    "reason": "Retrying with updated requirements",
    "rollback_metadata": {
      "new_task_id": "01HN3PQ...",
      "new_title": "[Retry] Implement Feature X"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Integration with State Machine

The rollback service works WITH the state machine, not against it:

```python
from agentos.core.task.service import TaskService
from agentos.core.task.rollback import TaskRollbackService

task_service = TaskService()
rollback_service = TaskRollbackService()

# Create draft
task = task_service.create_draft_task(title="Test Task", created_by="user")

# Approve (state machine)
task = task_service.approve_task(task.task_id, "approver", "Approved")

# Cancel approved (rollback service)
task = rollback_service.cancel_approved(task.task_id, "user", "No longer needed")

# State machine transition is used internally
print(task.status)  # canceled
```

## Best Practices

### 1. Always Provide Reason

```python
# ❌ Bad: No reason (will work but poor audit trail)
task = rollback_service.cancel_draft(task_id, "user", "Canceled")

# ✅ Good: Clear reason
task = rollback_service.cancel_approved(
    task_id,
    "user",
    "Requirements changed - feature replaced by CR-456"
)
```

### 2. Use Metadata for Context

```python
# ✅ Good: Add context to metadata
task = rollback_service.cancel_queued(
    task_id,
    "system",
    "Emergency maintenance",
    metadata={
        "maintenance_type": "database_upgrade",
        "scheduled_by": "ops_team",
        "ticket": "OPS-789"
    }
)
```

### 3. Check Before Canceling

```python
# ✅ Good: Check first
if rollback_service.can_cancel(task_id):
    task = rollback_service.cancel_draft(task_id, "user", "Not needed")
else:
    # Provide alternative
    options = rollback_service.get_rollback_options(task_id)
    print(f"Cannot cancel. Available: {options['allowed_operations']}")
```

### 4. Use Restart for Corrections

```python
# ✅ Good: Create corrective task instead of rollback
if task.status == "done" and needs_correction:
    corrective_task = rollback_service.create_new_draft_from_task(
        source_task_id=task.task_id,
        actor="user",
        reason="Creating corrective task - original had bug X",
        title_override=f"[Corrective] {task.title}"
    )
```

## CLI Integration

The rollback service can be integrated into CLI commands:

```bash
# Cancel a draft task
agentos task rollback cancel-draft <task_id> --reason "Not needed"

# Cancel an approved task
agentos task rollback cancel-approved <task_id> --reason "Requirements changed"

# Restart as new draft
agentos task rollback restart <task_id> --reason "Retry with fix"
```

## Security Considerations

1. **Authorization**: Implement proper authorization checks before allowing rollback operations
2. **Actor Tracking**: Always track who performed the rollback (for accountability)
3. **Rate Limiting**: Consider rate limiting restart operations to prevent abuse
4. **Approval Requirements**: For production, consider requiring approval for certain rollback operations

## Future Enhancements (Not in MVP)

The following features are NOT in the MVP but could be added later:

- Bulk cancellation (cancel multiple tasks at once)
- Scheduled cancellation (cancel at specific time)
- Conditional rollback (cancel if condition met)
- Rollback workflows (multi-step rollback process)
- Rollback permissions (role-based access control)

## References

- State Machine: `docs/task/task_state_machine.md`
- Task Service: `agentos/core/task/service.py`
- Rollback Implementation: `agentos/core/task/rollback.py`
- Tests: `tests/unit/task/test_task_rollback_rules.py`

## Compliance

This rollback strategy complies with:

- Task #1: State machine foundation (uses state machine for all transitions)
- Task #2: Complete audit trails (all operations fully audited)
- Task #3: State machine enforcement (no bypassing of state machine)
- Safety principles: No history tampering, immutable completed tasks
