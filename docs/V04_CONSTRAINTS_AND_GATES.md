# v0.4 Constraints and Validation Gates

**Version**: v0.4.0
**Status**: Semantic Freeze
**Date**: 2026-01-29

---

## Overview

This document defines the **hard constraints** and **validation gates** that enforce the v0.4 Project-Aware Task OS architecture. These constraints are **non-negotiable** and must be enforced at all layers (database, API, services, UI).

---

## Hard Constraints (MUST NOT VIOLATE)

### Constraint 1: Task-Project Binding (Iron Law)

**Rule**:
```python
# Before entering READY state:
assert task.project_id is not None, "Task must have project_id"
```

**Enforcement**:
- Database trigger (SQLite/PostgreSQL)
- API validation (POST /api/tasks)
- Service layer guard (task_service.transition)
- State machine validation (state_machine.py)

**Test**:
```python
def test_ready_without_project_fails():
    task = create_task(title="Test", project_id=None)
    with pytest.raises(ProjectNotBoundError):
        task_service.transition(task.id, to=TaskState.READY)
```

---

### Constraint 2: Spec Freezing (Immutability)

**Rule**:
```python
# Before entering READY state:
assert task.spec_version >= 1, "Spec must be frozen"

# After freezing:
assert spec_is_immutable(task), "Frozen spec cannot change"
```

**Enforcement**:
- spec_version counter (tasks.spec_version)
- Spec snapshot storage (tasks.spec_snapshot JSON)
- API endpoint guard (POST /api/tasks/{id}/freeze)
- Service layer validation (task_service.freeze_spec)

**Test**:
```python
def test_ready_without_frozen_spec_fails():
    task = create_task(title="Test", project_id="proj_01", spec_version=0)
    with pytest.raises(SpecNotFrozenError):
        task_service.transition(task.id, to=TaskState.READY)

def test_frozen_spec_cannot_change():
    task = freeze_spec(task_id="task_01")  # spec_version = 1
    with pytest.raises(SpecFrozenError):
        task_service.update_spec(task.id, new_spec={"goal": "changed"})
```

---

### Constraint 3: State Machine Transitions (Directed Graph)

**Rule**:
```python
# Only allowed transitions from transition table
assert (from_state, to_state) in TRANSITION_TABLE, "Invalid transition"
```

**Allowed Transitions** (excerpt):
```
DRAFT → PLANNED     ✅
DRAFT → CANCELLED   ✅
PLANNED → READY     ✅ (if project_id + spec_version)
READY → RUNNING     ✅
RUNNING → VERIFYING ✅
VERIFYING → VERIFIED ✅
VERIFIED → DONE     ✅

# BLOCKED transitions:
DRAFT → RUNNING     ❌
DRAFT → DONE        ❌
PLANNED → DONE      ❌ (must go through RUNNING)
VERIFIED → RUNNING  ❌ (cannot re-execute verified task)
```

**Enforcement**:
- State machine transition table (state_machine.TRANSITION_TABLE)
- Service layer (task_service.transition validates)
- Audit trail (all transitions logged)

**Test**:
```python
def test_invalid_transition_fails():
    task = create_task(status=TaskState.DRAFT)
    with pytest.raises(InvalidTransitionError):
        task_service.transition(task.id, to=TaskState.RUNNING)  # Skip PLANNED/READY
```

---

### Constraint 4: Terminal State Immutability

**Rule**:
```python
# Terminal states cannot be exited:
TERMINAL_STATES = {DONE, FAILED, CANCELLED, BLOCKED}
assert task.status not in TERMINAL_STATES, "Cannot transition from terminal state"
```

**Exception**: FAILED and BLOCKED can transition to QUEUED (retry).

**Enforcement**:
- State machine validation
- API guard (returns 409 Conflict)

**Test**:
```python
def test_done_task_cannot_change():
    task = create_task(status=TaskState.DONE)
    with pytest.raises(InvalidTransitionError):
        task_service.transition(task.id, to=TaskState.RUNNING)

def test_failed_task_can_retry():
    task = create_task(status=TaskState.FAILED)
    # This is allowed (explicit retry)
    task_service.transition(task.id, to=TaskState.READY, reason="retry")
```

---

### Constraint 5: Chat-Execution Boundary

**Rule**:
```python
# Chat CANNOT directly execute tasks
assert chat_session.can_execute_task() == False, "Chat is proposal-only"

# Only TaskService can execute
assert actor == "task_service", "Only service layer can execute"
```

**Enforcement**:
- Chat API does not expose task.run() method
- WebSocket handlers can only call task_service.create_task()
- Execution requires explicit approval (transition to READY)

**Test**:
```python
def test_chat_cannot_execute_task():
    chat_session = create_chat_session()
    task = chat_session.propose_task(title="Test")

    # Task is in DRAFT, not RUNNING
    assert task.status == TaskState.DRAFT

    # Chat cannot transition to RUNNING
    with pytest.raises(PermissionError):
        chat_session.execute_task(task.id)
```

---

## Validation Gates (Checkpoints)

### Gate 1: DRAFT → PLANNED

**Condition**:
```python
def can_plan(task: Task) -> bool:
    return (
        task.title is not None and len(task.title) > 0 and
        task.project_id is not None
    )
```

**What it checks**:
- Task has non-empty title
- Task has project binding

**Error if fails**: `IncompleteTaskError("Task must have title and project_id")`

---

### Gate 2: PLANNED → READY

**Condition**:
```python
def can_ready(task: Task) -> bool:
    return (
        task.project_id is not None and
        task.spec_version >= 1 and
        task.spec_snapshot is not None
    )
```

**What it checks**:
- Task has project binding (validated)
- Spec is frozen (spec_version ≥ 1)
- Spec snapshot is stored

**Error if fails**: `SpecNotFrozenError` or `ProjectNotBoundError`

---

### Gate 3: RUNNING → VERIFYING

**Condition**:
```python
def can_verify(task: Task) -> bool:
    return (
        task.exit_reason is not None or
        execution_completed(task)
    )
```

**What it checks**:
- Task execution completed (either success or error)
- exit_reason is set (done, max_iterations, blocked, etc.)

**Error if fails**: `ExecutionIncompleteError`

---

### Gate 4: VERIFYING → VERIFIED

**Condition**:
```python
def can_certify(task: Task) -> bool:
    gates = run_verification_gates(task)
    return all(gate.passed for gate in gates)
```

**What it checks**:
- All verification gates passed:
  - Tests passed (if required)
  - Linters passed (if required)
  - Security scans clean
  - No uncommitted changes (if required)

**Error if fails**: `GateFailedError("Verification gate XYZ failed")`

---

### Gate 5: VERIFIED → DONE

**Condition**:
```python
def can_finalize(task: Task) -> bool:
    return (
        task.spec_version >= 1 and
        all_artifacts_recorded(task)
    )
```

**What it checks**:
- Spec was frozen (sanity check)
- All artifacts (commits, PRs, patches) recorded in task_artifact_ref

**Error if fails**: `ArtifactMissingError`

---

## Enforcement Layers

### Layer 1: Database (SQLite Triggers)

```sql
-- Enforce project_id for READY+ states
CREATE TRIGGER enforce_project_binding
BEFORE UPDATE OF status ON tasks
FOR EACH ROW
WHEN NEW.status IN ('ready', 'running', 'verifying', 'verified', 'done')
  AND NEW.project_id IS NULL
BEGIN
  SELECT RAISE(ABORT, 'Tasks in READY+ states must have project_id');
END;

-- Prevent spec changes after freezing
CREATE TRIGGER prevent_spec_changes
BEFORE UPDATE OF spec_snapshot ON tasks
FOR EACH ROW
WHEN OLD.spec_version >= 1 AND NEW.spec_snapshot != OLD.spec_snapshot
BEGIN
  SELECT RAISE(ABORT, 'Cannot modify frozen spec (spec_version >= 1)');
END;
```

### Layer 2: Service Layer (Python)

```python
# task_service.py
class TaskService:
    def transition(self, task_id: str, to: TaskState, actor: str, reason: str):
        task = self.get_task(task_id)

        # Gate: READY requires project_id + frozen spec
        if to == TaskState.READY:
            if task.project_id is None:
                raise ProjectNotBoundError(f"Task {task_id} has no project_id")
            if task.spec_version < 1:
                raise SpecNotFrozenError(f"Task {task_id} spec not frozen")

        # Execute transition
        return self.state_machine.transition(task_id, to=to.value, actor=actor, reason=reason)
```

### Layer 3: API Layer (REST)

```python
# webui/api/tasks.py
@app.post("/api/tasks")
async def create_task(task_req: CreateTaskRequest):
    # Validate project_id is required
    if not task_req.project_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PROJECT_ID_REQUIRED",
                "message": "project_id is required in v0.4",
                "suggestion": "Specify project_id in request body"
            }
        )

    # Create task
    task = task_service.create_task(
        title=task_req.title,
        project_id=task_req.project_id,
        created_by=task_req.created_by
    )
    return task.to_dict()
```

### Layer 4: WebUI (JavaScript)

```javascript
// TasksView.js
async createTask() {
    const projectId = document.getElementById('project-selector').value;

    if (!projectId) {
        showError('Please select a project before creating a task');
        return;
    }

    const response = await fetch('/api/tasks', {
        method: 'POST',
        body: JSON.stringify({
            title: this.taskTitle,
            project_id: projectId  // ✅ Required
        })
    });

    if (!response.ok) {
        const error = await response.json();
        showError(error.detail.message || 'Failed to create task');
    }
}
```

---

## Testing Strategy

### Unit Tests (Per Constraint)

```python
# test_v04_constraints.py
class TestV04Constraints:
    def test_constraint_1_task_project_binding(self):
        """Task cannot enter READY without project_id"""
        task = create_task(title="Test", project_id=None)
        with pytest.raises(ProjectNotBoundError):
            task_service.transition(task.id, to=TaskState.READY)

    def test_constraint_2_spec_freezing(self):
        """Task cannot enter READY without frozen spec"""
        task = create_task(title="Test", project_id="proj_01", spec_version=0)
        with pytest.raises(SpecNotFrozenError):
            task_service.transition(task.id, to=TaskState.READY)

    def test_constraint_3_invalid_transition(self):
        """Invalid state transitions are rejected"""
        task = create_task(status=TaskState.DRAFT)
        with pytest.raises(InvalidTransitionError):
            task_service.transition(task.id, to=TaskState.DONE)

    def test_constraint_4_terminal_immutability(self):
        """Terminal states cannot be changed"""
        task = create_task(status=TaskState.DONE)
        with pytest.raises(InvalidTransitionError):
            task_service.transition(task.id, to=TaskState.RUNNING)

    def test_constraint_5_chat_boundary(self):
        """Chat cannot directly execute tasks"""
        chat_session = create_chat_session()
        task = chat_session.propose_task(title="Test")
        assert task.status == TaskState.DRAFT
```

### Integration Tests (End-to-End)

```python
# test_v04_e2e.py
class TestV04EndToEnd:
    def test_complete_task_lifecycle(self):
        """Test full task lifecycle from DRAFT to DONE"""
        # 1. Create project
        project = project_service.create_project(name="Test Project", path=".")

        # 2. Create task (DRAFT)
        task = task_service.create_task(title="Test Task", project_id=project.id)
        assert task.status == TaskState.DRAFT

        # 3. Freeze spec (DRAFT → PLANNED)
        spec = {"goal": "Test goal", "repos": ["repo_01"]}
        task = task_service.freeze_spec(task.id, spec=spec)
        assert task.status == TaskState.PLANNED
        assert task.spec_version == 1

        # 4. Transition to READY
        task = task_service.transition(task.id, to=TaskState.READY, actor="user", reason="approved")
        assert task.status == TaskState.READY

        # 5. Execute (READY → RUNNING → VERIFYING)
        task = task_runner.execute(task.id)
        assert task.status in (TaskState.RUNNING, TaskState.VERIFYING)

        # 6. Verify (VERIFYING → VERIFIED)
        task = gate_runner.verify(task.id)
        assert task.status == TaskState.VERIFIED

        # 7. Finalize (VERIFIED → DONE)
        task = task_service.finalize(task.id)
        assert task.status == TaskState.DONE
```

---

## Acceptance Criteria (v0.4 Release)

### Must Have (Blocking)

- [ ] All 5 hard constraints enforced at all layers
- [ ] All 5 validation gates implemented and tested
- [ ] Database triggers active (SQLite + PostgreSQL)
- [ ] Service layer validation complete
- [ ] API layer returns correct error codes (400/403/409)
- [ ] WebUI enforces project selection before task creation
- [ ] State machine audit trail records all transitions
- [ ] Migration script handles v0.3 → v0.4 upgrade
- [ ] All unit tests pass (coverage ≥ 90%)
- [ ] All integration tests pass

### Should Have (Important)

- [ ] CLI commands support new constraints
- [ ] Error messages are clear and actionable
- [ ] WebUI shows helpful tooltips for new concepts
- [ ] API documentation updated with examples
- [ ] Migration guide tested on real v0.3 databases

### Could Have (Nice to Have)

- [ ] WebUI state machine visualization
- [ ] CLI `task replay` command
- [ ] Spec diff viewer (compare spec versions)
- [ ] Performance benchmarks (no regression)

---

## Rollout Plan

### Phase 1: Internal Testing (Week 1)
- Deploy to staging environment
- Run full test suite
- Test migration on production-like data
- Fix any blocking issues

### Phase 2: Alpha Release (Week 2)
- Release to early adopters
- Monitor error logs for constraint violations
- Gather feedback on UX friction
- Iterate on error messages

### Phase 3: Beta Release (Week 3)
- Open beta to all users
- Publish migration guide
- Provide migration support
- Monitor adoption metrics

### Phase 4: GA Release (Week 4)
- Mark v0.4 as stable
- Update documentation
- Announce breaking changes
- Deprecate v0.3 (EOL in 6 months)

---

## Monitoring and Alerts

### Key Metrics

1. **Constraint Violation Rate**: <0.1% (should be near-zero)
2. **State Machine Error Rate**: <1% (some user errors expected)
3. **Migration Success Rate**: >99%
4. **API Error Rate (400/403/409)**: Monitor for spikes
5. **Task Creation Success Rate**: >95%

### Alerts

- **CRITICAL**: Database constraint violation detected
- **HIGH**: API returning 500 errors for state transitions
- **MEDIUM**: High rate of 400 errors (project_id missing)
- **LOW**: Users repeatedly hitting terminal state errors

---

## References

- [ADR-V04: Project-Aware Task OS](./ADR_V04_PROJECT_AWARE_TASK_OS.md)
- [State Machine Implementation](../../agentos/core/task/state_machine.py)
- [Task States Enum](../../agentos/core/task/states.py)
- [API Error Codes](../../agentos/webui/api/errors.py)

---

**Maintained by**: AgentOS Architecture Team
**Review Cycle**: Every release
**Status**: 🔒 Semantic Freeze (v0.4)
**Last Updated**: 2026-01-29
