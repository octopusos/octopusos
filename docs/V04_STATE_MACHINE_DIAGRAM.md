# v0.4 Task State Machine Diagram

**Version**: v0.4.0
**Date**: 2026-01-29

---

## Complete State Machine

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           v0.4 Task State Machine                               │
│                                                                                  │
│  Legend:                                                                         │
│  ─────►  Normal transition                                                      │
│  ═════►  Guarded transition (requires validation)                               │
│  - - →   Retry/recovery transition                                              │
│  [GATE]  Validation checkpoint                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘


        ┌──────────┐
        │  START   │  (New task created)
        └────┬─────┘
             │
             ▼
        ┌──────────┐
        │  DRAFT   │  Chat drafting TaskSpec
        │          │  • No project_id required yet
        │          │  • spec_version = 0
        │          │  • Mutable spec
        └─┬──────┬─┘
          │      │
          │      └──────────────────────────────────────────────┐
          │ approve()                                           │ cancel()
          │                                                     │
          ▼                                                     ▼
     ┌──────────┐                                         ┌───────────┐
     │ PLANNED  │  [GATE 1: Spec Complete]                │ CANCELLED │
     │          │  • project_id MUST be set               │           │
     │          │  • Spec frozen (spec_version = 1)       │ Terminal  │
     │          │  • Immutable after this point           └───────────┘
     └─┬──────┬─┘
       │      │
       │      └──────────────────────────────────────────────────┐
       │ validate() + bind(project_id)                           │ cancel()
       │                                                          │
       ▼                                                          ▼
  ┌──────────┐                                               ┌───────────┐
  │  READY   │  [GATE 2: Execution Preconditions]           │ CANCELLED │
  │          │  ✅ project_id is NOT NULL                    │           │
  │          │  ✅ spec_version >= 1                         │ Terminal  │
  │          │  ✅ spec_snapshot stored                      └───────────┘
  │          │  • Ready for runner to pick up
  └─┬──────┬─┘
    │      │
    │      └──────────────────────────────────────────────────────┐
    │ runner.execute()                                            │ cancel()
    │                                                             │
    ▼                                                             ▼
┌──────────┐                                                 ┌───────────┐
│ RUNNING  │  Actual execution in progress                   │ CANCELLED │
│          │  • Executor has control                         │           │
│          │  • Progress updates stream                      │ Terminal  │
│          │  • Can take minutes/hours                       └───────────┘
└─┬──┬──┬─┘
  │  │  │
  │  │  └────────────────────────────────────┐
  │  │ gates.verify()                        │ error / cancel()
  │  │                                        │
  │  │                                        ▼
  │  │                                   ┌──────────┐
  │  │                                   │  FAILED  │  Execution error
  │  │                                   │          │  • exit_reason set
  │  │                                   │ Terminal │  • Retryable
  │  │                                   └────┬─────┘
  │  │                                        │
  │  │                                        │ retry()
  │  │                                        └─ - - - - - ┐
  │  │                                                     │
  │  └───────────────────────┐                            │
  │ blocked (approval needed) │                            │
  │                           │                            │
  │                           ▼                            │
  │                      ┌──────────┐                      │
  │                      │ BLOCKED  │                      │
  │                      │          │                      │
  │                      │ Terminal │                      │
  │                      └────┬─────┘                      │
  │                           │                            │
  │                           │ unblock()                  │
  │                           └─ - - - - - - - - - - - - -┘
  │
  ▼
┌──────────────┐  [GATE 3: Execution Complete]
│  VERIFYING   │  Post-execution verification
│              │  • Run tests
│              │  • Run linters
│              │  • Security scans
│              │  • Check uncommitted changes
└─┬───────┬──┬─┘
  │       │  │
  │       │  └─────────────────────────────────────┐
  │       │ gate failed                            │ cancel()
  │       │                                         │
  │       ▼                                         ▼
  │  ┌──────────┐                              ┌───────────┐
  │  │  FAILED  │  Verification failed         │ CANCELLED │
  │  │          │  • Which gate failed?        │           │
  │  │ Terminal │  • Retry after fix           │ Terminal  │
  │  └────┬─────┘                              └───────────┘
  │       │
  │       │ retry()
  │       └─ - - - - - - - - - - - - - - - - - - - - - - - - - ┐
  │                                                              │
  │ all gates passed                                            │
  │                                                              │
  ▼                                                              │
┌──────────┐  [GATE 4: Verification Passed]                     │
│ VERIFIED │  All gates passed                                  │
│          │  • Tests: ✅                                        │
│          │  • Linters: ✅                                      │
│          │  • Security: ✅                                     │
└─┬────────┘                                                     │
  │                                                              │
  │ finalize()                                                   │
  │                                                              │
  ▼                                                              │
┌──────────┐  [GATE 5: Artifacts Recorded]                      │
│   DONE   │  Task completed successfully                       │
│          │  • All commits recorded                            │
│          │  • Artifacts linked                                │
│ Terminal │  • Cannot be changed                               │
└──────────┘                                                     │
                                                                 │
                            ┌────────────────────────────────────┘
                            │
                            ▼
                       [BACK TO READY]
                       (Retry after fix)

```

---

## State Details

### Initial States

#### DRAFT
- **Entry**: Task created via API or Chat
- **Characteristics**:
  - project_id: Optional (but recommended)
  - spec_version: 0 (mutable)
  - User can edit spec freely
- **Exit Actions**:
  - Freeze spec (spec_version becomes 1)
  - Bind to project (project_id set)
- **Valid Transitions**: PLANNED, CANCELLED

---

### Approval Phase

#### PLANNED
- **Entry**: User approves spec (freeze action)
- **Characteristics**:
  - project_id: MUST be set
  - spec_version: ≥1 (frozen)
  - Spec snapshot stored in DB
  - Spec is now IMMUTABLE
- **Validation Gate 1**:
  ```python
  assert task.project_id is not None
  assert task.spec_version >= 1
  assert task.spec_snapshot is not None
  ```
- **Exit Actions**: Validate execution preconditions
- **Valid Transitions**: READY, CANCELLED

---

### Execution Phase

#### READY
- **Entry**: Validation gate passed
- **Characteristics**:
  - All execution preconditions met
  - Waiting for runner to pick up
  - Can be queued in task queue
- **Validation Gate 2** (ENFORCED):
  ```python
  # Hard constraints (database trigger + service layer)
  assert task.project_id is not None, "PROJECT_ID_REQUIRED"
  assert task.spec_version >= 1, "SPEC_NOT_FROZEN"
  ```
- **Exit Actions**: Runner claims task
- **Valid Transitions**: RUNNING, CANCELLED

#### RUNNING
- **Entry**: Runner starts execution
- **Characteristics**:
  - Active execution in progress
  - Progress updates stream to WebUI
  - Can take minutes to hours
  - exit_reason updates in real-time
- **Exit Conditions**:
  - Success: Execution completed → VERIFYING
  - Error: Exception thrown → FAILED
  - Blocked: Needs approval → BLOCKED
  - User: Cancellation requested → CANCELLED
- **Valid Transitions**: VERIFYING, FAILED, BLOCKED, CANCELLED

---

### Verification Phase

#### VERIFYING
- **Entry**: Execution completed
- **Characteristics**:
  - Run post-execution gates:
    - Unit tests
    - Integration tests
    - Linters (ESLint, Pylint, etc.)
    - Security scans
    - Uncommitted changes check
  - Each gate can pass/fail independently
- **Validation Gate 3**:
  ```python
  gates = run_all_gates(task)
  if all(gate.passed for gate in gates):
      transition_to(VERIFIED)
  else:
      transition_to(FAILED)
  ```
- **Exit Actions**:
  - Record gate results in audit log
  - Store failure reasons
- **Valid Transitions**: VERIFIED, FAILED, CANCELLED, READY (retry)

#### VERIFIED
- **Entry**: All verification gates passed
- **Characteristics**:
  - Task execution successful
  - All quality checks passed
  - Ready for finalization
- **Exit Actions**: Record artifacts
- **Valid Transitions**: DONE

---

### Terminal States

#### DONE
- **Entry**: Task finalized
- **Characteristics**:
  - Execution: ✅ Success
  - Verification: ✅ All gates passed
  - Artifacts: ✅ All recorded
  - **CANNOT be changed** (terminal)
- **Validation Gate 5**:
  ```python
  assert all_artifacts_recorded(task)
  assert task.spec_version >= 1  # Sanity check
  ```
- **Valid Transitions**: None (terminal)

#### FAILED
- **Entry**: Execution or verification failed
- **Characteristics**:
  - exit_reason: fatal_error / gate_failed / etc.
  - Error details in audit log
  - **Can be retried** (transition to READY)
- **Exit Actions**: Prepare retry context
- **Valid Transitions**: READY (retry)

#### CANCELLED
- **Entry**: User or system cancelled task
- **Characteristics**:
  - Can happen at any non-terminal state
  - exit_reason: user_cancelled / system_cancelled
  - **CANNOT be resumed** (terminal)
- **Valid Transitions**: None (terminal)

#### BLOCKED
- **Entry**: Task needs approval (AUTONOMOUS mode)
- **Characteristics**:
  - Waiting for human decision
  - Common in AUTONOMOUS run_mode
  - exit_reason: approval_needed
  - **Can be unblocked** (transition to READY)
- **Exit Actions**: Record approval decision
- **Valid Transitions**: READY (approved), CANCELLED (rejected)

---

## Transition Rules

### Normal Flow (Happy Path)
```
DRAFT → PLANNED → READY → RUNNING → VERIFYING → VERIFIED → DONE
```

**Duration**: ~1-60 minutes (depends on task complexity)

---

### Error Flow (Failure)
```
RUNNING → FAILED
```

**Recovery**: Manual retry
```
FAILED → READY → RUNNING (retry)
```

---

### Blocking Flow (Approval Needed)
```
RUNNING → BLOCKED
```

**Recovery**: Human approval
```
BLOCKED → READY → RUNNING (approved)
```

---

### Cancellation Flow (User Abort)
```
ANY_STATE → CANCELLED
```

**Note**: Cannot be resumed (terminal)

---

## State Transition Matrix

| From \ To | DRAFT | PLANNED | READY | RUNNING | VERIFYING | VERIFIED | DONE | FAILED | CANCELLED | BLOCKED |
|-----------|-------|---------|-------|---------|-----------|----------|------|--------|-----------|---------|
| **DRAFT** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **PLANNED** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **READY** | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **RUNNING** | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **VERIFYING** | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| **VERIFIED** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **DONE** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **FAILED** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **CANCELLED** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **BLOCKED** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

Legend:
- ✅ = Allowed
- ❌ = Blocked

---

## Validation Gates (Detailed)

### Gate 1: Spec Complete (DRAFT → PLANNED)
```python
def validate_gate_1(task: Task) -> bool:
    """Check if task spec is complete enough to freeze"""
    if not task.title or len(task.title.strip()) == 0:
        raise ValueError("Task title cannot be empty")

    if not task.project_id:
        raise ValueError("Task must be bound to a project")

    return True
```

### Gate 2: Execution Preconditions (PLANNED → READY)
```python
def validate_gate_2(task: Task) -> bool:
    """Check if task is ready for execution (HARD CONSTRAINT)"""
    if task.project_id is None:
        raise ProjectNotBoundError(
            f"Task {task.task_id} has no project_id. "
            "Cannot enter READY state without project binding."
        )

    if task.spec_version < 1:
        raise SpecNotFrozenError(
            f"Task {task.task_id} spec not frozen (spec_version={task.spec_version}). "
            "Call freeze_spec() before transitioning to READY."
        )

    if not task.spec_snapshot:
        raise ValueError("Spec snapshot must be stored before READY")

    return True
```

### Gate 3: Execution Complete (RUNNING → VERIFYING)
```python
def validate_gate_3(task: Task) -> bool:
    """Check if execution completed (success or error)"""
    if task.exit_reason is None:
        raise ExecutionIncompleteError(
            f"Task {task.task_id} has no exit_reason. "
            "Execution may still be in progress."
        )

    return True
```

### Gate 4: Verification Passed (VERIFYING → VERIFIED)
```python
def validate_gate_4(task: Task) -> bool:
    """Run all verification gates"""
    gates = [
        run_tests(task),
        run_linters(task),
        run_security_scans(task),
        check_uncommitted_changes(task),
    ]

    failed_gates = [g for g in gates if not g.passed]

    if failed_gates:
        raise GateFailedError(
            f"Verification failed for task {task.task_id}. "
            f"Failed gates: {[g.name for g in failed_gates]}"
        )

    return True
```

### Gate 5: Artifacts Recorded (VERIFIED → DONE)
```python
def validate_gate_5(task: Task) -> bool:
    """Check if all artifacts are recorded"""
    artifacts = get_task_artifacts(task.task_id)

    if not artifacts:
        logger.warning(f"Task {task.task_id} has no artifacts recorded")
        # This is a warning, not a hard error

    return True
```

---

## Examples

### Example 1: Happy Path
```
1. User creates task in WebUI → DRAFT
2. Chat helps draft spec
3. User clicks "Freeze Spec" → PLANNED
4. User clicks "Approve" → READY
5. Runner picks up task → RUNNING
6. Execution completes → VERIFYING
7. All gates pass → VERIFIED
8. Artifacts recorded → DONE
```

### Example 2: Execution Failure + Retry
```
1. Task reaches RUNNING
2. Execution fails (e.g., test failed) → FAILED
3. User fixes code
4. User clicks "Retry" → READY
5. Runner picks up task → RUNNING
6. Execution succeeds → VERIFYING → VERIFIED → DONE
```

### Example 3: Verification Failure + Fix
```
1. Task reaches VERIFYING
2. Linter fails → FAILED
3. User fixes linter errors
4. User clicks "Retry" → READY
5. Execution → VERIFYING (linter passes) → VERIFIED → DONE
```

### Example 4: Autonomous Mode Blocked
```
1. Task reaches RUNNING (AUTONOMOUS mode)
2. Agent needs approval for risky operation → BLOCKED
3. User reviews and approves → READY
4. Runner resumes → RUNNING → VERIFYING → VERIFIED → DONE
```

### Example 5: User Cancellation
```
1. Task reaches RUNNING
2. User realizes mistake, clicks "Cancel" → CANCELLED
3. Task cannot be resumed (terminal state)
```

---

## References

- [ADR-V04: Project-Aware Task OS](./ADR_V04_PROJECT_AWARE_TASK_OS.md)
- [State Machine Implementation](../../agentos/core/task/state_machine.py)
- [Task States Enum](../../agentos/core/task/states.py)
- [Validation Gates](./V04_CONSTRAINTS_AND_GATES.md)

---

**Maintained by**: AgentOS Architecture Team
**Status**: 🔒 Semantic Freeze (v0.4)
**Last Updated**: 2026-01-29
