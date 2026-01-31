# Test Quick Reference Guide

## Running E2E Tests

### Full E2E Test Suite
```bash
# Run all E2E scenarios (recommended)
python3 test_e2e.py

# Expected output: 5/5 scenarios passing in < 1 second
# Generates: E2E_TEST_REPORT.md
```

### Smoke Tests (Quick Sanity Check)
```bash
# Run smoke tests (< 2 minutes)
python3 test_smoke.py

# Expected output: 6/6 tests passing
# Generates: SMOKE_TEST_REPORT.md
```

---

## Test Scenarios Overview

### E2E Test Scenarios (test_e2e.py)

| Scenario | Command | Duration | Purpose |
|----------|---------|----------|---------|
| 1 | `/comm search` | 0.42s | Complete search flow validation |
| 2 | `/comm fetch` | 0.02s | Complete fetch flow validation |
| 3 | `/comm brief` | 0.02s | Complex pipeline (multi-query + fetch) |
| 4 | Markdown | 0.02s | Rendering format verification |
| 5 | Audit | 0.02s | Audit logging verification |

### Smoke Test Scenarios (test_smoke.py)

| Test | Purpose | Validates |
|------|---------|-----------|
| 1 | Service Startup | Module imports and instantiation |
| 2 | Command Registration | /comm command availability |
| 3 | Basic Search | Search with mock adapter |
| 4 | Basic Fetch | Fetch with mock adapter |
| 5 | Phase Gate | Planning phase blocks commands |
| 6 | SSRF Protection | Security policy enforcement |

---

## Test Reports Generated

### Primary Reports
- `E2E_TEST_REPORT.md` - Detailed E2E test results with scenarios
- `E2E_TEST_SUMMARY.md` - Executive summary of E2E testing
- `SMOKE_TEST_REPORT.md` - Smoke test results

### Supporting Documents
- `SMOKE_TEST_EXECUTION_SUMMARY.md` - Smoke test overview
- `README_SMOKE_TEST.md` - Smoke test documentation
- `TEST_QUICK_REFERENCE.md` - This guide

---

## Understanding Test Results

### Success Indicators
```
✅ All scenarios PASSED
✅ Performance within limits
✅ Audit logs generated
✅ Markdown formatting correct
```

### Failure Indicators
```
❌ Scenario FAILED - Check error message
⚠️  Performance exceeds limit - Optimization needed
✗ Assertion failed - Code fix required
```

---

## Test Architecture

### E2E Test Flow
```
Test Input
    ↓
Mock CommunicationAdapter (controlled responses)
    ↓
Real ChatEngine
    ↓
Real CommCommandHandler
    ↓
Real CommunicationAdapter logic
    ↓
Mocked external connectors
    ↓
Validate Output + Audit Trail
```

### Smoke Test Flow
```
Quick Checks
    ↓
Module Import Tests
    ↓
Command Registration
    ↓
Mock Execution Tests
    ↓
Security Policy Tests
    ↓
Fast Feedback (< 2 min)
```

---

## Test Coverage Matrix

| Component | E2E Test | Smoke Test | Unit Test |
|-----------|----------|------------|-----------|
| ChatEngine | ✅ Full | ✅ Basic | ✅ |
| CommCommandHandler | ✅ Full | ✅ Basic | ✅ |
| CommunicationAdapter | ✅ Full | ✅ Mock | ✅ |
| CommunicationService | ✅ Integrated | ✅ Mock | ✅ |
| Phase Gate | ✅ | ✅ | ✅ |
| SSRF Protection | ✅ | ✅ | ✅ |
| Audit Logging | ✅ | ❌ | ✅ |
| Markdown Rendering | ✅ | ❌ | ❌ |

---

## Troubleshooting

### Test Failures

**Scenario fails with "Command not found"**
- Check: `/comm` command registration
- Fix: Verify `register_comm_command()` is called
- File: `agentos/core/chat/handlers.py`

**Scenario fails with "blocked by phase gate"**
- Check: `execution_phase` in session metadata
- Fix: Ensure session has `execution_phase: "execution"`
- Expected: Planning phase should block commands

**Scenario fails with "No audit ID"**
- Check: CommunicationAdapter mock setup
- Fix: Ensure mock returns `audit_id` in metadata
- File: Test mock configuration

**Performance exceeds limit**
- Check: System load and resource availability
- Note: E2E tests with mocks should complete in < 1s
- Action: Re-run tests or investigate system issues

### Common Issues

**Import errors**
```bash
# Solution: Ensure you're in project directory
cd /Users/pangge/PycharmProjects/AgentOS
python3 test_e2e.py
```

**Deprecation warnings**
```
# Known issue: datetime.utcnow() deprecation
# Status: Does not affect test results
# Action: Can be ignored or fixed in future update
```

---

## Running Individual Scenarios

### Run specific E2E scenario
```python
# Edit test_e2e.py and comment out unwanted scenarios
# Or create a custom test file:

from test_e2e import test_e2e_search, E2ETestRunner

runner = E2ETestRunner()
runner.run_test("Custom: Search Only", test_e2e_search, timeout=10)
runner.print_summary()
```

### Run with verbose output
```bash
# Add debug prints in test functions
python3 test_e2e.py 2>&1 | tee test_output.log
```

---

## Test Maintenance

### When to Update Tests

1. **New command added** → Add E2E scenario
2. **Command behavior changed** → Update assertions
3. **New security check** → Add smoke test
4. **Performance degradation** → Adjust timeout limits

### Test File Structure
```
test_e2e.py
├── E2ETestRunner (test harness)
├── test_e2e_search() (scenario 1)
├── test_e2e_fetch() (scenario 2)
├── test_e2e_brief() (scenario 3)
├── test_markdown_rendering() (scenario 4)
├── test_audit_logging() (scenario 5)
└── generate_report() (reporting)
```

---

## Performance Benchmarks

### E2E Tests (Mock Mode)
- Total Duration: 0.51s
- Search: 0.42s (82% of total)
- Other scenarios: < 0.02s each

### Real Connector Tests (Expected)
- Search: 3-8s (DuckDuckGo API)
- Fetch: 2-5s (HTTP request + parsing)
- Brief: 15-30s (multi-query + concurrent fetch)

---

## Next Steps After E2E

1. **Scenario Coverage Testing** - Edge cases and error conditions
2. **Real Simulation Testing** - Live connectors with real APIs
3. **Load Testing** - Concurrent users and requests
4. **Security Testing** - Penetration testing and fuzzing
5. **User Acceptance Testing** - Real user workflows

---

## Contact & Support

**Test Suite Author**: Claude Sonnet 4.5 (Agent Assistant)
**Test Framework**: Python unittest with mocking
**Documentation**: See reports in project root
**Issues**: Review error messages and check troubleshooting section

---

**Last Updated**: 2026-01-31
**Test Status**: ✅ All E2E Tests Passing
