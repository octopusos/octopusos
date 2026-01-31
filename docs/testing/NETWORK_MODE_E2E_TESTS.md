# Network Mode E2E Test Documentation

## Overview

This document provides comprehensive information about the Network Mode End-to-End (E2E) test suite, which validates the complete network mode functionality from frontend to backend.

## Test Architecture

### Test Structure

```
tests/e2e/test_network_mode_e2e.py
├── Fixtures (pytest)
│   ├── api_base_url
│   ├── session
│   ├── temp_db
│   ├── network_mode_manager
│   └── reset_mode_to_on
│
├── TestNetworkModeBasicFunctionality
│   ├── test_get_initial_mode
│   ├── test_set_mode_to_readonly
│   ├── test_set_mode_to_off
│   ├── test_set_mode_to_on
│   └── test_mode_persistence
│
├── TestNetworkModePermissionEnforcement
│   ├── test_readonly_allows_fetch
│   ├── test_readonly_blocks_send
│   ├── test_off_blocks_all
│   └── test_on_allows_all
│
├── TestNetworkModeErrorHandling
│   ├── test_invalid_mode_rejected
│   ├── test_duplicate_mode_idempotent
│   ├── test_string_mode_conversion
│   └── test_case_insensitive_operations
│
├── TestNetworkModeHistoryTracking
│   ├── test_mode_history_tracking
│   ├── test_history_limit
│   └── test_get_mode_info
│
├── TestNetworkModeConcurrency
│   ├── test_concurrent_mode_changes
│   └── test_concurrent_reads
│
├── TestNetworkModePerformance
│   ├── test_get_mode_performance
│   ├── test_set_mode_performance
│   └── test_is_operation_allowed_performance
│
└── TestNetworkModeFullWorkflow
    ├── test_full_workflow_on_to_readonly_to_off_to_on
    └── test_workflow_with_metadata
```

### Test Categories

1. **Basic Functionality (5 tests)**
   - Initial mode retrieval
   - Mode transitions (ON/READONLY/OFF)
   - Database persistence

2. **Permission Enforcement (4 tests)**
   - Read operation permissions in READONLY mode
   - Write operation blocking in READONLY mode
   - All operations blocked in OFF mode
   - All operations allowed in ON mode

3. **Error Handling (4 tests)**
   - Invalid mode rejection
   - Idempotent mode setting
   - String to enum conversion
   - Case-insensitive operation checking

4. **History Tracking (3 tests)**
   - Mode change history recording
   - History pagination limits
   - Comprehensive mode information

5. **Concurrency (2 tests)**
   - Concurrent mode changes
   - Concurrent read operations

6. **Performance (3 tests)**
   - get_mode() latency (<50ms)
   - set_mode() latency (<100ms)
   - is_operation_allowed() latency (<10ms)

7. **Full Workflow (2 tests)**
   - Complete mode transition cycle
   - Metadata preservation

**Total: 23 test cases**

## Running the Tests

### Quick Start

```bash
# Run all E2E tests
./scripts/run_e2e_network_mode_tests.sh

# Run tests directly with pytest
python3 -m pytest tests/e2e/test_network_mode_e2e.py -v

# Run specific test class
python3 -m pytest tests/e2e/test_network_mode_e2e.py::TestNetworkModeBasicFunctionality -v

# Run specific test
python3 -m pytest tests/e2e/test_network_mode_e2e.py::TestNetworkModeBasicFunctionality::test_get_initial_mode -v
```

### Test Options

```bash
# Verbose output with detailed logs
pytest tests/e2e/test_network_mode_e2e.py -v -s

# Generate HTML report
pytest tests/e2e/test_network_mode_e2e.py --html=report.html --self-contained-html

# Show performance metrics (10 slowest tests)
pytest tests/e2e/test_network_mode_e2e.py --durations=10

# Run in parallel (requires pytest-xdist)
pytest tests/e2e/test_network_mode_e2e.py -n auto

# Stop on first failure
pytest tests/e2e/test_network_mode_e2e.py -x

# Run only tests matching keyword
pytest tests/e2e/test_network_mode_e2e.py -k "performance"
```

## Prerequisites

### Required Dependencies

```bash
# Core dependencies
pip install pytest>=7.0.0
pip install pytest-asyncio>=0.21.0
pip install requests>=2.28.0

# Optional (for better reporting)
pip install pytest-html>=3.1.0
pip install pytest-cov>=4.0.0
pip install pytest-xdist>=3.0.0  # For parallel execution
```

### Environment Setup

```bash
# Set project root in PYTHONPATH
export PYTHONPATH=/path/to/AgentOS:$PYTHONPATH

# Optional: Set custom database path for testing
export AGENTOS_TEST_DB=/tmp/test_network_mode.db
```

## Test Scenarios

### Scenario 1: Basic Mode Operations

**Test**: `test_get_initial_mode`, `test_set_mode_to_readonly`

**Steps**:
1. Get initial mode (should be ON)
2. Set mode to READONLY
3. Verify mode changed successfully
4. Verify history record created

**Expected Result**: ✅ Mode transitions successfully, history tracked

### Scenario 2: Permission Enforcement

**Test**: `test_readonly_blocks_send`, `test_off_blocks_all`

**Steps**:
1. Set mode to READONLY
2. Attempt write operation (send)
3. Verify operation blocked with clear error message
4. Set mode to OFF
5. Verify all operations blocked

**Expected Result**: ✅ Operations blocked according to mode restrictions

### Scenario 3: Database Persistence

**Test**: `test_mode_persistence`

**Steps**:
1. Create NetworkModeManager instance
2. Set mode to READONLY
3. Destroy manager instance
4. Create new manager instance (simulates restart)
5. Verify mode is still READONLY

**Expected Result**: ✅ Mode persists across application restarts

### Scenario 4: Concurrent Operations

**Test**: `test_concurrent_mode_changes`

**Steps**:
1. Launch 10 threads
2. Each thread attempts to change mode
3. Wait for all threads to complete
4. Verify no errors occurred
5. Verify final state is consistent

**Expected Result**: ✅ No race conditions, database integrity maintained

### Scenario 5: Performance Benchmarks

**Test**: `test_get_mode_performance`, `test_set_mode_performance`

**Steps**:
1. Execute get_mode() 100 times
2. Measure average and max response time
3. Execute set_mode() 50 times
4. Measure average and max response time
5. Verify times meet performance thresholds

**Expected Result**: ✅ All operations complete within latency thresholds

### Scenario 6: Complete Workflow

**Test**: `test_full_workflow_on_to_readonly_to_off_to_on`

**Steps**:
1. Start in ON mode
2. Transition to READONLY
3. Verify read operations allowed, write blocked
4. Transition to OFF
5. Verify all operations blocked
6. Transition back to ON
7. Verify all operations allowed
8. Check complete history trail

**Expected Result**: ✅ Full cycle completes with correct permissions at each stage

## Performance Benchmarks

### Latency Targets

| Operation | Target | Threshold | Notes |
|-----------|--------|-----------|-------|
| get_mode() | <25ms | <50ms | Fast path, in-memory cache |
| set_mode() | <50ms | <100ms | Includes DB write + history |
| is_operation_allowed() | <5ms | <10ms | Logic only, no I/O |

### Throughput Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Concurrent reads | >100/sec | Read-heavy workload |
| Mode changes | >10/sec | Write workload |
| Permission checks | >1000/sec | Hot path operation |

## Troubleshooting

### Common Issues

#### Issue 1: Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'agentos'`

**Solution**:
```bash
# Add project root to PYTHONPATH
export PYTHONPATH=/path/to/AgentOS:$PYTHONPATH

# Or run from project root
cd /path/to/AgentOS
python3 -m pytest tests/e2e/test_network_mode_e2e.py
```

#### Issue 2: Database Lock Errors

**Symptom**: `sqlite3.OperationalError: database is locked`

**Solution**:
```bash
# Tests use temporary databases, but if issues persist:
# 1. Check for zombie processes
ps aux | grep python

# 2. Clear any test databases
rm -f /tmp/test_*.db

# 3. Run tests sequentially (not in parallel)
pytest tests/e2e/test_network_mode_e2e.py
```

#### Issue 3: Fixture Errors

**Symptom**: `fixture 'network_mode_manager' not found`

**Solution**:
```bash
# Ensure pytest is discovering fixtures correctly
pytest --fixtures tests/e2e/test_network_mode_e2e.py | grep network_mode_manager

# Run with verbose output
pytest tests/e2e/test_network_mode_e2e.py -v --tb=short
```

#### Issue 4: Performance Tests Failing

**Symptom**: `AssertionError: Average get_mode time (75.2ms) exceeds 50ms threshold`

**Solution**:
```bash
# Performance tests may fail on slower systems or under load
# 1. Check system load
top

# 2. Run performance tests separately
pytest tests/e2e/test_network_mode_e2e.py::TestNetworkModePerformance -v

# 3. Adjust thresholds in test if necessary (for CI/CD)
# Edit PERFORMANCE_THRESHOLD_MS in test file
```

### Debug Mode

To run tests with maximum debug output:

```bash
# Enable debug logging
export AGENTOS_LOG_LEVEL=DEBUG

# Run with verbose pytest output
pytest tests/e2e/test_network_mode_e2e.py -v -s --log-cli-level=DEBUG

# Capture full traceback
pytest tests/e2e/test_network_mode_e2e.py --tb=long
```

## Test Data Management

### Temporary Databases

Tests use isolated temporary databases to ensure independence:

```python
@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()  # Cleanup after test
```

### Test Isolation

Each test is isolated using the `reset_mode_to_on` fixture:

```python
@pytest.fixture(autouse=True)
def reset_mode_to_on(network_mode_manager):
    """Ensure each test starts with mode set to ON."""
    network_mode_manager.set_mode(NetworkMode.ON, updated_by="test_setup")
    yield
    network_mode_manager.set_mode(NetworkMode.ON, updated_by="test_teardown")
```

## Continuous Integration

### CI Configuration

Example GitHub Actions workflow:

```yaml
name: Network Mode E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-html pytest-asyncio

      - name: Run E2E tests
        run: |
          ./scripts/run_e2e_network_mode_tests.sh

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: test-reports/
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any

    stages {
        stage('Test') {
            steps {
                sh './scripts/run_e2e_network_mode_tests.sh'
            }
        }

        stage('Report') {
            steps {
                publishHTML([
                    reportDir: 'test-reports',
                    reportFiles: '*.html',
                    reportName: 'E2E Test Report'
                ])
            }
        }
    }
}
```

## Test Coverage

### Coverage Report

Generate coverage report:

```bash
# Run tests with coverage
pytest tests/e2e/test_network_mode_e2e.py \
    --cov=agentos.core.communication.network_mode \
    --cov-report=html \
    --cov-report=term

# View coverage
open htmlcov/index.html
```

### Expected Coverage

| Module | Target Coverage |
|--------|----------------|
| network_mode.py | >95% |
| API endpoints | >90% |
| Service integration | >85% |

## Test Maintenance

### Adding New Tests

1. Choose appropriate test class based on category
2. Follow naming convention: `test_<feature>_<scenario>`
3. Include docstring with expected behavior
4. Use fixtures for setup/teardown
5. Add assertions with clear error messages

Example:

```python
def test_new_feature(self, network_mode_manager):
    """Test that new feature works correctly.

    Expected: Feature behaves as specified in requirements.
    """
    # Arrange
    network_mode_manager.set_mode(NetworkMode.ON)

    # Act
    result = network_mode_manager.new_feature()

    # Assert
    assert result is not None, "Feature should return a value"
    assert result.success is True, "Feature should succeed"
```

### Updating Tests

When updating network mode functionality:

1. Review affected test cases
2. Update test expectations
3. Add new test cases for new behavior
4. Run full test suite to verify
5. Update documentation

## Reporting

### Test Reports

After running tests, reports are generated in `test-reports/`:

- **HTML Report**: `network_mode_e2e_YYYYMMDD_HHMMSS.html`
- **JUnit XML**: `junit.xml`
- **Log File**: `network_mode_e2e_YYYYMMDD_HHMMSS.log`

### Viewing Reports

```bash
# Open HTML report in browser
open test-reports/network_mode_e2e_*.html

# View log file
less test-reports/network_mode_e2e_*.log

# Parse JUnit XML for CI integration
xmllint --format test-reports/junit.xml
```

## Best Practices

1. **Test Independence**: Each test should be runnable in isolation
2. **Clean Teardown**: Use fixtures for resource cleanup
3. **Clear Assertions**: Include descriptive error messages
4. **Performance Awareness**: Monitor test execution time
5. **Documentation**: Keep test docstrings up-to-date
6. **Error Handling**: Test both success and failure paths
7. **Realistic Scenarios**: Mirror production use cases

## Related Documentation

- [Network Mode Quick Reference](../NETWORK_MODE_QUICK_REFERENCE.md)
- [Network Mode Implementation Summary](../NETWORK_MODE_IMPLEMENTATION_SUMMARY.md)
- [CommunicationOS API Documentation](../api/COMMUNICATION_API.md)
- [Testing Strategy](./TESTING_SUMMARY.md)

## Support

For issues or questions about E2E tests:

1. Check [Troubleshooting](#troubleshooting) section
2. Review test logs in `test-reports/`
3. Enable debug logging for more details
4. Open an issue with test output and environment details
