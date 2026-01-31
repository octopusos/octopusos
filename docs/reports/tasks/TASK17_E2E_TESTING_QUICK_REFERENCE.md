# Task #17 E2E Testing - Quick Reference Guide

## Overview

**File**: `tests/e2e/test_mode_system_100_complete.py`
**Tests**: 13 (100% passing)
**Execution Time**: 0.49s

---

## Quick Commands

### Run All Tests
```bash
python3 -m pytest tests/e2e/test_mode_system_100_complete.py -v
```

### Run Specific Test
```bash
# Full mode system test
pytest tests/e2e/test_mode_system_100_complete.py::TestModeSystem100Complete::test_full_mode_system_e2e -v

# Policy override test
pytest tests/e2e/test_mode_system_100_complete.py::TestModeSystem100Complete::test_policy_override_e2e -v

# Monitoring API test
pytest tests/e2e/test_mode_system_100_complete.py::TestModeSystem100Complete::test_monitoring_api_e2e -v
```

### Run with Coverage
```bash
pytest tests/e2e/test_mode_system_100_complete.py --cov=agentos.core.mode --cov-report=term-missing
```

---

## Test Categories

### Core E2E Tests (9 tests)

1. **test_full_mode_system_e2e** - Complete system flow
2. **test_policy_override_e2e** - Policy switching
3. **test_alert_propagation_e2e** - Multi-channel alerts
4. **test_monitoring_api_e2e** - API simulation
5. **test_mode_violation_error_integration** - Error handling
6. **test_policy_file_fallback_behavior** - Fallback logic
7. **test_alert_buffer_fifo_behavior** - Buffer management
8. **test_multiple_policies_sequential_loading** - Sequential loading
9. **test_end_to_end_scenario_realistic_workflow** - Real workflow

### Edge Case Tests (4 tests)

10. **test_alert_with_empty_context** - Empty context handling
11. **test_unknown_mode_permissions** - Unknown mode safety
12. **test_concurrent_alert_sending** - Stress test (1000 alerts)
13. **test_output_failure_isolation** - Failure isolation

---

## Key Test Scenarios

### Scenario 1: Full System Flow
```python
# Load policy → Trigger violation → Verify alert → Check stats
strict_policy = load_policy_from_file("strict_policy.json")
alert_mode_violation(mode_id="design", operation="commit", ...)
assert aggregator.alert_count == 1
assert stats["severity_breakdown"]["error"] == 1
```

### Scenario 2: Policy Override
```python
# Default policy → Dev policy → Verify changes
default_policy = ModePolicy()
dev_policy = load_policy_from_file("dev_policy.json")
assert debug_mode.allows_diff() is True  # Changed!
```

### Scenario 3: Alert Propagation
```python
# Console + File output → Trigger alert → Verify both
aggregator.add_output(FileAlertOutput(alert_file))
alert_mode_violation(...)
assert "error" in captured.err  # Console
assert json.loads(file_content)["severity"] == "error"  # File
```

### Scenario 4: Monitoring API
```python
# Send alerts → Filter → Paginate → Clear
aggregator.alert(severity=AlertSeverity.ERROR, ...)
error_alerts = [a for a in all_alerts if a.severity == AlertSeverity.ERROR]
last_3 = aggregator.get_recent_alerts(limit=3)
aggregator.clear_recent()
```

---

## Policy Files Used in Tests

### 1. strict_policy.json
```json
{
  "modes": {
    "implementation": {
      "allows_commit": false,  // Strict: no commits
      "allows_diff": true
    },
    "design": {
      "allows_commit": false,
      "allows_diff": false
    }
  }
}
```

### 2. dev_policy.json
```json
{
  "modes": {
    "implementation": {
      "allows_commit": true,   // Dev: allows commits
      "allows_diff": true
    },
    "debug": {
      "allows_commit": false,
      "allows_diff": true      // Dev: allows debug diff
    }
  }
}
```

### 3. default_policy.json
```python
# In-code default policy
implementation: allows_commit=True, allows_diff=True
others: allows_commit=False, allows_diff=False
```

---

## Common Assertions

### Policy Assertions
```python
assert policy.get_policy_version() == "1.0"
assert mode.allows_commit() is True
assert mode.allows_diff() is False
assert check_mode_permission("design", "commit") is False
```

### Alert Assertions
```python
assert aggregator.alert_count == expected_count
assert len(aggregator.recent_alerts) == expected_recent
assert alert.severity == AlertSeverity.ERROR
assert alert.mode_id == "design"
assert alert.operation == "commit"
assert "forbidden" in alert.message.lower()
```

### Statistics Assertions
```python
stats = aggregator.get_stats()
assert stats["total_alerts"] == 5
assert stats["recent_count"] == 5
assert stats["severity_breakdown"]["error"] == 2
assert stats["output_count"] >= 1
```

---

## Test Structure Pattern

```python
class TestModeSystem100Complete:
    def setup_method(self):
        """Reset global state"""
        reset_global_aggregator()
        set_global_policy(ModePolicy())

    def teardown_method(self):
        """Clean up"""
        reset_global_aggregator()
        set_global_policy(ModePolicy())

    def test_scenario(self, tmp_path, capsys):
        """Test description"""
        # 1. Setup
        policy = load_policy_from_file(...)

        # 2. Action
        alert_mode_violation(...)

        # 3. Verify
        assert aggregator.alert_count == 1

        # 4. Cleanup (automatic via teardown)
```

---

## Debugging Tips

### View Console Output
```bash
pytest tests/e2e/test_mode_system_100_complete.py -v -s
```

### Run Single Test with Detailed Traceback
```bash
pytest tests/e2e/test_mode_system_100_complete.py::TestModeSystem100Complete::test_full_mode_system_e2e -vv --tb=long
```

### Check Test Duration
```bash
pytest tests/e2e/test_mode_system_100_complete.py --durations=10
```

### Run in Parallel (if pytest-xdist installed)
```bash
pytest tests/e2e/test_mode_system_100_complete.py -n auto
```

---

## Expected Test Output

```
tests/e2e/test_mode_system_100_complete.py::TestModeSystem100Complete::test_full_mode_system_e2e PASSED [  7%]
tests/e2e/test_mode_system_100_complete.py::TestModeSystem100Complete::test_policy_override_e2e PASSED [ 15%]
tests/e2e/test_mode_system_100_complete.py::TestModeSystem100Complete::test_alert_propagation_e2e PASSED [ 23%]
tests/e2e/test_mode_system_100_complete.py::TestModeSystem100Complete::test_monitoring_api_e2e PASSED [ 30%]
...
======================== 13 passed in 0.49s ========================
```

---

## Troubleshooting

### Test Fails Due to Missing Policy File
```python
# Ensure policy files exist
configs/mode/strict_policy.json
configs/mode/dev_policy.json
```

### Test Fails Due to Import Error
```python
# Verify imports
from agentos.core.mode import get_mode, ModeViolationError
from agentos.core.mode.mode_alerts import get_alert_aggregator
```

### Test Fails Due to Global State
```python
# Ensure setup/teardown run
def setup_method(self):
    reset_global_aggregator()
    set_global_policy(ModePolicy())
```

---

## Integration Points

### With Mode System
```python
from agentos.core.mode import get_mode, ModeViolationError
mode = get_mode("design")
if not mode.allows_commit():
    raise ModeViolationError(...)
```

### With Alert System
```python
from agentos.core.mode.mode_alerts import alert_mode_violation
alert_mode_violation(
    mode_id="design",
    operation="commit",
    message="Violation message",
    context={"key": "value"}
)
```

### With Policy System
```python
from agentos.core.mode import load_policy_from_file
policy = load_policy_from_file(Path("config/policy.json"))
```

---

## Test Data Examples

### Alert Example
```json
{
  "timestamp": "2026-01-30T12:00:00Z",
  "severity": "error",
  "mode_id": "design",
  "operation": "commit",
  "message": "Design mode attempted commit (forbidden)",
  "context": {
    "policy": "strict",
    "allows_commit": false
  }
}
```

### Statistics Example
```json
{
  "total_alerts": 150,
  "recent_count": 50,
  "severity_breakdown": {
    "info": 10,
    "warning": 30,
    "error": 60,
    "critical": 0
  },
  "max_recent": 100,
  "output_count": 2
}
```

---

## Performance Benchmarks

- **Single test**: ~0.03s
- **Full suite**: 0.49s
- **Stress test (1000 alerts)**: ~0.05s

---

## Related Files

```
tests/e2e/test_mode_system_100_complete.py    # Main test file
tests/unit/mode/test_mode_policy.py           # Unit tests
tests/unit/mode/test_mode_alerts.py           # Unit tests
agentos/core/mode/mode.py                     # Mode classes
agentos/core/mode/mode_policy.py              # Policy engine
agentos/core/mode/mode_alerts.py              # Alert system
configs/mode/*.json                            # Policy files
```

---

## Quick Checklist

Before running tests:
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pytest`, `pytest-cov`)
- [ ] Policy files in `configs/mode/` directory
- [ ] Working directory is project root

After running tests:
- [ ] All tests pass (13/13)
- [ ] No warnings (except known Pydantic deprecations)
- [ ] Execution time < 1s

---

**Last Updated**: 2026-01-30
**Version**: 1.0
**Status**: ✅ Production Ready
