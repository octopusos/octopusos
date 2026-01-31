# Coverage Measurement Quick Reference

## TL;DR

```bash
# Run coverage measurement (recommended)
./scripts/coverage_working.sh

# View HTML report
open htmlcov/index.html

# Current Status: 32.33% line coverage (target: 85%)
```

## One-Line Commands

```bash
# Full coverage with all reports
uv run pytest tests/unit --cov=agentos --cov-report=term-missing --cov-report=xml --cov-report=html --cov-branch

# Quick coverage check (terminal only)
uv run pytest tests/unit --cov=agentos --cov-report=term

# Coverage for specific module
uv run pytest tests/unit/task --cov=agentos.core.task --cov-report=term

# Coverage diff (only changed files)
uv run pytest tests/unit --cov=agentos --cov-report=term --cov-fail-under=85
```

## Script Usage

### Primary Script (Excludes Broken Tests)

```bash
# Run coverage excluding known broken tests
./scripts/coverage_working.sh
```

Output:
- ✅ Terminal summary with missing lines
- ✅ `coverage.xml` for CI
- ✅ `htmlcov/index.html` for local viewing

### Full Script (All Tests)

```bash
# Run all tests (may fail on broken tests)
./scripts/coverage.sh
```

⚠️ Currently has 3 import errors. Use `coverage_working.sh` instead.

## Reading Reports

### Terminal Output

```
Name                        Stmts   Miss Branch BrPart  Cover
-------------------------------------------------------------
agentos/core/task/states.py  120     45     30      5   68.75%
agentos/core/gates/gate.py     85     12     18      2   89.41%
```

- **Stmts**: Total statements
- **Miss**: Missed statements
- **Branch**: Total branches
- **BrPart**: Partially covered branches
- **Cover**: Overall coverage %

### HTML Report Structure

```
htmlcov/
├── index.html          # Overview (start here)
├── status.json         # Machine-readable status
└── *.html              # Per-file coverage details
```

Click any file to see:
- ✅ Green lines: Covered
- ❌ Red lines: Not covered
- ⚠️ Yellow lines: Partially covered (branches)

## Configuration Files

### pyproject.toml

```toml
[tool.coverage.run]
source = ["agentos"]
branch = true
omit = ["tests/*", "*/migrations/*"]

[tool.coverage.report]
precision = 2
skip_empty = true
```

Location: `/Users/pangge/PycharmProjects/AgentOS/pyproject.toml`

### .coveragerc (Alternative)

Not used. Configuration is in `pyproject.toml`.

## Common Issues

### Issue: "No data to report"

**Cause**: No tests executed or wrong source path

**Fix**:
```bash
# Ensure pytest finds tests
pytest tests/unit --collect-only

# Check coverage source
grep "source = " pyproject.toml
```

### Issue: "Module not found"

**Cause**: Missing dependencies

**Fix**:
```bash
# Install all dev dependencies
uv sync --all-extras

# Or install specific package
uv add numpy
```

### Issue: "Coverage didn't run"

**Cause**: pytest-cov not installed

**Fix**:
```bash
uv add --dev pytest-cov
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run tests with coverage
  run: |
    uv run pytest tests/unit \
      --cov=agentos \
      --cov-report=xml \
      --cov-fail-under=85

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest tests/unit --cov=agentos --cov-fail-under=85 || exit 1
```

## Coverage Goals

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| core.task.state_machine | ~60% | 95% | HIGH |
| core.task.states | ~65% | 95% | HIGH |
| core.runner | 0% | 85% | HIGH |
| core.gates | ~70% | 90% | HIGH |
| core.project | ~45% | 85% | MEDIUM |
| webui.api | ~50% | 80% | MEDIUM |

## Tips & Tricks

### Focus on Changed Files

```bash
# Get list of changed files
git diff --name-only HEAD~1 | grep '\.py$'

# Run coverage on specific files
uv run pytest tests/unit/task --cov=agentos.core.task
```

### Find Uncovered Lines

```bash
# Extract uncovered lines from terminal output
pytest tests/unit --cov=agentos --cov-report=term-missing | grep -E "^agentos.*[0-9]+%"
```

### Generate Badge

```bash
# Extract percentage for badge
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
rate = float(tree.getroot().attrib['line-rate']) * 100
print(f'![Coverage](https://img.shields.io/badge/coverage-{rate:.1f}%25-red)')
"
```

### Coverage Trending

```bash
# Save coverage history
mkdir -p .coverage_history
cp coverage.xml .coverage_history/coverage_$(date +%Y%m%d_%H%M%S).xml

# Compare with previous
diff <(grep line-rate .coverage_history/coverage_*.xml | tail -2 | head -1) \
     <(grep line-rate .coverage_history/coverage_*.xml | tail -1)
```

## Performance

| Test Set | Duration | Tests | Coverage |
|----------|----------|-------|----------|
| Unit only | ~60s | 1,674 | 32.33% |
| Integration | ~5min | ~200 | N/A |
| E2E | ~10min | ~50 | N/A |

**Recommendation**: Run unit tests for coverage, integration/e2e separately.

## Next Actions

1. **Fix broken tests**: 207 failures + 67 errors
2. **Add tests for core.runner**: Currently 0% coverage
3. **Improve state machine tests**: Target 95%+
4. **Add branch coverage**: Currently 17%, target 80%+
5. **Setup CI coverage gate**: Fail builds <85%

## Resources

- **Full Report**: `docs/testing/COVERAGE_REPORT.md`
- **HTML Report**: `htmlcov/index.html`
- **XML Report**: `coverage.xml`
- **Config**: `pyproject.toml` (lines 85-130)

---

**Last Updated**: 2026-01-30
**Current Coverage**: 32.33% (line), 17.04% (branch)
**Target**: 85%+ (line), 80%+ (branch)
