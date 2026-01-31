# Coverage Gates Quick Reference

## Gate Scripts

### 1. Scope Coverage Gate
```bash
python3 scripts/gate_coverage_scope.py
```
- **Checks**: Line ≥85%, Branch ≥70%
- **Scope**: `agentos/core/task` (state machine)
- **Exit**: 0=pass, 1=fail
- **Blocking**: Yes (on line coverage)

### 2. Project Coverage Gate
```bash
python3 scripts/gate_coverage_project.py
```
- **Checks**: Reports exist
- **Scope**: `agentos/**` (full repo)
- **Exit**: 0=pass, 1=fail
- **Blocking**: No (informational)

### 3. Combined Gates
```bash
./scripts/gate_coverage_all.sh
```
- **Runs**: Both gates sequentially
- **Exit**: 0=all pass, 1=scope fail
- **Blocking**: Scope only

## Prerequisites

Before running gates:
```bash
# Generate scope coverage
./scripts/coverage_scope_task.sh

# Generate project coverage
./scripts/coverage_project.sh
```

## Quick Test

```bash
# Full workflow
./scripts/coverage_scope_task.sh && \
./scripts/coverage_project.sh && \
./scripts/gate_coverage_all.sh
```

## Exit Code Logic

| Scenario | Scope | Project | Combined | Action |
|----------|-------|---------|----------|--------|
| All pass | 0 | 0 | 0 | Continue |
| Scope fail | 1 | - | 1 | Block merge |
| Project fail | 0 | 1 | 0 | Warn only |
| Both fail | 1 | 1 | 1 | Block merge |

## Output Examples

### Scope Pass
```
📊 Scope Coverage (agentos/core/task):
   Line Coverage:   87.40%
   Branch Coverage: 72.00%
✅ SCOPE COVERAGE GATE PASSED
```

### Scope Fail
```
📊 Scope Coverage (agentos/core/task):
   Line Coverage:   82.00%
   Branch Coverage: 65.00%
❌ SCOPE COVERAGE GATE FAILED
```

### Project Pass
```
📊 Project Coverage (agentos/** full repository):
   XML Report:  ✅ EXISTS
   HTML Report: ✅ EXISTS
📈 Current Project Coverage: 42.37%
✅ PROJECT COVERAGE GATE PASSED
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Scope Coverage Gate
  run: |
    ./scripts/coverage_scope_task.sh
    python3 scripts/gate_coverage_scope.py
```

### Pre-commit Hook
```bash
#!/bin/bash
python3 scripts/gate_coverage_scope.py || exit 1
```

## Files Created

- `scripts/gate_coverage_scope.py` (2.7K)
- `scripts/gate_coverage_project.py` (1.9K)
- `scripts/gate_coverage_all.sh` (771B)
- `scripts/README_DUAL_COVERAGE.md` (3.5K)
- `scripts/TEST_GATE_COVERAGE.md` (test report)

## Thresholds

### Scope (Blocking)
- Line: **85%** (hard requirement)
- Branch: **70%** (warning only)

### Project (Tracking)
- Line: **No threshold** (informational)
- Branch: **No threshold** (informational)

## Troubleshooting

### "coverage-scope.xml not found"
```bash
./scripts/coverage_scope_task.sh
```

### "coverage-project.xml not found"
```bash
./scripts/coverage_project.sh
```

### "Permission denied"
```bash
chmod +x scripts/gate_coverage*.py scripts/gate_coverage_all.sh
```

## Documentation

- **Full Guide**: `scripts/README_DUAL_COVERAGE.md`
- **Test Report**: `scripts/TEST_GATE_COVERAGE.md`
- **Coverage Scripts**: `scripts/README_COVERAGE.md`
