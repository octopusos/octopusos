# Execution Boundaries - Quick Reference

**Full ADR**: [docs/architecture/ADR_EXECUTION_BOUNDARIES_FREEZE.md](docs/architecture/ADR_EXECUTION_BOUNDARIES_FREEZE.md)

**Status**: 🔒 FROZEN - Non-negotiable architecture constraints

---

## The Three Iron Law Boundaries

### Boundary #1: Chat ≠ Execution

```
chat → ❌ direct execution (FORBIDDEN)
chat → ✅ create Task (DRAFT state) → task runner → execution
```

**Error**: `ChatExecutionForbiddenError`

**Implementation**: `executor_engine.py` checks `caller_source` parameter

**Tests**: `tests/integration/task/test_chat_execution_gate_simple.py` (7/7 passing)

### Boundary #2: Planning = Zero Side-Effect

```
Planning Phase (DRAFT/APPROVED):
  ❌ shell, file writes, git, network
  ✅ file reads, computation, specs

Implementation Phase (RUNNING):
  ✅ ALL operations allowed
```

**Error**: `PlanningSideEffectForbiddenError`

**Implementation**: `planning_guard.py` enforces side-effect prevention

**Tests**: 34/34 tests passing (100%)

### Boundary #3: Execution Requires Frozen Spec

```
spec_frozen = 0 → ❌ execution blocked
spec_frozen = 1 → ✅ execution allowed
```

**Error**: `SpecNotFrozenError`

**Implementation**: `executor_engine.py` checks `task.is_spec_frozen()`

**Tests**: `tests/integration/task/test_spec_frozen_simple.py` (4/4 passing)

---

## PR Review Checklist (Quick)

**Boundary #1 Checks**:
```bash
# No chat calling executor directly
grep -r "ExecutorEngine" agentos/core/chat/

# All executor calls have caller_source
grep -r "executor.execute" | grep -v "caller_source="
```

**Boundary #2 Checks**:
```bash
# No subprocess without planning guard
grep -r "subprocess.run\|os.system" agentos/core/ | grep -v "planning_guard"

# Planning guard integrated
grep -r "assert_operation_allowed" agentos/core/
```

**Boundary #3 Checks**:
```bash
# Executor checks spec_frozen
grep -B 10 "executor.execute" | grep "is_spec_frozen"

# Task model has spec_frozen
grep "spec_frozen" agentos/core/task/models.py
```

---

## Violations = PR BLOCKED

**NO EXCEPTIONS** - Not for:
- Emergency situations
- Temporary workarounds
- Testing convenience
- Performance optimizations

---

## Key Files

**Error Definitions**: `agentos/core/task/errors.py`
- ChatExecutionForbiddenError
- PlanningSideEffectForbiddenError
- SpecNotFrozenError

**Enforcement Modules**:
- `agentos/core/executor/executor_engine.py` (all 3 boundaries)
- `agentos/core/task/planning_guard.py` (boundary #2)
- `agentos/core/task/models.py` (boundary #3)

**Test Suites**:
- `tests/integration/task/test_chat_execution_gate_simple.py` (7 tests)
- `tests/unit/task/test_planning_guard.py` (25 tests)
- `tests/integration/task/test_planning_guard_e2e.py` (9 tests)
- `tests/integration/task/test_spec_frozen_simple.py` (4 tests)

**Total**: 45 tests, all passing

---

## Verification Commands

```bash
# Run all boundary tests
python3 -m pytest tests/integration/task/test_chat_execution_gate_simple.py -v
python3 -m pytest tests/unit/task/test_planning_guard.py -v
python3 -m pytest tests/integration/task/test_planning_guard_e2e.py -v
python3 -m pytest tests/integration/task/test_spec_frozen_simple.py -v

# Check audit logs for violations
grep -r "ChatExecutionForbiddenError\|PlanningSideEffectForbiddenError\|SpecNotFrozenError" store/runs/
```

---

## References

**Full Documentation**: [ADR_EXECUTION_BOUNDARIES_FREEZE.md](docs/architecture/ADR_EXECUTION_BOUNDARIES_FREEZE.md)

**Implementation Reports**:
- Task #1: [TASK_1_ACCEPTANCE_REPORT.md](TASK_1_ACCEPTANCE_REPORT.md)
- Task #3: [TASK_3_ACCEPTANCE_REPORT.md](TASK_3_ACCEPTANCE_REPORT.md)
- Task #4: [TASK_4_ACCEPTANCE_REPORT.md](TASK_4_ACCEPTANCE_REPORT.md)

**Version Matrix**: [docs/VERSION_COMPLETENESS_MATRIX.md](docs/VERSION_COMPLETENESS_MATRIX.md)

---

**Last Updated**: 2026-01-30
**Status**: FROZEN
