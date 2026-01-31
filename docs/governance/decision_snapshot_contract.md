# DecisionSnapshot Schema Contract

## Overview

`DecisionSnapshot` is the core data structure for Decision Replay. It represents a complete, immutable record of a governance decision.

This document defines the schema contract and versioning rules.

## Schema Version

**Current Version:** `1.0`

**Location:** `agentos.core.supervisor.audit_schema`

## Schema Definition

```python
@dataclass(frozen=True)
class DecisionSnapshot:
    """
    Complete decision record for audit and replay

    All fields are required unless explicitly marked Optional.
    """
    decision_id: str                      # Decision unique ID
    policy: str                           # Applied policy name
    event: EventRef                       # Triggering event
    inputs: dict[str, Any]                # Policy inputs (task state, context)
    findings: list[FindingSnapshot]       # Issues found during evaluation
    decision: dict[str, Any]              # Final decision result
    actions: list[dict[str, Any]]         # Actions executed
    metrics: dict[str, Any]               # Performance metrics
```

### EventRef

Records the event that triggered the decision.

```python
@dataclass(frozen=True)
class EventRef:
    event_id: str      # Event unique ID
    event_type: str    # Event type (TASK_CREATED, TASK_STEP_COMPLETED, etc.)
    source: str        # Event source: "eventbus" | "polling"
    ts: str            # ISO8601 timestamp
```

**Validation Rules:**
- All fields are required and must be non-empty strings
- `source` must be exactly `"eventbus"` or `"polling"`
- `ts` must be valid ISO8601 format

### FindingSnapshot

Records an issue discovered during policy evaluation.

```python
@dataclass(frozen=True)
class FindingSnapshot:
    kind: FindingKind               # Finding type
    severity: Severity              # Severity level
    code: str                       # Issue code (e.g., "REDLINE_001")
    message: str                    # Human-readable description
    evidence: dict[str, Any]        # Evidence data
```

**Enums:**
```python
FindingKind = Literal["REDLINE", "CONFLICT", "RISK", "RUNTIME"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
```

**Validation Rules:**
- All fields are required
- `kind` must be one of the `FindingKind` values
- `severity` must be one of the `Severity` values
- `code` and `message` must be non-empty strings
- `evidence` must be a dict (can be empty)

### Decision

The `decision` field is a dictionary with the following structure:

```python
{
    "decision_type": DecisionType,  # Required
    "reason": str,                  # Optional - human-readable reason
    # Additional fields as needed
}
```

**Enums:**
```python
DecisionType = Literal["ALLOW", "PAUSE", "BLOCK", "RETRY"]
```

**Validation Rules:**
- `decision_type` is required and must be one of the `DecisionType` values
- Additional fields are allowed for extensibility

### Actions

The `actions` field is a list of action records:

```python
{
    "action_type": str,             # Required - action type identifier
    "status": ActionStatus,         # Optional - execution status
    # Additional fields as needed
}
```

**Enums:**
```python
ActionStatus = Literal["OK", "FAILED"]
```

**Validation Rules:**
- `action_type` is required and must be non-empty
- `status` is optional, but if present must be `"OK"` or `"FAILED"`
- Additional fields are allowed for extensibility

### Inputs

The `inputs` field captures the complete state used for decision making:

```python
{
    "task_status": str,             # Current task status
    "context": dict,                # Task context
    "previous_decisions": list,     # Previous decision history
    # Additional fields as needed
}
```

**Validation Rules:**
- Must be a dictionary
- No specific required fields (policy-dependent)
- All data must be JSON-serializable

### Metrics

The `metrics` field records performance data:

```python
{
    "decision_time_ms": float,      # Decision processing time
    "policy_eval_time_ms": float,   # Policy evaluation time
    # Additional metrics as needed
}
```

**Validation Rules:**
- Must be a dictionary
- No specific required fields
- All data must be JSON-serializable

## Complete Example

```json
{
  "decision_id": "dec-2024-01-28-001",
  "policy": "default_v1",
  "event": {
    "event_id": "evt-123",
    "event_type": "TASK_CREATED",
    "source": "eventbus",
    "ts": "2024-01-28T10:30:00.123456Z"
  },
  "inputs": {
    "task_status": "PENDING",
    "task_id": "task-456",
    "context": {
      "user": "alice",
      "tool_requests": ["file_delete"]
    },
    "previous_decisions": []
  },
  "findings": [
    {
      "kind": "REDLINE",
      "severity": "HIGH",
      "code": "REDLINE_001",
      "message": "Dangerous file operation detected",
      "evidence": {
        "tool": "file_delete",
        "path": "/etc/passwd",
        "line_number": 42
      }
    }
  ],
  "decision": {
    "decision_type": "BLOCK",
    "reason": "Redline violation: attempting to delete system file",
    "confidence": 1.0
  },
  "actions": [
    {
      "action_type": "BLOCK_TASK",
      "status": "OK",
      "timestamp": "2024-01-28T10:30:00.234567Z"
    },
    {
      "action_type": "NOTIFY_USER",
      "status": "OK",
      "channel": "email",
      "timestamp": "2024-01-28T10:30:00.345678Z"
    }
  ],
  "metrics": {
    "decision_time_ms": 123.45,
    "policy_eval_time_ms": 98.76,
    "finding_count": 1,
    "action_count": 2
  }
}
```

## Versioning Rules

### Semantic Versioning

Schema version follows semver: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (fields removed, types changed)
- **MINOR**: Backward-compatible additions (new optional fields)
- **PATCH**: Documentation or validation rule clarifications

### Backward Compatibility

**MUST maintain:**
- All existing required fields
- All existing enum values
- Validation rules (cannot become stricter)
- Field types and semantics

**MAY add:**
- New optional fields
- New enum values
- Additional validation (if more lenient)

**MUST NOT:**
- Remove required fields
- Remove enum values
- Change field types
- Make validation stricter

### Migration Strategy

When making breaking changes (MAJOR version bump):

1. Add new schema version as separate dataclass
2. Support both versions in read path for 1+ major releases
3. Write new version only
4. Document migration path
5. Provide conversion utilities

Example:
```python
# v1 (legacy)
@dataclass(frozen=True)
class DecisionSnapshotV1:
    # ... old schema

# v2 (current)
@dataclass(frozen=True)
class DecisionSnapshotV2:
    # ... new schema

# Type alias for current version
DecisionSnapshot = DecisionSnapshotV2

# Converter
def migrate_v1_to_v2(v1: DecisionSnapshotV1) -> DecisionSnapshotV2:
    # ... migration logic
```

## Validation

Use `validate_decision_snapshot()` to ensure compliance:

```python
from agentos.core.supervisor.audit_schema import validate_decision_snapshot

# Validate a snapshot dict
try:
    validate_decision_snapshot(snapshot_dict)
    print("✓ Valid snapshot")
except ValueError as e:
    print(f"✗ Invalid snapshot: {e}")
```

**Validation covers:**
- All required fields present
- Field types correct
- Enum values valid
- Nested structures complete

## Storage Contract

DecisionSnapshots are stored in `task_audits.payload`:

```sql
CREATE TABLE task_audits (
    audit_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    decision_id TEXT,
    event_type TEXT NOT NULL,
    payload TEXT,  -- JSON string containing {"decision_snapshot": {...}}
    created_at TEXT NOT NULL,
    -- ... other fields
);
```

**Storage format:**
```json
{
  "decision_snapshot": {
    "decision_id": "...",
    "policy": "...",
    // ... complete snapshot
  },
  // Optional: additional metadata
}
```

## Testing

All schema changes MUST include:

1. Unit tests for validation
2. Integration tests for serialization/deserialization
3. Migration tests (for breaking changes)
4. Example snapshots in documentation

Example test:
```python
def test_decision_snapshot_validation():
    """Test that valid snapshot passes validation"""
    snapshot = {
        "decision_id": "dec-001",
        "policy": "default",
        "event": {
            "event_id": "evt-001",
            "event_type": "TASK_CREATED",
            "source": "eventbus",
            "ts": "2024-01-28T10:30:00Z"
        },
        "inputs": {},
        "findings": [],
        "decision": {"decision_type": "ALLOW"},
        "actions": [],
        "metrics": {}
    }

    validate_decision_snapshot(snapshot)  # Should not raise
```

## Change Log

### Version 1.0 (2024-01-28)
- Initial schema definition
- Core fields: decision_id, policy, event, inputs, findings, decision, actions, metrics
- Support for ALLOW, PAUSE, BLOCK, RETRY decisions
- Four finding kinds: REDLINE, CONFLICT, RISK, RUNTIME
- Four severity levels: LOW, MEDIUM, HIGH, CRITICAL

## References

- Implementation: `agentos/core/supervisor/audit_schema.py`
- Validation: `validate_decision_snapshot()`, `validate_event_ref()`, `validate_finding_snapshot()`
- API: See `decision_replay_api.md`
- Usage: See `decision_replay_runbook.md`
