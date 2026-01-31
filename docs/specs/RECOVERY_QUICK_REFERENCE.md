# Recovery System Quick Reference

**Version**: 0.30.0 | **Last Updated**: 2026-01-29

Quick reference for developers using the recovery system tables.

---

## Table Overview

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **work_items** | Lease-managed work units | work_item_id, lease_holder, heartbeat_at |
| **checkpoints** | Execution snapshots | checkpoint_id, sequence_number, snapshot_data |
| **idempotency_keys** | Deduplication cache | idempotency_key, request_hash, response_data |

---

## Common Operations

### 1. Claim Work Item (Atomic)

```python
def claim_work_item(worker_id: str) -> Optional[dict]:
    """Atomically claim the highest priority pending work item"""
    cursor = conn.execute("""
        UPDATE work_items
        SET
            status = 'in_progress',
            lease_holder = ?,
            lease_acquired_at = CURRENT_TIMESTAMP,
            lease_expires_at = datetime(CURRENT_TIMESTAMP, '+5 minutes'),
            heartbeat_at = CURRENT_TIMESTAMP,
            started_at = CASE WHEN started_at IS NULL THEN CURRENT_TIMESTAMP ELSE started_at END
        WHERE work_item_id = (
            SELECT work_item_id FROM work_items
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
        )
        RETURNING work_item_id, task_id, input_data
    """, (worker_id,))
    return cursor.fetchone()
```

### 2. Send Heartbeat

```python
def send_heartbeat(work_item_id: str, worker_id: str) -> bool:
    """Extend lease by sending heartbeat"""
    cursor = conn.execute("""
        UPDATE work_items
        SET
            heartbeat_at = CURRENT_TIMESTAMP,
            lease_expires_at = datetime(CURRENT_TIMESTAMP, '+5 minutes')
        WHERE work_item_id = ? AND lease_holder = ? AND status = 'in_progress'
    """, (work_item_id, worker_id))
    return cursor.rowcount > 0
```

### 3. Create Checkpoint

```python
def create_checkpoint(task_id: str, checkpoint_type: str, snapshot: dict,
                     work_item_id: Optional[str] = None) -> str:
    """Create execution checkpoint"""
    checkpoint_id = generate_ulid()
    sequence = get_next_sequence(task_id)

    conn.execute("""
        INSERT INTO checkpoints (
            checkpoint_id, task_id, work_item_id, checkpoint_type,
            sequence_number, snapshot_data
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (checkpoint_id, task_id, work_item_id, checkpoint_type,
          sequence, json.dumps(snapshot)))

    return checkpoint_id
```

### 4. Check Idempotency

```python
def check_idempotency(key: str) -> Optional[dict]:
    """Check if operation already completed"""
    cursor = conn.execute("""
        SELECT response_data, status
        FROM idempotency_keys
        WHERE idempotency_key = ?
          AND status = 'completed'
          AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
    """, (key,))

    row = cursor.fetchone()
    return json.loads(row['response_data']) if row else None
```

### 5. Complete Work Item

```python
def complete_work_item(work_item_id: str, result: dict):
    """Mark work item as completed"""
    conn.execute("""
        UPDATE work_items
        SET
            status = 'completed',
            output_data = ?,
            completed_at = CURRENT_TIMESTAMP,
            lease_holder = NULL,
            lease_expires_at = NULL
        WHERE work_item_id = ?
    """, (json.dumps(result), work_item_id))
```

### 6. Recover from Last Checkpoint

```python
def recover_task(task_id: str) -> Optional[dict]:
    """Get last checkpoint for recovery"""
    cursor = conn.execute("""
        SELECT snapshot_data, checkpoint_type, sequence_number
        FROM checkpoints
        WHERE task_id = ?
        ORDER BY sequence_number DESC
        LIMIT 1
    """, (task_id,))

    row = cursor.fetchone()
    return json.loads(row['snapshot_data']) if row else None
```

---

## Checkpoint Types

| Type | When to Use | Example Snapshot |
|------|-------------|-----------------|
| **iteration_start** | Beginning of iteration | `{"iteration": 1, "plan": {...}}` |
| **iteration_end** | End of iteration | `{"iteration": 1, "result": "success"}` |
| **tool_executed** | After tool runs | `{"tool": "bash", "result": {...}}` |
| **llm_response** | After LLM call | `{"prompt": "...", "response": "..."}` |
| **approval_point** | Manual approval needed | `{"action": "deploy", "status": "pending"}` |
| **state_transition** | Task state changes | `{"from": "running", "to": "blocked"}` |
| **manual_checkpoint** | User-created | `{"note": "Before critical operation"}` |
| **error_boundary** | Error occurred | `{"error": "timeout", "retry": 1}` |

---

## Work Item States

```
pending ──────────────────────> failed (max retries)
  │                                  ↑
  │                                  │
  ↓                                  │
in_progress ───> completed           │
  │              (terminal)          │
  │                                  │
  ├────────────> failed ─────────────┘
  │              (terminal)
  │
  └────────────> expired ────> pending (retry)
                               or failed
```

---

## Lease States

| Field | Value | Meaning |
|-------|-------|---------|
| **lease_holder** | NULL | No lease (pending or completed) |
| **lease_holder** | "worker-123" | Active lease |
| **lease_expires_at** | future | Lease valid |
| **lease_expires_at** | past | Lease expired (cleanup needed) |
| **heartbeat_at** | recent | Worker alive |
| **heartbeat_at** | stale | Worker may be dead |

---

## Maintenance Queries

### Clean Expired Leases

```sql
UPDATE work_items
SET
    status = CASE
        WHEN retry_count < max_retries THEN 'pending'
        ELSE 'failed'
    END,
    retry_count = retry_count + 1,
    lease_holder = NULL,
    lease_expires_at = NULL,
    error_message = 'Lease expired'
WHERE status = 'in_progress'
  AND lease_expires_at < CURRENT_TIMESTAMP;
```

### Clean Old Checkpoints (Keep Last 100)

```sql
DELETE FROM checkpoints
WHERE checkpoint_id IN (
    SELECT checkpoint_id FROM checkpoints
    WHERE task_id = ?
    ORDER BY sequence_number DESC
    OFFSET 100
);
```

### Clean Expired Idempotency Keys

```sql
DELETE FROM idempotency_keys
WHERE expires_at < CURRENT_TIMESTAMP;
```

### Monitor Stale Leases

```sql
SELECT
    work_item_id,
    lease_holder,
    julianday(CURRENT_TIMESTAMP) - julianday(heartbeat_at) * 24 * 60 as minutes_since_heartbeat
FROM work_items
WHERE status = 'in_progress'
  AND heartbeat_at < datetime('now', '-2 minutes')
ORDER BY heartbeat_at ASC;
```

---

## Best Practices

### ✅ DO

1. **Always use heartbeats** - Send every 30-60 seconds
2. **Check idempotency first** - Before expensive operations
3. **Create checkpoints frequently** - Before and after key operations
4. **Use RETURNING clause** - For atomic claim operations
5. **Set expires_at** - On idempotency keys for cleanup
6. **Handle terminal states** - Don't try to modify completed/failed items
7. **Use priority** - Set higher priority for urgent work
8. **Clean up regularly** - Run maintenance queries periodically

### ❌ DON'T

1. **Don't skip heartbeats** - Lease will expire
2. **Don't modify terminal states** - Triggers will block
3. **Don't store huge snapshots** - Keep checkpoints < 1 MB
4. **Don't forget foreign keys** - Always PRAGMA foreign_keys = ON
5. **Don't delete checkpoints** - They're evidence (except via CASCADE)
6. **Don't reuse idempotency keys** - Each operation needs unique key
7. **Don't ignore retry_count** - Implement exponential backoff
8. **Don't hold leases forever** - Release when done

---

## Error Handling

### Lease Expired

```python
try:
    result = do_work()
except LeaseExpiredError:
    # Don't update work_item - it's already expired
    # Let watchdog handle cleanup
    log.warning("Lease expired during execution")
```

### Idempotency Conflict

```python
# Different request with same key
cached = check_idempotency(key)
if cached:
    request_hash = compute_hash(request)
    cursor = conn.execute("""
        SELECT request_hash FROM idempotency_keys WHERE idempotency_key = ?
    """, (key,))
    stored_hash = cursor.fetchone()['request_hash']

    if stored_hash != request_hash:
        raise IdempotencyConflictError("Same key, different request")

    return cached  # Same request, return cached result
```

### Checkpoint Recovery

```python
def resume_task(task_id: str):
    # Find last iteration checkpoint
    snapshot = recover_task(task_id)

    if not snapshot:
        # Start from beginning
        return start_task(task_id)

    # Resume from snapshot
    state = snapshot['state']
    iteration = snapshot['iteration'] + 1
    return continue_task(task_id, state, iteration)
```

---

## Performance Tips

1. **Batch operations** - Use transactions for multiple inserts
2. **Use indexes** - All query patterns are indexed
3. **Limit checkpoint size** - Compress large snapshots
4. **Archive old data** - Move completed work items to history table
5. **Monitor index usage** - EXPLAIN QUERY PLAN to verify
6. **Vacuum regularly** - After bulk deletes
7. **Use WAL mode** - Better concurrency (already enabled)
8. **Connection pooling** - Reuse connections

---

## Example: Complete Workflow

```python
# 1. Claim work
work = claim_work_item("worker-123")
if not work:
    return  # Nothing to do

# 2. Start heartbeat thread
heartbeat_thread = start_heartbeat_thread(work['work_item_id'], "worker-123")

try:
    # 3. Create checkpoint before
    create_checkpoint(
        work['task_id'],
        'iteration_start',
        {'state': get_state(), 'timestamp': datetime.now().isoformat()},
        work['work_item_id']
    )

    # 4. Check idempotency
    idem_key = f"work-{work['work_item_id']}"
    cached = check_idempotency(idem_key)

    if cached:
        result = cached
    else:
        # 5. Create idempotency key
        create_idempotency_key(idem_key, work['task_id'], work['work_item_id'])

        # 6. Execute
        result = execute_work(work['input_data'])

        # 7. Update idempotency key
        complete_idempotency_key(idem_key, result)

    # 8. Create checkpoint after
    create_checkpoint(
        work['task_id'],
        'tool_executed',
        {'result': result, 'timestamp': datetime.now().isoformat()},
        work['work_item_id']
    )

    # 9. Complete work item
    complete_work_item(work['work_item_id'], result)

except Exception as e:
    # 10. Handle failure
    fail_work_item(work['work_item_id'], str(e))

    # Create error checkpoint
    create_checkpoint(
        work['task_id'],
        'error_boundary',
        {'error': str(e), 'timestamp': datetime.now().isoformat()},
        work['work_item_id']
    )

finally:
    # 11. Stop heartbeat
    heartbeat_thread.stop()
```

---

## Monitoring Queries

### Active Work Items

```sql
SELECT status, COUNT(*) as count
FROM work_items
WHERE created_at > datetime('now', '-1 day')
GROUP BY status;
```

### Lease Health

```sql
SELECT
    COUNT(*) as active_leases,
    COUNT(CASE WHEN heartbeat_at < datetime('now', '-2 minutes') THEN 1 END) as stale,
    AVG(julianday('now') - julianday(heartbeat_at)) * 24 * 60 as avg_minutes_since_heartbeat
FROM work_items
WHERE status = 'in_progress';
```

### Checkpoint Growth

```sql
SELECT
    task_id,
    COUNT(*) as checkpoint_count,
    SUM(LENGTH(snapshot_data)) / 1024.0 / 1024.0 as size_mb
FROM checkpoints
GROUP BY task_id
ORDER BY checkpoint_count DESC
LIMIT 10;
```

### Retry Statistics

```sql
SELECT
    retry_count,
    COUNT(*) as work_items,
    AVG(julianday(completed_at) - julianday(created_at)) * 24 as avg_hours
FROM work_items
WHERE status IN ('completed', 'failed')
  AND created_at > datetime('now', '-7 days')
GROUP BY retry_count
ORDER BY retry_count;
```

---

## Troubleshooting

### Problem: Work items stuck in pending

**Diagnosis**:
```sql
SELECT work_item_id, created_at,
       julianday('now') - julianday(created_at) * 24 as age_hours
FROM work_items
WHERE status = 'pending'
ORDER BY created_at ASC
LIMIT 10;
```

**Solution**: Check if workers are running, increase priority

---

### Problem: Leases expiring too fast

**Diagnosis**:
```sql
SELECT
    AVG(julianday(completed_at) - julianday(started_at)) * 24 * 60 as avg_duration_minutes
FROM work_items
WHERE status = 'completed';
```

**Solution**: Increase lease duration to 2x average execution time

---

### Problem: Checkpoint table growing too large

**Diagnosis**:
```sql
SELECT
    COUNT(*) as total_checkpoints,
    SUM(LENGTH(snapshot_data)) / 1024.0 / 1024.0 as total_size_mb
FROM checkpoints;
```

**Solution**: Archive old checkpoints, implement retention policy

---

## References

- Full Documentation: `docs/specs/RECOVERY_DATABASE_SCHEMA.md`
- Migration: `agentos/store/migrations/schema_v30_recovery.sql`
- Tests: `test_recovery_migration.py`, `test_recovery_integration.py`
- Completion Report: `TASK6_RECOVERY_SCHEMA_COMPLETION_REPORT.md`

---

**Quick Help**: `sqlite3 store/registry.sqlite ".schema work_items"`
