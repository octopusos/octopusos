# Task #3: S3 - Quick Start Guide

**State Machine Enforcement for Task Operations**

## What Changed?

All task status changes now go through a centralized `TaskService` that enforces state machine validation.

## Quick Migration

### Before (Old Way - Deprecated)
```python
from agentos.core.task import TaskManager

manager = TaskManager()
task = manager.create_task(title="My Task")
manager.update_task_status(task.task_id, "running")  # ❌ Deprecated
```

### After (New Way - Recommended)
```python
from agentos.core.task.service import TaskService

service = TaskService()
task = service.create_draft_task(title="My Task", created_by="user")
task = service.approve_task(task.task_id, actor="approver", reason="Approved")
task = service.queue_task(task.task_id, actor="scheduler", reason="Queued")
task = service.start_task(task.task_id, actor="runner", reason="Running")
```

## Common Operations

### Create Task
```python
task = service.create_draft_task(
    title="Task Title",
    created_by="username",
    metadata={"key": "value"}
)
# Task starts in DRAFT state
```

### Approve Task
```python
task = service.approve_task(
    task_id=task_id,
    actor="approver_name",
    reason="Task approved for execution"
)
```

### Execute Task
```python
# Queue
task = service.queue_task(task_id, actor="scheduler", reason="Ready")

# Start
task = service.start_task(task_id, actor="runner", reason="Starting")

# Complete
task = service.complete_task_execution(task_id, actor="runner", reason="Done")

# Verify
task = service.verify_task(task_id, actor="verifier", reason="Verified")

# Mark Done
task = service.mark_task_done(task_id, actor="user", reason="Complete")
```

### Handle Failure
```python
# Fail
task = service.fail_task(
    task_id,
    actor="runner",
    reason="Error occurred",
    metadata={"error": "details"}
)

# Retry
task = service.retry_failed_task(
    task_id,
    actor="user",
    reason="Fixed issue, retrying"
)
```

### Cancel Task
```python
task = service.cancel_task(
    task_id,
    actor="user",
    reason="No longer needed"
)
```

## State Transition Flow

```
DRAFT → APPROVED → QUEUED → RUNNING → VERIFYING → VERIFIED → DONE
                              ↓           ↓
                           FAILED     FAILED
                              ↓
                           QUEUED (retry)

Any non-terminal state → CANCELED
```

## Error Handling

```python
from agentos.core.task.errors import InvalidTransitionError

try:
    service.start_task(draft_task_id, actor="runner", reason="Starting")
except InvalidTransitionError as e:
    print(f"Invalid transition: {e}")
    # Handle error - task is not in correct state
```

## Check Valid Transitions

```python
valid_states = service.get_valid_transitions(task_id)
print(f"Can transition to: {valid_states}")
```

## View Transition History

```python
history = service.get_transition_history(task_id)
for transition in history:
    print(f"{transition['from_state']} → {transition['to_state']} "
          f"by {transition['actor']}: {transition['reason']}")
```

## Key Files

- **Service Layer**: `agentos/core/task/service.py`
- **State Machine**: `agentos/core/task/state_machine.py`
- **States**: `agentos/core/task/states.py`
- **Errors**: `agentos/core/task/errors.py`
- **Tests**: `tests/unit/task/test_task_api_enforces_state_machine.py`
- **Migration Guide**: `agentos/core/task/MIGRATION_GUIDE.md`
- **Examples**: `examples/task_service_usage.py`

## Running Examples

```bash
python examples/task_service_usage.py
```

## Running Tests

```bash
pytest tests/unit/task/test_task_api_enforces_state_machine.py -v
```

## Benefits

✅ State machine validation (no invalid transitions)
✅ Automatic audit logging (actor/reason/metadata)
✅ Clear, named operations (self-documenting)
✅ Type safety and error handling
✅ Easy to test and extend

## Need Help?

1. Read the full migration guide: `agentos/core/task/MIGRATION_GUIDE.md`
2. Check examples: `examples/task_service_usage.py`
3. Review tests: `tests/unit/task/test_task_api_enforces_state_machine.py`
4. See completion report: `TASK_S3_COMPLETION_REPORT.md`
