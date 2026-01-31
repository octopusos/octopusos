# ADR: Execution Boundaries Freeze

**Status**: FROZEN - Non-Negotiable Architecture Constraints
**Date**: 2026-01-30
**Version**: v0.6.0
**Authors**: AgentOS Core Team
**Supersedes**: None (Establishes new IRON LAW constraints)

---

## Executive Summary

This document establishes **THREE IRON LAW EXECUTION BOUNDARIES** that are fundamental to AgentOS architecture integrity. These boundaries are **FROZEN** and cannot be compromised without breaking the system's core safety guarantees.

**Any Pull Request that violates these boundaries MUST be BLOCKED.**

These boundaries are not design preferences or best practices - they are **architectural constraints** enforced at multiple layers (database, service, executor) with comprehensive audit trails.

---

## Status Definition

**FROZEN** means:
- These rules cannot be changed without a full architecture review
- No "temporary" violations allowed
- No "emergency" bypasses permitted
- Breaking these boundaries invalidates the system's safety guarantees
- PR reviewers MUST reject any code that violates these boundaries

---

## Context

AgentOS v0.6 establishes a fundamental separation between planning (pure reasoning) and execution (side-effects). This separation is critical for:

1. **Safety**: Preventing accidental execution during planning phase
2. **Auditability**: Clear boundaries enable precise audit trails
3. **Reproducibility**: Frozen specs ensure tasks can be replayed exactly
4. **Integrity**: Chat cannot bypass the execution state machine

Without these boundaries, the system degrades into:
- Chat "pretending" to execute without actual task creation
- Planning phases accidentally triggering side effects
- Execution of unstable/mutable specifications
- Audit trails that cannot be trusted

---

## The Three Iron Law Boundaries

### Boundary #1: Chat ≠ Execution

**Definition**: Chat system is **FORBIDDEN** from directly triggering execution. All execution must flow through the Task state machine.

#### The Rule

```
chat → ❌ direct execution (FORBIDDEN)
chat → ✅ create Task (DRAFT state) → task runner → execution
```

#### Why This Matters

**Problem Without This Boundary**:
```
User: "Update the README"
Chat: "I'll update it for you..." [generates diff, never creates task]
User: [sees diff in chat] "Thanks!"
Result: Nothing actually happened, audit trail is polluted
```

**With This Boundary**:
```
User: "Update the README"
Chat: "I'll create a task..." [creates DRAFT task]
System: Task created, approved, queued
TaskRunner: Executes task, updates README
Result: Change actually happened, fully audited
```

#### Implementation

**Error Class**: `ChatExecutionForbiddenError` (in `agentos/core/task/errors.py`)

```python
class ChatExecutionForbiddenError(TaskStateError):
    """
    Exception raised when chat attempts to directly execute tasks

    Architecture Rule:
        chat → ✅ create Task (DRAFT state)
        chat → ❌ direct execution (FORBIDDEN)
        task runner → ✅ execution (ALLOWED)
    """
```

**Enforcement Point**: `ExecutorEngine.execute()` (in `agentos/core/executor/executor_engine.py`)

```python
def execute(
    self,
    execution_request: Dict[str, Any],
    sandbox_policy: Dict[str, Any],
    policy_path: Optional[Path] = None,
    caller_source: str = "unknown"  # Boundary #1 enforcement parameter
) -> Dict[str, Any]:
    # Hard gate - reject chat execution attempts
    if caller_source == "chat":
        raise ChatExecutionForbiddenError(
            caller_context="ExecutorEngine.execute",
            attempted_operation="execute_task",
            task_id=execution_request.get("task_id"),
            metadata={
                "execution_request_id": execution_request.get("request_id"),
                "enforcement": "boundary_1_chat_execution_forbidden"
            }
        )

    # Enforce that only task_runner can execute
    if caller_source != "task_runner":
        logger.warning(
            f"Execution called with non-task_runner source: {caller_source}. "
            f"This should only be called by task runner."
        )
```

#### Enforcement Layers

| Layer | Mechanism | Location |
|-------|-----------|----------|
| **Executor** | `caller_source` parameter check | `executor_engine.py:execute()` |
| **Pipeline Runner** | Passes `caller_source="task_runner"` | `pipeline_runner.py` |
| **Error Handling** | ChatExecutionForbiddenError raised | `errors.py` |
| **Audit** | All execution attempts logged with source | `audit.py` |

#### Allowed Operations

✅ **Chat → Create DRAFT Task**
```python
from agentos.core.task.service import TaskService

task_service = TaskService()
task = task_service.create_draft_task(
    title="Task from chat",
    created_by="chat_mode",
    metadata={"source": "chat"}
)
# Result: task.status == "draft"
```

✅ **Task Runner → Execute Task**
```python
from agentos.core.executor.executor_engine import ExecutorEngine

executor = ExecutorEngine(repo_path=..., output_dir=...)
result = executor.execute(
    execution_request=exec_req,
    sandbox_policy={},
    caller_source="task_runner"  # ALLOWED
)
```

#### Forbidden Operations

❌ **Chat → Direct Execution**
```python
# This will raise ChatExecutionForbiddenError
executor = ExecutorEngine(repo_path=..., output_dir=...)
result = executor.execute(
    execution_request=exec_req,
    sandbox_policy={},
    caller_source="chat"  # FORBIDDEN
)
# Result: ChatExecutionForbiddenError raised
```

#### Test Coverage

**Test File**: `tests/integration/task/test_chat_execution_gate_simple.py`

**7/7 Tests Passing**:
1. `test_chat_execution_forbidden_error_exists` - Error class validation
2. `test_chat_can_create_draft_task` - Chat can create DRAFT tasks
3. `test_chat_cannot_approve_task_directly` - Chat cannot bypass workflow
4. `test_complete_workflow_chat_to_execution` - Full workflow validation
5. `test_error_inheritance` - Exception hierarchy validation
6. `test_create_approve_queue_and_start_workflow` - Legal execution path
7. `test_task_runner_source_identification` - Source parameter validation

#### References

- **Implementation**: Task #1 - Chat → Execution System-Level Hard Gate
- **Acceptance Report**: `TASK_1_ACCEPTANCE_REPORT.md`
- **Quick Reference**: `TASK_1_QUICK_REFERENCE.md`

---

### Boundary #2: Planning = Zero Side-Effect

**Definition**: Planning phase (DRAFT/APPROVED states) is **FORBIDDEN** from executing any side-effect operations. Planning is pure reasoning only.

#### The Rule

```
Planning Phase (DRAFT/APPROVED):
  ❌ shell execution (subprocess, os.system)
  ❌ file writes (file.write, Path.mkdir)
  ❌ git operations (commit, push, branch)
  ❌ network calls (HTTP, API, socket)
  ✅ file reads (allowed)
  ✅ computation (allowed)
  ✅ specification generation (allowed)

Implementation Phase (RUNNING):
  ✅ ALL operations allowed
```

#### Why This Matters

**Problem Without This Boundary**:
```
State: DRAFT (planning)
Action: User asks "Can we deploy this?"
Planner: Runs actual deployment commands during planning
Result: Production system changed during "planning" phase
```

**With This Boundary**:
```
State: DRAFT (planning)
Action: User asks "Can we deploy this?"
Planner: Generates deployment plan specification (no execution)
Result: Plan created, nothing executed, safe to review
```

#### Implementation

**Error Class**: `PlanningSideEffectForbiddenError` (in `agentos/core/task/errors.py`)

```python
class PlanningSideEffectForbiddenError(TaskStateError):
    """
    Exception raised when side-effect operations are attempted during planning

    Architecture Rule (v0.6 Soul):
        Planning phase = Pure reasoning, ZERO side effects
        Implementation phase = Side effects allowed
    """
```

**Enforcement Module**: `PlanningGuard` (in `agentos/core/task/planning_guard.py`)

```python
class PlanningGuard:
    """
    Planning phase side-effect prevention guard

    Phase Detection:
        - DRAFT, APPROVED states → planning phase
        - RUNNING state → implementation phase
        - metadata.current_stage → phase override

    Side-Effect Categories:
        - shell: subprocess.run, os.system, etc.
        - file_write: file.write, Path.mkdir, etc.
        - git: git.commit, git.push, etc.
        - network: http requests, API calls, etc.
    """

    def assert_operation_allowed(
        self,
        operation_type: str,
        operation_name: str,
        task: Optional[Task] = None,
        mode_id: Optional[str] = None
    ) -> None:
        """
        Assert that an operation is allowed in current phase
        Raises PlanningSideEffectForbiddenError if forbidden
        """
        if self.is_planning_phase(task, mode_id):
            if operation_type in ["shell", "file_write", "git", "network"]:
                raise PlanningSideEffectForbiddenError(
                    task_id=task.task_id if task else None,
                    operation_type=operation_type,
                    operation_name=operation_name,
                    current_phase="planning"
                )
```

#### Enforcement Layers

| Layer | Mechanism | Location |
|-------|-----------|----------|
| **Executor Engine** | Planning guard check before operations | `executor_engine.py` |
| **Tool Executor** | Planning guard check before shell | `tool_executor.py` |
| **Task State** | Phase detection based on TaskState | `models.py` |
| **Audit** | All side-effect attempts logged | `audit.py` |

#### Phase Detection Logic

The planning guard identifies phases based on multiple signals:

1. **TaskState.DRAFT** → planning phase
2. **TaskState.APPROVED** → planning phase (still planning before execution)
3. **TaskState.RUNNING** → implementation phase
4. **metadata.current_stage == "planning"** → planning phase
5. **mode_id == "planning"** → planning phase

#### Operation Classification

All major side-effect categories are covered:

| Category | Operations | Planning | Implementation |
|----------|-----------|----------|----------------|
| **shell** | subprocess.run, os.system | ❌ FORBIDDEN | ✅ ALLOWED |
| **file_write** | file.write, Path.mkdir | ❌ FORBIDDEN | ✅ ALLOWED |
| **git** | git.commit, git.push | ❌ FORBIDDEN | ✅ ALLOWED |
| **network** | HTTP, API calls | ❌ FORBIDDEN | ✅ ALLOWED |
| **file_read** | file.read, Path.read_text | ✅ ALLOWED | ✅ ALLOWED |
| **computation** | Pure functions | ✅ ALLOWED | ✅ ALLOWED |

#### Test Coverage

**Test Files**:
- Unit: `tests/unit/task/test_planning_guard.py` (25 tests)
- E2E: `tests/integration/task/test_planning_guard_e2e.py` (9 tests)

**Total: 34/34 Tests Passing** (100% pass rate)

**Test Categories**:
- Phase detection (8 tests)
- Side-effect prevention (8 tests)
- Unknown operation handling (2 tests)
- Check and log functionality (2 tests)
- Global instance management (2 tests)
- Error metadata validation (3 tests)
- Service integration (5 tests)
- Mode integration (2 tests)
- State transitions (2 tests)

#### References

- **Implementation**: Task #3 - Planning Phase Side-Effect Prevention
- **Acceptance Report**: `TASK_3_ACCEPTANCE_REPORT.md`
- **Core Module**: `agentos/core/task/planning_guard.py`

---

### Boundary #3: Execution Requires Frozen Spec

**Definition**: Execution is **FORBIDDEN** for tasks with unfrozen specifications (spec_frozen = 0). Only tasks with spec_frozen = 1 can be executed.

#### The Rule

```
spec_frozen = 0 → ❌ execution blocked (FORBIDDEN)
spec_frozen = 1 → ✅ execution allowed (VALID)
```

#### Why This Matters

**Problem Without This Boundary**:
```
Time T0: Task spec created, spec_frozen = 0
Time T1: Execution starts based on spec
Time T2: Spec modified mid-execution
Time T3: Execution completes
Result: Cannot reproduce - spec changed during execution
```

**With This Boundary**:
```
Time T0: Task spec created, spec_frozen = 0
Time T1: User freezes spec, spec_frozen = 1
Time T2: Execution starts based on frozen spec
Time T3: Spec cannot be modified (frozen)
Time T4: Execution completes
Result: Fully reproducible - spec was immutable
```

#### Implementation

**Error Class**: `SpecNotFrozenError` (in `agentos/core/task/errors.py`)

```python
class SpecNotFrozenError(TaskStateError):
    """
    Exception raised when attempting to execute a task with unfrozen spec

    Architecture Rule (v0.6 Frozen Plan):
        spec_frozen = 0 → ❌ execution blocked (FORBIDDEN)
        spec_frozen = 1 → ✅ execution allowed (VALID)
    """
```

**Enforcement Point**: `ExecutorEngine.execute()` (in `agentos/core/executor/executor_engine.py`)

```python
def execute(self, execution_request: Dict[str, Any], ...) -> Dict[str, Any]:
    # Extract task_id
    task_id = execution_request.get("task_id")

    # Load task from database
    task = self.task_manager.get_task(task_id)
    if not task:
        raise TaskNotFoundError(f"Task {task_id} not found")

    # Boundary #3: Check spec_frozen flag
    if not task.is_spec_frozen():
        # Audit rejection
        run_tape.audit_logger.log_event("execution_blocked_spec_not_frozen", details={
            "task_id": task_id,
            "spec_frozen": task.spec_frozen,
            "reason": "Execution requires frozen specification (spec_frozen = 1)",
            "enforcement": "boundary_3_frozen_plan_validation",
            "v06_constraint": True
        })

        # Raise error
        raise SpecNotFrozenError(
            task_id=task_id,
            spec_frozen=task.spec_frozen,
            message="Task specification is not frozen. "
                    "Execution requires spec_frozen = 1 (v0.6 constraint). "
                    "Please freeze the task specification before executing."
        )

    # Log successful validation
    run_tape.audit_logger.log_event("spec_frozen_validation_passed", details={
        "task_id": task_id,
        "spec_frozen": task.spec_frozen
    })

    # Proceed with execution...
```

**Task Model Enhancement**: `Task.is_spec_frozen()` method (in `agentos/core/task/models.py`)

```python
class Task:
    spec_frozen: int = 0  # 0=unfrozen, 1=frozen

    def is_spec_frozen(self) -> bool:
        """Check if task specification is frozen"""
        return self.spec_frozen == 1
```

#### Enforcement Layers

| Layer | Mechanism | Location |
|-------|-----------|----------|
| **Database** | spec_frozen column with default 0 | `schema_v31_project_aware.sql` |
| **Database Trigger** | Enforces spec_frozen=1 for READY+ states | `schema_v31_project_aware.sql` |
| **Task Model** | is_spec_frozen() method | `models.py` |
| **Task Manager** | Loads spec_frozen from DB | `manager.py` |
| **Executor Engine** | Checks spec_frozen before execution | `executor_engine.py` |
| **Audit** | Logs rejection and validation events | `audit.py` |

#### Database Schema

```sql
-- From schema_v31_project_aware.sql
ALTER TABLE tasks ADD COLUMN spec_frozen INTEGER DEFAULT 0;

-- Index for efficient querying
CREATE INDEX idx_tasks_spec_frozen
ON tasks(spec_frozen)
WHERE spec_frozen = 1;

-- Trigger: Enforce spec_frozen=1 for READY+ states
CREATE TRIGGER enforce_spec_frozen_on_ready
BEFORE UPDATE OF status ON tasks
FOR EACH ROW
WHEN NEW.status IN ('ready', 'running', 'verifying', 'verified', 'done')
  AND NEW.spec_frozen = 0
BEGIN
  SELECT RAISE(ABORT, 'Tasks in READY+ states must have spec_frozen = 1');
END;
```

#### Workflow Integration

**Correct Flow**:
```
1. Create task (spec_frozen = 0)
2. Edit specification (mutable)
3. Freeze specification (spec_frozen = 1)
4. Transition to READY state
5. Execute task (validation passes)
```

**Incorrect Flow (Blocked)**:
```
1. Create task (spec_frozen = 0)
2. Try to execute immediately
3. SpecNotFrozenError raised
4. Execution blocked
```

#### Test Coverage

**Test File**: `tests/integration/task/test_spec_frozen_simple.py`

**4/4 Tests Passing**:
1. `test_task_model_spec_frozen_field` - Task model field validation
2. `test_task_manager_loads_spec_frozen` - Database loading validation
3. `test_spec_not_frozen_error` - Error structure validation
4. `test_spec_frozen_in_task_dict` - Serialization validation

#### References

- **Implementation**: Task #4 - Execution Frozen Plan Validation
- **Acceptance Report**: `TASK_4_ACCEPTANCE_REPORT.md`
- **Database Schema**: `agentos/store/migrations/schema_v31_project_aware.sql`

---

## PR Review Checklist

When reviewing Pull Requests, reviewers MUST verify these boundaries are not violated:

### Boundary #1: Chat ≠ Execution

- [ ] **No direct executor calls from chat code**
  - Search for: `ExecutorEngine` imports in `agentos/core/chat/` or `agentos/webui/api/chat*.py`
  - Search for: `executor.execute()` calls with `caller_source="chat"`
  - Verify: All execution flows through TaskService

- [ ] **Chat only creates DRAFT tasks**
  - Verify: Chat code uses `task_service.create_draft_task()`
  - Verify: No direct state transitions to RUNNING
  - Verify: No bypassing of approval workflow

- [ ] **caller_source parameter preserved**
  - Verify: All `executor.execute()` calls include `caller_source` parameter
  - Verify: Pipeline runner passes `caller_source="task_runner"`
  - Verify: No hardcoded `caller_source="unknown"`

**Commands to Check**:
```bash
# Check for ExecutorEngine imports in chat code
grep -r "ExecutorEngine" agentos/core/chat/ agentos/webui/api/chat*.py

# Check for executor.execute calls with caller_source
grep -r "executor.execute" --include="*.py" | grep -v "caller_source="

# Check for chat bypassing task creation
grep -r "task.*running\|task.*execute" agentos/core/chat/
```

### Boundary #2: Planning = Zero Side-Effect

- [ ] **No side-effects in planning mode code**
  - Search for: `subprocess.run`, `os.system` in planning mode code
  - Search for: `file.write()`, `Path.mkdir()` in planning mode code
  - Search for: `git.commit`, `git.push` in planning mode code
  - Verify: Planning guard checks are present

- [ ] **Planning guard integration**
  - Verify: New execution paths include planning guard checks
  - Verify: `assert_operation_allowed()` called before side-effects
  - Verify: Task state passed to planning guard

- [ ] **Mode identification correct**
  - Verify: DRAFT/APPROVED states marked as planning phase
  - Verify: RUNNING state marked as implementation phase
  - Verify: No state misclassification

**Commands to Check**:
```bash
# Check for subprocess calls without planning guard
grep -r "subprocess.run\|os.system" agentos/core/ | grep -v "planning_guard"

# Check for file writes without planning guard
grep -r "\.write(\|\.mkdir(" agentos/core/ | grep -v "planning_guard"

# Check for planning guard imports
grep -r "from.*planning_guard import\|import.*planning_guard" agentos/core/
```

### Boundary #3: Execution Requires Frozen Spec

- [ ] **No execution of unfrozen specs**
  - Search for: Execution calls without spec_frozen check
  - Verify: `task.is_spec_frozen()` checked before execution
  - Verify: SpecNotFrozenError handling in place

- [ ] **Database consistency**
  - Verify: spec_frozen field present in Task model
  - Verify: spec_frozen loaded from database
  - Verify: spec_frozen included in to_dict()

- [ ] **State transition validation**
  - Verify: Cannot transition to READY without spec_frozen=1
  - Verify: Database triggers enforced
  - Verify: Service layer validation in place

**Commands to Check**:
```bash
# Check for executor.execute without spec_frozen check
grep -B 10 "executor.execute" agentos/core/ | grep -L "is_spec_frozen\|spec_frozen"

# Check Task model has spec_frozen field
grep "spec_frozen" agentos/core/task/models.py

# Check database schema has spec_frozen
grep "spec_frozen" agentos/store/migrations/schema_v31*.sql
```

### General Checks

- [ ] **Tests include boundary validation**
  - Verify: New tests check boundary violations
  - Verify: Error cases tested
  - Verify: Audit logging verified

- [ ] **Documentation updated**
  - Verify: Boundary violations documented
  - Verify: Correct usage examples provided
  - Verify: Error messages are actionable

- [ ] **Audit trail complete**
  - Verify: Boundary violations logged
  - Verify: Audit events have context
  - Verify: Enforcement tags present

---

## Violation Examples & Correct Approaches

### Example 1: Chat Trying to Execute

**WRONG** ❌:
```python
# In chat/engine.py
from agentos.core.executor.executor_engine import ExecutorEngine

def handle_user_request(self, message: str):
    # VIOLATION: Chat directly executing
    executor = ExecutorEngine(...)
    result = executor.execute(
        execution_request={"task_id": "task_123"},
        caller_source="chat"  # FORBIDDEN
    )
    return result
```

**CORRECT** ✅:
```python
# In chat/engine.py
from agentos.core.task.service import TaskService

def handle_user_request(self, message: str):
    # Create DRAFT task instead
    task_service = TaskService()
    task = task_service.create_draft_task(
        title=f"Task from chat: {message}",
        created_by="chat_mode",
        metadata={"source": "chat"}
    )
    return {"task_id": task.task_id, "status": "draft"}
```

### Example 2: Planning Phase Executing Shell Commands

**WRONG** ❌:
```python
# In planner.py
def create_deployment_plan(self, task: Task):
    if task.status == "draft":  # Planning phase
        # VIOLATION: Side effect during planning
        result = subprocess.run(
            ["kubectl", "get", "pods"],
            capture_output=True
        )
        return {"plan": result.stdout}
```

**CORRECT** ✅:
```python
# In planner.py
from agentos.core.task.planning_guard import planning_guard

def create_deployment_plan(self, task: Task):
    if task.status == "draft":  # Planning phase
        # Generate plan specification (no execution)
        plan_spec = {
            "type": "deployment",
            "steps": [
                {"action": "kubectl_get_pods", "dry_run": True},
                {"action": "validate_deployment"}
            ]
        }
        return {"plan": plan_spec}

def execute_deployment_plan(self, task: Task, plan: dict):
    if task.status == "running":  # Implementation phase
        # Now we can execute
        planning_guard.assert_operation_allowed(
            operation_type="shell",
            operation_name="subprocess.run",
            task=task
        )
        result = subprocess.run(
            ["kubectl", "get", "pods"],
            capture_output=True
        )
        return result
```

### Example 3: Executing Unfrozen Spec

**WRONG** ❌:
```python
# In task_runner.py
def run_task(self, task_id: str):
    task = task_manager.get_task(task_id)
    # VIOLATION: No spec_frozen check
    executor = ExecutorEngine(...)
    result = executor.execute(
        execution_request={"task_id": task_id},
        caller_source="task_runner"
    )
    return result
```

**CORRECT** ✅:
```python
# In task_runner.py
from agentos.core.task.errors import SpecNotFrozenError

def run_task(self, task_id: str):
    task = task_manager.get_task(task_id)

    # Check spec is frozen before execution
    if not task.is_spec_frozen():
        raise SpecNotFrozenError(
            task_id=task_id,
            spec_frozen=task.spec_frozen,
            message="Cannot execute task with unfrozen spec"
        )

    # Spec is frozen, safe to execute
    executor = ExecutorEngine(...)
    result = executor.execute(
        execution_request={"task_id": task_id},
        caller_source="task_runner"
    )
    return result
```

---

## Exceptions

### Are There Any Exceptions?

**NO.** These boundaries have **ZERO EXCEPTIONS**.

There are NO scenarios where these boundaries can be bypassed:
- Not for "emergency" situations
- Not for "temporary" workarounds
- Not for "testing" purposes (use proper test infrastructure)
- Not for "performance" optimizations
- Not for "convenience" features

### What About Testing?

Tests MUST respect these boundaries:

**Test Execution**: Use `caller_source="test"` (not "chat")
**Test Planning**: Mock side-effects instead of executing them
**Test Frozen Specs**: Use proper spec freezing workflow in tests

**Example**:
```python
# In tests
def test_execution_flow():
    # Create task with frozen spec
    task = create_task_with_frozen_spec()

    # Execute with test caller source
    executor = ExecutorEngine(...)
    result = executor.execute(
        execution_request={"task_id": task.task_id},
        caller_source="test"  # Not "chat", not bypassing
    )

    assert result["status"] == "success"
```

### What About Development Mode?

Development mode MUST also respect these boundaries. Use proper workflows:

1. **For rapid testing**: Use `TaskService.create_approve_queue_and_start()` (respects boundaries)
2. **For debugging**: Use proper test infrastructure with `caller_source="test"`
3. **For experiments**: Create proper DRAFT tasks and freeze them

**NO SHORTCUTS ALLOWED** - even in development.

---

## Consequences

### Breaking These Boundaries Results In

#### Immediate Technical Consequences

1. **Loss of Audit Trail Integrity**
   - Cannot trust execution logs
   - Cannot answer "who executed what and when?"
   - Compliance requirements violated

2. **Loss of Reproducibility**
   - Cannot replay tasks from audit logs
   - Cannot debug "what was the exact state when this ran?"
   - Cannot prove task behavior in audits

3. **Loss of Safety Guarantees**
   - Planning phase may accidentally execute
   - Chat may bypass approval workflows
   - Unfrozen specs may be executed and modified mid-run

4. **Loss of System Integrity**
   - State machine bypassed
   - Database constraints violated
   - System behavior becomes unpredictable

#### Operational Consequences

1. **Production Incidents**
   - Accidental execution during planning
   - Unauthorized operations executed
   - Data corruption from unstable specs

2. **Security Vulnerabilities**
   - Chat-initiated execution without approval
   - Side-effects without proper authorization
   - Audit trail gaps enable attacks

3. **Compliance Failures**
   - Cannot prove execution chain of custody
   - Cannot demonstrate spec immutability
   - Cannot answer regulatory inquiries

#### Business Consequences

1. **Customer Trust Loss**
   - System behaves unpredictably
   - Cannot guarantee safety
   - Cannot provide audit proof

2. **Support Burden**
   - Cannot debug issues without proper audit trail
   - Cannot reproduce customer problems
   - Cannot provide reliable root cause analysis

3. **Development Velocity Loss**
   - Technical debt accumulates
   - Workarounds breed more workarounds
   - System becomes unmaintainable

### Why These Consequences Are Severe

These are not "nice to have" features - they are **fundamental safety properties**:

- **Auditability** is required for compliance (SOC2, ISO27001, etc.)
- **Reproducibility** is required for debugging and incident response
- **Safety** is required for production systems
- **Integrity** is required for trust

Breaking any of these boundaries breaks ALL of them, because they are **interconnected safety properties**.

---

## Implementation Status

### Boundary #1: Chat ≠ Execution

**Status**: ✅ **COMPLETE** (Task #1)

**Implementation**:
- Error class: `ChatExecutionForbiddenError` defined
- Executor check: `caller_source` parameter validation
- Pipeline integration: `caller_source="task_runner"` passed
- Test coverage: 7/7 tests passing

**Files**:
- `agentos/core/task/errors.py` - Error definition
- `agentos/core/executor/executor_engine.py` - Enforcement
- `agentos/core/mode/pipeline_runner.py` - Integration
- `tests/integration/task/test_chat_execution_gate_simple.py` - Tests

### Boundary #2: Planning = Zero Side-Effect

**Status**: ✅ **COMPLETE** (Task #3)

**Implementation**:
- Error class: `PlanningSideEffectForbiddenError` defined
- Planning guard: Full side-effect prevention module
- Executor integration: Planning guard checks before operations
- Test coverage: 34/34 tests passing (100%)

**Files**:
- `agentos/core/task/errors.py` - Error definition
- `agentos/core/task/planning_guard.py` - Core module
- `agentos/core/executor/executor_engine.py` - Integration
- `agentos/core/capabilities/tool_executor.py` - Integration
- `tests/unit/task/test_planning_guard.py` - Unit tests (25)
- `tests/integration/task/test_planning_guard_e2e.py` - E2E tests (9)

### Boundary #3: Execution Requires Frozen Spec

**Status**: ✅ **COMPLETE** (Task #4)

**Implementation**:
- Error class: `SpecNotFrozenError` defined
- Task model: `spec_frozen` field and `is_spec_frozen()` method
- Database: spec_frozen column with trigger enforcement
- Executor validation: spec_frozen check before execution
- Test coverage: 4/4 tests passing

**Files**:
- `agentos/core/task/errors.py` - Error definition
- `agentos/core/task/models.py` - Task model enhancement
- `agentos/core/task/manager.py` - Database loading
- `agentos/core/executor/executor_engine.py` - Validation
- `agentos/store/migrations/schema_v31_project_aware.sql` - Schema
- `tests/integration/task/test_spec_frozen_simple.py` - Tests

---

## Known Limitations (v0.6.0)

This section documents the actual enforcement strength of each boundary in v0.6.0, based on comprehensive penetration testing (Task #8). These are not technical debt or compromises - they represent the current phased implementation of a security-in-depth strategy.

### Boundary #1: Chat → Execution Gate

**Enforcement Level**: ✅ **SYSTEM-LEVEL HARD GATE**

**System-level Enforcement**: ✅ YES

**Status**: PRODUCTION-READY

**Current Implementation**:
- Hard gate at `ExecutorEngine.execute()` with `caller_source` parameter validation
- `ChatExecutionForbiddenError` raised on violation attempts
- All execution paths require `caller_source="task_runner"` to proceed
- 100% penetration test pass rate (3/3 attacks blocked)

**Verification**:
```python
# Test: tests/integration/task/test_chat_execution_gate_simple.py
# Result: 7/7 tests passing
```

**Minor Improvements (Non-Blocking)**:
- Make `caller_source` parameter required with explicit whitelist (currently warns on "unknown")
- Consider call stack inspection for defense-in-depth

**References**:
- Penetration test: `BOUNDARY_PENETRATION_TEST_REPORT.md` (Boundary #1)
- Vulnerabilities: B1-M1 (Medium), B1-L1 (Low) - neither critical
- Verdict: ✅ SECURE - Boundary holds under attack

---

### Boundary #2: Planning Side-Effect Prevention

**Enforcement Level**: ⚠️ **CONVENTION + GUARD (Requires Explicit Calls)**

**System-level Enforcement**: ❌ NO (planned for v0.6.1)

**Status**: REQUIRES DEVELOPER DISCIPLINE

**Current Implementation**:
- `PlanningGuard` module provides side-effect checking
- `PlanningSideEffectForbiddenError` raised when guard is called
- Correctly blocks shell, file_write, git, network operations
- 100% test pass rate when guard is properly invoked (34/34 tests)

**Limitation**:
The planning guard **must be explicitly called** by application code. Direct calls to `subprocess.run()`, file I/O, or network APIs can bypass the guard if developers forget to invoke it. This is not a bug - it's an architectural constraint of Python's dynamic runtime.

**Current Architecture**:
```
Application Code ──can call──> subprocess.run()  ✅ Executes
       │                       (no automatic interception)
       │
       │ (must remember to call)
       ▼
PlanningGuard ──raises──> PlanningSideEffectForbiddenError
                          (only when explicitly invoked)
```

**Protection Mechanism**:
- Code review checklist verifies guard usage
- Static analysis detects unguarded side effects (recommended)
- Integration tests validate guard integration
- Documentation mandates guard usage in all execution paths

**Upgrade Path (v0.6.1)**:
- Import hooks to auto-wrap subprocess/file/network operations
- Runtime monitoring with `sys.settrace()` for side-effect detection
- OS-level sandbox enforcement (containers with read-only filesystem)
- AST-based static analysis integrated into CI/CD

**Why Not Implemented in v0.6.0?**:
Auto-enforcement requires deep Python runtime integration (import hooks, sys.settrace, or OS-level sandboxing). v0.6.0 establishes the architectural principle and guard interface. v0.6.1 adds automatic enforcement mechanisms.

**References**:
- Penetration test: `BOUNDARY_PENETRATION_TEST_REPORT.md` (Boundary #2)
- Critical vulnerability: **B2-C1** - "Planning guard not automatically enforced"
- Additional issues: B2-M1 (Medium), B2-M2 (Medium)
- Verdict: 🚨 VULNERABLE - Can be bypassed by not calling guard

**Current Mitigation**:
1. Mandatory code review checklist (enforce guard usage)
2. Grep-based checks: `grep -r "subprocess.run\|os.system" | grep -v "planning_guard"`
3. Test coverage validates guard integration in critical paths
4. Documentation clearly states guard must be called before side effects

---

### Boundary #3: Frozen Spec Validation

**Enforcement Level**: ⚠️ **FLAG-BASED (No Cryptographic Guarantee)**

**Cryptographic Guarantee**: ❌ NO (planned for v0.6.1)

**Status**: FLAG ENFORCED, CONTENT NOT VERIFIED

**Current Implementation**:
- Database column `spec_frozen` (0=unfrozen, 1=frozen)
- Database trigger prevents state transitions to READY+ without `spec_frozen=1`
- `SpecNotFrozenError` raised by executor if `spec_frozen=0`
- Task model provides `is_spec_frozen()` validation method
- 100% test pass rate for flag-based checks (4/4 tests)

**Limitation**:
The `spec_frozen` flag does **not cryptographically enforce immutability**. It's a database flag that can be:
1. Modified directly via SQL UPDATE (bypasses workflow validation)
2. Set to 1 without actually freezing content
3. Changed while spec content is also modified (no content hash verification)

**Current Schema**:
```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    spec_frozen INTEGER DEFAULT 0,
    metadata TEXT,  -- Contains spec content
    ...
);
-- ⚠️  No spec_hash column
-- ⚠️  No constraint linking spec_frozen to metadata immutability
```

**What v0.6.0 Guarantees**:
- Executor checks `spec_frozen=1` before execution
- Database trigger prevents unfrozen tasks from entering READY+ states
- Task service APIs respect frozen flag

**What v0.6.0 Does NOT Guarantee**:
- Spec content cannot be modified after freezing (no hash validation)
- Flag cannot be tampered with via direct DB access
- No cryptographic proof of what was frozen

**Upgrade Path (v0.6.1)**:
```sql
-- Add cryptographic verification column
ALTER TABLE tasks ADD COLUMN spec_hash TEXT;

-- Trigger prevents spec modification when frozen
CREATE TRIGGER prevent_spec_modification_when_frozen
BEFORE UPDATE OF metadata ON tasks
FOR EACH ROW
WHEN NEW.spec_frozen = 1
BEGIN
    SELECT CASE
        WHEN NEW.metadata != OLD.metadata THEN
            RAISE(ABORT, 'Cannot modify spec content when spec_frozen = 1')
    END;
END;
```

```python
# Compute SHA-256 hash when freezing
import hashlib, json

def freeze_spec(task_id: str, spec: dict):
    spec_json = json.dumps(spec, sort_keys=True)
    spec_hash = hashlib.sha256(spec_json.encode()).hexdigest()

    cursor.execute(
        "UPDATE tasks SET spec_frozen = 1, spec_hash = ? WHERE task_id = ?",
        (spec_hash, task_id)
    )

# Verify hash before execution
def execute(self, execution_request):
    task = self.task_manager.get_task(task_id)

    # v0.6.0: Check flag
    if not task.is_spec_frozen():
        raise SpecNotFrozenError(...)

    # v0.6.1: Verify hash
    current_hash = compute_spec_hash(task.metadata.get("spec"))
    if current_hash != task.spec_hash:
        raise SpecModifiedAfterFreezeError(...)
```

**Why Not Implemented in v0.6.0?**:
Cryptographic verification requires schema migration, hash computation at freeze time, and verification at execution time. v0.6.0 establishes the flag-based constraint and workflow integration. v0.6.1 adds cryptographic immutability proof.

**References**:
- Penetration test: `BOUNDARY_PENETRATION_TEST_REPORT.md` (Boundary #3)
- Critical vulnerabilities:
  - **B3-C1** - "Direct database modification bypasses validation"
  - **B3-C2** - "No verification of spec content immutability"
- Additional issues: B3-M1 (Medium), B3-M2 (Medium), B3-L1 (Low), B3-L2 (Low)
- Verdict: 🚨 VULNERABLE - Flag can be bypassed via direct DB access

**Current Mitigation**:
1. Executor always reloads task from database (prevents in-memory forgery)
2. Database trigger enforces `spec_frozen=1` for READY+ states
3. Task service APIs provide proper freezing workflow
4. Code review verifies proper freeze/execute flow
5. Database access controls limit direct SQL modification

---

### Engineering Transparency

These limitations are not "technical debt" or "compromises" - they represent **phased security implementation**:

**v0.6.0 Delivers**:
- ✅ Architectural boundaries defined and documented
- ✅ API contracts established (error classes, guard interface)
- ✅ Workflow integration complete (task states, executor checks)
- ✅ Test coverage comprehensive (45 tests passing)
- ✅ One boundary fully enforced at system level (Boundary #1)

**v0.6.1 Will Add**:
- 🔄 Automatic enforcement for Boundary #2 (import hooks, syscall interception)
- 🔄 Cryptographic verification for Boundary #3 (spec_hash column, SHA-256)
- 🔄 Runtime monitoring and alerting
- 🔄 Static analysis integrated into CI/CD

**Design Principle**:
Establish architectural boundaries first, then strengthen enforcement mechanisms iteratively. v0.6.0 creates the "fence posts" - v0.6.1 adds "barbed wire" and "motion sensors".

**Honest Assessment**:
- Boundary #1: Production-ready ✅
- Boundary #2: Requires code review discipline ⚠️
- Boundary #3: Provides workflow enforcement, not cryptographic proof ⚠️

This is transparent engineering: we document what works, what has limitations, and exactly how we'll address them. These are not excuses - they're roadmap clarity.

---

## Enforcement Verification

### How to Verify Boundaries Are Enforced

#### Automated Verification

Run these commands to verify boundaries are enforced:

```bash
# Boundary #1: Chat ≠ Execution
python3 -m pytest tests/integration/task/test_chat_execution_gate_simple.py -v

# Boundary #2: Planning = Zero Side-Effect
python3 -m pytest tests/unit/task/test_planning_guard.py -v
python3 -m pytest tests/integration/task/test_planning_guard_e2e.py -v

# Boundary #3: Execution Requires Frozen Spec
python3 -m pytest tests/integration/task/test_spec_frozen_simple.py -v
```

**Expected**: All tests should pass (45 total tests)

#### Manual Verification

**Verify Boundary #1**:
```python
from agentos.core.executor.executor_engine import ExecutorEngine
from agentos.core.task.errors import ChatExecutionForbiddenError

executor = ExecutorEngine(...)
try:
    executor.execute(
        execution_request={"task_id": "test"},
        caller_source="chat"
    )
    assert False, "Should have raised ChatExecutionForbiddenError"
except ChatExecutionForbiddenError:
    print("✅ Boundary #1 enforced")
```

**Verify Boundary #2**:
```python
from agentos.core.task.planning_guard import planning_guard
from agentos.core.task.errors import PlanningSideEffectForbiddenError
from agentos.core.task.models import Task

task = Task(task_id="test", title="test", status="draft")
try:
    planning_guard.assert_operation_allowed(
        operation_type="shell",
        operation_name="subprocess.run",
        task=task
    )
    assert False, "Should have raised PlanningSideEffectForbiddenError"
except PlanningSideEffectForbiddenError:
    print("✅ Boundary #2 enforced")
```

**Verify Boundary #3**:
```python
from agentos.core.task.models import Task

task = Task(task_id="test", title="test", spec_frozen=0)
assert not task.is_spec_frozen(), "spec_frozen=0 should return False"

task.spec_frozen = 1
assert task.is_spec_frozen(), "spec_frozen=1 should return True"
print("✅ Boundary #3 enforced")
```

### Audit Log Verification

Check audit logs for boundary enforcement:

```bash
# Check for boundary enforcement events
grep -r "enforcement.*boundary" store/runs/*/run_tape.jsonl
grep -r "ChatExecutionForbiddenError" store/runs/*/run_tape.jsonl
grep -r "PlanningSideEffectForbiddenError" store/runs/*/run_tape.jsonl
grep -r "SpecNotFrozenError" store/runs/*/run_tape.jsonl
```

**Expected**: Boundary violations should be logged with enforcement tags

---

## Related Documentation

### Core Architecture Documents

- **ADR-V04: Project-Aware Task Operating System** - Establishes project-task binding and state machine
  - Location: `docs/architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md`
  - Relevance: Defines the state machine that Boundary #3 enforces

- **Version Completeness Matrix** - Documents version progression and constraints
  - Location: `docs/VERSION_COMPLETENESS_MATRIX.md`
  - Relevance: Records v0.6 completion status including these boundaries

- **Validation Layers Architecture** - Defines validation layer separation
  - Location: `docs/architecture/VALIDATION_LAYERS.md`
  - Relevance: Context for planning vs execution separation

### Implementation Documents

- **Task #1 Acceptance Report** - Chat → Execution hard gate
  - Location: `TASK_1_ACCEPTANCE_REPORT.md`
  - Relevance: Complete implementation details for Boundary #1

- **Task #1 Quick Reference** - Chat → Execution usage guide
  - Location: `TASK_1_QUICK_REFERENCE.md`
  - Relevance: Quick usage examples for Boundary #1

- **Task #3 Acceptance Report** - Planning side-effect prevention
  - Location: `TASK_3_ACCEPTANCE_REPORT.md`
  - Relevance: Complete implementation details for Boundary #2

- **Task #4 Acceptance Report** - Execution frozen plan validation
  - Location: `TASK_4_ACCEPTANCE_REPORT.md`
  - Relevance: Complete implementation details for Boundary #3

### Code References

- **Error Definitions**: `agentos/core/task/errors.py`
- **Planning Guard**: `agentos/core/task/planning_guard.py`
- **Task Model**: `agentos/core/task/models.py`
- **Executor Engine**: `agentos/core/executor/executor_engine.py`
- **Database Schema**: `agentos/store/migrations/schema_v31_project_aware.sql`

---

## Approval and Sign-off

This ADR establishes **IRON LAW** constraints that are non-negotiable. All team members must understand and respect these boundaries.

### Acknowledgment Required

All contributors MUST acknowledge understanding of these boundaries:

- [ ] I understand that these boundaries are FROZEN and cannot be bypassed
- [ ] I understand that PRs violating these boundaries will be BLOCKED
- [ ] I understand the consequences of breaking these boundaries
- [ ] I commit to enforcing these boundaries in code reviews
- [ ] I commit to updating this document if architectural changes are needed

### Change Process

To modify these boundaries requires:

1. **Architecture Review**: Full team review of proposed changes
2. **Impact Analysis**: Document all affected systems and downstream consequences
3. **Alternative Analysis**: Prove no other solution exists
4. **Migration Plan**: Complete migration plan for existing code
5. **Test Update**: Update all tests to reflect new boundaries
6. **Documentation Update**: Update all documentation
7. **Approval**: Unanimous approval from architecture team

**Timeline**: Minimum 2 weeks for review and approval process

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-01-30 | Initial FREEZE document created | AgentOS Core Team |

---

## Summary

This document establishes **THREE IRON LAW EXECUTION BOUNDARIES** that are fundamental to AgentOS v0.6 architecture:

1. **Boundary #1: Chat ≠ Execution** - Chat cannot directly execute, must create tasks
2. **Boundary #2: Planning = Zero Side-Effect** - Planning phase forbids all side-effects
3. **Boundary #3: Execution Requires Frozen Spec** - Only frozen specs can be executed

**These boundaries are FROZEN and cannot be compromised.**

**Any PR that violates these boundaries MUST be BLOCKED.**

These are not design preferences - they are **architectural constraints** that ensure:
- Audit trail integrity
- Reproducibility
- Safety guarantees
- System integrity

Breaking any of these boundaries breaks ALL of them, because they are interconnected safety properties.

---

**Status**: FROZEN
**Review Cycle**: Requires full architecture review to modify
**Next Review**: v0.7.0 planning phase (if changes proposed)
**Last Updated**: 2026-01-30
