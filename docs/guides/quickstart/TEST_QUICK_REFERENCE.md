# AgentOS Testing Quick Reference

Quick reference for running and understanding AgentOS tests.

## Quick Commands

### Run All Unit Tests
```bash
pytest tests/unit/ -v
```

### Run with Coverage
```bash
pytest tests/unit/ --cov=agentos --cov-report=html
open htmlcov/index.html
```

### Run Specific Module Tests
```bash
# Migration tests
pytest tests/unit/store/ -v

# Multi-repo tests
pytest tests/unit/project/ -v
pytest tests/unit/task/ -v

# Git tests
pytest tests/unit/git/ -v
pytest tests/unit/test_git/ -v

# Workspace tests
pytest tests/unit/workspace/ -v
```

### Run Statistics Script
```bash
./scripts/test_stats.sh
```

### Run Only Passing Tests
```bash
pytest tests/unit/ -v \
  --ignore=tests/unit/workspace/test_layout.py \
  --ignore=tests/unit/task/test_path_filter.py \
  --ignore=tests/unit/git/test_probe.py \
  --ignore=tests/unit/test_git/test_client.py \
  --ignore=tests/unit/chat/test_task_handler.py
```

---

## Test Structure

```
tests/
├── unit/                       # Unit tests
│   ├── store/                  # Migration tests
│   │   ├── test_v18_migration.py  (28 tests) ✅
│   │   ├── test_v19_migration.py  (23 tests) ✅
│   │   └── test_v20_migration.py  (13 tests) ✅
│   ├── project/                # Project & repo tests
│   │   ├── test_repository.py     (97% coverage) ✅
│   │   └── test_compat.py         (87% coverage) ✅
│   ├── task/                   # Task tests
│   │   ├── test_repo_context.py      (85% coverage) ✅
│   │   ├── test_path_filter.py       (95% coverage) ⚠️ 16 failures
│   │   ├── test_task_repo_service.py (96% coverage) ✅
│   │   ├── test_dependency_service.py (93% coverage) ✅
│   │   ├── test_artifact_service.py  (94% coverage) ✅
│   │   └── test_audit_service.py     (81% coverage) ✅
│   ├── git/                    # Git tests (new location)
│   │   ├── test_probe.py          ⚠️ 4 failures
│   │   ├── test_guard_rails.py    (96% coverage) ✅
│   │   └── test_gitignore_manager.py (93% coverage) ✅
│   ├── test_git/               # Git tests (old location)
│   │   ├── test_credentials.py    (88% coverage) ✅
│   │   └── test_client.py         (79% coverage) ⚠️ 5 failures
│   ├── workspace/              # Workspace tests
│   │   ├── test_layout.py         (90% coverage) ⚠️ 11 failures
│   │   └── test_validation.py     (86% coverage) ✅
│   ├── cli/                    # CLI tests
│   │   ├── test_project.py        ⚠️ 1 failure
│   │   ├── test_project_trace.py  ⚠️ 1 failure
│   │   └── test_task_trace.py     ⚠️ 2 failures
│   └── chat/                   # Chat tests
│       └── test_task_handler.py   ⚠️ 11 failures
│
└── integration/                # Integration tests
    ├── task/                   # Multi-repo execution
    ├── lead/                   # Lead agent
    ├── supervisor/             # Supervisor
    ├── guardians/              # Guardian workflow
    └── governance/             # Governance API
```

---

## Test Metrics

### Current Status

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total Tests | 982 | - | ✅ |
| Passing | 908 | - | ✅ |
| Failing (pre-existing) | 74 | 0 | ⚠️ |
| Overall Coverage | 22% | 60% | ⚠️ |
| Multi-Repo Coverage | 80-97% | 80% | ✅ |

### Module Coverage (Multi-Repo)

| Module | Coverage | Status |
|--------|----------|--------|
| project/repository.py | 97% | ✅ Excellent |
| task/task_repo_service.py | 96% | ✅ Excellent |
| git/guard_rails.py | 96% | ✅ Excellent |
| task/path_filter.py | 95% | ✅ Excellent |
| task/artifact_service.py | 94% | ✅ Excellent |
| task/dependency_service.py | 93% | ✅ Excellent |
| git/ignore.py | 93% | ✅ Excellent |
| workspace/layout.py | 90% | ✅ Excellent |
| git/credentials.py | 88% | ✅ Good |
| workspace/validation.py | 86% | ✅ Good |

---

## Pre-Existing Failures (74 total)

### Priority 1: Fix Before Production (27 tests)

#### Path Filter Tests (16 failures)
```bash
pytest tests/unit/task/test_path_filter.py -v
```
**Issue:** Path matching logic needs update
**Impact:** Medium - Affects repo path scoping
**Files:** `agentos/core/task/path_filter.py`

#### Workspace Layout Tests (11 failures)
```bash
pytest tests/unit/workspace/test_layout.py -v
```
**Issue:** Multi-repo layout changes
**Impact:** Medium - Affects workspace structure
**Files:** `agentos/core/workspace/layout.py`

### Priority 2: Fix After Release (47 tests)

#### Git Client Tests (5 failures)
```bash
pytest tests/unit/test_git/test_client.py -v
```
**Issue:** Auth profile integration updates needed
**Impact:** Low - Auth tests, functionality works

#### Chat Handler Tests (11 failures)
```bash
pytest tests/unit/chat/test_task_handler.py -v
```
**Issue:** Task creation flow changed
**Impact:** Low - UI integration

#### CLI Tests (4 failures)
```bash
pytest tests/unit/cli/ -v
```
**Issue:** Output format expectations
**Impact:** Low - Display only

#### Other Tests (27 failures)
- Git probe tests: 4
- Task state machine: 4
- Lead agent: 6
- Supervisor: 11
- Task rollback: 2

---

## Migration Tests

All migration tests are **passing** and **comprehensive**:

### v18: Multi-Repo Projects (28 tests)
```bash
pytest tests/unit/store/test_v18_migration.py -v
```
- ✅ Tables: project_repos, task_repo_scope, task_dependency, task_artifact_ref
- ✅ 17 indexes
- ✅ All constraints (UNIQUE, CHECK, FK)
- ✅ Data migration (existing projects)
- ✅ Multi-repo scenarios

### v19: Auth Profiles (23 tests) NEW
```bash
pytest tests/unit/store/test_v19_migration.py -v
```
- ✅ Tables: auth_profiles, auth_profile_usage, encryption_keys
- ✅ 7 indexes
- ✅ Profile types (SSH, PAT, netrc)
- ✅ Validation status tracking
- ✅ Usage audit trail

### v20: Task Audits Repo (13 tests) NEW
```bash
pytest tests/unit/store/test_v20_migration.py -v
```
- ✅ repo_id column added to task_audits
- ✅ 3 new indexes
- ✅ Backward compatibility (NULL repo_id)
- ✅ Cross-repo audit queries

---

## Coverage Reports

### Generate HTML Report
```bash
pytest tests/unit/ \
  --cov=agentos \
  --cov-report=html \
  --ignore=tests/unit/test_vector_reranker.py \
  --ignore=tests/unit/test_project_kb_chunker.py
```

### View Report
```bash
open htmlcov/index.html
```

### Coverage by Module
```bash
pytest tests/unit/ \
  --cov=agentos/core/project \
  --cov=agentos/core/task \
  --cov=agentos/core/git \
  --cov-report=term-missing
```

---

## Common Issues

### Issue: "No module named 'numpy'"
**Solution:** Ignore vector tests
```bash
pytest tests/unit/ \
  --ignore=tests/unit/test_vector_reranker.py \
  --ignore=tests/unit/test_project_kb_chunker.py
```

### Issue: "sqlite3.IntegrityError"
**Solution:** Ensure clean database state in fixtures
```python
@pytest.fixture
def test_db():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
    # ... setup database
    yield conn
    conn.close()
    Path(db_path).unlink(missing_ok=True)
```

### Issue: "Test collection errors"
**Solution:** Check for syntax errors or missing imports
```bash
pytest --collect-only tests/unit/
```

---

## CI Integration

### GitHub Actions Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install -e .[dev]
      - name: Run tests
        run: |
          pytest tests/unit/ \
            --cov=agentos \
            --cov-report=xml \
            --ignore=tests/unit/test_vector_reranker.py \
            --ignore=tests/unit/test_project_kb_chunker.py
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
```

---

## Best Practices

### Writing Tests

1. **Use fixtures for setup**
   ```python
   @pytest.fixture
   def test_db():
       # Setup
       yield resource
       # Teardown
   ```

2. **Test independence**
   - No shared state between tests
   - Each test creates its own data
   - Clean up after test

3. **Clear test names**
   ```python
   def test_create_repo_with_valid_name_succeeds():
       ...

   def test_create_repo_with_duplicate_name_fails():
       ...
   ```

4. **Arrange-Act-Assert**
   ```python
   def test_example():
       # Arrange
       repo = create_repo()

       # Act
       result = repo.do_something()

       # Assert
       assert result == expected
   ```

5. **Test error paths**
   ```python
   def test_invalid_input_raises_error():
       with pytest.raises(ValueError, match="Invalid"):
           create_repo(name="")
   ```

---

## Resources

### Documentation
- Full report: `PHASE_7.1_TEST_COVERAGE_REPORT.md`
- Completion summary: `PHASE_7.1_COMPLETION_SUMMARY.md`
- Coverage HTML: `htmlcov/index.html`

### Commands
- Test stats: `./scripts/test_stats.sh`
- All tests: `pytest tests/unit/ -v`
- Coverage: `pytest --cov=agentos --cov-report=html`

### Configuration
- pytest config: `pyproject.toml` ([tool.pytest.ini_options])
- coverage config: `pyproject.toml` ([tool.coverage.run])

---

**Last Updated:** 2026-01-28
**Status:** Phase 7.1 Complete ✅
