# PR-V2 Quick Reference: Event Instrumentation

Quick reference for all 19 event types instrumented in PR-V2.

---

## Event Types Summary

| # | Event Type | Actor | Span | Phase | Trigger |
|---|------------|-------|------|-------|---------|
| 1 | `runner_spawn` | runner | main | - | Runner process starts |
| 2 | `runner_exit` | runner | main | - | Runner process exits |
| 3 | `phase_enter` | runner | main | planning/executing/verifying | Phase transition |
| 4 | `phase_exit` | runner | main | planning/executing/verifying | Phase completes |
| 5 | `checkpoint_begin` | checkpoint_manager | main | execution | Checkpoint step begins |
| 6 | `checkpoint_commit` | checkpoint_manager | main | execution | Checkpoint saved |
| 7 | `checkpoint_verified` | checkpoint_manager | main | execution | Checkpoint evidence verified |
| 8 | `checkpoint_invalid` | checkpoint_manager | main | execution | Checkpoint verification failed |
| 9 | `gate_start` | gate_runner | main | verifying | Gate execution starts |
| 10 | `gate_result` | gate_runner | main | verifying | Gate execution completes |
| 11 | `work_item_dispatched` | runner | main | executing | Work item dispatched to worker |
| 12 | `work_item_start` | worker | work_{id} | executing | Work item execution starts |
| 13 | `work_item_done` | worker | work_{id} | executing | Work item succeeds |
| 14 | `work_item_failed` | worker | work_{id} | executing | Work item fails |
| 15 | `lease_acquired` | lease_manager | work_{id} | executing | Lease acquired on work item |
| 16 | `lease_renewed` | lease_manager | work_{id} | executing | Lease heartbeat renewed |
| 17 | `recovery_detected` | recovery_sweep | recovery_sweep | recovery | Expired leases detected |
| 18 | `recovery_requeued` | recovery_sweep | recovery_sweep | recovery | Work item re-queued |
| 19 | `recovery_resumed_from_checkpoint` | runner | main | recovery | Task resumed from checkpoint |

---

## Span Hierarchy

```
main (runner)
├── work_{item_id} (work items - child of main)
recovery_sweep (independent)
```

**Rules**:
- Main runner span: `span_id="main"`, `parent_span_id=None`
- Work item spans: `span_id="work_{work_item_id}"`, `parent_span_id="main"`
- Recovery span: `span_id="recovery_sweep"`, `parent_span_id=None`

---

## Query Examples

### Get all events for a task
```python
from agentos.core.task.event_service import TaskEventService

service = TaskEventService()
events = service.get_events(task_id="task-123", limit=100)
```

### Get events since last poll (streaming)
```python
events = service.get_events(task_id="task-123", since_seq=50, limit=100)
```

### Get span tree (for graph visualization)
```python
events = service.get_span_tree(task_id="task-123")
# Build hierarchy from parent_span_id relationships
```

### Get checkpoint events only
```python
events = service.get_checkpoint_events(task_id="task-123")
```

---

## Testing

### Run integration tests
```bash
pytest tests/integration/test_runner_events.py -v -s
```

### Verify all 19 event types
```bash
pytest tests/integration/test_runner_events.py::TestRunnerEvents::test_all_event_types_coverage -v
```

### Test work item coordination
```bash
pytest tests/integration/test_runner_events.py::TestRunnerEvents::test_work_item_events -v
```

---

## Common Payloads

### Runner Events
```json
{
  "runner_spawn": {
    "runner_pid": 12345,
    "runner_version": "v0.4.0",
    "explanation": "Runner process started"
  },
  "runner_exit": {
    "runner_pid": 12345,
    "exit_reason": "done",
    "iterations": 10,
    "explanation": "Runner exited: done"
  }
}
```

### Work Item Events
```json
{
  "work_item_dispatched": {
    "work_item_id": "wi_001",
    "title": "Implement feature X",
    "index": 0,
    "explanation": "Work item wi_001 dispatched"
  },
  "work_item_start": {
    "work_item_id": "wi_001",
    "work_type": "sub_agent_execution",
    "explanation": "Starting work item: Implement feature X"
  },
  "work_item_done": {
    "work_item_id": "wi_001",
    "title": "Implement feature X",
    "files_changed": ["src/feature.py", "tests/test_feature.py"],
    "explanation": "Work item wi_001 completed successfully"
  }
}
```

### Checkpoint Events
```json
{
  "checkpoint_commit": {
    "checkpoint_id": "ckpt-abc123",
    "checkpoint_type": "work_item_executing",
    "sequence_number": 5,
    "work_item_id": "wi_001",
    "evidence_count": 3,
    "explanation": "Checkpoint committed: work_item_executing (seq=5)"
  }
}
```

### Gate Events
```json
{
  "gate_result": {
    "gate_name": "doctor",
    "status": "passed",
    "passed": true,
    "exit_code": 0,
    "duration_seconds": 1.23,
    "explanation": "Gate doctor passed"
  }
}
```

---

## Modified Files

| File | Lines | Event Types |
|------|-------|-------------|
| `task_runner.py` | ~150 | 8 types |
| `checkpoint_manager.py` | ~60 | 4 types |
| `done_gate.py` | ~40 | 2 types |
| `lease.py` | ~40 | 2 types |
| `recovery_sweep.py` | ~40 | 2 types |

---

## Next Steps

1. ✅ PR-V1: Event model + API (DONE)
2. ✅ PR-V2: Event instrumentation (DONE)
3. 🚧 PR-V3: Real-time streaming (SSE/WebSocket)
4. 📋 PR-V4: Pipeline graph view
5. 📋 PR-V5: Timeline view
6. 📋 PR-V6: Evidence drawer
7. 📋 PR-V7: Performance + throttling
8. 📋 PR-V8: Testing + load testing

---

## Troubleshooting

### Events not appearing?
1. Check SQLiteWriter is running: `get_writer()` should not raise
2. Verify task_events table exists: `SELECT * FROM task_events LIMIT 1`
3. Check logs for event emission errors: grep for "Failed to emit"

### Sequence numbers out of order?
- This should never happen (strict monotonic guarantee)
- Check task_event_seq_counters table: `SELECT * FROM task_event_seq_counters WHERE task_id = ?`

### Missing parent_span_id?
- Work item events should always have `parent_span_id="main"`
- Runner events should have `parent_span_id=None`

---

**Last Updated**: 2026-01-30
