# ADR-V04: Project-Aware Task Operating System

**Status**: Draft
**Date**: 2026-01-29
**Version**: v0.4.0
**Authors**: AgentOS Core Team
**Supersedes**: None (New major version)

---

## Context and Problem Statement

AgentOS v0.3 established a stable foundation for task execution with robust concurrency controls, SQLite write serialization, and governance mechanisms. However, it still operates on a **repository-centric** model where Tasks are loosely bound to repositories, and Chat sessions can inadvertently bypass execution boundaries.

Three critical issues emerge:

1. **Semantic Confusion**: "Project" and "Repository" are conflated, making multi-repo workflows impossible
2. **Weak Execution Boundaries**: Chat can "pretend" to execute without actually running tasks through the state machine
3. **Non-Reproducibility**: Tasks cannot be reliably replayed from the database because their specifications are not frozen at execution time

v0.4 solves these issues by introducing a **Project-Aware Task Operating System** with strict semantic boundaries and reproducible execution.

---

## Decision Drivers

### 1. Real-World Requirements

Modern software projects span multiple repositories:
- **Microservices**: Each service in its own repo
- **Monorepo workspaces**: Frontend, backend, infrastructure
- **Documentation repos**: Separate from code repos
- **Infrastructure as Code**: Terraform, Kubernetes configs

**Example**: A task to "Update API and deploy to staging" needs:
- `api-repo` (code changes)
- `infra-repo` (K8s manifests)
- `docs-repo` (API documentation)

### 2. Execution Integrity

**Problem**: Chat can generate TaskSpecs but bypass actual execution:

```
User: "Update the README"
Chat: "I'll update it for you..." [generates diff, never runs task]
User: [sees diff in chat] "Thanks!"
```

**Result**: The change never happened, but the audit trail is polluted.

### 3. Reproducibility Gap

Tasks in v0.3 reference external state (repos, configs) but don't snapshot it:
- Cannot replay a task from 3 months ago
- Cannot answer "What was the actual spec when this task ran?"
- Debugging is impossible without full context

---

## Decision

We introduce **5 Core Principles** for v0.4:

### Principle 1: Project ≠ Repository (Semantic Separation)

```yaml
Project:
  id: proj_01HY6X9...
  name: "E-Commerce Platform"
  repos:
    - repo_id: repo_api
      role: code
      path: ./services/api
    - repo_id: repo_frontend
      role: code
      path: ./services/web
    - repo_id: repo_infra
      role: infra
      path: ./infrastructure
```

**Constraints**:
- A Project MUST contain ≥1 Repository
- A Repository CAN belong to multiple Projects
- Tasks MUST bind to exactly ONE Project (not repos)

### Principle 2: Task MUST Bind to Project (Strong Constraint)

**Iron Law**:
```python
# Before entering READY state:
assert task.project_id is not None, "Task must have project_id"
assert task.spec_version >= 1, "Task must have frozen spec"
```

**Important**: This constraint is **state-dependent**:
- DRAFT state: `project_id = NULL` is **allowed** (work-in-progress)
- READY+ states: `project_id ≠ NULL` is **required** (execution-ready)

*See [VERSION_COMPLETENESS_MATRIX.md](../VERSION_COMPLETENESS_MATRIX.md#a2-project_id-constraint---freeze-decision) for the architectural decision rationale.*

**Rationale**: Without project binding, we cannot:
- Determine which repos the task can access
- Apply project-level policies (security, quotas)
- Enforce multi-repo consistency

### Principle 3: Chat ↔ Task ↔ Execution Boundary (Strict Separation)

```
┌─────────────────┐
│  Chat Session   │  Role: Clarify requirements, propose TaskSpec
│                 │  Cannot: Execute, modify files, commit
└────────┬────────┘
         │ emits
         ▼
┌─────────────────┐
│   Task Spec     │  Role: Frozen specification (immutable after PLANNED)
│  (spec_version) │  Cannot: Change after entering READY
└────────┬────────┘
         │ triggers
         ▼
┌─────────────────┐
│   Execution     │  Role: Run the spec through state machine
│  (READY→RUNNING)│  Cannot: Skip states, bypass gates
└─────────────────┘
```

**Enforcement**:
- Chat API CANNOT directly call `task.run()`
- Chat can only call `task_service.create_task()` or `task_service.propose_spec()`
- Execution requires `task_service.transition(task_id, to="READY")`

### Principle 4: Task State Machine (Clear Lifecycle)

```
┌────────┐
│ DRAFT  │  Chat drafting TaskSpec
└───┬────┘
    │ approve()
    ▼
┌────────┐
│PLANNED │  Spec frozen (spec_version >= 1)
└───┬────┘
    │ validate() + bind(project_id)
    ▼
┌────────┐
│ READY  │  ✅ Checkpoint: Must have project_id + spec_version
└───┬────┘
    │ runner.execute()
    ▼
┌────────┐
│RUNNING │  Actual execution in progress
└───┬────┘
    │ gates.verify()
    ▼
┌────────────┐
│ VERIFYING  │  Post-execution verification (tests, lints, gates)
└─────┬──────┘
      │ pass
      ▼
┌──────────┐
│ VERIFIED │  All gates passed
└────┬─────┘
     │ finalize()
     ▼
┌────────┐
│  DONE  │  Terminal: Success
└────────┘

# Terminal Error States:
FAILED    - Execution failed (retryable)
CANCELLED - User/system cancelled
BLOCKED   - Stuck (e.g., approval needed in AUTONOMOUS mode)
```

**Key State Transitions**:

| From State | To State | Allowed? | Condition |
|------------|----------|----------|-----------|
| DRAFT | PLANNED | ✅ | Spec is complete |
| PLANNED | READY | ✅ | project_id + spec_version set |
| READY | RUNNING | ✅ | Runner picked up task |
| RUNNING | VERIFYING | ✅ | Execution completed |
| VERIFYING | VERIFIED | ✅ | All gates passed |
| VERIFIED | DONE | ✅ | Task finalized |
| RUNNING | FAILED | ✅ | Execution error |
| FAILED | READY | ✅ | Retry (explicit) |
| * | CANCELLED | ✅ | User/system cancel |
| RUNNING | BLOCKED | ✅ | Waiting for approval |

**Validation Rule (HARD)**:
```python
def transition_to_ready(task: Task) -> None:
    if task.spec_version < 1:
        raise SpecNotFrozenError("Cannot enter READY without frozen spec")
    if task.project_id is None:
        raise ProjectNotBoundError("Cannot enter READY without project binding")
```

### Principle 5: Spec Freezing (Reproducibility)

**Spec Versioning**:
```json
{
  "task_id": "task_01HY6XA...",
  "spec_version": 3,  // Increments on each modification
  "spec_snapshot": {
    "project_id": "proj_01HY6X9...",
    "repos": [
      {"repo_id": "repo_api", "commit": "abc1234", "branch": "main"},
      {"repo_id": "repo_infra", "commit": "def5678", "branch": "main"}
    ],
    "goal": "Deploy API v2.1 to staging",
    "constraints": ["no_destructive_ops", "require_tests"],
    "model_policy": {"planner": "claude-opus-4.5", "executor": "claude-sonnet-4"}
  },
  "frozen_at": "2026-01-29T12:34:56Z"
}
```

**Freezing Rules**:
1. spec_version = 0: Task in DRAFT (mutable)
2. spec_version ≥ 1: Spec frozen (immutable)
3. Any change after freezing creates a NEW task (not a spec_version bump)

**Why?**:
- **Reproducibility**: Replay task from DB without external state
- **Debugging**: "What was the exact spec when this failed?"
- **Audit**: "Did the task change mid-execution?"

---

## Detailed Design

### 1. Database Schema Changes (v0.30)

#### tasks table (updated)
```sql
ALTER TABLE tasks ADD COLUMN project_id TEXT;
ALTER TABLE tasks ADD COLUMN spec_version INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN spec_snapshot TEXT;  -- JSON

-- Constraint: Tasks in READY+ must have project_id
CREATE TRIGGER enforce_project_binding
BEFORE UPDATE OF status ON tasks
FOR EACH ROW
WHEN NEW.status IN ('ready', 'running', 'verifying', 'verified', 'done')
  AND NEW.project_id IS NULL
BEGIN
  SELECT RAISE(ABORT, 'Tasks in READY+ states must have project_id');
END;
```

#### task_spec_history table (new)
```sql
CREATE TABLE task_spec_history (
  history_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  spec_version INTEGER NOT NULL,
  spec_snapshot TEXT NOT NULL,  -- JSON
  created_at TEXT NOT NULL,
  created_by TEXT,
  FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
  UNIQUE(task_id, spec_version)
);
```

### 2. API Changes

#### Task Creation (v0.4)
```python
# OLD (v0.3): Implicit project binding
POST /api/tasks
{
  "title": "Update README",
  "session_id": "sess_01HY..."
}

# NEW (v0.4): Explicit project binding REQUIRED
POST /api/tasks
{
  "title": "Update README",
  "project_id": "proj_01HY...",  # ✅ REQUIRED
  "session_id": "sess_01HY..."   # Optional
}
```

#### Spec Freezing API
```python
# Freeze spec and transition to PLANNED
POST /api/tasks/{task_id}/freeze
{
  "spec": {
    "goal": "Deploy API to staging",
    "repos": ["repo_api", "repo_infra"],
    "constraints": ["require_tests"]
  }
}

# Response:
{
  "task_id": "task_01HY...",
  "status": "planned",
  "spec_version": 1,
  "frozen_at": "2026-01-29T12:34:56Z"
}
```

### 3. State Machine Integration

#### TaskService (updated)
```python
class TaskService:
    def transition(self, task_id: str, to: TaskState, actor: str, reason: str):
        """Execute state transition with validation"""
        task = self.get_task(task_id)

        # Gate: Cannot enter READY without project_id + spec freeze
        if to == TaskState.READY:
            if task.project_id is None:
                raise ProjectNotBoundError(f"Task {task_id} has no project_id")
            if task.spec_version < 1:
                raise SpecNotFrozenError(f"Task {task_id} spec not frozen")

        # Execute transition via state machine
        updated = self.state_machine.transition(
            task_id, to=to.value, actor=actor, reason=reason
        )
        return updated
```

### 4. WebUI Changes

#### Task Creation Flow (v0.4)
```
┌──────────────────────────────┐
│  Select Project (Required)   │  ← NEW: Must select project first
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Enter Task Title            │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Draft Spec (Chat)           │  Chat helps draft spec
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Review Spec                 │  User reviews before freezing
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Freeze Spec → PLANNED       │  ← NEW: Explicit freeze action
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Approve → READY → Execute   │
└──────────────────────────────┘
```

---

## Consequences

### Positive

1. **Semantic Clarity**: Project ≠ Repo eliminates confusion
2. **Execution Integrity**: Chat cannot bypass execution
3. **Reproducibility**: All tasks can be replayed from DB
4. **Multi-Repo Support**: Tasks can span multiple repositories
5. **Clear Boundaries**: State machine enforces strict lifecycle
6. **Audit Trail**: spec_version tracks all changes

### Negative

1. **Breaking Change**: All existing tasks must be migrated to bind to projects
2. **API Complexity**: Task creation now requires 2 steps (create → freeze)
3. **Storage Overhead**: spec_snapshot stores full context per task
4. **Migration Effort**: v0.3 → v0.4 requires data migration script

### Migration Strategy

#### 1. Database Migration (schema_v30.sql)
```sql
-- Add new columns (nullable for backward compat)
ALTER TABLE tasks ADD COLUMN project_id TEXT;
ALTER TABLE tasks ADD COLUMN spec_version INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN spec_snapshot TEXT;

-- Create default project for orphan tasks
INSERT INTO projects (id, name, path, status)
VALUES ('proj_default', 'Legacy Tasks', '.', 'active');

-- Bind orphan tasks to default project
UPDATE tasks SET project_id = 'proj_default'
WHERE project_id IS NULL;

-- Make project_id NOT NULL after migration
-- (Done manually after verifying all tasks have project_id)
```

#### 2. Code Migration
```python
# OLD (v0.3): Create task without project
task = task_service.create_task(title="Update README")

# NEW (v0.4): Must specify project
project = project_service.get_project_by_name("my-project")
task = task_service.create_task(title="Update README", project_id=project.id)
```

---

## Success Criteria

v0.4 is considered successful when:

### 1. Functional Requirements
- [ ] All tasks have project_id (no NULL values)
- [ ] Tasks cannot enter READY state without project_id + spec_version ≥ 1
- [ ] Chat API cannot directly execute tasks
- [ ] Spec freezing is enforced via API
- [ ] Tasks can be replayed from spec_snapshot

### 2. State Machine Requirements
- [ ] All state transitions follow the defined table
- [ ] Invalid transitions raise clear errors
- [ ] Audit trail records all transitions
- [ ] Terminal states (DONE/FAILED/CANCELLED) cannot be exited

### 3. Multi-Repo Requirements
- [ ] Projects can bind to multiple repos
- [ ] Tasks can access all repos in their project
- [ ] Repo scope can be limited per task
- [ ] Cross-repo artifact references work

### 4. Backward Compatibility
- [ ] v0.3 tasks migrate cleanly to v0.4
- [ ] Single-repo projects work as before
- [ ] API clients receive clear error messages
- [ ] WebUI shows migration hints

### 5. Documentation Requirements
- [ ] ADR published in docs/architecture/
- [ ] Migration guide published
- [ ] API documentation updated
- [ ] WebUI tooltips explain new concepts

---

## Alternatives Considered

### Alternative 1: Keep Project = Repo (Do Nothing)
**Rejected**: Cannot support multi-repo workflows, which are increasingly common.

### Alternative 2: Soft Project Binding (Optional)
**Rejected**: Weak constraints lead to ambiguous semantics. Hard binding forces clarity.

### Alternative 3: Runtime Spec Binding (No Freezing)
**Rejected**: Cannot replay tasks reliably. Spec must be immutable after PLANNED.

### Alternative 4: Implicit Freezing on Execute
**Rejected**: Users need explicit review step before execution. Auto-freeze hides critical decision point.

---

## Related Decisions

- **ADR-V02: Invariants** - v0.4 extends v0.2 invariants with new constraints
- **ADR-007: Database Write Serialization** - Spec snapshots use SQLiteWriter
- **Task State Machine (states.py)** - Defines the state enumeration
- **Project Schema (v25)** - Multi-repo project model

---

## Notes

### Design Rationale

#### Why Spec Freezing?
- **User Safety**: Prevents accidental mid-execution changes
- **Debugging**: Eliminates "it worked yesterday" syndrome
- **Compliance**: Regulatory environments require immutable records

#### Why PLANNED State?
- Separates "spec ready for review" from "ready to execute"
- Allows human checkpoint before resource-intensive operations
- Supports async approval workflows (governance gates)

#### Why Project Binding is HARD (not SOFT)?
- Soft binding leads to "magic" (system guesses project)
- Hard binding forces explicit decisions (good UX friction)
- Errors are easier to debug when constraints are strict

---

## Implementation Phases

### Phase 0: ADR and Semantic Freeze ✅ (This Document)
- Write ADR
- Define state machine
- Document constraints
- Update CHANGELOG

### Phase 1: Schema and Data Migration
- Create schema_v30.sql
- Write migration script
- Test backward compatibility
- Migrate existing tasks

### Phase 2: Core Services
- Update TaskService with project binding
- Implement spec freezing
- Add state transition validation
- Create spec history tracking

### Phase 3: API Layer
- Update POST /api/tasks (require project_id)
- Add POST /api/tasks/{id}/freeze
- Add GET /api/tasks/{id}/spec/{version}
- Update error responses

### Phase 4: WebUI Integration
- Add project selector to task creation
- Add spec review UI
- Add freeze button
- Show spec_version in task details

### Phase 5: CLI Commands
- `agentos task create --project <id>`
- `agentos task freeze <task_id>`
- `agentos task replay <task_id>`
- `agentos project bind-repo <project_id> <repo_path>`

### Phase 6: Testing and Documentation
- Write integration tests
- Write migration guide
- Update API docs
- Create video tutorials

---

## References

- [Multi-Repo Projects Design](./DATABASE_ARCHITECTURE.md)
- [Task State Machine](../../agentos/core/task/state_machine.py)
- [Project Schema](../../agentos/schemas/project.py)
- [v0.3 Release Notes](../../CHANGELOG.md#03x---2026-01-29)

---

**Status**: Draft
**Review**: Architecture Team
**Approval**: Pending (To be approved after Phase 0 deliverables)
**Last Updated**: 2026-01-29
