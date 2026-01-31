# E2E Test Quick Start Guide
## SEARCH → FETCH → BRIEF Pipeline

This guide provides quick commands for running the E2E tests for the CommunicationOS SEARCH→FETCH→BRIEF pipeline.

---

## Prerequisites

```bash
# Ensure you're in the project root
cd /Users/pangge/PycharmProjects/AgentOS

# Ensure pytest and dependencies are installed
python3 -m pip install pytest pytest-asyncio pytest-cov
```

---

## Quick Commands

### 1. Run All Tests (Fast Mode - Recommended)

```bash
# Using pytest directly
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v -m "not slow"

# Using test runner script
./scripts/run_communication_e2e_tests.sh --fast
```

**Expected**: 14 passed, 2 deselected in ~0.88s

---

### 2. Run Specific Test Groups

#### Golden Path Test Only
```bash
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py::test_golden_path_full_pipeline -v
```

#### Phase Gate Tests
```bash
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v -k "phase_gate"
```
**Expected**: 3 passed

#### Output Format Tests
```bash
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v -k "output_format"
```
**Expected**: 3 passed

#### Error Handling Tests
```bash
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v -k "handles"
```
**Expected**: 3 passed

#### Gate Execution Tests
```bash
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v -k "gate_"
```
**Expected**: 2 passed

---

### 3. Run with Different Verbosity Levels

#### Minimal Output
```bash
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -q
```

#### Standard Output
```bash
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v
```

#### Detailed Output (Show Print Statements)
```bash
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v -s
```

---

### 4. Run with Coverage Report

```bash
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py \
    --cov=agentos.core.communication \
    --cov=agentos.core.chat.communication_adapter \
    --cov-report=html \
    --cov-report=term
```

**Output**: HTML coverage report in `htmlcov/index.html`

---

### 5. Run Live Tests (Requires Internet)

```bash
# Remove skip markers and run
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v

# Or use test runner with --live flag
./scripts/run_communication_e2e_tests.sh --live
```

⚠️ **Warning**: Live tests make real network requests and may be rate-limited.

---

## Test Categories

| Category | Command | Tests | Duration |
|----------|---------|-------|----------|
| **All Fast** | `pytest -m "not slow"` | 14 | ~0.9s |
| **Golden Path** | `pytest::test_golden_path_full_pipeline` | 1 | ~0.3s |
| **Phase Gates** | `pytest -k "phase_gate"` | 3 | ~0.3s |
| **Output Format** | `pytest -k "output_format"` | 3 | ~0.2s |
| **Error Handling** | `pytest -k "handles"` | 3 | ~0.3s |
| **Gates** | `pytest -k "gate_"` | 2 | ~0.5s |
| **Concurrency** | `pytest::test_concurrent_fetch_operations` | 1 | ~0.2s |
| **Trust Tier** | `pytest::test_trust_tier_hierarchy` | 1 | ~0.2s |
| **Live** | `pytest` (all) | 16 | ~10-30s |

---

## Troubleshooting

### Test Collection Fails

```bash
# Verify test can be collected
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py --collect-only
```

**Expected**: Should show 16 collected items

---

### Import Errors

```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:/Users/pangge/PycharmProjects/AgentOS"

# Or run from project root
cd /Users/pangge/PycharmProjects/AgentOS
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py
```

---

### Mock Errors

If tests fail with mock-related errors:

```bash
# Install unittest.mock (usually built-in)
python3 -c "from unittest.mock import AsyncMock, MagicMock, patch; print('OK')"
```

---

### Gate Script Errors

If gate tests fail:

```bash
# Verify gate scripts exist
ls -la scripts/gates/gate_no_semantic_in_search.py
ls -la scripts/gates/gate_no_sql_in_code.py

# Run gates manually
python3 scripts/gates/gate_no_semantic_in_search.py
python3 scripts/gates/gate_no_sql_in_code.py
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Communication Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - name: Install dependencies
        run: |
          pip install pytest pytest-asyncio pytest-cov
          pip install -r requirements.txt
      - name: Run E2E tests
        run: |
          pytest tests/integration/communication/test_golden_path_search_fetch_brief.py \
            -v -m "not slow" --tb=short
```

---

## Test Output Examples

### Success Output
```
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0
plugins: anyio-4.12.1, asyncio-1.3.0, cov-7.0.0
collecting ... collected 16 items / 2 deselected / 14 selected

tests/integration/communication/test_golden_path_search_fetch_brief.py::test_golden_path_full_pipeline PASSED [  7%]
tests/integration/communication/test_golden_path_search_fetch_brief.py::test_phase_gate_blocks_unverified PASSED [ 14%]
...
======================= 14 passed, 2 deselected in 0.88s =======================
```

---

### Failure Output Example
```
=================================== FAILURES ===================================
________________________ test_golden_path_full_pipeline ________________________
tests/integration/communication/test_golden_path_search_fetch_brief.py:264: in test_golden_path_full_pipeline
    assert is_valid, f"Phase gate failed: {error}"
E   AssertionError: Phase gate failed: ...
```

---

## Performance Benchmarks

Expected test durations on standard hardware:

| Test | Expected Duration |
|------|-------------------|
| `test_golden_path_full_pipeline` | < 0.5s |
| `test_phase_gate_blocks_unverified` | < 0.1s |
| `test_phase_gate_requires_minimum_docs` | < 0.1s |
| `test_phase_gate_accepts_verified_sources` | < 0.2s |
| `test_search_output_format_compliant` | < 0.1s |
| `test_fetch_output_format_compliant` | < 0.1s |
| `test_brief_output_format_compliant` | < 0.1s |
| `test_gate_no_semantic_in_search_passes` | < 0.3s |
| `test_gate_no_sql_in_code_passes` | < 0.3s |
| `test_search_handles_network_errors` | < 0.2s |
| `test_fetch_handles_ssrf_protection` | < 0.2s |
| `test_brief_handles_insufficient_sources` | < 0.1s |
| `test_concurrent_fetch_operations` | < 0.2s |
| `test_trust_tier_hierarchy` | < 0.1s |

**Total (Fast Tests)**: < 1.0s

---

## Developer Workflow

### Before Committing

```bash
# 1. Run fast tests
./scripts/run_communication_e2e_tests.sh --fast

# 2. If all pass, run full test suite (optional)
./scripts/run_communication_e2e_tests.sh

# 3. Check coverage (optional)
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py \
    --cov=agentos.core.communication --cov-report=term-missing
```

---

### After Modifying Pipeline Code

```bash
# Run golden path test to verify basic functionality
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py::test_golden_path_full_pipeline -v

# If golden path passes, run full suite
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v -m "not slow"
```

---

### After Modifying Phase Gates

```bash
# Run phase gate tests
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v -k "phase_gate"

# Run gate execution tests
python3 -m pytest tests/integration/communication/test_golden_path_search_fetch_brief.py -v -k "gate_"
```

---

## Related Documentation

- **Full Test Report**: `E2E_TEST_EXECUTION_REPORT.md`
- **ADR**: `docs/adr/ADR-COMM-002-SEARCH-FETCH-BRIEF-Pipeline.md`
- **Test File**: `tests/integration/communication/test_golden_path_search_fetch_brief.py`
- **Test Runner**: `scripts/run_communication_e2e_tests.sh`

---

## Support

### Common Issues

1. **Import errors**: Ensure `PYTHONPATH` includes project root
2. **Mock errors**: Verify `unittest.mock` is available
3. **Gate failures**: Verify gate scripts exist and are executable
4. **Slow tests**: Use `-m "not slow"` to skip live tests

---

### Getting Help

```bash
# Show pytest help
python3 -m pytest --help

# Show available markers
python3 -m pytest --markers

# Show available fixtures
python3 -m pytest --fixtures
```

---

**Quick Start Author**: Claude Sonnet 4.5
**Last Updated**: 2026-01-31
**pytest Version**: 9.0.2
**Python Version**: 3.14.2
