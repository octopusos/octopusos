# Task #4: Exit Reason - Quick Reference

## Overview

The `exit_reason` field clarifies why task execution stopped, preventing "false completion" scenarios.

---

## Exit Reason Values

| exit_reason | When to use | Typical status |
|------------|-------------|----------------|
| `done` | Task completed successfully or paused normally | `succeeded`, `awaiting_approval` |
| `max_iterations` | Exceeded iteration limit | `failed` |
| `blocked` | Execution cannot continue (e.g., AUTONOMOUS hit approval) | `blocked` |
| `fatal_error` | Unrecoverable error | `failed` |
| `user_cancelled` | User explicitly canceled | `canceled` |
| `unknown` | Fallback for unclear cases | any |

---

## Common Scenarios

### ✅ Task Completes Successfully
```python
task_manager.update_task_exit_reason(task_id, "done", status="succeeded")
```

### ⚠️ AUTONOMOUS Mode Hits Approval Checkpoint (BLOCKED)
```python
if run_mode == "autonomous" and needs_approval:
    task_manager.update_task_exit_reason(task_id, "blocked", status="blocked")
```

### 🔄 ASSISTED Mode Pauses for Approval (Normal)
```python
if run_mode in ["assisted", "interactive"] and needs_approval:
    task_manager.update_task_exit_reason(task_id, "done")  # Normal pause
```

### ❌ Fatal Error
```python
try:
    execute_task()
except Exception as e:
    task_manager.update_task_exit_reason(task_id, "fatal_error", status="failed")
```

### ⏱️ Max Iterations Exceeded
```python
if iteration >= max_iterations:
    task_manager.update_task_exit_reason(task_id, "max_iterations", status="failed")
```

### 🛑 User Cancels Task
```python
task_manager.update_task_exit_reason(task_id, "user_cancelled", status="canceled")
```

---

## AUTONOMOUS Mode Blocking Logic

**Critical Pattern**:
```python
if next_status == "awaiting_approval":
    metadata = TaskMetadata.from_dict(task.metadata)
    run_mode = metadata.run_mode.value

    if run_mode == "autonomous":
        # AUTONOMOUS should never pause - this is BLOCKING
        task_manager.update_task_exit_reason(task_id, "blocked", status="blocked")
        logger.warning(f"Task {task_id} blocked: AUTONOMOUS mode cannot pause for approval")
    else:
        # INTERACTIVE/ASSISTED: normal pause
        task_manager.update_task_exit_reason(task_id, "done")
        logger.info(f"Task {task_id} paused for approval")
```

**Why?**
- AUTONOMOUS = "run without human intervention"
- If it needs approval, it's misconfigured → should be BLOCKED
- ASSISTED/INTERACTIVE = approval is expected → normal pause

---

## State Machine

### BLOCKED State Transitions

```
RUNNING → BLOCKED     (execution hit blocking condition)
BLOCKED → QUEUED      (recovery: unblock and retry)
BLOCKED → CANCELED    (give up on blocked task)
```

**BLOCKED is a terminal state** - requires manual intervention.

---

## API Reference

### TaskManager.update_task_exit_reason()

```python
task_manager.update_task_exit_reason(
    task_id="01JQ...",
    exit_reason="blocked",      # Required: one of the valid values
    status="blocked"            # Optional: update status simultaneously
)
```

### TaskManager.get_task()

```python
task = task_manager.get_task(task_id)
print(f"Status: {task.status}, Exit reason: {task.exit_reason}")
```

---

## SQL Queries

### Find all blocked tasks
```sql
SELECT task_id, title, created_at
FROM tasks
WHERE exit_reason = 'blocked'
ORDER BY created_at DESC;
```

### Find tasks that hit max iterations
```sql
SELECT task_id, title, status, exit_reason
FROM tasks
WHERE exit_reason = 'max_iterations';
```

### Success rate by exit_reason
```sql
SELECT
    exit_reason,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM tasks WHERE exit_reason IS NOT NULL), 2) as percentage
FROM tasks
WHERE exit_reason IS NOT NULL
GROUP BY exit_reason
ORDER BY count DESC;
```

### Tasks by status and exit_reason
```sql
SELECT status, exit_reason, COUNT(*) as count
FROM tasks
WHERE exit_reason IS NOT NULL
GROUP BY status, exit_reason
ORDER BY count DESC;
```

---

## Testing Checklist

When implementing task runner logic:

- [ ] Record exit_reason at all exit points
- [ ] Check run_mode before treating awaiting_approval as normal
- [ ] Use "blocked" for AUTONOMOUS mode hitting approval
- [ ] Use "done" for successful completion or normal pause
- [ ] Use "max_iterations" for iteration limit
- [ ] Use "fatal_error" for unrecoverable errors
- [ ] Log appropriate audit entries for each exit_reason

---

## Migration Notes

### Database
```bash
sqlite3 agentos.db < agentos/store/migrations/schema_v28.sql
```

### Code Updates

**Before**:
```python
task_manager.update_task_status(task_id, "failed")
```

**After**:
```python
task_manager.update_task_exit_reason(task_id, "fatal_error", status="failed")
```

---

## Common Mistakes to Avoid

❌ **Wrong**: Treating AUTONOMOUS awaiting_approval as normal
```python
if next_status == "awaiting_approval":
    break  # All modes treated the same
```

✅ **Correct**: Check run_mode
```python
if next_status == "awaiting_approval":
    if run_mode == "autonomous":
        # BLOCKED - shouldn't need approval
        task_manager.update_task_exit_reason(task_id, "blocked", status="blocked")
    else:
        # Normal pause
        task_manager.update_task_exit_reason(task_id, "done")
```

❌ **Wrong**: Not recording exit_reason
```python
if iteration >= max_iterations:
    task_manager.update_task_status(task_id, "failed")  # Missing exit_reason!
```

✅ **Correct**: Always record exit_reason
```python
if iteration >= max_iterations:
    task_manager.update_task_exit_reason(task_id, "max_iterations", status="failed")
```

---

## Quick Decision Tree

```
Task execution stops
    ├─ Completed successfully? → exit_reason="done", status="succeeded"
    ├─ Needs approval?
    │   ├─ run_mode = "autonomous"? → exit_reason="blocked", status="blocked"
    │   └─ run_mode = "assisted/interactive"? → exit_reason="done", status="awaiting_approval"
    ├─ Hit max iterations? → exit_reason="max_iterations", status="failed"
    ├─ Fatal error? → exit_reason="fatal_error", status="failed"
    ├─ User canceled? → exit_reason="user_cancelled", status="canceled"
    └─ Unknown? → exit_reason="unknown"
```

---

## Related Documentation

- Full implementation report: `TASK4_EXIT_REASON_IMPLEMENTATION_REPORT.md`
- Test suite: `test_task4_exit_reason.py`
- Schema migration: `agentos/store/migrations/schema_v28.sql`
- State machine: `agentos/core/task/state_machine.py`

---

**Last Updated**: 2026-01-29
**Version**: v0.28.0
