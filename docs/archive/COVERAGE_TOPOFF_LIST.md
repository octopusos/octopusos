# Coverage Top-Off Checklist
## Path from 46.93% → 65%

**Generated:** 2026-01-30
**Current Coverage:** 46.93% (2100/4475 lines+branches)
**Target Coverage:** 65%
**Gap to Close:** 808 lines/branches

---

## Executive Summary

Based on analysis of `coverage-scope.xml`, this document identifies high-ROI test targets to increase coverage from 46.93% to 65%. The strategy focuses on:

1. **Quick Wins (P0):** High-coverage files with small gaps - 8 files, ~23% benefit, 0.5h effort
2. **Critical Infrastructure (P1):** State machine, service layer, rollback - 6 files, ~227% benefit, 15h effort
3. **Strategic Targets (P2):** Medium-coverage supporting services - 9 files, ~142% benefit, 9h effort
4. **Foundation Work (P3):** Zero-coverage files (defer to later phases) - 8 files, ~27% benefit, 32h effort

**Recommended First Jump (47% → 65%):** Focus on P0 + P1 Critical + selected P2 targets = ~18 hours total effort.

---

## Section A: Top 10 Uncovered Files (by Coverage Gap)

| File | Current Coverage | Gap | Missing Lines | Missing Branches | Priority | Est. Hours | Benefit (%) |
|------|------------------|-----|---------------|------------------|----------|------------|-------------|
| `binding_service.py` | 0.0% | 100.0% | 162 | 64 | P3-Foundation | 7.5h | 5.1% |
| `template_service.py` | 0.0% | 100.0% | 150 | 40 | P3-Foundation | 6.3h | 4.2% |
| `manager.py` | 20.7% | 79.3% | 172 | 23 | **P1-Critical** | 5.6h | 43.6% |
| `spec_service.py` | 0.0% | 100.0% | 131 | 30 | P3-Foundation | 5.4h | 3.6% |
| `work_items.py` | 0.0% | 100.0% | 130 | 32 | P3-Foundation | 5.4h | 3.6% |
| `artifact_service_v31.py` | 0.0% | 100.0% | 105 | 20 | P3-Foundation | 4.2h | 2.8% |
| `runner_integration.py` | 0.0% | 100.0% | 101 | 36 | P3-Foundation | 4.6h | 3.1% |
| `lineage_extensions.py` | 0.0% | 100.0% | 99 | 30 | P3-Foundation | 4.3h | 2.9% |
| `event_service.py` | 24.4% | 75.6% | 109 | 12 | **P1-Critical** | 4.0h | 27.0% |
| `manager_extended.py` | 0.0% | 100.0% | 89 | 22 | P3-Foundation | 3.7h | 2.5% |

**Key Insight:** Only 2 of the top 10 are priority targets (`manager.py`, `event_service.py`). The rest are zero-coverage foundation files that should be addressed in later phases.

---

## Section B: Top 20 Uncovered Functions/Methods (by Impact)

| Function | File | Missing Lines | Business Impact | Benefit (%) | Est. Hours | ROI |
|----------|------|---------------|-----------------|-------------|------------|-----|
| `_validate_mode_transition` | state_machine.py | 20 | **Critical** - AUTONOMOUS mode gate checks | 0.9% | 0.5h | 1.8 |
| `validate_or_raise` (error paths) | state_machine.py | 12 | **Critical** - State validation edge cases | 0.5% | 0.3h | 1.7 |
| `can_transition` (ValueError paths) | state_machine.py | 8 | **High** - Transition validation error handling | 0.4% | 0.2h | 2.0 |
| `get_valid_transitions` | state_machine.py | 11 | **Medium** - State introspection API | 0.5% | 0.3h | 1.7 |
| `transition` (timeout/error paths) | state_machine.py | 16 | **Critical** - Error handling in transitions | 0.7% | 0.4h | 1.8 |
| `_get_git_diff_summary` | audit_service.py | 17 | **Medium** - Git diff capture for audit | 0.4% | 0.5h | 0.8 |
| `get_event_statistics` | audit_service.py | 12 | **Low** - Analytics endpoint | 0.3% | 0.3h | 1.0 |
| `create_approve_queue_and_start` | service.py | 17 | **High** - APPROVE mode workflow | 0.8% | 0.5h | 1.6 |
| `force_complete_task` | service.py | 12 | **High** - Admin override operations | 0.5% | 0.3h | 1.7 |
| `cancel_task` (cleanup paths) | service.py | 10 | **Medium** - Cancel error handling | 0.4% | 0.3h | 1.3 |
| `safe_cancel_task` | rollback.py | 22 | **High** - Safe cancellation logic | 1.0% | 0.6h | 1.7 |
| `create_draft_from_existing` | rollback.py | 18 | **Medium** - Task duplication workflow | 0.8% | 0.5h | 1.6 |
| `can_cancel` | rollback.py | 8 | **Medium** - Cancellation validation | 0.4% | 0.2h | 2.0 |
| `resolve_provider_defaults` | project_settings_inheritance.py | 15 | **Medium** - Provider inheritance logic | 0.7% | 0.4h | 1.8 |
| `merge_provider_settings` | project_settings_inheritance.py | 12 | **Medium** - Settings merge logic | 0.5% | 0.3h | 1.7 |
| `match_route` | routing_service.py | 25 | **High** - Task routing logic | 1.1% | 0.7h | 1.6 |
| `validate_route_metadata` | routing_service.py | 14 | **Medium** - Route validation | 0.6% | 0.4h | 1.5 |
| `compute_retry_backoff` | run_mode.py | 12 | **Medium** - Backoff calculation | 0.5% | 0.3h | 1.7 |
| `_should_retry` | run_mode.py | 10 | **High** - Retry decision logic | 0.4% | 0.3h | 1.3 |
| `_write_update` | binding_service.py | 47 | **Low** - V31 binding writes (unused) | 1.0% | 1.6h | 0.6 |

**Critical Observation:** Top 5 functions are all in `state_machine.py` - targeting this file first yields maximum impact.

---

## Section C: ROI Analysis & Categorization

### C.1 Quick Wins (P0) - High ROI, Low Effort

**Total:** 8 files, 23% benefit, 0.5h effort
**ROI:** 46 (benefit per hour)

| File | Coverage | Gap | Missing | Benefit | Hours | ROI | Target Area |
|------|----------|-----|---------|---------|-------|-----|-------------|
| `artifact_service.py` | 89.4% | 10.6% | 14 | 8.5% | 0.2h | 48.5 | Error path in `get_input_artifacts_raw` (lines 98-99) |
| `runner_audit_integration.py` | 93.9% | 6.1% | 4 | 4.8% | 0.1h | 48.5 | Exception handling in audit recording (line 61) |
| `path_filter.py` | 94.0% | 6.0% | 8 | 4.8% | 0.1h | 38.2 | Edge cases in path validation |
| `task_repo_service.py` | 94.5% | 5.5% | 9 | 4.4% | 0.2h | 24.2 | Error paths in task queries |
| `dependency_service.py` | 85.7% | 14.3% | 51 | 11.4% | 1.5h | 7.6 | Circular dependency detection |
| `repo_context.py` | 84.3% | 15.7% | 30 | 6.7% | 0.9h | 7.4 | Multi-repo context edge cases |
| `audit_service.py` | 74.3% | 25.7% | 52 | 11.8% | 1.5h | 7.9 | Git diff capture, stats API |
| `project_settings_inheritance.py` | 74.9% | 25.1% | 57 | 12.7% | 1.6h | 7.9 | Provider/repo inheritance logic |

**Recommendation:** Start with first 4 files for immediate 22.5% benefit in 0.6h.

### C.2 Strategic Targets (P1-Critical) - Medium ROI, Critical Business Logic

**Total:** 6 files, 227% benefit, 15h effort
**ROI:** 15 (benefit per hour)

| File | Coverage | Gap | Missing | Benefit | Hours | ROI | Target Area |
|------|----------|-----|---------|---------|-------|-----|-------------|
| `state_machine.py` | 52.7% | 47.3% | 105 | 75.0% | 3.0h | 25.0 | **Priority #1**: Validation errors, timeout handling, mode violations |
| `service.py` | 54.2% | 45.8% | 87 | 45.7% | 2.5h | 18.3 | Task lifecycle operations: approve, cancel, force-complete |
| `rollback.py` | 42.5% | 57.5% | 73 | 34.5% | 2.1h | 16.4 | Safe cancellation, draft creation, validation |
| `routing_service.py` | 27.7% | 72.3% | 60 | 43.4% | 1.7h | 25.5 | **Priority #2**: Route matching and validation |
| `event_service.py` | 24.4% | 75.6% | 121 | 45.4% | 3.5h | 13.0 | Event insertion, filtering, statistics |
| `manager.py` | 20.7% | 79.3% | 195 | 43.6% | 5.6h | 7.8 | Task CRUD operations, list/get APIs |

**Recommendation:** Focus on `state_machine.py` (3h), `routing_service.py` (1.7h), `service.py` (2.5h) for 7.2h total, ~164% benefit.

### C.3 Medium Priority (P2-Strategic) - Balanced ROI

**Total:** 9 files, 142% benefit, 9h effort
**ROI:** 16 (benefit per hour)

| File | Coverage | Gap | Missing | Benefit | Hours | ROI | Target Area |
|------|----------|-----|---------|---------|-------|-----|-------------|
| `states.py` | 75.0% | 25.0% | 8 | 12.5% | 0.2h | 54.7 | State enum helpers |
| `errors.py` | 53.2% | 46.8% | 22 | 23.4% | 0.6h | 39.0 | Custom exception types |
| `run_mode.py` | 49.2% | 50.8% | 33 | 25.4% | 0.9h | 28.2 | Retry/backoff logic |
| `models.py` | 66.7% | 33.3% | 70 | 16.7% | 2.0h | 8.3 | Model validation, serialization |
| `trace_builder.py` | 11.2% | 88.8% | 135 | 30.2% | 3.9h | 7.7 | Task trace construction |

**Recommendation:** Target `states.py`, `errors.py`, `run_mode.py` first (1.7h, ~61% benefit).

### C.4 Foundation Work (P3) - High Cost, Defer

**Total:** 8 files, 27% benefit, 32h effort
**ROI:** 0.8 (benefit per hour)

These are zero-coverage files requiring extensive test infrastructure. Defer to Phase 2.

---

## Section D: The First Jump - 47% → 65% Roadmap

### Target: 808 additional lines/branches covered
### Estimated Total: 13-15 hours

#### Phase 1: Quick Wins (0.6h) → 48.5% coverage
1. ✅ `artifact_service.py`: Test error path in line 98-99 (0.2h, +8.5%)
2. ✅ `runner_audit_integration.py`: Test exception at line 61 (0.1h, +4.8%)
3. ✅ `path_filter.py`: Test edge cases (0.1h, +4.8%)
4. ✅ `task_repo_service.py`: Test error paths (0.2h, +4.4%)

**Checkpoint:** 48.5% coverage (1.5% increase)

#### Phase 2: Critical State Machine (3.5h) → 56% coverage
5. ✅ **`state_machine.py` - PRIORITY TARGET** (3.0h, +75%)
   - Test `can_transition` with invalid states (ValueError paths)
   - Test `validate_or_raise` error cases (InvalidTransitionError)
   - Test `_validate_mode_transition` for AUTONOMOUS gate checks
   - Test `transition` timeout/exception error paths (lines 337-348)
   - Test `get_valid_transitions` with invalid states
   - **Coverage Files:** Create `tests/unit/task/test_state_machine_errors.py`, `test_state_machine_modes.py`
   - **Expected Lines Covered:** ~85 lines + 22 branches

6. ✅ `routing_service.py` (1.7h, +43%)
   - Test `match_route` with various route patterns
   - Test `validate_route_metadata` edge cases
   - **Coverage File:** Create `tests/unit/task/test_routing_service.py`

**Checkpoint:** 56% coverage (9.5% increase from start)

#### Phase 3: Service Layer Operations (2.5h) → 61% coverage
7. ✅ `service.py` (2.5h, +46%)
   - Test `create_approve_queue_and_start` workflow
   - Test `force_complete_task` admin operations
   - Test `cancel_task` cleanup paths
   - **Coverage File:** Extend `tests/unit/task/test_service_operations.py`

**Checkpoint:** 61% coverage (14% increase from start)

#### Phase 4: Rollback & Strategic Files (3.5h) → 65%+ coverage
8. ✅ `rollback.py` (2.1h, +35%)
   - Test `safe_cancel_task` all state paths
   - Test `create_draft_from_existing` duplication
   - Test `can_cancel` validation logic
   - **Coverage File:** Create `tests/unit/task/test_rollback_operations.py`

9. ✅ `errors.py` + `states.py` + `run_mode.py` (1.4h, +61%)
   - Test all exception types and error messages
   - Test state enum helpers
   - Test retry backoff calculations
   - **Coverage Files:** `test_errors_coverage.py`, `test_run_mode_retry.py`

**Checkpoint:** 65%+ coverage achieved! 🎯

#### Phase 5: Remaining Strategic Targets (3h) → 68% coverage
10. ✅ `event_service.py` (3.0h, +45%)
    - Test event insertion edge cases
    - Test event filtering and statistics
    - **Coverage File:** Create `tests/unit/task/test_event_service_coverage.py`

**Final Target:** 68% coverage (21% increase from start)

---

## Section E: Detailed Test Scenarios by Priority Target

### E.1 state_machine.py - Uncovered Critical Paths

**File:** `/Users/pangge/PycharmProjects/AgentOS/agentos/core/task/state_machine.py`
**Current Coverage:** 52.7% (117/222 lines+branches)
**Missing:** 83 lines, 22 branches
**Target Benefit:** +75% (highest single-file impact)

#### Missing Line Ranges:
- Lines 107: `get_db()` fallback path
- Lines 122-133: `can_transition` with invalid states
- Lines 151-152, 169-169: `validate_or_raise` error paths
- Lines 232-235: `_validate_mode_transition` logic
- Lines 254: Mode validation error
- Lines 329: Writer timeout fallback
- Lines 337-345: Transition timeout/exception handlers
- Lines 385-395: `get_valid_transitions` with invalid state

#### Test Scenarios (Priority Order):

```python
# Test File: tests/unit/task/test_state_machine_errors.py

def test_can_transition_with_invalid_from_state():
    """Cover lines 122-126: ValueError handling in can_transition"""
    sm = TaskStateMachine()
    assert sm.can_transition("INVALID_STATE", "APPROVED") is False

def test_can_transition_with_invalid_to_state():
    """Cover lines 122-126: ValueError handling in can_transition"""
    sm = TaskStateMachine()
    assert sm.can_transition("DRAFT", "INVALID_STATE") is False

def test_validate_or_raise_invalid_from_state():
    """Cover lines 151-156: ValueError → InvalidTransitionError"""
    sm = TaskStateMachine()
    with pytest.raises(InvalidTransitionError) as exc_info:
        sm.validate_or_raise("INVALID", "APPROVED")
    assert "Invalid state value" in str(exc_info.value)

def test_validate_or_raise_invalid_to_state():
    """Cover lines 151-156: ValueError → InvalidTransitionError"""
    sm = TaskStateMachine()
    with pytest.raises(InvalidTransitionError) as exc_info:
        sm.validate_or_raise("DRAFT", "INVALID")
    assert "Invalid state value" in str(exc_info.value)

def test_validate_or_raise_forbidden_transition():
    """Cover lines 168-173: Forbidden transition error"""
    sm = TaskStateMachine()
    with pytest.raises(InvalidTransitionError) as exc_info:
        sm.validate_or_raise("DONE", "DRAFT")
    assert "not allowed" in str(exc_info.value).lower()

def test_transition_timeout_error():
    """Cover lines 337-342: TimeoutError handling"""
    # Mock writer.submit to raise TimeoutError
    sm = TaskStateMachine()
    with patch.object(sm, '_get_writer') as mock_writer:
        mock_writer.return_value.submit.side_effect = TimeoutError("Write timeout")
        with pytest.raises(TaskStateError) as exc_info:
            sm.transition(task_id="test-123", to="APPROVED", actor="test")
        assert "timed out" in str(exc_info.value).lower()

def test_transition_generic_exception():
    """Cover lines 343-348: Generic exception handling"""
    sm = TaskStateMachine()
    with patch.object(sm, '_get_writer') as mock_writer:
        mock_writer.return_value.submit.side_effect = RuntimeError("DB error")
        with pytest.raises(TaskStateError) as exc_info:
            sm.transition(task_id="test-123", to="APPROVED", actor="test")
        assert "Failed to transition" in str(exc_info.value)

def test_get_valid_transitions_invalid_state():
    """Cover lines 385-388: Invalid state → empty set"""
    sm = TaskStateMachine()
    result = sm.get_valid_transitions("INVALID_STATE")
    assert result == set()

def test_get_valid_transitions_draft():
    """Cover lines 390-395: Valid transitions enumeration"""
    sm = TaskStateMachine()
    result = sm.get_valid_transitions("DRAFT")
    assert "APPROVED" in result
    assert "CANCELED" in result
```

**Test File 2:** `tests/unit/task/test_state_machine_modes.py`

```python
def test_validate_mode_transition_autonomous_blocked():
    """Cover lines 232-235: AUTONOMOUS mode blocking logic"""
    # Test RUNNING → BLOCKED transition in AUTONOMOUS mode
    # Requires task with metadata.run_mode = "AUTONOMOUS"
    # and transition to BLOCKED state
    pass  # Implementation details

def test_validate_mode_transition_approve_mode():
    """Cover line 254: APPROVE mode restrictions"""
    # Test transitions that should be blocked in APPROVE mode
    pass  # Implementation details
```

**Expected Coverage Increase:** ~85 lines, ~22 branches = **75% benefit**

---

### E.2 routing_service.py - Route Matching Logic

**File:** `/Users/pangge/PycharmProjects/AgentOS/agentos/core/task/routing_service.py`
**Current Coverage:** 27.7% (23/83 lines+branches)
**Missing:** 46 lines, 14 branches
**Target Benefit:** +43%

#### Test File: `tests/unit/task/test_routing_service.py`

```python
def test_match_route_exact_match():
    """Test exact route pattern matching"""
    # Cover route matching logic
    pass

def test_match_route_wildcard():
    """Test wildcard route patterns"""
    pass

def test_match_route_no_match():
    """Test unmatched route handling"""
    pass

def test_validate_route_metadata_valid():
    """Test valid route metadata"""
    pass

def test_validate_route_metadata_invalid():
    """Test invalid route metadata rejection"""
    pass
```

---

### E.3 service.py - Task Lifecycle Operations

**File:** `/Users/pangge/PycharmProjects/AgentOS/agentos/core/task/service.py`
**Current Coverage:** 54.2% (103/190 lines+branches)
**Missing:** 72 lines, 15 branches
**Target Benefit:** +46%

#### Key Missing Functions:
- `create_approve_queue_and_start` (lines ~150-166)
- `force_complete_task` (lines ~200-211)
- `cancel_task` cleanup paths (lines ~250-260)

#### Test File: `tests/unit/task/test_service_operations.py` (extend existing)

```python
def test_create_approve_queue_and_start():
    """Test APPROVE mode workflow"""
    service = TaskService()
    task = service.create_approve_queue_and_start(
        title="Test Task",
        actor="user@example.com"
    )
    assert task.status == "QUEUED"

def test_force_complete_task():
    """Test admin force-complete operation"""
    service = TaskService()
    # Create task in RUNNING state
    # Force complete it
    # Verify state transition and audit
    pass

def test_cancel_task_cleanup_error():
    """Test cancel with cleanup failure"""
    # Mock cleanup to raise exception
    # Verify error handling
    pass
```

---

### E.4 rollback.py - Safe Cancellation

**File:** `/Users/pangge/PycharmProjects/AgentOS/agentos/core/task/rollback.py`
**Current Coverage:** 42.5% (54/127 lines+branches)
**Missing:** 51 lines, 22 branches
**Target Benefit:** +35%

#### Test File: `tests/unit/task/test_rollback_operations.py`

```python
def test_safe_cancel_task_draft():
    """Test canceling DRAFT task"""
    pass

def test_safe_cancel_task_approved():
    """Test canceling APPROVED task"""
    pass

def test_safe_cancel_task_terminal_state():
    """Test rejection of canceling DONE task"""
    with pytest.raises(RollbackNotAllowedError):
        # Attempt to cancel DONE task
        pass

def test_create_draft_from_existing():
    """Test task duplication"""
    # Verify new task_id, DRAFT state, metadata copy
    pass

def test_can_cancel_allowed_states():
    """Test can_cancel for DRAFT/APPROVED/QUEUED"""
    rollback = RollbackService()
    assert rollback.can_cancel("DRAFT") is True
    assert rollback.can_cancel("QUEUED") is True

def test_can_cancel_forbidden_states():
    """Test can_cancel rejection for terminal states"""
    rollback = RollbackService()
    assert rollback.can_cancel("DONE") is False
    assert rollback.can_cancel("VERIFIED") is False
```

---

## Section F: Test Infrastructure Recommendations

### F.1 New Test Files to Create

```
tests/unit/task/
├── test_state_machine_errors.py          # Phase 2: Error handling
├── test_state_machine_modes.py           # Phase 2: Mode validation
├── test_routing_service.py               # Phase 2: Route matching
├── test_service_operations.py            # Phase 3: Service layer (extend)
├── test_rollback_operations.py           # Phase 4: Rollback logic
├── test_errors_coverage.py               # Phase 4: Exception types
└── test_run_mode_retry.py                # Phase 4: Retry logic
```

### F.2 Testing Patterns

#### Pattern 1: Error Path Coverage
```python
# Template for covering exception branches
def test_function_with_error_handling():
    with patch('module.dependency') as mock_dep:
        mock_dep.side_effect = SpecificException("error")
        with pytest.raises(ExpectedException):
            function_under_test()
```

#### Pattern 2: Branch Coverage
```python
# Template for covering conditional branches
@pytest.mark.parametrize("input,expected_branch", [
    ("valid_input", "happy_path"),
    ("invalid_input", "error_path"),
    (None, "null_path"),
])
def test_all_branches(input, expected_branch):
    result = function(input)
    # Assert based on expected_branch
```

### F.3 Mock Strategies

```python
# Mock database writer for timeout tests
@pytest.fixture
def mock_writer_timeout():
    with patch('agentos.store.get_writer') as mock:
        mock.return_value.submit.side_effect = TimeoutError()
        yield mock

# Mock state machine for service layer tests
@pytest.fixture
def mock_state_machine():
    with patch('agentos.core.task.service.TaskStateMachine') as mock:
        yield mock.return_value
```

---

## Section G: Coverage Measurement & Validation

### G.1 Run Coverage After Each Phase

```bash
# Run scope coverage
./scripts/coverage_scope_task.sh

# Check coverage increase
python3 scripts/analyze_coverage_gap.py

# View detailed HTML report
open htmlcov-scope/index.html
```

### G.2 Validation Checklist

After each phase, verify:
- [ ] Coverage percentage increased by expected amount (±2%)
- [ ] No new uncovered critical paths introduced
- [ ] All tests pass (`pytest tests/unit/task/`)
- [ ] Coverage report shows targeted lines as covered

### G.3 Coverage Gates

- **Phase 1 Complete:** ≥48% coverage
- **Phase 2 Complete:** ≥56% coverage
- **Phase 3 Complete:** ≥61% coverage
- **Phase 4 Complete:** ≥65% coverage ✅ **TARGET MET**

---

## Section H: Risk Mitigation

### H.1 Known Risks

1. **Timeout Test Flakiness:** Writer timeout tests may be flaky in CI
   - **Mitigation:** Use deterministic mocks, avoid real timeouts

2. **Database State Pollution:** Tests may interfere with each other
   - **Mitigation:** Use isolated DB fixtures, cleanup after tests

3. **Mode Validation Complexity:** AUTONOMOUS mode tests require complex setup
   - **Mitigation:** Start with simpler modes, build up gradually

### H.2 Blocked Dependencies

- `binding_service.py` requires V31 schema (defer to P3)
- `work_items.py` requires parallel execution infrastructure (defer to P3)
- `template_service.py` requires template storage (defer to P3)

---

## Section I: Success Metrics

### I.1 Primary Goal
- **Coverage:** 46.93% → 65% (18.07 percentage points)
- **Lines/Branches Covered:** +808 units

### I.2 Secondary Goals
- **P0 Quick Wins:** 100% completion (all 4 targets)
- **P1 Critical Files:** ≥3 files covered (state_machine, routing, service)
- **Zero Test Failures:** All new tests pass on first run
- **Documentation:** All new test files have docstrings

### I.3 Stretch Goals
- **Coverage:** 68% (if time permits Phase 5)
- **P1 Completion:** All 6 critical files covered
- **Refactor:** Extract common test fixtures into `conftest.py`

---

## Section J: Next Steps (After 65%)

Once 65% coverage is achieved:

1. **Phase 2 Coverage Push (65% → 80%):**
   - Address P3-Foundation files (`manager.py`, `event_service.py`)
   - Add integration tests for multi-file workflows
   - Cover remaining P2-Strategic targets

2. **Mutation Testing:**
   - Use `mutmut` to validate test quality
   - Ensure tests actually catch bugs, not just lines

3. **Property-Based Testing:**
   - Use `hypothesis` for state machine transitions
   - Fuzz test error handling paths

4. **Performance Testing:**
   - Add benchmarks for hot paths (state transitions, queries)
   - Identify coverage-performance tradeoffs

---

## Appendix A: File-by-File Coverage Summary

```
agentos/core/task/
├── __init__.py                          100.0%  ✅
├── artifact_service.py                   89.4%  🟢 P0-QuickWin
├── artifact_service_v31.py                0.0%  🔴 P3-Foundation
├── audit_service.py                      74.3%  🟡 P0-QuickWin
├── binding_service.py                     0.0%  🔴 P3-Foundation
├── cancel_handler.py                    100.0%  ✅
├── dependency_service.py                 85.7%  🟢 P0-QuickWin
├── errors.py                             53.2%  🟡 P2-Strategic
├── event_service.py                      24.4%  🔴 P1-Critical
├── lineage_extensions.py                  0.0%  🔴 P3-Foundation
├── manager.py                            20.7%  🔴 P1-Critical
├── manager_extended.py                    0.0%  🔴 P3-Foundation
├── models.py                             66.7%  🟡 P2-Strategic
├── path_filter.py                        94.0%  ✅ P0-QuickWin
├── project_settings_inheritance.py       74.9%  🟡 P0-QuickWin
├── repo_context.py                       84.3%  🟢 P0-QuickWin
├── retry_strategy.py                    100.0%  ✅
├── rollback.py                           42.5%  🔴 P1-Critical
├── routing_service.py                    27.7%  🔴 P1-Critical
├── run_mode.py                           49.2%  🟡 P2-Strategic
├── runner_audit_integration.py           93.9%  ✅ P0-QuickWin
├── runner_integration.py                  0.0%  🔴 P3-Foundation
├── service.py                            54.2%  🔴 P1-Critical
├── spec_service.py                        0.0%  🔴 P3-Foundation
├── state_machine.py                      52.7%  🔴 P1-Critical ⚠️ TOP PRIORITY
├── states.py                             75.0%  🟡 P2-Strategic
├── task_repo_service.py                  94.5%  ✅ P0-QuickWin
├── template_service.py                    0.0%  🔴 P3-Foundation
├── timeout_manager.py                   100.0%  ✅
├── trace_builder.py                      11.2%  🔴 P2-Strategic
└── work_items.py                          0.0%  🔴 P3-Foundation
```

---

## Appendix B: Analysis Script Usage

```bash
# Generate this report
python3 scripts/analyze_coverage_gap.py

# Filter by priority
python3 scripts/analyze_coverage_gap.py --priority P0

# Show detailed function analysis
python3 scripts/analyze_coverage_gap.py --functions

# Export to CSV
python3 scripts/analyze_coverage_gap.py --format csv > coverage_gaps.csv
```

---

**Document Version:** 1.0
**Last Updated:** 2026-01-30
**Next Review:** After Phase 2 completion (target: 56% coverage)
