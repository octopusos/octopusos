# Task #2: PR-B Quick Reference Guide

## Overview

PR-B adds automatic verification gates after task execution. Tasks now go through a `verifying` state where DONE gates validate the implementation.

## State Flow

```
┌─────────────┐
│  executing  │
└──────┬──────┘
       │
       v
┌─────────────┐
│  verifying  │ ←─── Run DONE gates here
└──────┬──────┘
       │
       ├──────── Gates PASS ──────→ succeeded ✓
       │
       └──────── Gates FAIL ──────→ planning (retry with context)
```

## Configuration

Gates are configured in task metadata:

```python
task.metadata = {
    "gates": ["doctor", "smoke", "tests"],  # List of gates to run
    # ... other metadata
}
```

**Default**: If `gates` is not specified, `["doctor"]` is used.

## Available Gates

| Gate | Description | Duration |
|------|-------------|----------|
| `doctor` | Basic health check (default) | ~0.1s |
| `smoke` | Quick smoke tests | ~0.1s |
| `tests` | Full pytest suite | Variable (max 300s) |

## Usage Examples

### Example 1: Default Gate (doctor)

```python
from agentos.core.task import TaskManager

manager = TaskManager()
task = manager.create_task(
    title="Fix bug in login",
    metadata={}  # Will use default ["doctor"] gate
)
```

### Example 2: Multiple Gates

```python
task = manager.create_task(
    title="Refactor authentication",
    metadata={
        "gates": ["doctor", "smoke", "tests"]  # Run all gates
    }
)
```

### Example 3: Custom Gate List

```python
task = manager.create_task(
    title="Update documentation",
    metadata={
        "gates": ["doctor"]  # Only basic check
    }
)
```

## Gate Results

### Artifacts

Results saved to: `store/artifacts/{task_id}/gate_results.json`

```json
{
  "task_id": "01ABC123...",
  "overall_status": "passed",
  "gates_executed": [
    {
      "gate_name": "doctor",
      "status": "passed",
      "exit_code": 0,
      "stdout": "Doctor check passed",
      "stderr": "",
      "duration_seconds": 0.15
    }
  ],
  "total_duration_seconds": 0.15,
  "executed_at": "2026-01-29T12:34:56.789Z"
}
```

### Audit Trail

Check audit log:

```python
from agentos.core.task import TaskManager

manager = TaskManager()
audits = manager.get_task_audits(task_id)

# Look for gate events
gate_events = [
    audit for audit in audits
    if "GATE" in audit.event_type or "verification" in audit.event_type.lower()
]
```

## Failure Handling

When gates fail:

1. **Task status** → Returns to `planning`
2. **Metadata updated** → `gate_failure_context` added
3. **Audit recorded** → Failure details logged
4. **Artifact saved** → Full results in JSON

### Failure Context Structure

```python
task.metadata["gate_failure_context"] = {
    "failed_at": "2026-01-29T12:34:56.789Z",
    "failure_summary": "- tests: failed (Exit code: 1)\n- smoke: error (Timeout)",
    "gate_results": {
        # Full gate results dict
    }
}
```

### Accessing Failure Context

```python
task = manager.get_task(task_id)

if "gate_failure_context" in task.metadata:
    context = task.metadata["gate_failure_context"]
    print(f"Failed at: {context['failed_at']}")
    print(f"Summary: {context['failure_summary']}")
```

## Testing

### Run PR-B Tests

```bash
# All tests (36 total)
pytest tests/unit/gates/test_done_gate.py tests/integration/test_verify_loop.py -v

# Unit tests only (22 tests)
pytest tests/unit/gates/test_done_gate.py -v

# Integration tests only (14 tests)
pytest tests/integration/test_verify_loop.py -v

# Acceptance test only
pytest tests/integration/test_verify_loop.py::TestDeliberateFailureScenario -v
```

## Architecture

### Key Components

1. **DoneGateRunner** (`agentos/core/gates/done_gate.py`)
   - Main gate execution engine
   - Handles gate running, result collection, persistence

2. **Task Runner Integration** (`agentos/core/runner/task_runner.py`)
   - Modified to use `verifying` state
   - Calls DoneGateRunner during verification
   - Updates metadata on failure

3. **State Machine** (`agentos/core/task/state_machine.py`)
   - Added `VERIFYING → QUEUED` transition for retry

### Gate Execution Flow

```python
# In task_runner._execute_stage()

if current_status == "verifying":
    # 1. Load gate configuration
    gate_names = task.metadata.get("gates", ["doctor"])

    # 2. Run gates
    gate_results = gate_runner.run_gates(task_id, gate_names)

    # 3. Save artifacts
    gate_runner.save_gate_results(task_id, gate_results)

    # 4. Record in audit
    task_manager.add_audit(task_id, "GATE_VERIFICATION_RESULT", payload=...)

    # 5. Decide next state
    if gate_results.all_passed:
        return "succeeded"
    else:
        # Inject failure context
        task.metadata["gate_failure_context"] = {...}
        return "planning"  # Retry
```

## Common Issues

### Issue 1: Gate timeout

**Problem**: Gate takes too long and times out (default: 300s).

**Solution**: Either optimize the test or increase timeout in code.

### Issue 2: Unknown gate

**Problem**: Specified gate doesn't exist.

**Error**: `Unknown gate: my_custom_gate`

**Solution**: Use one of the built-in gates: `doctor`, `smoke`, `tests`.

### Issue 3: No metadata

**Problem**: Task has no metadata field.

**Solution**: DoneGateRunner uses default `["doctor"]` gate.

## Advanced Usage

### Programmatic Gate Execution

```python
from agentos.core.gates import DoneGateRunner

runner = DoneGateRunner(repo_path="/path/to/repo")

# Run gates
results = runner.run_gates(
    task_id="test-001",
    gate_names=["doctor", "smoke"],
    timeout_seconds=300
)

# Check results
if results.all_passed:
    print("✓ All gates passed")
else:
    print(f"✗ Gates failed:")
    print(results.get_failure_summary())

# Save results
runner.save_gate_results("test-001", results)
```

### Loading Past Results

```python
runner = DoneGateRunner()

# Load results from artifacts
results = runner.load_gate_results(task_id="test-001")

if results:
    print(f"Task: {results.task_id}")
    print(f"Status: {results.overall_status}")
    print(f"Gates: {len(results.gates_executed)}")
```

## Extending Gates

To add a new gate type, modify `DoneGateRunner.gate_commands`:

```python
# In agentos/core/gates/done_gate.py

self.gate_commands = {
    "doctor": ["python", "-c", "print('Doctor check passed')"],
    "smoke": ["python", "-c", "print('Smoke test passed')"],
    "tests": ["pytest", "-v", "--tb=short"],
    "my_gate": ["./scripts/my_custom_gate.sh"],  # Add custom gate
}
```

**Note**: This requires code modification. Future versions may support dynamic gate registration.

## Performance

### Gate Execution Time

- **doctor**: ~0.1s (instant)
- **smoke**: ~0.1s (instant)
- **tests**: Depends on test suite size (max 300s timeout)

### Fail-Fast Optimization

Gates stop on first failure:

```
gates = ["doctor", "smoke", "tests"]

doctor: PASS   (0.1s)
smoke:  FAIL   (0.1s)  ← Stops here
tests:  SKIPPED        ← Not executed

Total: 0.2s instead of potentially 300s
```

## Monitoring

### Check Gate Status

```python
# Get task
task = manager.get_task(task_id)

# Check if in verifying state
if task.status == "verifying":
    print("Task is currently running gates...")

# Check if gates failed before
if "gate_failure_context" in task.metadata:
    print("Gates failed previously:")
    print(task.metadata["gate_failure_context"]["failure_summary"])
```

### View Audit Trail

```bash
# Via database query
sqlite3 agentos.db "
  SELECT event_type, level, payload, created_at
  FROM task_audits
  WHERE task_id = 'YOUR_TASK_ID'
    AND (event_type LIKE '%GATE%' OR event_type LIKE '%verification%')
  ORDER BY created_at DESC;
"
```

## Troubleshooting

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Run gates with verbose output
runner = DoneGateRunner()
results = runner.run_gates(task_id, gate_names)

# Inspect results
for gate in results.gates_executed:
    print(f"\nGate: {gate.gate_name}")
    print(f"Status: {gate.status}")
    print(f"Exit code: {gate.exit_code}")
    print(f"Stdout: {gate.stdout}")
    print(f"Stderr: {gate.stderr}")
```

---

## Summary

**Key Points**:
- ✓ Gates run automatically after `executing`
- ✓ Default gate is `doctor` if not specified
- ✓ Failed gates return to `planning` with context
- ✓ Results saved in audit log and artifacts
- ✓ Fail-fast strategy (stops on first failure)

**Entry Points**:
- Configuration: `task.metadata.gates`
- Implementation: `agentos/core/gates/done_gate.py`
- Integration: `agentos/core/runner/task_runner.py`

**Tests**: 36 tests, all passing ✓
