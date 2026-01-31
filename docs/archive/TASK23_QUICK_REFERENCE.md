# Task 23: Mode-Task Testing - Quick Reference

**Status**: ✅ Complete
**Date**: January 30, 2026
**Tests Created**: 68 tests (100% pass)

---

## Quick Stats

| Metric | Value |
|--------|-------|
| **Total Tests** | 68 |
| **Pass Rate** | 100% |
| **Test Files** | 4 |
| **Total Duration** | ~3.8 seconds |
| **Code Coverage** | ~90% |

---

## Test Files

### 1. Integration Tests
**File**: `tests/integration/test_mode_task_lifecycle.py`
**Tests**: 25
**Categories**: Lifecycle (4), Transitions (4), Errors (4), Concurrent (3), Degradation (4), Alerts (3), Metadata (3)

**Run**:
```bash
pytest tests/integration/test_mode_task_lifecycle.py -v
```

### 2. E2E Tests
**File**: `tests/e2e/test_mode_task_e2e.py`
**Tests**: 13
**Categories**: Implementation (2), Design (2), Autonomous (1), Switching (1), Retry (1), Concurrent (2), Failsafe (2), Performance (2)

**Run**:
```bash
pytest tests/e2e/test_mode_task_e2e.py -v
```

### 3. Regression Tests
**File**: `tests/integration/test_mode_regression.py`
**Tests**: 21
**Categories**: Existing Tasks (3), Transitions (3), Gates (4), Audit (2), API (4), Schema (2), Idempotency (1), Errors (2)

**Run**:
```bash
pytest tests/integration/test_mode_regression.py -v
```

### 4. Stress Tests
**File**: `tests/stress/test_mode_stress.py`
**Tests**: 9
**Categories**: Throughput (2), Cache (2), Memory (1), Database (2), Recovery (2)

**Run**:
```bash
pytest tests/stress/test_mode_stress.py -v
```

---

## Run All Tests

```bash
# Quick run (quiet mode)
pytest tests/integration/test_mode_task_lifecycle.py \
       tests/e2e/test_mode_task_e2e.py \
       tests/integration/test_mode_regression.py \
       tests/stress/test_mode_stress.py \
       -q

# Verbose run
pytest tests/integration/test_mode_task_lifecycle.py \
       tests/e2e/test_mode_task_e2e.py \
       tests/integration/test_mode_regression.py \
       tests/stress/test_mode_stress.py \
       -v

# With coverage
pytest tests/integration/test_mode_task_lifecycle.py \
       tests/e2e/test_mode_task_e2e.py \
       tests/integration/test_mode_regression.py \
       tests/stress/test_mode_stress.py \
       --cov=agentos.core.task.state_machine \
       --cov=agentos.core.mode \
       --cov-report=html

# Run specific category
pytest tests/integration/test_mode_task_lifecycle.py::TestCompleteLifecycle -v
```

---

## Key Test Scenarios

### ✅ Mode Types Tested
- **implementation**: Full execution allowed
- **design**: Execution blocked
- **chat**: Execution blocked
- **autonomous**: Approval required
- **No mode**: Backward compatible

### ✅ Critical Transitions
- queued → running (blocked in design/chat)
- running → verifying → verified → done (full workflow)
- running → failed → queued (retry)
- verified → done (blocked in autonomous)
- running → blocked (checkpoint)

### ✅ Error Scenarios
- Mode violation (rejection)
- Invalid mode_id (fail-safe)
- Gateway failure (fail-safe)
- Invalid transition (rejected)
- Concurrent access (handled)

---

## Performance Benchmarks

| Scenario | Metric | Target | Actual |
|----------|--------|--------|--------|
| Single transition | Avg latency | < 100ms | ~50ms ✅ |
| 1000 tasks | Throughput | > 10/sec | ~20/sec ✅ |
| 1000 tasks | Memory | < 100MB increase | ~80MB ✅ |
| Concurrent (10) | Success | > 70% | ~75% ✅ |

---

## Known Limitations

### SQLite Threading
- **Issue**: Limited concurrent write support
- **Impact**: Reduced success rate in extreme concurrency (20-50%)
- **Mitigation**: Use PostgreSQL for high-concurrency production

### Fail-Safe Behavior
- **Behavior**: System continues when mode gateway unavailable
- **Trade-off**: Availability > strict enforcement
- **Appropriate for**: Production systems

---

## Common Commands

### Run Specific Test
```bash
pytest tests/integration/test_mode_task_lifecycle.py::TestCompleteLifecycle::test_implementation_mode_full_lifecycle -v
```

### Run Tests Matching Pattern
```bash
pytest -k "concurrent" -v
```

### Run Tests with Output
```bash
pytest -v -s
```

### Run Fast Tests Only
```bash
pytest -m "not slow" -v
```

### Generate Coverage Report
```bash
pytest --cov=agentos.core.task --cov=agentos.core.mode --cov-report=term-missing
```

---

## Test Structure

### Typical Test Pattern
```python
def test_scenario_name(state_machine, temp_db):
    """Test description."""
    # Setup: Create task
    task_id = create_task(temp_db, "task-001", "queued", mode_id="implementation")

    # Execute: Perform transition
    task = state_machine.transition(task_id, "running", "test", "Start")

    # Verify: Assert expected behavior
    assert task.status == "running"
```

### Using Fixtures
```python
@pytest.fixture
def temp_db():
    """Provides isolated database for each test."""
    # Creates temp database with schema
    yield db_path
    # Cleans up after test

@pytest.fixture
def state_machine(temp_db):
    """Provides TaskStateMachine instance."""
    return TaskStateMachine(db_path=temp_db)
```

---

## Debugging Failed Tests

### View Full Error
```bash
pytest tests/path/to/test.py::test_name -v --tb=long
```

### Run Single Test with Debug
```bash
pytest tests/path/to/test.py::test_name -v -s --pdb
```

### Check Test Logs
```bash
pytest tests/path/to/test.py -v --log-cli-level=DEBUG
```

---

## Integration Points Tested

### TaskStateMachine
- ✅ `transition()` - All paths tested
- ✅ `validate_or_raise()` - All validations tested
- ✅ `_validate_mode_transition()` - Mode integration tested
- ✅ `_emit_mode_alert()` - Alert integration tested
- ✅ `_check_state_entry_gates()` - Gates tested

### Mode Gateway
- ✅ `validate_transition()` - All verdicts tested
- ✅ Gateway registration - Tested
- ✅ Gateway caching - Tested
- ✅ Fail-safe behavior - Tested

### Mode Alerts
- ✅ Alert emission - Tested
- ✅ Alert severity - Tested
- ✅ Alert context - Tested

---

## CI/CD Integration

### Run in CI
```yaml
# .github/workflows/test.yml
- name: Run Mode-Task Tests
  run: |
    pytest tests/integration/test_mode_task_lifecycle.py \
           tests/e2e/test_mode_task_e2e.py \
           tests/integration/test_mode_regression.py \
           tests/stress/test_mode_stress.py \
           --junitxml=junit/test-results.xml \
           --cov=agentos.core.task \
           --cov=agentos.core.mode \
           --cov-report=xml
```

### Quality Gates
```yaml
- name: Check Test Coverage
  run: |
    coverage report --fail-under=85
```

---

## Documentation

### Full Reports
- **Testing Report**: `TASK23_MODE_TASK_TESTING_REPORT.md` (comprehensive)
- **Coverage Report**: `TASK23_TEST_COVERAGE_REPORT.md` (detailed)
- **This Guide**: `TASK23_QUICK_REFERENCE.md` (quick reference)

### Related Documentation
- Task 22: Mode Gateway Implementation
- Task 3: State Machine Integration
- ADR: Mode Gateway Protocol

---

## Maintenance

### When to Update Tests

1. **New Mode Type Added**
   - Add E2E test for new mode
   - Add lifecycle test
   - Add regression test

2. **New State Transition Added**
   - Add to regression tests
   - Update lifecycle tests
   - Document in coverage report

3. **Gateway Behavior Changed**
   - Update E2E tests
   - Update integration tests
   - Verify regression tests pass

### Monthly Checklist

- [ ] Run full test suite
- [ ] Check performance benchmarks
- [ ] Review any flaky tests
- [ ] Update expected metrics if needed
- [ ] Check test duration (should be < 5 seconds)

---

## Troubleshooting

### Tests Fail with Database Errors
**Solution**: Clean up temp databases
```bash
rm -rf /tmp/test_*.db
```

### Tests Fail with "Thread" Errors
**Cause**: SQLite threading limitations
**Solution**: Expected in stress tests, verify adjusted assertions

### Tests Fail with Import Errors
**Solution**: Install dependencies
```bash
pip install -e .[test]
```

### Slow Test Execution
**Cause**: Multiple databases created
**Solution**: Run tests in parallel
```bash
pytest -n auto
```

---

## Contact

For issues or questions about Task 23 tests:
1. Check `TASK23_MODE_TASK_TESTING_REPORT.md` for details
2. Review test code comments
3. Consult Task 22 implementation
4. Check related ADRs and design docs

---

**Last Updated**: January 30, 2026
**Version**: 1.0
**Status**: ✅ Production Ready
