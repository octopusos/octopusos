# v0.4 Quick Reference Card

**Version**: v0.4.0 - Project-Aware Task OS
**Status**: Semantic Freeze
**Date**: 2026-01-29

---

## TL;DR (30 Second Summary)

v0.4 makes 3 critical changes:

1. **Tasks MUST bind to Projects** (not repos)
2. **Specs MUST be frozen** before execution (immutable)
3. **Chat CANNOT execute** (only propose specs)

**Migration**: Add `project_id` to all task creation calls.

---

## 5 Core Principles

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Project ≠ Repository                                      │
│    • A Project can have multiple repos                       │
│    • Tasks bind to Projects, not repos                       │
├──────────────────────────────────────────────────────────────┤
│ 2. Task MUST Bind to Project (HARD)                          │
│    • assert task.project_id is not None                      │
│    • Enforced at database + service + API layers             │
├──────────────────────────────────────────────────────────────┤
│ 3. Chat ↔ Task ↔ Execution Boundary                          │
│    • Chat proposes specs (cannot execute)                    │
│    • Task stores frozen specs                                │
│    • Execution runs through state machine                    │
├──────────────────────────────────────────────────────────────┤
│ 4. Task State Machine (10 states)                            │
│    • DRAFT → PLANNED → READY → RUNNING → VERIFYING →        │
│      VERIFIED → DONE                                         │
│    • Terminal: DONE, FAILED, CANCELLED, BLOCKED              │
├──────────────────────────────────────────────────────────────┤
│ 5. Spec Freezing (Reproducibility)                           │
│    • spec_version = 0: Mutable (DRAFT)                       │
│    • spec_version ≥ 1: Immutable (PLANNED+)                  │
│    • spec_snapshot stores full context                       │
└──────────────────────────────────────────────────────────────┘
```

---

## State Machine (1-Line)

```
DRAFT → PLANNED → READY → RUNNING → VERIFYING → VERIFIED → DONE
  ↓                 ↓         ↓          ↓
CANCELLED       (validation) FAILED/BLOCKED
```

---

## Hard Constraints (DO NOT VIOLATE)

### Constraint 1: Project Binding
```python
# Before READY:
assert task.project_id is not None
```

### Constraint 2: Spec Freezing
```python
# Before READY:
assert task.spec_version >= 1
```

### Constraint 3: Valid Transitions
```python
# Only allowed transitions:
(DRAFT, PLANNED)       ✅
(PLANNED, READY)       ✅
(READY, RUNNING)       ✅
(RUNNING, VERIFYING)   ✅
(VERIFYING, VERIFIED)  ✅
(VERIFIED, DONE)       ✅

# Blocked transitions:
(DRAFT, RUNNING)       ❌
(DRAFT, DONE)          ❌
(VERIFIED, RUNNING)    ❌
```

### Constraint 4: Terminal States
```python
# Cannot exit (except retry):
DONE       → any (❌)
CANCELLED  → any (❌)
FAILED     → READY (✅ retry only)
BLOCKED    → READY (✅ unblock only)
```

### Constraint 5: Chat Boundary
```python
# Chat CANNOT:
chat_session.execute_task(task_id)  # ❌

# Chat CAN:
chat_session.propose_task(spec)     # ✅
```

---

## API Changes (v0.3 → v0.4)

### Before (v0.3)
```bash
# Task creation
POST /api/tasks
{
  "title": "Update README"
}

# Response
{
  "task_id": "task_01",
  "status": "created"
}
```

### After (v0.4)
```bash
# Task creation (project_id REQUIRED)
POST /api/tasks
{
  "title": "Update README",
  "project_id": "proj_01"  # ✅ REQUIRED
}

# Response
{
  "task_id": "task_01",
  "status": "draft",       # NEW: enum value
  "project_id": "proj_01",
  "spec_version": 0
}

# Freeze spec
POST /api/tasks/task_01/freeze
{
  "spec": {
    "goal": "Update README with new features",
    "repos": ["repo_01"]
  }
}

# Response
{
  "task_id": "task_01",
  "status": "planned",
  "spec_version": 1,       # Frozen
  "frozen_at": "2026-01-29T12:34:56Z"
}
```

---

## Migration Checklist

### Step 1: Update Task Creation
```python
# OLD
task = task_service.create_task(title="Test")

# NEW
task = task_service.create_task(
    title="Test",
    project_id="proj_01"  # ✅ Add this
)
```

### Step 2: Update State Handling
```python
# OLD
if task.status == "created":
    ...
elif task.status == "executing":
    ...

# NEW
if task.status == TaskState.DRAFT:
    ...
elif task.status == TaskState.RUNNING:
    ...
```

### Step 3: Run Database Migration
```bash
# Backup first
cp agentos.db agentos_v03_backup.db

# Migrate
uv run agentos migrate --to v30

# Verify
uv run agentos task list  # All tasks should have project_id
```

---

## Validation Gates (Summary)

```
Gate 1: DRAFT → PLANNED
├─ task.title not empty
└─ task.project_id not None

Gate 2: PLANNED → READY (HARD)
├─ task.project_id not None
├─ task.spec_version >= 1
└─ task.spec_snapshot not None

Gate 3: RUNNING → VERIFYING
└─ task.exit_reason not None

Gate 4: VERIFYING → VERIFIED
├─ Tests passed
├─ Linters passed
├─ Security scans passed
└─ No uncommitted changes

Gate 5: VERIFIED → DONE
└─ All artifacts recorded
```

---

## Common Errors and Fixes

### Error 1: ProjectNotBoundError
```
Error: Task must have project_id
Fix: Add project_id to task creation request
```

### Error 2: SpecNotFrozenError
```
Error: Task spec must be frozen (spec_version >= 1)
Fix: Call POST /api/tasks/{id}/freeze before execution
```

### Error 3: InvalidTransitionError
```
Error: Cannot transition from DRAFT to RUNNING
Fix: Must go through PLANNED → READY first
```

### Error 4: 400 Bad Request (API)
```
Error: {"code": "PROJECT_ID_REQUIRED", "message": "..."}
Fix: Include "project_id" in request body
```

---

## Key Differences (v0.3 vs v0.4)

| Aspect | v0.3 | v0.4 |
|--------|------|------|
| **Project Binding** | Optional | REQUIRED (hard constraint) |
| **Spec Mutability** | Always mutable | Frozen after PLANNED |
| **States** | 5 states (free-form) | 10 states (enum) |
| **Chat Execution** | Can execute | Cannot execute (proposal-only) |
| **Reproducibility** | No | Yes (spec_snapshot) |
| **Multi-Repo** | No | Yes (via Projects) |
| **State Machine** | Implicit | Explicit (transition table) |

---

## File Locations

### Documentation
- **ADR**: `docs/architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md`
- **Constraints**: `docs/V04_CONSTRAINTS_AND_GATES.md`
- **State Machine**: `docs/V04_STATE_MACHINE_DIAGRAM.md`
- **Quick Reference**: `docs/V04_QUICK_REFERENCE.md` (this file)
- **Deliverables**: `docs/V04_PHASE0_DELIVERABLES.md`

### Code
- **State Machine**: `agentos/core/task/state_machine.py`
- **States Enum**: `agentos/core/task/states.py`
- **Task Models**: `agentos/core/task/models.py`
- **Project Schema**: `agentos/schemas/project.py`

---

## Success Criteria (Short Form)

### Must Have ✅
- [ ] All tasks have project_id
- [ ] Tasks cannot enter READY without frozen spec
- [ ] Chat cannot execute tasks
- [ ] State machine enforced
- [ ] Database triggers active

### Should Have
- [ ] Migration script tested
- [ ] API documentation updated
- [ ] WebUI updated
- [ ] CLI commands working

---

## Testing Quick Commands

```bash
# Test project_id requirement
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Test"}'
# Expected: 400 Bad Request (PROJECT_ID_REQUIRED)

# Test correct creation
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "project_id": "proj_01"}'
# Expected: 200 OK (status: "draft")

# Test spec freezing
curl -X POST http://localhost:8000/api/tasks/task_01/freeze \
  -H "Content-Type: application/json" \
  -d '{"spec": {"goal": "Test goal"}}'
# Expected: 200 OK (status: "planned", spec_version: 1)

# Test invalid transition
curl -X PUT http://localhost:8000/api/tasks/task_01/transition \
  -H "Content-Type: application/json" \
  -d '{"to": "running"}'
# Expected: 403 Forbidden (InvalidTransitionError)
```

---

## When to Use Which State

### Use DRAFT when:
- User is still drafting the task
- Spec is not finalized
- Project binding not set yet

### Use PLANNED when:
- Spec is finalized and frozen
- Ready for review/approval
- Waiting for execution approval

### Use READY when:
- All validation passed
- Waiting for runner to pick up
- Can be queued

### Use RUNNING when:
- Active execution in progress
- Cannot modify task
- Progress updates streaming

### Use VERIFYING when:
- Execution completed
- Running post-execution gates
- Tests, linters, security scans

### Use VERIFIED when:
- All gates passed
- Ready for finalization
- Artifacts can be recorded

### Use DONE when:
- Task successfully completed
- All artifacts recorded
- Terminal state (no changes)

### Use FAILED when:
- Execution or verification failed
- Can be retried
- Error details in audit log

### Use CANCELLED when:
- User or system cancelled
- Cannot be resumed
- Terminal state

### Use BLOCKED when:
- Needs human approval
- Common in AUTONOMOUS mode
- Can be unblocked to READY

---

## One-Line Commands

```bash
# Create project
agentos project create --name "my-project" --path /path/to/repo

# Create task
agentos task create --project proj_01 --title "Update README"

# Freeze spec
agentos task freeze task_01

# Transition to READY
agentos task transition task_01 --to ready

# Execute task
agentos task run task_01

# View state history
agentos task history task_01

# Replay task
agentos task replay task_01
```

---

## Troubleshooting

### Q: My task creation fails with 400 error
**A**: Add `project_id` to your request. All tasks MUST bind to a project in v0.4.

### Q: Cannot transition to RUNNING from DRAFT
**A**: Must go through PLANNED → READY first. Freeze spec, then transition.

### Q: How to update a frozen spec?
**A**: You can't. Create a new task instead. Frozen specs are immutable.

### Q: What happened to `status = "created"`?
**A**: Replaced with `status = "draft"`. Update your code to use TaskState enum.

### Q: Can I skip PLANNED and go straight to READY?
**A**: No. Must freeze spec in PLANNED before entering READY.

### Q: How do I retry a FAILED task?
**A**: Call transition API: `PUT /api/tasks/{id}/transition {"to": "ready"}`

---

## Version History

- **v0.3**: Repository-centric, implicit execution, free-form states
- **v0.4**: Project-centric, explicit state machine, frozen specs

---

**Last Updated**: 2026-01-29
**Maintained by**: AgentOS Architecture Team
**Status**: 🔒 Semantic Freeze
