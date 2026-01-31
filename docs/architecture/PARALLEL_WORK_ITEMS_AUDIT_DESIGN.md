# Parallel Work Items: Audit Design (PR-D)

## ⚠️ Critical Principle

**Parallelism ≠ Loss of Audit Order**

When implementing parallel work item execution (PR-D), we MUST preserve audit trail integrity. This document defines the architecture for maintaining logical order even with concurrent execution.

---

## Problem Statement

### Current State (Serial Execution - v1.0)

```python
for work_item in work_items:
    execute(work_item)  # Sequential
    # Audit entries appear in execution order
```

**Audit trail** (clean, sequential):
```sql
1. WORK_ITEM_EXECUTING_item-1   2026-01-29 10:00:00
2. WORK_ITEM_COMPLETED_item-1   2026-01-29 10:00:18
3. WORK_ITEM_EXECUTING_item-2   2026-01-29 10:00:19
4. WORK_ITEM_COMPLETED_item-2   2026-01-29 10:00:37
5. WORK_ITEM_EXECUTING_item-3   2026-01-29 10:00:38
6. WORK_ITEM_COMPLETED_item-3   2026-01-29 10:00:56
```

**Logical order = Wall-clock order** ✅

---

### Future State (Parallel Execution - v1.1)

```python
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(execute, item) for item in work_items]
    # Work items execute concurrently
```

**Audit trail** (wall-clock order):
```sql
1. WORK_ITEM_EXECUTING_item-1   2026-01-29 10:00:00.001
2. WORK_ITEM_EXECUTING_item-2   2026-01-29 10:00:00.003  # Started before item-1 finished!
3. WORK_ITEM_EXECUTING_item-3   2026-01-29 10:00:00.005
4. WORK_ITEM_COMPLETED_item-2   2026-01-29 10:00:15.000  # Finished first (fastest)
5. WORK_ITEM_COMPLETED_item-1   2026-01-29 10:00:18.000
6. WORK_ITEM_COMPLETED_item-3   2026-01-29 10:00:20.000
```

**Problem**: Wall-clock order ≠ Logical order ❌

**Questions**:
- Which work_item was assigned first?
- What was the intended execution order?
- How do we reconstruct the planning decision?

---

## Solution: Preserve Logical Order Metadata

### Key Principle

**Every audit entry MUST have both**:
1. **Wall-clock timestamp** - When it actually happened (for performance analysis)
2. **Logical order** - Where it belongs in the task flow (for reconstruction)

---

## Database Schema Extension

### Current Schema

```sql
CREATE TABLE task_audits (
    audit_id INTEGER PRIMARY KEY,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    level TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL,  -- Wall-clock timestamp
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
```

### Extended Schema (v0.29)

```sql
CREATE TABLE task_audits (
    audit_id INTEGER PRIMARY KEY,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    level TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL,           -- Wall-clock timestamp (when it happened)

    -- NEW: Logical ordering fields
    parent_task_id TEXT,                -- Parent task (for hierarchical tasks)
    work_item_id TEXT,                  -- Work item ID (if part of work items)
    logical_order INTEGER,              -- Sequence number (0, 1, 2, ...)
    execution_context TEXT,             -- "serial" or "parallel_{worker_id}"

    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id)
);

-- Index for logical order queries
CREATE INDEX idx_audits_logical_order ON task_audits(task_id, logical_order);

-- Index for work item queries
CREATE INDEX idx_audits_work_item ON task_audits(task_id, work_item_id);
```

---

## Audit Entry Structure

### Example: Parallel Execution

```python
# Work item 1 (started at T+0ms, completed at T+18s)
audit_entry_1_start = {
    "audit_id": 101,
    "task_id": "task-01HXXX",
    "event_type": "WORK_ITEM_EXECUTING",
    "created_at": "2026-01-29T10:00:00.001Z",  # Wall-clock
    "parent_task_id": "task-01HXXX",
    "work_item_id": "item-1",
    "logical_order": 0,                         # First in planning order
    "execution_context": "parallel_worker_1",
    "payload": {
        "work_item_title": "Implement frontend UI",
        "assigned_to": "worker_1"
    }
}

audit_entry_1_complete = {
    "audit_id": 105,
    "task_id": "task-01HXXX",
    "event_type": "WORK_ITEM_COMPLETED",
    "created_at": "2026-01-29T10:00:18.000Z",  # Wall-clock (finished 2nd)
    "parent_task_id": "task-01HXXX",
    "work_item_id": "item-1",
    "logical_order": 0,                         # Still first in planning order
    "execution_context": "parallel_worker_1",
    "payload": {
        "status": "succeeded",
        "duration_seconds": 18
    }
}

# Work item 2 (started at T+3ms, completed at T+15s - FINISHED FIRST)
audit_entry_2_start = {
    "audit_id": 102,
    "task_id": "task-01HXXX",
    "event_type": "WORK_ITEM_EXECUTING",
    "created_at": "2026-01-29T10:00:00.003Z",  # Wall-clock
    "parent_task_id": "task-01HXXX",
    "work_item_id": "item-2",
    "logical_order": 1,                         # Second in planning order
    "execution_context": "parallel_worker_2",
    "payload": {
        "work_item_title": "Implement backend API",
        "assigned_to": "worker_2"
    }
}

audit_entry_2_complete = {
    "audit_id": 104,
    "task_id": "task-01HXXX",
    "event_type": "WORK_ITEM_COMPLETED",
    "created_at": "2026-01-29T10:00:15.000Z",  # Wall-clock (finished FIRST!)
    "parent_task_id": "task-01HXXX",
    "work_item_id": "item-2",
    "logical_order": 1,                         # Still second in planning order
    "execution_context": "parallel_worker_2",
    "payload": {
        "status": "succeeded",
        "duration_seconds": 15
    }
}
```

---

## Query Patterns

### Query 1: Logical Order (Reconstruction)

```sql
-- Get audit trail in LOGICAL order (how it was planned)
SELECT
    event_type,
    work_item_id,
    logical_order,
    created_at,
    execution_context
FROM task_audits
WHERE task_id = 'task-01HXXX'
  AND work_item_id IS NOT NULL
ORDER BY logical_order, created_at;

-- Result (planning order preserved):
┌─────────────────────┬────────────┬───────────────┬─────────────────────┬─────────────────────┐
│ event_type          │ work_item  │ logical_order │ created_at          │ execution_context   │
├─────────────────────┼────────────┼───────────────┼─────────────────────┼─────────────────────┤
│ WORK_ITEM_EXECUTING │ item-1     │ 0             │ 10:00:00.001        │ parallel_worker_1   │
│ WORK_ITEM_COMPLETED │ item-1     │ 0             │ 10:00:18.000        │ parallel_worker_1   │
│ WORK_ITEM_EXECUTING │ item-2     │ 1             │ 10:00:00.003        │ parallel_worker_2   │
│ WORK_ITEM_COMPLETED │ item-2     │ 1             │ 10:00:15.000        │ parallel_worker_2   │
│ WORK_ITEM_EXECUTING │ item-3     │ 2             │ 10:00:00.005        │ parallel_worker_3   │
│ WORK_ITEM_COMPLETED │ item-3     │ 2             │ 10:00:20.000        │ parallel_worker_3   │
└─────────────────────┴────────────┴───────────────┴─────────────────────┴─────────────────────┘
```

**Interpretation**: Item-1 was planned first, item-2 second, item-3 third, even though item-2 finished first by wall-clock.

---

### Query 2: Wall-Clock Order (Performance Analysis)

```sql
-- Get audit trail in WALL-CLOCK order (what actually happened)
SELECT
    event_type,
    work_item_id,
    logical_order,
    created_at,
    execution_context
FROM task_audits
WHERE task_id = 'task-01HXXX'
  AND work_item_id IS NOT NULL
ORDER BY created_at;

-- Result (actual execution order):
┌─────────────────────┬────────────┬───────────────┬─────────────────────┬─────────────────────┐
│ event_type          │ work_item  │ logical_order │ created_at          │ execution_context   │
├─────────────────────┼────────────┼───────────────┼─────────────────────┼─────────────────────┤
│ WORK_ITEM_EXECUTING │ item-1     │ 0             │ 10:00:00.001        │ parallel_worker_1   │
│ WORK_ITEM_EXECUTING │ item-2     │ 1             │ 10:00:00.003        │ parallel_worker_2   │
│ WORK_ITEM_EXECUTING │ item-3     │ 2             │ 10:00:00.005        │ parallel_worker_3   │
│ WORK_ITEM_COMPLETED │ item-2     │ 1             │ 10:00:15.000        │ parallel_worker_2   │ <- Finished first!
│ WORK_ITEM_COMPLETED │ item-1     │ 0             │ 10:00:18.000        │ parallel_worker_1   │
│ WORK_ITEM_COMPLETED │ item-3     │ 2             │ 10:00:20.000        │ parallel_worker_3   │
└─────────────────────┴────────────┴───────────────┴─────────────────────┴─────────────────────┘
```

**Interpretation**: Item-2 completed fastest (15s), item-1 took 18s, item-3 took 20s.

---

### Query 3: Work Item Timeline

```sql
-- Timeline for a specific work item
SELECT
    event_type,
    created_at,
    CAST((julianday(created_at) - julianday(MIN(created_at) OVER ())) * 86400 AS INTEGER) as elapsed_seconds
FROM task_audits
WHERE task_id = 'task-01HXXX'
  AND work_item_id = 'item-2'
ORDER BY created_at;

-- Result:
┌─────────────────────┬─────────────────────┬──────────────────┐
│ event_type          │ created_at          │ elapsed_seconds  │
├─────────────────────┼─────────────────────┼──────────────────┤
│ WORK_ITEM_EXECUTING │ 10:00:00.003        │ 0                │
│ WORK_ITEM_COMPLETED │ 10:00:15.000        │ 15               │
└─────────────────────┴─────────────────────┴──────────────────┘

Duration: 15 seconds
```

---

## Implementation Guidelines

### 1. Work Item Assignment

```python
# During planning stage
work_items = extract_work_items(plan)

# Assign logical_order at extraction time
for idx, work_item in enumerate(work_items):
    work_item.logical_order = idx  # 0, 1, 2, ...

# Save to metadata
task.metadata["work_items"] = [item.to_dict() for item in work_items]
```

### 2. Parallel Execution

```python
# During executing stage
from concurrent.futures import ThreadPoolExecutor

work_items = load_work_items(task.metadata)

def execute_work_item_with_audit(work_item):
    # Start audit (with logical_order preserved)
    audit_entry(
        task_id=task.task_id,
        event_type="WORK_ITEM_EXECUTING",
        work_item_id=work_item.work_item_id,
        logical_order=work_item.logical_order,  # From planning
        execution_context=f"parallel_worker_{threading.current_thread().ident}"
    )

    # Execute
    result = execute(work_item)

    # Complete audit (same logical_order)
    audit_entry(
        task_id=task.task_id,
        event_type="WORK_ITEM_COMPLETED",
        work_item_id=work_item.work_item_id,
        logical_order=work_item.logical_order,  # Same as start
        execution_context=f"parallel_worker_{threading.current_thread().ident}",
        payload={"status": result.status, "duration": result.duration}
    )

    return result

# Execute in parallel
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(execute_work_item_with_audit, item)
               for item in work_items]
    results = [f.result() for f in futures]
```

### 3. Audit Helper

```python
# agentos/core/task/audit_helper.py

def log_work_item_event(
    task_id: str,
    event_type: str,
    work_item_id: str,
    logical_order: int,
    execution_context: str,
    payload: dict = None
):
    """
    Log work item event with logical order preserved.

    Args:
        task_id: Parent task ID
        event_type: Event type (WORK_ITEM_EXECUTING, WORK_ITEM_COMPLETED, etc.)
        work_item_id: Work item ID
        logical_order: Logical sequence number (from planning)
        execution_context: Execution context (serial or parallel_worker_N)
        payload: Additional data
    """
    import json
    from datetime import datetime, timezone
    from agentos.store import get_db

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO task_audits (
            task_id, event_type, level, payload, created_at,
            parent_task_id, work_item_id, logical_order, execution_context
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            event_type,
            "info",
            json.dumps(payload) if payload else None,
            datetime.now(timezone.utc).isoformat(),
            task_id,  # parent_task_id same as task_id for work items
            work_item_id,
            logical_order,
            execution_context
        )
    )

    conn.commit()
    conn.close()
```

---

## Validation Tests

### Test 1: Logical Order Preserved

```python
def test_parallel_execution_preserves_logical_order():
    """Verify logical_order is preserved even with concurrent execution"""

    # Execute 3 work items in parallel
    task = create_task_with_work_items(3)
    execute_parallel(task)

    # Query in logical order
    audits = get_audits(task_id, order_by="logical_order")

    # Assert logical order matches planning order
    assert audits[0].work_item_id == "item-1"
    assert audits[0].logical_order == 0
    assert audits[1].work_item_id == "item-1"  # COMPLETED event
    assert audits[1].logical_order == 0        # Same logical_order

    assert audits[2].work_item_id == "item-2"
    assert audits[2].logical_order == 1
    # ... and so on
```

### Test 2: Wall-Clock Order Reflects Reality

```python
def test_parallel_execution_wall_clock_order():
    """Verify wall-clock timestamps reflect actual execution order"""

    task = create_task_with_work_items(3)
    execute_parallel(task)

    # Query in wall-clock order
    audits = get_audits(task_id, order_by="created_at")

    # Wall-clock order may differ from logical order
    # (that's the whole point!)
    completed_events = [a for a in audits if a.event_type == "WORK_ITEM_COMPLETED"]

    # Assert fastest work item completed first
    # (even if it wasn't logical_order == 0)
    assert completed_events[0].created_at < completed_events[1].created_at
    assert completed_events[1].created_at < completed_events[2].created_at
```

---

## Benefits

1. **Reconstruction** - Can replay task in planning order
2. **Performance Analysis** - Can identify slow work items
3. **Debugging** - Can trace parallel execution issues
4. **Compliance** - Clear audit trail even with concurrency
5. **Backward Compatibility** - Serial execution still works (logical_order == wall-clock order)

---

## Migration from v1.0 to v1.1

### Backward Compatibility

- Existing `task_audits` entries without `logical_order` → treated as `logical_order = NULL`
- Query with `ORDER BY COALESCE(logical_order, audit_id)` for backward compatibility
- Serial execution continues to work (just adds `logical_order` field)

### Migration Script

```sql
-- Add new columns (nullable for backward compatibility)
ALTER TABLE task_audits ADD COLUMN parent_task_id TEXT;
ALTER TABLE task_audits ADD COLUMN work_item_id TEXT;
ALTER TABLE task_audits ADD COLUMN logical_order INTEGER;
ALTER TABLE task_audits ADD COLUMN execution_context TEXT;

-- Add indexes
CREATE INDEX idx_audits_logical_order ON task_audits(task_id, logical_order);
CREATE INDEX idx_audits_work_item ON task_audits(task_id, work_item_id);

-- Backfill existing work item audits (if possible)
-- This is optional - only if we can infer logical_order from existing data
UPDATE task_audits
SET execution_context = 'serial'
WHERE event_type LIKE 'WORK_ITEM_%'
  AND execution_context IS NULL;
```

---

## Conclusion

**The Iron Rule**: When implementing parallel work items, ALWAYS preserve logical order in audit entries.

**Implementation Checklist**:
- ✅ Add `logical_order`, `work_item_id`, `parent_task_id`, `execution_context` to `task_audits`
- ✅ Assign `logical_order` during planning (before execution)
- ✅ Preserve `logical_order` in all audit entries (even concurrent ones)
- ✅ Query by `logical_order` for reconstruction
- ✅ Query by `created_at` for performance analysis
- ✅ Test both serial and parallel execution
- ✅ Verify backward compatibility

**This design ensures AgentOS can scale to parallel execution without losing the audit integrity that makes it trustworthy.**
