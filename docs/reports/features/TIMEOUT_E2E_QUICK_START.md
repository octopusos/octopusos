# Timeout E2E Tests - Quick Start Guide

## 🚀 Quick Commands

### Run All Timeout Tests
```bash
pytest tests/integration/task/test_timeout_e2e.py -v
```

### Run Specific Test
```bash
# Test timeout failure
pytest tests/integration/task/test_timeout_e2e.py::TestTimeoutE2E::test_task_timeout_after_limit -v

# Test timeout warning
pytest tests/integration/task/test_timeout_e2e.py::TestTimeoutE2E::test_task_timeout_warning -v

# Test successful completion
pytest tests/integration/task/test_timeout_e2e.py::TestTimeoutE2E::test_task_completes_before_timeout -v
```

### Run with Detailed Output
```bash
pytest tests/integration/task/test_timeout_e2e.py -v -s
```

---

## 📋 Test Scenarios

| Test | Purpose | Expected Result |
|------|---------|----------------|
| `test_task_timeout_after_limit` | Task exceeds timeout limit | Task fails, exit_reason='timeout' |
| `test_task_timeout_warning` | Task approaching timeout | Warning issued at 80% threshold |
| `test_task_completes_before_timeout` | Task completes quickly | Success, no timeout |
| `test_timeout_disabled` | Timeout disabled | Task runs without limits |
| `test_timeout_integration_with_runner` | Full runner integration | Timeout detected in runner loop |

---

## 🔍 What Each Test Verifies

### ✅ test_task_timeout_after_limit
- Task with 5s timeout runs for 6s
- Status changes to 'failed'
- exit_reason set to 'timeout'
- Audit log contains timeout error

### ✅ test_task_timeout_warning
- Task with 10s timeout runs for 8.5s
- Warning issued at 80% (8s)
- No timeout yet
- Audit log contains warning
- Duplicate warnings prevented

### ✅ test_task_completes_before_timeout
- Task with 10s timeout completes in 3s
- No warning or timeout
- Status is 'succeeded'
- exit_reason is 'done'

### ✅ test_timeout_disabled
- Timeout disabled
- Task runs for 10s (would timeout at 5s)
- No timeout triggered
- Task completes normally

### ✅ test_timeout_integration_with_runner
- Full TaskRunner integration
- Timeout detected in execution loop
- Proper state transitions

---

## 📁 File Locations

```
tests/integration/task/test_timeout_e2e.py  # Test file
TIMEOUT_E2E_TEST_REPORT.md                  # Full report
TIMEOUT_E2E_QUICK_START.md                  # This guide
```

---

## 🛠️ Test Infrastructure

### Fixtures Available
- `temp_db`: Isolated temporary database
- `task_manager`: TaskManager with test DB
- `timeout_manager`: TimeoutManager instance

### Dependencies
- pytest
- tempfile
- unittest.mock
- agentos.core.task
- agentos.core.runner

---

## 💡 Usage Examples

### Example 1: Verify Timeout Detection
```bash
pytest tests/integration/task/test_timeout_e2e.py::TestTimeoutE2E::test_task_timeout_after_limit -v -s
```

Expected output:
```
✓ Test passed: Task xxx timed out after 6s (limit: 5s)
  - Status: failed
  - Exit reason: timeout
  - Timeout message: Task execution timed out...
```

### Example 2: Verify Warning System
```bash
pytest tests/integration/task/test_timeout_e2e.py::TestTimeoutE2E::test_task_timeout_warning -v -s
```

Expected output:
```
✓ Test passed: Task xxx correctly issued warning at 8.5s
  - Warning message: Task execution approaching timeout...
  - warning_issued: True
```

---

## 🔧 Troubleshooting

### Test Fails to Run
```bash
# Verify pytest is available
which pytest

# Use venv pytest if needed
.venv/bin/pytest tests/integration/task/test_timeout_e2e.py -v
```

### Database Locked Error
- Each test uses isolated temporary database
- Tests clean up automatically
- If issue persists, check for zombie processes

### Import Errors
```bash
# Ensure in project root
cd /Users/pangge/PycharmProjects/AgentOS

# Activate virtual environment
source .venv/bin/activate

# Verify agentos package
python -c "import agentos; print(agentos.__file__)"
```

---

## 📊 Test Coverage

Run with coverage report:
```bash
pytest tests/integration/task/test_timeout_e2e.py \
  --cov=agentos.core.task.timeout_manager \
  --cov=agentos.core.runner.task_runner \
  --cov-report=term-missing \
  --cov-report=html
```

View HTML report:
```bash
open htmlcov/index.html
```

---

## 🎯 Key Assertions

Each test includes multiple assertions:

```python
# Timeout detection
assert is_timeout is True
assert task.status == "failed"
assert task.exit_reason == "timeout"

# Warning detection
assert warning_msg is not None
assert "approaching timeout" in warning_msg.lower()
assert timeout_state.warning_issued is True

# Successful completion
assert is_timeout is False
assert task.status == "succeeded"
assert task.exit_reason == "done"
```

---

## 🔄 Integration Points

Tests verify integration with:

1. **TimeoutManager**
   - `start_timeout_tracking()`
   - `check_timeout()`
   - `mark_warning_issued()`
   - `get_timeout_metrics()`

2. **TaskManager**
   - `create_task()`
   - `update_task_status()`
   - `update_task_exit_reason()`
   - `add_audit()`

3. **TaskRunner**
   - Timeout checking in run loop
   - Audit logging
   - State transitions

---

## ⚡ Performance Notes

- Tests use **time simulation** (not real sleep)
- Each test runs in < 1 second (except runner integration)
- No network calls or external dependencies
- Isolated temporary databases ensure speed

---

## 📝 Adding New Tests

To add a new timeout test:

1. Add method to `TestTimeoutE2E` class:
```python
def test_my_new_scenario(self, task_manager, timeout_manager):
    """Test description"""
    # Create task
    task = task_manager.create_task(...)

    # Setup timeout
    timeout_config = TimeoutConfig(...)

    # Test scenario
    # ...

    # Assertions
    assert condition
```

2. Run new test:
```bash
pytest tests/integration/task/test_timeout_e2e.py::TestTimeoutE2E::test_my_new_scenario -v
```

---

## ✅ Completion Checklist

- ✅ Test file created and syntax validated
- ✅ 5 test scenarios implemented
- ✅ All tests use isolated databases
- ✅ Comprehensive assertions
- ✅ Integration with real components
- ✅ Audit log verification
- ✅ Documentation complete

---

**Status**: ✅ READY FOR USE
**Last Updated**: 2026-01-30

