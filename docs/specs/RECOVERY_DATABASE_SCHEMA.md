# Recovery System Database Schema

**Version**: 0.30.0
**Purpose**: Database foundation for resumable task execution (断点续跑)
**Created**: 2026-01-29

## Overview

The Recovery System provides database infrastructure for reliable task recovery after interruption or failure. It consists of three core tables:

1. **work_items** - Manages recoverable work units with lease-based concurrency control
2. **checkpoints** - Append-only evidence registry for execution progress
3. **idempotency_keys** - Prevents duplicate execution through request deduplication

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Recovery System                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐  │
│  │ work_items   │──┬──>│ checkpoints  │      │idempotency│ │
│  │              │  │   │              │      │  _keys   │  │
│  │ - lease mgmt │  │   │ - snapshots  │      │          │  │
│  │ - heartbeat  │  │   │ - sequences  │      │ - dedup  │  │
│  │ - retry      │  │   │ - evidence   │      │ - cache  │  │
│  └──────┬───────┘  │   └──────────────┘      └──────────┘  │
│         │          │                                         │
│         v          │                                         │
│  ┌──────────────┐  │                                         │
│  │   tasks      │<─┘                                         │
│  │ (existing)   │                                            │
│  └──────────────┘                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Entity Relationship Diagram

```
┌────────────────┐
│     tasks      │
│ ─────────────  │
│ task_id (PK)   │
└────────┬───────┘
         │ 1
         │
         │ N
    ┌────┴────────────────────────────┐
    │                                 │
    │ N                               │ N
┌───┴──────────────┐         ┌────────┴────────┐
│   work_items     │    N    │   checkpoints   │
│ ──────────────── │ ───────>│ ──────────────  │
│ work_item_id (PK)│    0..1 │ checkpoint_id   │
│ task_id (FK)     │<────────│ task_id (FK)    │
│ lease_holder     │         │ work_item_id    │
│ lease_expires_at │         │ sequence_number │
│ heartbeat_at     │         │ snapshot_data   │
│ retry_count      │         └─────────────────┘
└──────────────────┘
         │
         │ N
         │
         │ 0..1
┌────────┴───────────┐
│ idempotency_keys   │
│ ────────────────── │
│ idempotency_key(PK)│
│ task_id (FK)       │
│ work_item_id (FK)  │
│ request_hash       │
│ response_data      │
└────────────────────┘
```

---

## Table 1: work_items

### Purpose

Manages the lifecycle of recoverable work units with distributed lease-based concurrency control. Each work item represents an atomic unit of work that can be retried independently.

### Schema

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| **work_item_id** | TEXT | PRIMARY KEY | ULID or UUID |
| **task_id** | TEXT | NOT NULL, FK | Links to parent task |
| **work_type** | TEXT | NOT NULL | Type of work (e.g., 'tool_execution', 'llm_call', 'subtask') |
| **status** | TEXT | NOT NULL, DEFAULT 'pending' | Current state: pending, in_progress, completed, failed, expired |
| **priority** | INTEGER | DEFAULT 0 | Higher values = higher priority |
| **lease_holder** | TEXT | NULL | Worker/process ID holding the lease |
| **lease_acquired_at** | TIMESTAMP | NULL | When lease was acquired |
| **lease_expires_at** | TIMESTAMP | NULL | When lease expires |
| **heartbeat_at** | TIMESTAMP | NULL | Last heartbeat timestamp |
| **retry_count** | INTEGER | DEFAULT 0 | Current retry attempt |
| **max_retries** | INTEGER | DEFAULT 3 | Maximum retry attempts |
| **input_data** | TEXT | NULL | Input parameters (JSON) |
| **output_data** | TEXT | NULL | Execution result (JSON) |
| **error_message** | TEXT | NULL | Error details if failed |
| **created_at** | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |
| **started_at** | TIMESTAMP | NULL | First execution start |
| **completed_at** | TIMESTAMP | NULL | Completion time |
| **updated_at** | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |

### Indexes

1. **idx_work_items_task** - `(task_id, status, created_at DESC)`
   - Use case: List all work items for a task, filtered by status

2. **idx_work_items_status_priority** - `(status, priority DESC, created_at ASC)`
   - Use case: Find next pending work item to process (priority queue)

3. **idx_work_items_lease_expiry** - `(lease_expires_at)` WHERE `status = 'in_progress'`
   - Use case: Find expired leases for cleanup

4. **idx_work_items_lease_holder** - `(lease_holder, status)` WHERE `lease_holder IS NOT NULL`
   - Use case: Find all work items held by a specific worker

### Triggers

1. **update_work_items_timestamp** - Auto-update `updated_at` on any change
2. **check_work_items_status** - Validate status values and prevent changes from terminal states

### State Machine

```
pending ──> in_progress ──> completed (terminal)
  │              │
  │              └──> failed (terminal)
  │              └──> expired
  │
  └──> failed (if max_retries exceeded)
```

### Lease Management Flow

```
┌──────────────────────────────────────────────────────┐
│ Worker acquires lease on pending work item           │
│ - Set status = 'in_progress'                          │
│ - Set lease_holder = worker_id                        │
│ - Set lease_acquired_at = now()                       │
│ - Set lease_expires_at = now() + 5 minutes            │
│ - Set heartbeat_at = now()                            │
└───────────────────────┬──────────────────────────────┘
                        │
                        v
┌──────────────────────────────────────────────────────┐
│ Worker sends periodic heartbeats                      │
│ - Update heartbeat_at = now()                         │
│ - Extend lease_expires_at = now() + 5 minutes         │
└───────────────────────┬──────────────────────────────┘
                        │
                        v
┌──────────────────────────────────────────────────────┐
│ Worker completes work                                 │
│ - Set status = 'completed'                            │
│ - Set output_data = result                            │
│ - Set completed_at = now()                            │
│ - Clear lease_holder and lease_expires_at            │
└──────────────────────────────────────────────────────┘

OR

┌──────────────────────────────────────────────────────┐
│ Lease expires (no heartbeat)                          │
│ - Watchdog sets status = 'expired'                    │
│ - Clear lease_holder and lease_expires_at            │
│ - Increment retry_count                               │
│ - If retry_count < max_retries: reset to 'pending'   │
│ - Else: set status = 'failed'                         │
└──────────────────────────────────────────────────────┘
```

### Usage Examples

#### 1. Create Work Item

```sql
INSERT INTO work_items (
    work_item_id, task_id, work_type, priority, input_data
) VALUES (
    'work-01KG4ABC', 'task-01KG4XYZ', 'tool_execution', 10,
    '{"tool": "bash", "command": "ls -la", "args": []}'
);
```

#### 2. Acquire Lease (Claim Next Work Item)

```sql
-- Atomic claim using UPDATE + subquery
UPDATE work_items
SET
    status = 'in_progress',
    lease_holder = 'worker-abc-123',
    lease_acquired_at = CURRENT_TIMESTAMP,
    lease_expires_at = datetime(CURRENT_TIMESTAMP, '+5 minutes'),
    heartbeat_at = CURRENT_TIMESTAMP,
    started_at = CASE WHEN started_at IS NULL THEN CURRENT_TIMESTAMP ELSE started_at END
WHERE work_item_id = (
    SELECT work_item_id
    FROM work_items
    WHERE status = 'pending'
    ORDER BY priority DESC, created_at ASC
    LIMIT 1
)
RETURNING work_item_id, input_data;
```

#### 3. Send Heartbeat

```sql
UPDATE work_items
SET
    heartbeat_at = CURRENT_TIMESTAMP,
    lease_expires_at = datetime(CURRENT_TIMESTAMP, '+5 minutes')
WHERE work_item_id = 'work-01KG4ABC'
  AND lease_holder = 'worker-abc-123'
  AND status = 'in_progress';
```

#### 4. Complete Work Item

```sql
UPDATE work_items
SET
    status = 'completed',
    output_data = '{"result": "success", "files_found": 42}',
    completed_at = CURRENT_TIMESTAMP,
    lease_holder = NULL,
    lease_expires_at = NULL
WHERE work_item_id = 'work-01KG4ABC';
```

#### 5. Handle Failure

```sql
UPDATE work_items
SET
    status = 'failed',
    error_message = 'Command execution timeout',
    completed_at = CURRENT_TIMESTAMP,
    lease_holder = NULL,
    lease_expires_at = NULL
WHERE work_item_id = 'work-01KG4ABC';
```

#### 6. Clean Up Expired Leases (Watchdog)

```sql
-- Find and expire stale work items
UPDATE work_items
SET
    status = CASE
        WHEN retry_count < max_retries THEN 'pending'
        ELSE 'failed'
    END,
    retry_count = retry_count + 1,
    lease_holder = NULL,
    lease_expires_at = NULL,
    error_message = 'Lease expired - no heartbeat received'
WHERE status = 'in_progress'
  AND lease_expires_at < CURRENT_TIMESTAMP;
```

---

## Table 2: checkpoints

### Purpose

Append-only evidence registry that records execution progress snapshots. Enables fine-grained recovery by allowing tasks to resume from specific points rather than restarting completely.

### Schema

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| **checkpoint_id** | TEXT | PRIMARY KEY | ULID or UUID |
| **task_id** | TEXT | NOT NULL, FK | Links to parent task |
| **work_item_id** | TEXT | NULL, FK | Optional link to work item |
| **checkpoint_type** | TEXT | NOT NULL | Type of checkpoint (see enum below) |
| **sequence_number** | INTEGER | NOT NULL | Monotonic sequence within task |
| **snapshot_data** | TEXT | NOT NULL | State snapshot (JSON) |
| **metadata** | TEXT | NULL | Additional metadata (JSON) |
| **created_at** | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |

### Checkpoint Types (Enum)

| Type | Description | Use Case |
|------|-------------|----------|
| **iteration_start** | Iteration beginning | Resume at iteration N |
| **iteration_end** | Iteration completion | Skip completed iterations |
| **tool_executed** | Tool execution result | Avoid re-running expensive tools |
| **llm_response** | LLM API response | Cache and reuse responses |
| **approval_point** | Manual approval checkpoint | Resume after approval |
| **state_transition** | Task state change | Audit trail for state machine |
| **manual_checkpoint** | User-created checkpoint | Custom recovery points |
| **error_boundary** | Error occurred | Debug and retry from failure point |

### Indexes

1. **idx_checkpoints_task_sequence** - `(task_id, sequence_number ASC)`
   - Use case: Get checkpoints in order for a task

2. **idx_checkpoints_work_item** - `(work_item_id, sequence_number ASC)` WHERE `work_item_id IS NOT NULL`
   - Use case: Get checkpoints for a specific work item

3. **idx_checkpoints_type** - `(checkpoint_type, created_at DESC)`
   - Use case: Find all checkpoints of a certain type

4. **idx_checkpoints_created_at** - `(created_at DESC)`
   - Use case: Cleanup old checkpoints

### Triggers

1. **check_checkpoints_type** - Validate checkpoint_type against allowed values

### Properties

- **Append-only**: Checkpoints are never updated or deleted (except CASCADE on task deletion)
- **Monotonic sequence**: sequence_number must increment within each task
- **Immutable**: Once written, snapshot_data should not be modified

### Usage Examples

#### 1. Create Checkpoint at Iteration Start

```sql
INSERT INTO checkpoints (
    checkpoint_id, task_id, checkpoint_type, sequence_number, snapshot_data
) VALUES (
    'ckpt-01KG4ABC', 'task-01KG4XYZ', 'iteration_start', 1,
    json_object(
        'iteration', 1,
        'state', json_object('step', 'planning', 'context', '...'),
        'timestamp', datetime('now')
    )
);
```

#### 2. Create Checkpoint After Tool Execution

```sql
INSERT INTO checkpoints (
    checkpoint_id, task_id, work_item_id, checkpoint_type,
    sequence_number, snapshot_data
) VALUES (
    'ckpt-01KG4DEF', 'task-01KG4XYZ', 'work-01KG4ABC', 'tool_executed', 2,
    json_object(
        'tool', 'bash',
        'command', 'ls -la',
        'result', json_object('stdout', '...', 'stderr', '', 'exit_code', 0),
        'duration_ms', 1234
    )
);
```

#### 3. Find Latest Checkpoint

```sql
SELECT checkpoint_id, checkpoint_type, snapshot_data
FROM checkpoints
WHERE task_id = 'task-01KG4XYZ'
ORDER BY sequence_number DESC
LIMIT 1;
```

#### 4. Resume from Last Iteration Start

```sql
SELECT snapshot_data
FROM checkpoints
WHERE task_id = 'task-01KG4XYZ'
  AND checkpoint_type = 'iteration_start'
ORDER BY sequence_number DESC
LIMIT 1;
```

#### 5. Get All Checkpoints for Recovery Analysis

```sql
SELECT
    checkpoint_type,
    sequence_number,
    snapshot_data,
    created_at
FROM checkpoints
WHERE task_id = 'task-01KG4XYZ'
ORDER BY sequence_number ASC;
```

#### 6. Count Checkpoints by Type

```sql
SELECT
    checkpoint_type,
    COUNT(*) as count
FROM checkpoints
WHERE task_id = 'task-01KG4XYZ'
GROUP BY checkpoint_type;
```

---

## Table 3: idempotency_keys

### Purpose

Prevents duplicate execution through request deduplication and response caching. Ensures that the same operation submitted multiple times produces the same result without side effects.

### Schema

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| **idempotency_key** | TEXT | PRIMARY KEY | Client-provided unique key |
| **task_id** | TEXT | NULL, FK | Optional link to task |
| **work_item_id** | TEXT | NULL, FK | Optional link to work item |
| **request_hash** | TEXT | NOT NULL | SHA256 hash of request payload |
| **response_data** | TEXT | NULL | Cached response (JSON) |
| **status** | TEXT | NOT NULL, DEFAULT 'pending' | Status: pending, completed, failed |
| **created_at** | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |
| **completed_at** | TIMESTAMP | NULL | Completion time |
| **expires_at** | TIMESTAMP | NULL | Expiration time for cleanup |

### Indexes

1. **idx_idempotency_keys_task** - `(task_id, created_at DESC)` WHERE `task_id IS NOT NULL`
   - Use case: Find all idempotency keys for a task

2. **idx_idempotency_keys_work_item** - `(work_item_id, created_at DESC)` WHERE `work_item_id IS NOT NULL`
   - Use case: Find idempotency keys for a work item

3. **idx_idempotency_keys_expires_at** - `(expires_at)` WHERE `expires_at IS NOT NULL`
   - Use case: Cleanup expired keys

4. **idx_idempotency_keys_status** - `(status, created_at DESC)`
   - Use case: Find pending/completed keys

### Triggers

1. **check_idempotency_keys_status** - Validate status values

### Idempotency Flow

```
Client sends request with idempotency_key
         │
         v
┌────────────────────────────────────┐
│ Check if key exists                │
│ SELECT * FROM idempotency_keys     │
│ WHERE idempotency_key = ?          │
└────────┬───────────────────────────┘
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    v         v
┌────────┐  ┌────────────────────────┐
│ Return │  │ Insert key (pending)   │
│ cached │  │ Execute operation      │
│ response│  │ Update key (completed) │
└────────┘  │ Store response         │
            └────────────────────────┘
```

### Usage Examples

#### 1. Check for Existing Key

```sql
SELECT idempotency_key, status, response_data, completed_at
FROM idempotency_keys
WHERE idempotency_key = 'idem-01KG4ABC'
  AND status = 'completed'
  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);
```

#### 2. Create Idempotency Key

```sql
INSERT INTO idempotency_keys (
    idempotency_key, task_id, request_hash, status, expires_at
) VALUES (
    'idem-01KG4ABC',
    'task-01KG4XYZ',
    'sha256:a1b2c3d4...',
    'pending',
    datetime(CURRENT_TIMESTAMP, '+24 hours')
);
```

#### 3. Update with Response

```sql
UPDATE idempotency_keys
SET
    status = 'completed',
    response_data = '{"result": "success", "data": {...}}',
    completed_at = CURRENT_TIMESTAMP
WHERE idempotency_key = 'idem-01KG4ABC';
```

#### 4. Mark as Failed

```sql
UPDATE idempotency_keys
SET
    status = 'failed',
    response_data = '{"error": "Operation failed", "details": "..."}',
    completed_at = CURRENT_TIMESTAMP
WHERE idempotency_key = 'idem-01KG4ABC';
```

#### 5. Clean Up Expired Keys

```sql
DELETE FROM idempotency_keys
WHERE expires_at < CURRENT_TIMESTAMP;
```

#### 6. Verify Request Integrity

```sql
-- Check if request matches original
SELECT
    CASE
        WHEN request_hash = 'sha256:a1b2c3d4...' THEN 'MATCH'
        ELSE 'CONFLICT'
    END as integrity_check
FROM idempotency_keys
WHERE idempotency_key = 'idem-01KG4ABC';
```

---

## Integration Patterns

### Pattern 1: Atomic Work Item Processing

```python
def process_work_item(worker_id: str):
    # 1. Claim work item with lease
    work_item = claim_next_work_item(worker_id, lease_duration=300)

    if not work_item:
        return None

    try:
        # 2. Start heartbeat thread
        heartbeat_thread = start_heartbeat(work_item.id, worker_id)

        # 3. Create checkpoint before execution
        create_checkpoint(
            task_id=work_item.task_id,
            work_item_id=work_item.id,
            checkpoint_type='iteration_start',
            snapshot=get_current_state()
        )

        # 4. Execute with idempotency
        result = execute_with_idempotency(
            key=f"work-{work_item.id}",
            fn=lambda: do_actual_work(work_item)
        )

        # 5. Create checkpoint after execution
        create_checkpoint(
            task_id=work_item.task_id,
            work_item_id=work_item.id,
            checkpoint_type='tool_executed',
            snapshot={'result': result}
        )

        # 6. Complete work item
        complete_work_item(work_item.id, result)

    except Exception as e:
        # 7. Handle failure
        fail_work_item(work_item.id, str(e))

    finally:
        # 8. Stop heartbeat
        heartbeat_thread.stop()
```

### Pattern 2: Task Recovery

```python
def recover_task(task_id: str):
    # 1. Find last completed iteration
    last_checkpoint = get_latest_checkpoint(
        task_id=task_id,
        checkpoint_type='iteration_end'
    )

    if last_checkpoint:
        # 2. Restore state from checkpoint
        state = restore_state(last_checkpoint.snapshot_data)
        iteration = state['iteration'] + 1
    else:
        # 3. Start from beginning
        state = initialize_state()
        iteration = 1

    # 4. Resume execution
    continue_execution(task_id, state, iteration)
```

### Pattern 3: Lease Watchdog

```python
def lease_watchdog():
    """Background process to clean up expired leases"""
    while True:
        # 1. Find expired leases
        expired = find_expired_leases()

        for work_item in expired:
            # 2. Check if should retry
            if work_item.retry_count < work_item.max_retries:
                # 3. Reset to pending for retry
                reset_work_item(work_item.id)

                # 4. Create error boundary checkpoint
                create_checkpoint(
                    task_id=work_item.task_id,
                    work_item_id=work_item.id,
                    checkpoint_type='error_boundary',
                    snapshot={'error': 'Lease expired', 'retry': work_item.retry_count + 1}
                )
            else:
                # 5. Mark as permanently failed
                fail_work_item(work_item.id, 'Max retries exceeded')

        time.sleep(60)  # Check every minute
```

---

## Maintenance and Operations

### Data Retention

#### Checkpoints Cleanup

```sql
-- Keep only last 100 checkpoints per task
DELETE FROM checkpoints
WHERE checkpoint_id IN (
    SELECT checkpoint_id
    FROM checkpoints
    WHERE task_id = ?
    ORDER BY sequence_number DESC
    OFFSET 100
);
```

#### Old Work Items Cleanup

```sql
-- Delete completed work items older than 30 days
DELETE FROM work_items
WHERE status IN ('completed', 'failed')
  AND updated_at < datetime('now', '-30 days');
```

#### Expired Idempotency Keys Cleanup

```sql
-- Delete expired keys
DELETE FROM idempotency_keys
WHERE expires_at < CURRENT_TIMESTAMP;

-- Delete old completed keys (keep last 7 days)
DELETE FROM idempotency_keys
WHERE status = 'completed'
  AND completed_at < datetime('now', '-7 days');
```

### Monitoring Queries

#### Active Work Items

```sql
SELECT
    work_type,
    status,
    COUNT(*) as count,
    AVG(julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 24 as avg_age_hours
FROM work_items
GROUP BY work_type, status;
```

#### Lease Health

```sql
SELECT
    COUNT(*) as active_leases,
    COUNT(CASE WHEN heartbeat_at < datetime('now', '-2 minutes') THEN 1 END) as stale_leases,
    AVG(julianday(CURRENT_TIMESTAMP) - julianday(heartbeat_at)) * 24 * 60 as avg_minutes_since_heartbeat
FROM work_items
WHERE status = 'in_progress';
```

#### Checkpoint Growth

```sql
SELECT
    task_id,
    COUNT(*) as checkpoint_count,
    MAX(sequence_number) as max_sequence,
    MIN(created_at) as first_checkpoint,
    MAX(created_at) as last_checkpoint
FROM checkpoints
GROUP BY task_id
ORDER BY checkpoint_count DESC
LIMIT 10;
```

---

## Performance Considerations

### Indexes

All critical query paths are covered by indexes:
- Work item claiming: `idx_work_items_status_priority`
- Lease expiry detection: `idx_work_items_lease_expiry`
- Checkpoint recovery: `idx_checkpoints_task_sequence`
- Idempotency lookup: Primary key on `idempotency_key`

### Concurrent Access

- **work_items**: Use row-level locking via `UPDATE ... WHERE work_item_id = (SELECT ... LIMIT 1)`
- **checkpoints**: Append-only design eliminates contention
- **idempotency_keys**: Primary key ensures unique constraint at database level

### Scalability

- Partition by `task_id` if using PostgreSQL
- Archive old checkpoints to separate table
- Use TTL for idempotency_keys to limit growth
- Consider VACUUM for SQLite after bulk deletions

---

## Migration Application

### Apply Migration

```bash
# Using AgentOS migration system
python3 -c "from agentos.store import ensure_migrations; ensure_migrations()"
```

### Verify Migration

```bash
# Check schema version
sqlite3 store/registry.sqlite "SELECT version FROM schema_version WHERE version = '0.30.0'"

# List tables
sqlite3 store/registry.sqlite ".tables"

# Describe work_items table
sqlite3 store/registry.sqlite ".schema work_items"
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.30.0 | 2026-01-29 | Initial recovery system schema |

---

## References

- Migration file: `agentos/store/migrations/schema_v30_recovery.sql`
- Test script: `test_recovery_migration.py`
- Related ADR: ADR-008-Recovery-System (TBD)

---

## Appendix: Complete Example Workflow

### Scenario: Execute a Tool with Full Recovery Support

```sql
-- 1. Create task
INSERT INTO tasks (task_id, title, status)
VALUES ('task-001', 'Process documents', 'running');

-- 2. Create work item
INSERT INTO work_items (
    work_item_id, task_id, work_type, priority, input_data
) VALUES (
    'work-001', 'task-001', 'tool_execution', 10,
    '{"tool": "pdf_parser", "file": "document.pdf"}'
);

-- 3. Worker claims work item
UPDATE work_items
SET
    status = 'in_progress',
    lease_holder = 'worker-abc',
    lease_acquired_at = CURRENT_TIMESTAMP,
    lease_expires_at = datetime(CURRENT_TIMESTAMP, '+5 minutes'),
    heartbeat_at = CURRENT_TIMESTAMP
WHERE work_item_id = 'work-001';

-- 4. Create checkpoint before execution
INSERT INTO checkpoints (
    checkpoint_id, task_id, work_item_id,
    checkpoint_type, sequence_number, snapshot_data
) VALUES (
    'ckpt-001', 'task-001', 'work-001',
    'iteration_start', 1,
    '{"state": "before_execution", "timestamp": "2026-01-29T10:00:00Z"}'
);

-- 5. Check idempotency
SELECT * FROM idempotency_keys WHERE idempotency_key = 'tool-pdf_parser-document.pdf';

-- 6. Create idempotency key if not exists
INSERT INTO idempotency_keys (
    idempotency_key, task_id, work_item_id, request_hash
) VALUES (
    'tool-pdf_parser-document.pdf', 'task-001', 'work-001', 'sha256:abc123...'
);

-- 7. Send heartbeat (repeat every 1 minute)
UPDATE work_items
SET heartbeat_at = CURRENT_TIMESTAMP,
    lease_expires_at = datetime(CURRENT_TIMESTAMP, '+5 minutes')
WHERE work_item_id = 'work-001';

-- 8. Tool execution completes - create checkpoint
INSERT INTO checkpoints (
    checkpoint_id, task_id, work_item_id,
    checkpoint_type, sequence_number, snapshot_data
) VALUES (
    'ckpt-002', 'task-001', 'work-001',
    'tool_executed', 2,
    '{"result": "success", "pages": 42, "text_length": 12345}'
);

-- 9. Update idempotency key with result
UPDATE idempotency_keys
SET
    status = 'completed',
    response_data = '{"pages": 42, "text_length": 12345}',
    completed_at = CURRENT_TIMESTAMP
WHERE idempotency_key = 'tool-pdf_parser-document.pdf';

-- 10. Complete work item
UPDATE work_items
SET
    status = 'completed',
    output_data = '{"pages": 42, "text_length": 12345}',
    completed_at = CURRENT_TIMESTAMP,
    lease_holder = NULL,
    lease_expires_at = NULL
WHERE work_item_id = 'work-001';

-- 11. Update task status
UPDATE tasks
SET status = 'succeeded', updated_at = CURRENT_TIMESTAMP
WHERE task_id = 'task-001';
```

### Recovery After Crash

```sql
-- 1. Find incomplete work items
SELECT * FROM work_items
WHERE task_id = 'task-001'
  AND status IN ('pending', 'expired');

-- 2. Find last checkpoint
SELECT * FROM checkpoints
WHERE task_id = 'task-001'
ORDER BY sequence_number DESC
LIMIT 1;

-- 3. Check idempotency cache
SELECT response_data FROM idempotency_keys
WHERE idempotency_key = 'tool-pdf_parser-document.pdf'
  AND status = 'completed';

-- If found in cache: use cached result
-- If not found: re-execute from last checkpoint
```

---

**End of Documentation**
