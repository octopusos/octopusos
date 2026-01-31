# PR-E1 Quick Reference

## API Endpoints

### Execute Command
```bash
POST /api/extensions/execute
Content-Type: application/json

{
  "session_id": "sess_abc123",
  "command": "/test hello world",
  "dry_run": false
}

# Response
{
  "run_id": "run_abc123def456",
  "status": "PENDING"
}
```

### Query Run Status
```bash
GET /api/runs/{run_id}

# Response
{
  "run_id": "run_abc123def456",
  "extension_id": "test.test",
  "action_id": "execute",
  "status": "RUNNING",
  "progress_pct": 60,
  "current_stage": "EXECUTING",
  "stages": [...],
  "stdout": "...",
  "stderr": "",
  "error": null,
  "started_at": "2024-01-30T10:00:00Z",
  "ended_at": null,
  "duration_seconds": null,
  "metadata": {...}
}
```

### List Runs
```bash
GET /api/runs?extension_id=test.test&status=RUNNING&limit=10

# Response
{
  "runs": [...],
  "total": 5
}
```

## Python Usage

### Create and Execute Run

```python
from agentos.core.capabilities.runner_base import Invocation
from agentos.core.capabilities.runner_base.mock import MockRunner
from agentos.core.runs import RunStore

# Create store
store = RunStore()

# Create run record
run = store.create_run(
    extension_id="test.example",
    action_id="demo"
)

# Create runner
runner = MockRunner(delay_per_stage=0.5)

# Create invocation
invocation = Invocation(
    extension_id="test.example",
    action_id="demo",
    session_id="sess_123",
    args=["arg1", "arg2"],
    flags={"verbose": True}
)

# Progress callback
def progress_cb(stage, pct, msg):
    store.update_progress(run.run_id, stage, pct, msg)

# Execute
result = runner.run(invocation, progress_cb=progress_cb)

# Complete run
store.complete_run(
    run_id=run.run_id,
    status=RunStatus.SUCCEEDED if result.success else RunStatus.FAILED,
    stdout=result.output,
    error=result.error
)

# Query run
final_run = store.get_run(run.run_id)
print(f"Status: {final_run.status.value}")
print(f"Progress: {final_run.progress_pct}%")
print(f"Output: {final_run.stdout}")
```

### Implement Custom Runner

```python
from agentos.core.capabilities.runner_base import (
    Runner, Invocation, RunResult, ProgressCallback
)
from typing import Optional

class MyCustomRunner(Runner):
    @property
    def runner_type(self) -> str:
        return "custom.my_runner"

    def run(
        self,
        invocation: Invocation,
        progress_cb: Optional[ProgressCallback] = None
    ) -> RunResult:
        # Validate inputs
        if progress_cb:
            progress_cb("VALIDATING", 5, "Validating inputs")

        # Do work
        if progress_cb:
            progress_cb("EXECUTING", 50, "Processing...")

        output = "Custom execution result"

        # Finalize
        if progress_cb:
            progress_cb("DONE", 100, "Complete")

        return RunResult(
            success=True,
            output=output,
            exit_code=0,
            duration_ms=1000
        )
```

## Run States

```
PENDING  → Created but not started
   ↓
RUNNING  → Currently executing
   ↓
SUCCEEDED / FAILED / TIMEOUT / CANCELED  → Terminal states
```

## Progress Stages

```
VALIDATING (5%)    → Validate inputs and permissions
   ↓
LOADING (15%)      → Load extension resources
   ↓
EXECUTING (60%)    → Main execution phase
   ↓
FINALIZING (90%)   → Post-processing and cleanup
   ↓
DONE (100%)        → Execution complete
```

## Testing

### Run Unit Tests
```bash
python3 test_pr_e1_runner.py
```

### Run API Tests (requires server)
```bash
# Terminal 1
python -m agentos.webui.app

# Terminal 2
python3 test_pr_e1_api.py
```

## File Locations

```
agentos/
├── core/
│   ├── capabilities/
│   │   └── runner_base/          # Runner base classes
│   │       ├── __init__.py
│   │       ├── base.py            # Runner, Invocation, RunResult
│   │       └── mock.py            # MockRunner
│   └── runs/                      # Run state management
│       ├── __init__.py
│       ├── models.py              # RunStatus, RunRecord
│       └── store.py               # RunStore
└── webui/
    └── api/
        └── extensions_execute.py  # API endpoints
```

## Key Classes

- **Runner** - Abstract base for execution
- **Invocation** - Execution request
- **RunResult** - Execution response
- **RunRecord** - Full run lifecycle tracking
- **RunStore** - Thread-safe run storage
- **MockRunner** - Test implementation

## Common Patterns

### Background Execution
```python
import threading

def execute_in_background(invocation, run_id):
    runner = MockRunner()
    result = runner.run(invocation, progress_cb=...)
    # Update store with result

thread = threading.Thread(
    target=execute_in_background,
    args=(invocation, run_id),
    daemon=True
)
thread.start()
```

### Polling for Completion
```python
import time

while True:
    run = store.get_run(run_id)
    if run.is_terminal:
        break
    time.sleep(0.5)

print(f"Final status: {run.status.value}")
```

### Filtering Runs
```python
# Get all successful runs for an extension
runs = store.list_runs(
    extension_id="test.example",
    status=RunStatus.SUCCEEDED,
    limit=10
)

for run in runs:
    print(f"{run.run_id}: {run.duration_seconds}s")
```
