# A2 project_id Decision - Quick Summary

**Decision Date**: 2026-01-30
**Decision ID**: A2-FREEZE-2026-01-30
**Status**: ✅ PASS (Changed from PARTIAL)

---

## TL;DR

The `project_id` field in tasks follows **state-based nullability**:

```
✅ DRAFT:  project_id CAN be NULL
✅ READY+: project_id MUST NOT be NULL
```

**This is not incomplete - it's intentional design.**

---

## Quick Facts

| Aspect | Decision |
|--------|----------|
| **Rule** | State-dependent nullability |
| **DRAFT state** | NULL allowed (work-in-progress) |
| **READY+ states** | NULL forbidden (execution-ready) |
| **Enforcement** | 4 layers (DB, Service, API, UI) |
| **Test Coverage** | ✅ Comprehensive |
| **Technical Debt** | ❌ No - working as designed |

---

## Why PASS Not PARTIAL?

1. **Complete Enforcement**: 4-layer validation (database trigger, service guard, API validation, UI prevention)
2. **Tested**: Full test coverage including constraint violation tests
3. **Documented**: ADR-V04, V04_CONSTRAINTS_AND_GATES.md
4. **Intentional**: Supports draft-first workflow without UX friction
5. **Consistent**: Follows state machine semantics (draft = mutable, ready+ = immutable)

---

## Where to Look

| Document | Purpose |
|----------|---------|
| [VERSION_COMPLETENESS_MATRIX.md](../VERSION_COMPLETENESS_MATRIX.md) | Full architectural decision record |
| [ADR_V04_PROJECT_AWARE_TASK_OS.md](../architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md) | Original design specification |
| [V04_CONSTRAINTS_AND_GATES.md](../V04_CONSTRAINTS_AND_GATES.md) | Implementation constraints |

---

## Code References

**Enforcement locations**:
- Database trigger: `agentos/store/migrations/schema_v31_project_aware.sql`
- Service guard: `agentos/core/task/service.py` (transition method)
- State machine: `agentos/core/task/state_machine.py`
- API validation: `agentos/webui/api/tasks.py`

**Test coverage**:
- `tests/unit/test_v04_constraints.py::test_constraint_1_task_project_binding`

---

## For Future Reviewers

If someone questions "Why can project_id be NULL?":

**Answer**: It's NULL only in DRAFT state, by design. The state machine enforces non-NULL before execution (READY state). This allows users to draft task ideas before committing to a project context.

**Not a bug. Not technical debt. Working as intended.**

---

**Last Updated**: 2026-01-30
**Maintained by**: AgentOS Architecture Team
