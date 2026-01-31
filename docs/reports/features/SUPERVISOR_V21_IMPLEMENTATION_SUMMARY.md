# Supervisor v21 Implementation Summary

## Quick Reference

This document provides a quick reference for implementing v21 redundant column writes in Supervisor.

**Full Documentation**: See `docs/governance/SUPERVISOR_V21_INTEGRATION.md` for complete details.

---

## What Needs to Change

### Files to Modify

1. **`agentos/core/supervisor/adapters/audit_adapter.py`** (核心修改)
   - Modify `write_audit_event()` method - add 2 optional parameters
   - Modify `write_decision()` method - pass source_event_ts
   - Modify `write_error()` method - pass source_event_ts (optional)

2. **`agentos/core/supervisor/policies/base.py`** (调用方修改)
   - Modify `__call__()` method - pass event.ts to write_decision()

---

## Code Changes at a Glance

### Change 1: audit_adapter.py - write_audit_event()

```python
# ADD two optional parameters:
def write_audit_event(
    self,
    task_id: str,
    event_type: str,
    level: str = "info",
    payload: Optional[Dict[str, Any]] = None,
    cursor: Optional[sqlite3.Cursor] = None,
    source_event_ts: Optional[str] = None,  # NEW
    supervisor_processed_at: Optional[str] = None,  # NEW
) -> int:
```

```python
# UPDATE SQL INSERT:
cursor.execute(
    """
    INSERT INTO task_audits (
        task_id, level, event_type, payload, created_at,
        source_event_ts, supervisor_processed_at  -- NEW
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    (
        task_id, level, event_type, payload_json,
        datetime.now(timezone.utc).isoformat(),
        source_event_ts,  # NEW
        supervisor_processed_at,  # NEW
    ),
)
```

### Change 2: audit_adapter.py - write_decision()

```python
# ADD one optional parameter:
def write_decision(
    self,
    task_id: str,
    decision: Decision,
    cursor: Optional[sqlite3.Cursor] = None,
    source_event_ts: Optional[str] = None,  # NEW
) -> int:
```

```python
# PASS to write_audit_event:
return self.write_audit_event(
    task_id=task_id,
    event_type=event_type,
    level=level,
    payload=payload,
    cursor=cursor,
    source_event_ts=source_event_ts,  # NEW
    supervisor_processed_at=datetime.now(timezone.utc).isoformat(),  # NEW
)
```

### Change 3: policies/base.py - __call__()

```python
# PASS event.ts to write_decision:
if decision:
    self.audit_adapter.write_decision(
        event.task_id,
        decision,
        cursor,
        source_event_ts=event.ts  # NEW - pass source event timestamp
    )
```

---

## Field Mapping

| Column | Source | Example |
|--------|--------|---------|
| `source_event_ts` | `SupervisorEvent.ts` | `2026-01-28T10:00:00Z` |
| `supervisor_processed_at` | `datetime.now()` | `2026-01-28T10:00:05Z` |

**Key Point**: `event.ts` comes from:
- EventBus events: original event timestamp
- Polling events: `created_at` from DB

---

## Validation Checklist

After implementation, verify:

```sql
-- ✅ Check redundant columns are populated
SELECT
    audit_id,
    event_type,
    source_event_ts,
    supervisor_processed_at,
    json_extract(payload, '$.timestamp') AS payload_timestamp
FROM task_audits
WHERE event_type LIKE 'SUPERVISOR_%'
ORDER BY created_at DESC
LIMIT 5;
```

Expected:
- `source_event_ts` IS NOT NULL
- `supervisor_processed_at` IS NOT NULL
- `source_event_ts ≈ payload_timestamp` (diff < 1 second)

```sql
-- ✅ Check coverage rate
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN source_event_ts IS NOT NULL THEN 1 ELSE 0 END) AS with_cols,
    ROUND(100.0 * SUM(CASE WHEN source_event_ts IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS coverage_pct
FROM task_audits
WHERE event_type LIKE 'SUPERVISOR_%'
  AND created_at >= datetime('now', '-1 hour');
```

Expected: `coverage_pct` close to 100% after deployment.

---

## Testing

### Unit Test Template

```python
def test_write_decision_with_redundant_columns():
    """Verify redundant columns are correctly populated"""
    from agentos.core.supervisor.adapters import AuditAdapter
    from agentos.core.supervisor.models import Decision, DecisionType

    adapter = AuditAdapter(test_db_path)
    decision = Decision(decision_type=DecisionType.ALLOW, reason="Test")

    # Write audit with source_event_ts
    audit_id = adapter.write_decision(
        task_id="test-task-1",
        decision=decision,
        cursor=cursor,
        source_event_ts="2026-01-28T10:00:00Z"
    )

    # Verify
    cursor.execute("""
        SELECT source_event_ts, supervisor_processed_at, payload
        FROM task_audits WHERE audit_id = ?
    """, (audit_id,))
    row = cursor.fetchone()

    # Check redundant columns
    assert row[0] == "2026-01-28T10:00:00Z"
    assert row[1] is not None

    # Check payload still has full data
    payload = json.loads(row[2])
    assert payload["decision_type"] == "allow"
    assert payload["reason"] == "Test"
```

### Integration Test Template

```python
def test_supervisor_end_to_end_with_v21():
    """Verify Supervisor writes redundant columns in end-to-end flow"""
    from agentos.core.supervisor.models import SupervisorEvent, EventSource
    from agentos.core.supervisor.policies.on_task_created import OnTaskCreatedPolicy

    # Create test event
    event = SupervisorEvent(
        event_id="test-1",
        source=EventSource.EVENTBUS,
        task_id="test-task-1",
        event_type="TASK_CREATED",
        ts="2026-01-28T10:00:00Z",
        payload={"agent_spec": {...}}
    )

    # Process event
    policy = OnTaskCreatedPolicy(test_db_path)
    decision = policy(event, cursor)

    # Verify audit record
    cursor.execute("""
        SELECT source_event_ts, supervisor_processed_at
        FROM task_audits
        WHERE task_id = ? AND event_type LIKE 'SUPERVISOR_%'
        ORDER BY created_at DESC LIMIT 1
    """, (event.task_id,))
    row = cursor.fetchone()

    assert row[0] == "2026-01-28T10:00:00Z"  # Should equal event.ts
    assert row[1] is not None
```

---

## Timeline

| Phase | Duration | Owner |
|-------|----------|-------|
| Code modification | D+1 ~ D+2 | Supervisor Team |
| Joint verification | D+3 | Lead + Supervisor Teams |
| Production deployment | D+4 ~ D+5 | Ops Team |
| Monitoring & optimization | D+6 ~ D+10 | Lead Team |

---

## Backward Compatibility

- ✅ Payload remains source of truth
- ✅ Redundant columns can be NULL (old data)
- ✅ Lead Agent auto-fallbacks to payload if columns are NULL
- ✅ No breaking changes to existing functionality

---

## Rollback Plan

If issues occur:
1. Revert Supervisor code
2. System continues to work (writes to payload, columns = NULL)
3. Lead Agent auto-fallbacks to payload extraction
4. Schema stays at v21 (no need to rollback migration)

---

## FAQ Quick Answers

**Q: What if I forget to pass source_event_ts?**
A: System still works. Column = NULL, Lead Agent uses payload (slower but functional).

**Q: Where does source_event_ts come from?**
A: From `SupervisorEvent.ts` (passed from calling code via event.ts).

**Q: Why not just use payload?**
A: Performance. Direct column access is 10x faster than JSON extraction.

**Q: How to test without breaking existing functionality?**
A: Run unit tests + integration tests. Verify payload still has complete data.

---

**For complete details, see**: `docs/governance/SUPERVISOR_V21_INTEGRATION.md`
