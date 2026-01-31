# Checkpoint Manager Design

**Version**: 0.1.0
**Task**: #7 - P0-2 - CheckpointManager + EvidenceVerifier Implementation
**Date**: 2026-01-29

## Overview

The Checkpoint Management System provides evidence-based checkpoint verification for resumable task execution. It consists of two main components:

1. **CheckpointManager**: Manages checkpoint lifecycle (begin, commit, verify, rollback)
2. **EvidenceVerifier**: Verifies checkpoint integrity through 4 evidence types

This system builds on top of the database schema from Task #6 (schema v30 - recovery system).

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Checkpoint Management                     │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐        ┌─────────────────────────┐  │
│  │ CheckpointManager│───────>│  EvidenceVerifier       │  │
│  │                  │        │                         │  │
│  │ - begin_step()   │        │ - artifact_exists       │  │
│  │ - commit_step()  │        │ - file_sha256          │  │
│  │ - verify()       │        │ - command_exit         │  │
│  │ - rollback()     │        │ - db_row               │  │
│  └────────┬─────────┘        └─────────────────────────┘  │
│           │                                                 │
│           v                                                 │
│  ┌────────────────────────────────────────────────────┐   │
│  │              Database (SQLite)                      │   │
│  │  - checkpoints table (from schema v30)             │   │
│  │  - tasks table                                      │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Evidence

Represents a single piece of evidence for checkpoint verification.

```python
@dataclass
class Evidence:
    evidence_type: EvidenceType       # Type of evidence
    description: str                   # Human-readable description
    expected: Dict[str, Any]          # Expected values/conditions
    metadata: Dict[str, Any]          # Additional metadata
    verified: bool                     # Verification status
    verification_status: VerificationStatus
    verification_error: Optional[str]
    verified_at: Optional[datetime]
```

### EvidencePack

Collection of evidence for a checkpoint.

```python
@dataclass
class EvidencePack:
    evidence_list: List[Evidence]     # List of evidence
    require_all: bool                 # All must verify (default: True)
    allow_partial: bool               # Allow partial verification
    min_verified: int                 # Minimum verified count
```

### Checkpoint

Checkpoint with evidence-based verification.

```python
@dataclass
class Checkpoint:
    checkpoint_id: str                # ULID or UUID
    task_id: str                      # Associated task
    work_item_id: Optional[str]       # Associated work item
    checkpoint_type: str              # Type (from schema enum)
    sequence_number: int              # Monotonic sequence
    snapshot_data: Dict[str, Any]     # State snapshot
    evidence_pack: EvidencePack       # Evidence for verification
    metadata: Dict[str, Any]          # Additional metadata
    created_at: Optional[datetime]
    verified: bool                    # Verification status
    last_verified_at: Optional[datetime]
```

---

## Evidence Types

### 1. artifact_exists

Verifies that a file or directory exists.

**Expected Format:**
```python
{
    "path": "/path/to/artifact",
    "type": "file" | "directory" | "any"  # optional, default: "any"
}
```

**Example:**
```python
Evidence(
    evidence_type=EvidenceType.ARTIFACT_EXISTS,
    description="Output file created",
    expected={"path": "/tmp/output.txt", "type": "file"}
)
```

**Verification Logic:**
1. Check if path exists
2. If type specified, verify it matches (file/directory)
3. Support relative paths (resolved against base_path)

### 2. file_sha256

Verifies file content hash matches expected SHA256.

**Expected Format:**
```python
{
    "path": "/path/to/file",
    "sha256": "expected_hash_hex"
}
```

**Example:**
```python
Evidence(
    evidence_type=EvidenceType.FILE_SHA256,
    description="Config file unchanged",
    expected={
        "path": "/etc/config.yaml",
        "sha256": "abc123..."
    }
)
```

**Verification Logic:**
1. Check file exists
2. Compute SHA256 hash
3. Compare with expected hash

### 3. command_exit

Verifies command exit code matches expected.

**Expected Format:**
```python
{
    "exit_code": 0  # expected exit code
}
```

**Metadata (optional):**
```python
{
    "command": "command that was run",  # for documentation
    "timeout": 30                        # not used in verification
}
```

**Example:**
```python
Evidence(
    evidence_type=EvidenceType.COMMAND_EXIT,
    description="Script executed successfully",
    expected={"exit_code": 0},
    metadata={"command": "python script.py"}
)
```

**Verification Logic:**
1. Validate expected_code is provided and is integer
2. Return True if valid (actual exit code stored in snapshot_data)

**Note:** This evidence type verifies that a command previously executed returned the expected exit code. It does NOT re-run the command during verification.

### 4. db_row

Verifies database row exists with expected values.

**Expected Format:**
```python
{
    "table": "table_name",
    "where": {"column": "value", ...},  # WHERE clause
    "values": {"column": "value", ...}  # expected values
}
```

**Metadata:**
```python
{
    "db_path": "/path/to/database.sqlite"  # optional
}
```

**Example:**
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

**Verification Logic:**
1. Connect to database
2. Execute SELECT with WHERE conditions
3. Check row exists
4. Verify column values match expected

---

## CheckpointManager API

### Constructor

```python
CheckpointManager(
    db_path: str = "store/registry.sqlite",
    base_path: Optional[Path] = None,
    auto_verify: bool = True
)
```

**Parameters:**
- `db_path`: Path to SQLite database
- `base_path`: Base path for evidence verification (default: cwd)
- `auto_verify`: Automatically verify checkpoints after creation

### Core Methods

#### begin_step()

Begin a new execution step.

```python
def begin_step(
    task_id: str,
    checkpoint_type: str,
    snapshot: Dict[str, Any],
    work_item_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str
```

**Returns:** step_id (use in commit_step)

**Example:**
```python
step_id = manager.begin_step(
    task_id="task-123",
    checkpoint_type="iteration_start",
    snapshot={"iteration": 1, "state": "planning"}
)
```

#### commit_step()

Commit a step as a checkpoint with evidence.

```python
def commit_step(
    step_id: str,
    evidence_pack: EvidencePack,
    checkpoint_id: Optional[str] = None
) -> Checkpoint
```

**Returns:** Checkpoint object with evidence

**Example:**
```python
evidence_pack = EvidencePack([
    Evidence(EvidenceType.ARTIFACT_EXISTS, "Log file", {"path": "/tmp/run.log"}),
])

checkpoint = manager.commit_step(step_id, evidence_pack)
```

#### verify_checkpoint()

Verify checkpoint evidence.

```python
def verify_checkpoint(checkpoint_id: str) -> bool
```

**Returns:** True if verification passed

**Example:**
```python
is_valid = manager.verify_checkpoint(checkpoint.checkpoint_id)
```

#### get_last_verified_checkpoint()

Get the last verified checkpoint for a task.

```python
def get_last_verified_checkpoint(
    task_id: str,
    checkpoint_type: Optional[str] = None
) -> Optional[Checkpoint]
```

**Returns:** Last verified Checkpoint or None

**Example:**
```python
last_checkpoint = manager.get_last_verified_checkpoint("task-123")
if last_checkpoint:
    snapshot = last_checkpoint.snapshot_data
```

#### rollback_to_checkpoint()

Rollback to a checkpoint.

```python
def rollback_to_checkpoint(checkpoint_id: str) -> Dict[str, Any]
```

**Returns:** Snapshot data from checkpoint

**Raises:** CheckpointError if verification fails

**Example:**
```python
try:
    snapshot = manager.rollback_to_checkpoint(checkpoint_id)
    # Restore state from snapshot
    restore_state(snapshot)
except CheckpointError as e:
    print(f"Rollback failed: {e}")
```

### Additional Methods

#### get_checkpoint()

```python
def get_checkpoint(checkpoint_id: str) -> Optional[Checkpoint]
```

#### list_checkpoints()

```python
def list_checkpoints(
    task_id: str,
    limit: int = 100,
    checkpoint_type: Optional[str] = None
) -> List[Checkpoint]
```

#### delete_checkpoint()

```python
def delete_checkpoint(checkpoint_id: str) -> bool
```

---

## EvidenceVerifier API

### Constructor

```python
EvidenceVerifier(base_path: Optional[Path] = None)
```

### Core Methods

#### verify_evidence()

Verify a single piece of evidence.

```python
def verify_evidence(evidence: Evidence) -> bool
```

**Updates evidence object with:**
- `verified`: True/False
- `verification_status`: VERIFIED or FAILED
- `verification_error`: Error message if failed
- `verified_at`: Timestamp

#### verify_evidence_pack()

Verify all evidence in a pack.

```python
def verify_evidence_pack(pack: EvidencePack) -> bool
```

**Returns:** True if pack verification passed according to requirements

#### verify_multiple()

Verify multiple evidence items and return summary.

```python
def verify_multiple(evidence_list: List[Evidence]) -> Dict[str, Any]
```

**Returns:**
```python
{
    "total": int,
    "verified": int,
    "failed": int,
    "success_rate": float,
    "all_passed": bool
}
```

---

## Usage Examples

### Example 1: Simple Checkpoint

```python
from agentos.core.checkpoints import CheckpointManager, EvidencePack, Evidence, EvidenceType

# Initialize manager
manager = CheckpointManager()

# Begin step
step_id = manager.begin_step(
    task_id="task-123",
    checkpoint_type="tool_executed",
    snapshot={"tool": "bash", "command": "ls -la", "result": "success"}
)

# Create evidence
evidence_pack = EvidencePack([
    Evidence(
        evidence_type=EvidenceType.ARTIFACT_EXISTS,
        description="Log file created",
        expected={"path": "/tmp/run.log"}
    )
])

# Commit checkpoint
checkpoint = manager.commit_step(step_id, evidence_pack)

print(f"Checkpoint created: {checkpoint.checkpoint_id}")
print(f"Verified: {checkpoint.verified}")
```

### Example 2: Multiple Evidence Types

```python
# Create comprehensive evidence pack
evidence_pack = EvidencePack([
    # File exists
    Evidence(
        evidence_type=EvidenceType.ARTIFACT_EXISTS,
        description="Output file created",
        expected={"path": "/tmp/output.txt", "type": "file"}
    ),
    # File hash
    Evidence(
        evidence_type=EvidenceType.FILE_SHA256,
        description="Output content verified",
        expected={
            "path": "/tmp/output.txt",
            "sha256": "abc123..."
        }
    ),
    # Command exit
    Evidence(
        evidence_type=EvidenceType.COMMAND_EXIT,
        description="Command succeeded",
        expected={"exit_code": 0}
    ),
    # Database row
    Evidence(
        evidence_type=EvidenceType.DB_ROW,
        description="Task status updated",
        expected={
            "table": "tasks",
            "where": {"task_id": "task-123"},
            "values": {"status": "completed"}
        }
    ),
])

step_id = manager.begin_step("task-123", "iteration_end", {"iteration": 1})
checkpoint = manager.commit_step(step_id, evidence_pack)
```

### Example 3: Recovery from Checkpoint

```python
# Find last verified checkpoint
last_checkpoint = manager.get_last_verified_checkpoint("task-123")

if last_checkpoint:
    # Rollback to checkpoint
    snapshot = manager.rollback_to_checkpoint(last_checkpoint.checkpoint_id)

    # Restore state
    iteration = snapshot["iteration"]
    state = snapshot["state"]

    print(f"Resuming from iteration {iteration}")
else:
    print("No verified checkpoint found, starting from beginning")
```

### Example 4: Partial Evidence Verification

```python
# Allow partial verification (at least 2 out of 3)
evidence_pack = EvidencePack(
    evidence_list=[
        Evidence(EvidenceType.ARTIFACT_EXISTS, "File 1", {"path": "/tmp/f1.txt"}),
        Evidence(EvidenceType.ARTIFACT_EXISTS, "File 2", {"path": "/tmp/f2.txt"}),
        Evidence(EvidenceType.ARTIFACT_EXISTS, "File 3", {"path": "/tmp/f3.txt"}),
    ],
    require_all=False,
    allow_partial=True,
    min_verified=2
)

step_id = manager.begin_step("task-123", "tool_executed", {"result": "partial"})
checkpoint = manager.commit_step(step_id, evidence_pack)

# Check verification summary
summary = checkpoint.evidence_pack.verification_summary()
print(f"Verified: {summary['verified']}/{summary['total']}")
print(f"Is valid: {summary['is_verified']}")
```

### Example 5: Manual Verification

```python
# Create checkpoint without auto-verify
manager = CheckpointManager(auto_verify=False)

step_id = manager.begin_step("task-123", "iteration_start", {"iteration": 1})
checkpoint = manager.commit_step(step_id, evidence_pack)

# Verify later
is_verified = manager.verify_checkpoint(checkpoint.checkpoint_id)

if is_verified:
    print("Checkpoint verified successfully")
else:
    # Check individual evidence
    checkpoint = manager.get_checkpoint(checkpoint.checkpoint_id)
    for evidence in checkpoint.evidence_pack.evidence_list:
        if not evidence.verified:
            print(f"Failed: {evidence.description} - {evidence.verification_error}")
```

---

## Integration with Recovery System

### Workflow Integration

```python
from agentos.core.checkpoints import CheckpointManager

def execute_task_with_checkpoints(task_id: str):
    manager = CheckpointManager()

    # Check for existing checkpoint
    last_checkpoint = manager.get_last_verified_checkpoint(task_id)

    if last_checkpoint:
        # Resume from checkpoint
        snapshot = manager.rollback_to_checkpoint(last_checkpoint.checkpoint_id)
        iteration = snapshot["iteration"] + 1
    else:
        # Start from beginning
        iteration = 1

    # Execute iterations
    while iteration <= max_iterations:
        # Begin step
        step_id = manager.begin_step(
            task_id=task_id,
            checkpoint_type="iteration_start",
            snapshot={"iteration": iteration, "state": get_state()}
        )

        try:
            # Do work
            result = execute_iteration(iteration)

            # Create evidence
            evidence_pack = create_evidence(result)

            # Commit checkpoint
            checkpoint = manager.commit_step(step_id, evidence_pack)

            if not checkpoint.verified:
                raise Exception("Checkpoint verification failed")

            iteration += 1

        except Exception as e:
            # Rollback to last checkpoint
            if last_checkpoint:
                manager.rollback_to_checkpoint(last_checkpoint.checkpoint_id)
            raise
```

---

## Best Practices

### Evidence Selection

✅ **DO:**
- Use multiple evidence types for critical checkpoints
- Verify file existence before file hash
- Store command exit codes in snapshot_data
- Use database evidence for state transitions

❌ **DON'T:**
- Don't rely on single evidence for important checkpoints
- Don't store large files in evidence (use hash instead)
- Don't skip verification for recovery checkpoints
- Don't assume evidence will always pass

### Checkpoint Strategy

✅ **DO:**
- Create checkpoints at iteration boundaries
- Include enough state to resume execution
- Verify checkpoints immediately after creation
- Keep snapshot_data < 1 MB

❌ **DON'T:**
- Don't create checkpoints too frequently (performance)
- Don't store secrets in snapshot_data
- Don't skip evidence for convenience
- Don't modify checkpoints after creation

### Error Handling

✅ **DO:**
- Handle verification failures gracefully
- Log verification errors for debugging
- Retry verification with exponential backoff
- Fall back to earlier checkpoint if recent fails

❌ **DON'T:**
- Don't ignore verification failures
- Don't assume filesystem state is stable
- Don't rollback without verification
- Don't delete checkpoints prematurely

---

## Testing

### Unit Tests

Located in `/tests/unit/checkpoints/`:

- `test_evidence.py`: Tests all 4 evidence types
- `test_manager.py`: Tests CheckpointManager lifecycle

**Run tests:**
```bash
pytest tests/unit/checkpoints/ -v
```

### Test Coverage

- ✅ All evidence types (artifact_exists, file_sha256, command_exit, db_row)
- ✅ Evidence pack verification (require_all, allow_partial)
- ✅ Checkpoint lifecycle (begin, commit, verify, rollback)
- ✅ Error handling and edge cases
- ✅ Serialization (to_dict, from_dict)
- ✅ Integration scenarios

---

## Performance Considerations

### Database Operations

- Checkpoint creation: O(1) - single INSERT
- Checkpoint verification: O(n) where n = evidence count
- Get last checkpoint: O(log m) where m = checkpoints for task
- List checkpoints: O(k) where k = limit

### Evidence Verification

- artifact_exists: O(1) - filesystem check
- file_sha256: O(f) where f = file size
- command_exit: O(1) - integer comparison
- db_row: O(1) with indexed query

### Optimization Tips

1. **Batch verification**: Verify multiple evidence in parallel
2. **Cache file hashes**: Store in metadata to avoid recomputation
3. **Index database**: Ensure WHERE columns are indexed
4. **Limit checkpoint retention**: Delete old checkpoints periodically

---

## Security Considerations

### Evidence Integrity

- File paths: Validate against directory traversal
- Database queries: Use parameterized queries only
- Command info: Store for audit, don't re-execute
- Hash verification: Use cryptographic hash (SHA256)

### Data Protection

- Don't store secrets in snapshot_data
- Don't log sensitive evidence details
- Encrypt checkpoints if required by policy
- Use file permissions to protect database

---

## Future Enhancements

### P1: Advanced Evidence Types

- `network_reachable`: Verify network connectivity
- `api_response`: Verify API endpoint response
- `container_running`: Verify Docker container state
- `process_exists`: Verify process is running

### P2: Compression

- Compress large snapshot_data (gzip)
- Store compressed evidence
- Implement checkpoint archival

### P3: Distributed Verification

- Verify checkpoints across multiple workers
- Consensus-based verification
- Remote evidence verification

### P4: Monitoring

- Checkpoint creation rate metrics
- Verification success rate metrics
- Evidence failure analysis
- Checkpoint size monitoring

---

## References

- Database Schema: `docs/specs/RECOVERY_DATABASE_SCHEMA.md`
- Quick Reference: `docs/specs/RECOVERY_QUICK_REFERENCE.md`
- Task #6 Report: `TASK6_RECOVERY_SCHEMA_COMPLETION_REPORT.md`
- Migration: `agentos/store/migrations/schema_v30_recovery.sql`

---

**Document Version**: 0.1.0
**Last Updated**: 2026-01-29
**Author**: Claude Sonnet 4.5
**Task**: #7 - P0-2 - CheckpointManager + EvidenceVerifier Implementation
