# Task #9: Runner Recovery Integration - Quick Reference

**Version**: 1.0.0
**Last Updated**: 2026-01-29

---

## Overview

Task #9 integrates checkpoint-based recovery, LLM caching, and tool replay into TaskRunner for resilient task execution.

---

## Quick Start

### Enable Recovery in TaskRunner

```python
from agentos.core.runner import TaskRunner

# Create runner with recovery enabled
runner = TaskRunner(
    enable_recovery=True,  # Enable checkpoint-based recovery
    use_real_pipeline=False  # Use simulation mode for testing
)

# Run task with recovery support
runner.run_with_recovery(task_id="task-123")
```

### Disable Recovery (Default Behavior)

```python
runner = TaskRunner(
    enable_recovery=False  # Disable recovery features
)

# Run task normally
runner.run_task(task_id="task-123")
```

---

## Key Components

### 1. CheckpointManager

**Purpose**: Manage checkpoint lifecycle with evidence verification

**Usage**:
```python
from agentos.core.checkpoints import CheckpointManager, Evidence, EvidenceType, EvidencePack

manager = CheckpointManager()

# Begin step
step_id = manager.begin_step(
    task_id="task-123",
    checkpoint_type="iteration_start",  # Valid types: see schema
    snapshot={"iteration": 1, "status": "running"}
)

# Create evidence
evidence = Evidence(
    evidence_type=EvidenceType.COMMAND_EXIT,
    description="Command succeeded",
    expected={"exit_code": 0}
)

# Commit checkpoint
checkpoint = manager.commit_step(
    step_id=step_id,
    evidence_pack=EvidencePack(evidence_list=[evidence])
)

# Verify checkpoint
is_valid = manager.verify_checkpoint(checkpoint.checkpoint_id)

# Get last checkpoint for recovery
last_checkpoint = manager.get_last_verified_checkpoint("task-123")
```

### 2. LLMOutputCache

**Purpose**: Cache LLM outputs to reduce token consumption

**Usage**:
```python
from agentos.core.idempotency import LLMOutputCache

cache = LLMOutputCache()

# Get cached or generate new
result = cache.get_or_generate(
    operation_type="plan",
    prompt="Generate a plan for task X",
    model="gpt-4",
    task_id="task-123",
    generate_fn=lambda: call_llm(prompt)  # Only called on cache miss
)

# Check cache statistics
stats = cache.get_stats()
print(f"Cache hit rate: {stats['hit_rate']:.2%}")
```

### 3. ToolLedger

**Purpose**: Record and replay tool executions for idempotency

**Usage**:
```python
from agentos.core.idempotency import ToolLedger

ledger = ToolLedger()

# Execute or replay tool
result = ledger.execute_or_replay(
    tool_name="bash",
    command="echo hello",
    task_id="task-123",
    execute_fn=lambda: run_bash_command("echo hello")  # Only called on first execution
)

# Check if result was replayed
if result.get("replayed"):
    print("Tool result was replayed from cache")

# Check ledger statistics
stats = ledger.get_stats()
print(f"Replay rate: {stats['replay_rate']:.2%}")
```

### 4. LeaseManager

**Purpose**: Coordinate work item execution across workers (infrastructure)

**Usage**:
```python
from agentos.core.worker_pool import LeaseManager
from agentos.store import get_db

conn = get_db()
manager = LeaseManager(conn, worker_id="worker-123")

# Acquire lease (requires work_items table)
lease = manager.acquire_lease(lease_duration_seconds=300)

if lease:
    # Work on item
    try:
        # ... execute work ...
        manager.release_lease(lease.work_item_id, success=True)
    except Exception as e:
        manager.release_lease(lease.work_item_id, success=False, error=str(e))
```

---

## Valid Checkpoint Types

From database schema (`checkpoints` table):

- `iteration_start` - Start of iteration
- `iteration_end` - End of iteration
- `tool_executed` - After tool execution
- `llm_response` - After LLM call
- `approval_point` - Approval checkpoint
- `state_transition` - State change
- `manual_checkpoint` - Manual checkpoint
- `error_boundary` - Error boundary

**Usage**:
```python
# Use valid checkpoint type
step_id = manager.begin_step(
    task_id="task-123",
    checkpoint_type="tool_executed",  # Must be from valid list
    snapshot={"tool": "bash", "status": "done"}
)
```

---

## Evidence Types

Four evidence types supported:

### 1. Command Exit Code
```python
Evidence(
    evidence_type=EvidenceType.COMMAND_EXIT,
    description="Command succeeded",
    expected={"exit_code": 0},
    metadata={"command": "echo test"}
)
```

### 2. Artifact Exists
```python
Evidence(
    evidence_type=EvidenceType.ARTIFACT_EXISTS,
    description="Output file created",
    expected={"path": "/tmp/output.txt", "type": "file"},
    metadata={}
)
```

### 3. File SHA256
```python
Evidence(
    evidence_type=EvidenceType.FILE_SHA256,
    description="Config file unchanged",
    expected={"path": "/etc/config.yaml", "sha256": "abc123..."},
    metadata={}
)
```

### 4. Database Row
```python
Evidence(
    evidence_type=EvidenceType.DB_ROW,
    description="Task status updated",
    expected={
        "table": "tasks",
        "where": {"task_id": "task-123"},
        "values": {"status": "completed"}
    },
    metadata={"db_path": "store/registry.sqlite"}
)
```

---

## Runner Integration Points

### Planning Stage (with LLM Cache)

```python
# In TaskRunner._execute_stage() - planning branch
if self.enable_recovery and self.llm_cache:
    pipeline_result = self._generate_plan_with_cache(task, nl_request)
else:
    pipeline_result = self._generate_plan_direct(task, nl_request)
```

### Work Item Execution (with Checkpoint)

```python
# In TaskRunner._execute_work_items_serial()
if self.enable_recovery:
    output = self.execute_work_item_with_checkpoint(task_id, work_item)
else:
    output = self._execute_single_work_item(task_id, work_item)
```

### Recovery on Startup

```python
# In TaskRunner.run_with_recovery()
last_checkpoint = self.checkpoint_manager.get_last_verified_checkpoint(task_id)
if last_checkpoint:
    self.resume_from_checkpoint(task_id, last_checkpoint)
```

---

## Testing

### Run Integration Tests

```bash
# Simplified integration tests (no heavy dependencies)
python3 test_runner_recovery_simple.py
```

**Expected Output**:
```
✅ PASS - Runner Components
✅ PASS - Checkpoint Lifecycle
✅ PASS - LLM Cache
✅ PASS - Tool Ledger
✅ PASS - Evidence Collection

Total: 5/5 tests passed
🎉 ALL TESTS PASSED
```

### Run E2E Tests

```bash
# End-to-end scenarios
python3 test_task9_e2e.py
```

**Expected Output**:
```
✅ PASS - Basic Recovery
✅ PASS - Idempotency
✅ PASS - Runner Integration

Total: 3/3 scenarios passed
🎉 ALL E2E TESTS PASSED
```

---

## Configuration

### Environment Variables

None required for basic operation.

### Database Schema

**Required Tables**:
- `checkpoints` - Checkpoint storage (from Task #6)
- `idempotency_keys` - Cache storage (from Task #10)
- `tasks` - Task metadata (existing)

**Optional Tables** (for full features):
- `work_items` - Work item tracking (from Task #6, pending)

---

## Performance Tips

### LLM Cache

- **Cache Duration**: Default 7 days, configurable via `expires_in_seconds`
- **Cache Key**: Based on `operation_type`, `prompt`, `model`, `task_id`
- **Best Practice**: Use consistent prompt formatting for better cache hits

### Tool Ledger

- **Cache Duration**: Default 30 days
- **Cache Key**: Based on `tool_name`, `command`, `task_id`
- **Best Practice**: Use deterministic commands for better replay

### Checkpoints

- **Overhead**: <10ms per checkpoint creation
- **Verification**: <50ms per checkpoint (evidence dependent)
- **Best Practice**: Create checkpoints at coarse-grained boundaries (iterations, phases)

---

## Troubleshooting

### Issue: Checkpoint creation fails with "Invalid checkpoint_type"

**Solution**: Use valid checkpoint type from schema:
```python
# ❌ Wrong
checkpoint_type="my_checkpoint"

# ✅ Correct
checkpoint_type="iteration_start"  # From valid list
```

### Issue: Foreign key constraint failed (work_item_id)

**Solution**: Work items table not yet available, omit `work_item_id`:
```python
# ❌ Fails if work_items table missing
step_id = manager.begin_step(
    task_id="task-123",
    checkpoint_type="tool_executed",
    snapshot={},
    work_item_id="work-item-123"  # FK constraint failure
)

# ✅ Works without work_items table
step_id = manager.begin_step(
    task_id="task-123",
    checkpoint_type="tool_executed",
    snapshot={"work_item_id": "work-item-123"}  # Store in snapshot instead
)
```

### Issue: LLM cache not working

**Check**:
1. Recovery enabled: `enable_recovery=True`
2. Task ID exists in database
3. Cache key consistent (same prompt, model, task_id)

### Issue: Tool replay not working

**Check**:
1. Same task_id and command used
2. First execution completed successfully
3. No `force_execute=True` parameter

---

## Migration Guide

### From Non-Recovery Runner

**Before**:
```python
runner = TaskRunner()
runner.run_task(task_id)
```

**After** (with recovery):
```python
runner = TaskRunner(enable_recovery=True)
runner.run_with_recovery(task_id)
```

**After** (without recovery):
```python
runner = TaskRunner(enable_recovery=False)
runner.run_task(task_id)  # Same as before
```

---

## API Reference

### TaskRunner Methods

- `run_with_recovery(task_id, max_iterations=100)` - Run with checkpoint recovery
- `resume_from_checkpoint(task_id, checkpoint)` - Resume from specific checkpoint
- `execute_work_item_with_checkpoint(task_id, work_item)` - Execute work item with checkpoint
- `collect_evidence(work_item, results)` - Collect evidence for verification

### CheckpointManager Methods

- `begin_step(task_id, checkpoint_type, snapshot, ...)` - Start checkpoint step
- `commit_step(step_id, evidence_pack)` - Commit checkpoint with evidence
- `verify_checkpoint(checkpoint_id)` - Verify checkpoint integrity
- `get_last_verified_checkpoint(task_id)` - Get last valid checkpoint
- `rollback_to_checkpoint(checkpoint_id)` - Rollback to checkpoint

### LLMOutputCache Methods

- `get_or_generate(operation_type, prompt, model, task_id, generate_fn)` - Get cached or generate
- `invalidate(operation_type, prompt, model, task_id)` - Invalidate cache entry
- `get_stats()` - Get cache statistics
- `reset_stats()` - Reset statistics counters

### ToolLedger Methods

- `execute_or_replay(tool_name, command, task_id, execute_fn)` - Execute or replay
- `get_execution_history(task_id, limit=100)` - Get execution history
- `get_stats()` - Get ledger statistics
- `reset_stats()` - Reset statistics counters

---

## Examples

### Complete Recovery Flow

```python
from agentos.core.runner import TaskRunner
from agentos.core.task import TaskManager

# Create task
task_mgr = TaskManager()
task = task_mgr.create_task(title="Recoverable Task")

# Create runner with recovery
runner = TaskRunner(enable_recovery=True)

# Run task (creates checkpoints automatically)
runner.run_with_recovery(task.task_id)

# If task crashes, restart will resume from last checkpoint
runner2 = TaskRunner(enable_recovery=True)
runner2.run_with_recovery(task.task_id)  # Resumes from checkpoint
```

### Manual Checkpoint Management

```python
from agentos.core.checkpoints import CheckpointManager, Evidence, EvidenceType, EvidencePack

manager = CheckpointManager()

# Begin work
step_id = manager.begin_step(
    task_id="task-123",
    checkpoint_type="iteration_start",
    snapshot={"iteration": 1}
)

# Do work...
result = execute_something()

# Collect evidence
evidence = Evidence(
    evidence_type=EvidenceType.COMMAND_EXIT,
    description="Work completed",
    expected={"exit_code": result["exit_code"]}
)

# Commit checkpoint
checkpoint = manager.commit_step(
    step_id=step_id,
    evidence_pack=EvidencePack(evidence_list=[evidence])
)

print(f"Checkpoint created: {checkpoint.checkpoint_id}")
```

---

## See Also

- [Task #9 Completion Report](TASK9_RUNNER_INTEGRATION_COMPLETION.md)
- [Task #7 CheckpointManager Documentation](agentos/core/checkpoints/README.md)
- [Task #10 Idempotency Documentation](agentos/core/idempotency/README.md)
- [Task #8 Lease Management Documentation](agentos/core/worker_pool/README.md)

---

**Document Version**: 1.0.0
**Last Updated**: 2026-01-29
**Maintained By**: AgentOS Team
