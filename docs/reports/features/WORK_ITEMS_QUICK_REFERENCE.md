# Work Items Framework - Quick Reference

## Overview

The work_items framework enables complex tasks to be broken down into independent sub-tasks (work items) that are executed by separate agents.

**Version**: PR-C (Serial Execution)
**Status**: Production Ready

---

## Quick Start

### 1. Define Work Items in Planning Stage

```python
from agentos.core.task.work_items import WorkItem

work_items = [
    WorkItem(
        item_id="wi_frontend",
        title="Implement frontend UI",
        description="Create React components with responsive design",
        dependencies=[],
    ),
    WorkItem(
        item_id="wi_backend",
        title="Implement backend API",
        description="Create REST endpoints with database models",
        dependencies=[],
    ),
    WorkItem(
        item_id="wi_tests",
        title="Write integration tests",
        description="End-to-end tests covering all features",
        dependencies=["wi_frontend", "wi_backend"],
    ),
]
```

### 2. Save to Task Metadata

```python
task.metadata["work_items"] = [item.to_dict() for item in work_items]
task_manager.update_task_metadata(task.task_id, task.metadata)
```

### 3. Execute (Automatic in TaskRunner)

When task reaches `executing` state, TaskRunner automatically:
1. Detects work_items in metadata
2. Executes each serially
3. Records audit for each
4. Creates summary artifact

### 4. Check Results

```python
from agentos.core.task.work_items import WorkItemsSummary

# Load summary artifact
with open(f"store/artifacts/{task_id}/work_items_summary.json") as f:
    summary_data = json.load(f)

summary = WorkItemsSummary.from_dict(summary_data)

if summary.all_succeeded:
    print("All work items completed successfully!")
else:
    print(f"Failures: {summary.get_failure_summary()}")
```

---

## Data Schemas

### WorkItem

```python
@dataclass
class WorkItem:
    item_id: str                    # Unique ID (e.g., "wi_001")
    title: str                      # Short description
    description: str                # Detailed task description
    dependencies: List[str]         # List of item_ids this depends on
    status: WorkItemStatus          # PENDING|RUNNING|COMPLETED|FAILED|SKIPPED
    output: Optional[WorkItemOutput]  # Execution results
    started_at: Optional[str]       # ISO timestamp
    completed_at: Optional[str]     # ISO timestamp
    error: Optional[str]            # Error message if failed
    metadata: Dict[str, Any]        # Additional metadata
```

### WorkItemOutput

```python
@dataclass
class WorkItemOutput:
    files_changed: List[str]              # ["src/app.py", "tests/test_app.py"]
    commands_run: List[str]               # ["pytest", "ruff check"]
    tests_run: List[Dict[str, Any]]       # Test execution results
    evidence: Optional[str]               # Execution evidence
    handoff_notes: Optional[str]          # Notes for next work item
```

### WorkItemsSummary

```python
@dataclass
class WorkItemsSummary:
    total_items: int              # Total work items
    completed_count: int          # Successfully completed
    failed_count: int             # Failed work items
    skipped_count: int            # Skipped work items
    overall_status: str           # "success"|"partial"|"failed"
    work_items: List[WorkItem]    # All work items with results
    execution_order: List[str]    # Order of execution
    total_duration_seconds: float # Total time taken
```

---

## Execution Flow

```
1. Planning Stage
   └─> Extract work_items from plan
   └─> Save to task.metadata.work_items
   └─> Record WORK_ITEMS_EXTRACTED audit

2. Executing Stage
   └─> Load work_items from metadata
   └─> For each work_item:
       ├─> Mark as RUNNING
       ├─> Record WORK_ITEM_STARTED audit
       ├─> Execute sub-agent
       ├─> Collect WorkItemOutput
       ├─> Mark as COMPLETED/FAILED
       ├─> Record WORK_ITEM_COMPLETED/FAILED audit
       └─> Save work_item artifact
   └─> Create WorkItemsSummary
   └─> Save work_items_summary.json
   └─> Transition to verifying

3. Verifying Stage
   └─> Run DONE gates (Task #2)
   └─> If pass: succeeded
   └─> If fail: back to planning
```

---

## API Reference

### Core Functions

```python
# Extract work items from pipeline result
from agentos.core.task.work_items import extract_work_items_from_pipeline

work_items = extract_work_items_from_pipeline(pipeline_result)
```

```python
# Create summary from work items
from agentos.core.task.work_items import create_work_items_summary

summary = create_work_items_summary(work_items)
```

### TaskRunner Methods

```python
# Extract and save work items (called in planning stage)
runner._extract_work_items(task_id, pipeline_result)

# Execute work items serially (called in executing stage)
summary = runner._execute_work_items_serial(task_id, work_items_data)

# Execute single work item
output = runner._execute_single_work_item(task_id, work_item)
```

---

## Artifacts

### work_items_summary.json

**Location**: `store/artifacts/{task_id}/work_items_summary.json`

**Structure**:
```json
{
  "total_items": 3,
  "completed_count": 3,
  "failed_count": 0,
  "overall_status": "success",
  "work_items": [
    {
      "item_id": "wi_001",
      "title": "Implement feature X",
      "status": "completed",
      "output": {
        "files_changed": ["src/x.py"],
        "commands_run": ["pytest"],
        "tests_run": [{"passed": 10, "failed": 0}],
        "evidence": "All tests passed",
        "handoff_notes": "Ready for review"
      },
      "started_at": "2026-01-29T10:00:00Z",
      "completed_at": "2026-01-29T10:05:00Z"
    }
  ],
  "execution_order": ["wi_001", "wi_002", "wi_003"],
  "total_duration_seconds": 15.5
}
```

### work_item_{item_id}.json

**Location**: `store/artifacts/{task_id}/work_item_{item_id}.json`

**Structure**:
```json
{
  "item_id": "wi_001",
  "output": {
    "files_changed": [...],
    "commands_run": [...],
    "tests_run": [...],
    "evidence": "...",
    "handoff_notes": "..."
  },
  "saved_at": "2026-01-29T10:05:00Z"
}
```

---

## Audit Events

### WORK_ITEMS_EXTRACTED
- **When**: After planning stage extracts work items
- **Payload**: `{"count": 3, "items": [...]}`

### WORK_ITEM_STARTED
- **When**: Before executing a work item
- **Payload**: `{"item_id": "wi_001", "title": "...", "index": 0}`

### WORK_ITEM_COMPLETED
- **When**: After successful execution
- **Payload**: `{"item_id": "wi_001", "title": "...", "output": {...}}`

### WORK_ITEM_FAILED
- **When**: After failed execution
- **Payload**: `{"item_id": "wi_001", "title": "...", "error": "..."}`

---

## Error Handling

### Failure Strategies

**PR-C (Current): Fail-Fast**
- Stop on first failure
- Return to planning with failure context
- User can retry or modify plan

**PR-D (Future): Advanced Policies**
- Retry with exponential backoff
- Skip failed items and continue
- Conditional execution based on dependencies

### Example: Handle Failure

```python
summary = runner._execute_work_items_serial(task_id, work_items_data)

if summary.any_failed:
    # Log failure details
    logger.error(f"Work items failed:\n{summary.get_failure_summary()}")

    # Return to planning with context
    task.metadata["work_items_failure"] = {
        "failed_items": [
            item.to_dict()
            for item in summary.work_items
            if item.status == WorkItemStatus.FAILED
        ],
        "failure_summary": summary.get_failure_summary(),
    }

    return "planning"  # Retry planning with failure context
```

---

## Testing

### Unit Test Example

```python
from agentos.core.task.work_items import WorkItem, WorkItemOutput

def test_work_item_lifecycle():
    item = WorkItem(
        item_id="wi_test",
        title="Test item",
        description="Test description",
    )

    # Mark running
    item.mark_running()
    assert item.status == WorkItemStatus.RUNNING

    # Mark completed
    output = WorkItemOutput(files_changed=["test.py"])
    item.mark_completed(output)
    assert item.status == WorkItemStatus.COMPLETED
    assert item.output is not None
```

### Integration Test Example

```python
def test_work_items_execution(task_manager, runner):
    # Create task with work items
    task = task_manager.create_task(title="Test task")
    task.metadata["work_items"] = [
        {
            "item_id": "wi_001",
            "title": "Item 1",
            "description": "First item",
            "dependencies": [],
            "status": "pending",
        }
    ]

    # Execute
    summary = runner._execute_work_items_serial(
        task.task_id,
        task.metadata["work_items"]
    )

    # Verify
    assert summary.all_succeeded
    assert summary.completed_count == 1
```

---

## Best Practices

### 1. Work Item Granularity
- Each work item should be independently executable
- Size: 5-30 minutes of work per item
- Too small = overhead; Too large = hard to parallelize

### 2. Dependencies
- Minimize dependencies when possible
- Use dependencies for true order requirements only
- Example: "tests" depends on "frontend" + "backend"

### 3. Descriptions
- Be specific and actionable
- Include acceptance criteria
- Provide context from previous work items

### 4. Output Schema
- Always populate all fields in WorkItemOutput
- Use evidence field for verification
- Use handoff_notes for next steps

### 5. Error Messages
- Be specific about what failed
- Include enough context for debugging
- Suggest remediation steps

---

## Common Patterns

### Pattern 1: Frontend + Backend + Tests

```python
work_items = [
    WorkItem(
        item_id="wi_frontend",
        title="Frontend implementation",
        description="Create UI components",
        dependencies=[],
    ),
    WorkItem(
        item_id="wi_backend",
        title="Backend implementation",
        description="Create API endpoints",
        dependencies=[],
    ),
    WorkItem(
        item_id="wi_tests",
        title="Integration tests",
        description="End-to-end testing",
        dependencies=["wi_frontend", "wi_backend"],
    ),
]
```

### Pattern 2: Sequential Pipeline

```python
work_items = [
    WorkItem(item_id="wi_data", title="Prepare data", dependencies=[]),
    WorkItem(item_id="wi_process", title="Process data", dependencies=["wi_data"]),
    WorkItem(item_id="wi_output", title="Generate output", dependencies=["wi_process"]),
]
```

### Pattern 3: Independent Tasks

```python
work_items = [
    WorkItem(item_id="wi_docs", title="Update docs", dependencies=[]),
    WorkItem(item_id="wi_tests", title="Add tests", dependencies=[]),
    WorkItem(item_id="wi_refactor", title="Refactor code", dependencies=[]),
]
# Can be parallelized in PR-D
```

---

## Troubleshooting

### Issue: Work items not extracted

**Symptom**: No work items in executing stage

**Solutions**:
1. Check planning stage output format
2. Verify `extract_work_items_from_pipeline()` implementation
3. Check audit logs for WORK_ITEMS_EXTRACTED event

### Issue: Work item stuck in RUNNING

**Symptom**: Work item never completes

**Solutions**:
1. Check sub-agent execution logs
2. Verify timeout settings
3. Check for blocking operations

### Issue: Summary artifact not found

**Symptom**: `work_items_summary.json` missing

**Solutions**:
1. Check executing stage completed successfully
2. Verify artifacts directory permissions
3. Check runner logs for save errors

---

## Performance Considerations

### Current (PR-C): Serial Execution
- Time = Sum of all work item durations
- Example: 3 items × 5 min = 15 min total

### Future (PR-D): Parallel Execution
- Time = Max(work item durations) + dependency overhead
- Example: 3 items × 5 min = ~5 min total (if no dependencies)

### Optimization Tips
1. Minimize work item size (faster iteration)
2. Reduce dependencies (enables parallelization)
3. Use efficient sub-agent execution
4. Cache intermediate results

---

## Related Documentation

- **Task #2**: DONE Gates Implementation
- **Task #3 PR-D**: Parallel Work Items (future)
- **Architecture**: Task State Machine
- **API Reference**: TaskManager and TaskRunner

---

**Last Updated**: 2026-01-29
**Version**: 1.0 (PR-C)
**Status**: Production Ready
