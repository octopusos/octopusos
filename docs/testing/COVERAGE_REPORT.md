# AgentOS Code Coverage Report

## Executive Summary

**Date**: 2026-01-30
**Coverage Tool**: pytest-cov (coverage.py)
**Test Scope**: Unit tests only (tests/unit/)

### Coverage Metrics

| Metric | Value | Status |
|--------|-------|--------|
| **Line Coverage** | 32.33% | ⚠️ Below Target |
| **Branch Coverage** | 17.04% | ⚠️ Below Target |
| **Combined Average** | 24.68% | ⚠️ Below Target |
| **Target** | ≥85% | ❌ Not Met |

### Test Execution Summary

- **Total Tests Collected**: 1,674
- **Tests Passed**: 1,396 (83.4%)
- **Tests Failed**: 207 (12.4%)
- **Tests Skipped**: 4 (0.2%)
- **Collection Errors**: 67 (4.0%)

## Configuration

### pyproject.toml Coverage Settings

```toml
[tool.coverage.run]
source = ["agentos"]
omit = [
    "tests/*",
    "*/tests/*",
    "**/test_*.py",
    "*/migrations/*",
    "**/migrations/*",
    "*/conftest.py",
    "*/__pycache__/*",
    "*/site-packages/*",
    "*/.venv/*",
    "*/venv/*",
    "agentos/webui/static/*",
    "agentos/webui/templates/*",
]
branch = true
parallel = true

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
skip_empty = true
```

## Running Coverage Reports

### Quick Start

```bash
# Run coverage measurement
./scripts/coverage_working.sh

# View HTML report in browser
open htmlcov/index.html

# View XML report for CI
cat coverage.xml
```

### Manual Execution

```bash
# Clean previous data
rm -f .coverage .coverage.*
rm -rf htmlcov/
rm -f coverage.xml

# Run with pytest
uv run pytest tests/unit \
    --cov=agentos \
    --cov-report=term-missing:skip-covered \
    --cov-report=xml:coverage.xml \
    --cov-report=html \
    --cov-branch
```

## Coverage Analysis

### Modules with 0% Coverage (Critical Gap)

The following core modules have no test coverage:

1. **Core Infrastructure**
   - `core.runner` - Task execution engine
   - `core.orchestrator` - Orchestration logic
   - `core.scheduler` - Task scheduling
   - `core.worker_pool` - Worker management
   - `core.recovery` - Recovery mechanisms

2. **LLM & Generation**
   - `core.llm` - LLM client abstractions
   - `core.generator` - Code generation
   - `core.generators` - Generator utilities

3. **Advanced Features**
   - `core.idempotency` - Idempotency checks
   - `core.healing` - Self-healing logic
   - `core.learning` - ML components
   - `core.locks` - Distributed locking
   - `core.review` - Code review automation

4. **Supervisor System**
   - `core.supervisor.policies` - Policy engine
   - `core.command.handlers` - Command handling

5. **Project Intelligence**
   - `core.project_kb.embedding` - Vector embeddings
   - `core.scanner` - Code scanning
   - `core.verify` - Verification logic

### Excluded Tests (Need Fixing)

The following test files are currently excluded due to import/dependency issues:

1. **tests/unit/store/test_answers_store.py**
   - **Issue**: Missing `AnswerNotFoundError` export
   - **Fix**: Add error class to `agentos.store.answers_store`

2. **tests/unit/test_vector_reranker.py**
   - **Issue**: numpy dependency not in core requirements
   - **Fix**: Move to optional dependencies or install numpy

3. **tests/unit/webui/api/***
   - **Issue**: Import path issue with conftest
   - **Fix**: Correct test discovery configuration

## Test Quality Issues

### Failed Tests (207 failures)

Major failure categories:

1. **Database Migration Tests** (67 errors)
   - `test_v18_migration.py` - Project repository schema
   - `test_v19_migration.py` - Auth profiles schema
   - `test_v20_migration.py` - Audit log enhancements

2. **API Tests** (multiple failures)
   - `tests/unit/api/test_projects_api.py`
   - Chat workflow tests
   - Task handler tests

3. **Workspace Layout Tests** (8 failures)
   - Path resolution issues
   - Project root detection

4. **Task Event Service** (9 errors)
   - Database schema issues

## Improvement Roadmap

### Phase 1: Fix Existing Tests (Priority: HIGH)

1. **Fix Migration Tests**
   - Ensure schema v18-v20 migrations work correctly
   - Target: 67 errors → 0 errors

2. **Fix Import Issues**
   - Add missing error classes
   - Install optional dependencies (numpy)
   - Fix webui/api test imports
   - Target: 3 collection errors → 0 errors

3. **Fix Failing Unit Tests**
   - Database connection issues
   - Mock strategy improvements
   - Target: 207 failures → <20 failures

### Phase 2: Cover Critical Modules (Priority: HIGH)

Target modules for 85%+ coverage:

1. **State Machine & Task Lifecycle**
   - `core.task.state_machine`
   - `core.task.states`
   - `core.runner.task_runner`
   - `core.gates.*`

2. **Project Management**
   - `core.project.service`
   - `core.project.repository`

3. **Recovery System**
   - `core.recovery.manager`
   - `core.checkpoints.manager`

### Phase 3: Comprehensive Coverage (Priority: MEDIUM)

1. Add integration tests for:
   - LLM provider interactions
   - End-to-end task execution
   - Multi-project scenarios

2. Increase branch coverage:
   - Error handling paths
   - Edge cases
   - Timeout/cancel scenarios

### Phase 4: CI/CD Integration (Priority: MEDIUM)

1. **Add Coverage Gates**
   ```yaml
   # .github/workflows/test.yml
   - name: Coverage Check
     run: |
       pytest --cov --cov-fail-under=85
   ```

2. **Coverage Reporting**
   - Upload to Codecov/Coveralls
   - PR comments with coverage diff
   - Fail on coverage decrease

## Reports Generated

### File Locations

| Report Type | Path | Purpose |
|-------------|------|---------|
| XML | `coverage.xml` | CI/CD integration, machine-readable |
| HTML | `htmlcov/index.html` | Local viewing, detailed analysis |
| Terminal | stdout | Quick feedback during development |

### HTML Report Features

The HTML report (`htmlcov/index.html`) provides:

- ✅ Per-file coverage breakdown
- ✅ Line-by-line coverage visualization
- ✅ Uncovered line highlighting
- ✅ Branch coverage details
- ✅ Sortable columns (name, coverage, lines)

### XML Report Usage

```bash
# Extract overall coverage
grep -oP 'line-rate="\K[0-9.]+' coverage.xml

# Find uncovered files
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
for cls in tree.findall('.//class'):
    if float(cls.attrib['line-rate']) < 0.85:
        print(cls.attrib['filename'])
"
```

## Next Steps

1. ✅ **COMPLETED**: Coverage measurement infrastructure
2. ⏳ **IN PROGRESS**: Fix broken tests
3. ⬜ **TODO**: Achieve 85% coverage on core modules
4. ⬜ **TODO**: Add coverage gates to CI/CD
5. ⬜ **TODO**: Weekly coverage review meetings

## Appendix

### Coverage Calculation Formula

```
Line Coverage = (Lines Executed / Total Executable Lines) × 100
Branch Coverage = (Branches Taken / Total Branches) × 100
Combined = (Line Coverage + Branch Coverage) / 2
```

### Recommended Tools

- **pytest-cov**: Coverage collection
- **coverage.py**: Backend coverage engine
- **Codecov**: Cloud coverage reporting
- **diff-cover**: Coverage for changed lines only

### References

- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
