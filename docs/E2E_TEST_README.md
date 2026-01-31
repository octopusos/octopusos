# E2E Test Suite - Quick Start Guide

## Overview

This directory contains a comprehensive end-to-end test suite for the AgentOS WebUI Extension Management system. The test suite validates the complete extension lifecycle from creation to uninstallation.

## Test Files

- **`run_e2e_test.py`** - Main test script (executable)
- **`E2E_TEST_REPORT.md`** - Detailed test results and analysis
- **`e2e_test_output.txt`** - Raw test execution output

## Prerequisites

1. **WebUI Service Running**
   ```bash
   # Ensure WebUI is running on http://localhost:8000
   curl http://localhost:8000/api/extensions
   ```

2. **Python Dependencies**
   ```bash
   pip install requests
   ```

## Running the Tests

### Quick Run
```bash
cd /Users/pangge/PycharmProjects/AgentOS
python3 run_e2e_test.py
```

### Run with Output Logging
```bash
python3 run_e2e_test.py 2>&1 | tee e2e_test_output_$(date +%Y%m%d_%H%M%S).txt
```

### Expected Output

```
============================================================
Starting E2E Test Suite for WebUI Extension Management
============================================================

============================================================
Phase 1: Create Extension Template
============================================================
✅ Template generated successfully
✅ ZIP contains 8 files
...

============================================================
Test Summary
============================================================
✅ Phase 1: Create Template: PASSED
✅ Phase 2: Install Extension: PASSED
✅ Phase 3: Enable/Disable: PASSED
✅ Phase 4: View Details: PASSED
✅ Phase 5: Uninstall: PASSED

============================================================
✅ ALL E2E TESTS PASSED
============================================================
```

## Test Phases

### Phase 1: Create Extension Template
- Tests: Template Generator API
- Validates: ZIP structure, manifest.json, ADR-EXT-002 compliance
- Duration: ~0.5s

### Phase 2: Install Extension
- Tests: File upload, installation, progress tracking
- Validates: Extension appears in list, correct status, metadata persistence
- Duration: ~2s

### Phase 3: Enable/Disable Extension
- Tests: State management endpoints
- Validates: Enable/disable operations, state persistence
- Duration: ~1s

### Phase 4: View Extension Details
- Tests: Detail retrieval API
- Validates: Complete metadata, runtime info, capabilities
- Duration: ~0.5s

### Phase 5: Uninstall Extension
- Tests: Uninstallation endpoint
- Validates: Complete removal, cleanup
- Duration: ~1s

**Total Duration**: ~8 seconds

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

## Troubleshooting

### WebUI Not Running
```
Error: Failed to connect to http://localhost:8000
Solution: Start the WebUI service first
```

### Extension Already Exists
```
Error: Extension test.e2e already installed
Solution: Manually delete the extension first
  curl -X DELETE http://localhost:8000/api/extensions/test.e2e
```

### Installation Timeout
```
The test handles this automatically by checking the extension list.
If issues persist, increase the timeout in phase2_install_extension().
```

## Test Configuration

Edit these variables in `run_e2e_test.py` to customize:

```python
BASE_URL = "http://localhost:8000"  # Change if WebUI on different port
TEST_EXT_ID = "test.e2e"            # Test extension ID
TEST_ZIP_PATH = "test_e2e_extension.zip"  # Temp file location
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run E2E Tests
  run: |
    cd /path/to/AgentOS
    python3 run_e2e_test.py
  timeout-minutes: 5
```

### Jenkins Example
```groovy
stage('E2E Tests') {
    steps {
        sh 'python3 run_e2e_test.py'
    }
}
```

## Continuous Testing

For continuous testing during development:

```bash
# Watch for changes and re-run tests
watch -n 60 python3 run_e2e_test.py
```

## Extending the Tests

To add new test phases:

1. Create a new `phaseN_description()` function
2. Add the phase to the `results` dictionary in `main()`
3. Call the phase function in the execution sequence
4. Update the test report template

## Related Documentation

- **ADR-EXT-002**: Python-Only Runtime Policy
- **Extension API Docs**: `/docs/api/extensions.md`
- **Extension Development Guide**: `/docs/development/extensions.md`

## Support

For issues or questions:
- Check the detailed test report: `E2E_TEST_REPORT.md`
- Review test output: `e2e_test_output.txt`
- Check WebUI logs for server-side errors

## Last Test Run

- **Date**: 2026-01-30
- **Status**: ✅ ALL PASSED
- **Duration**: ~8 seconds
- **Pass Rate**: 100% (5/5 phases)

---

*Generated as part of Task #15: E2E Testing for WebUI Extension Complete Workflow*
