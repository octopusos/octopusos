# DB Integrity Gate System

## Overview

The DB Integrity Gate System is a multi-layer defense mechanism that ensures **exactly one database instance** exists in AgentOS at all times. It prevents anyone from accidentally or intentionally introducing a second DB instance, dual-table systems, or violating the single-DB-entry-point architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Gate System Layers                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 1: Code Pattern Gates                                 │
│  ├── gate_no_sqlite_connect_enhanced.py                     │
│  │   └── Detects: Direct DB connections, new Store classes  │
│  ├── gate_single_db_entry.py                                │
│  │   └── Detects: Multiple get_db() functions               │
│  └── gate_no_sql_in_code.py                                 │
│      └── Detects: SQL schema changes in code                │
│                                                               │
│  Layer 2: Schema Gates                                       │
│  └── gate_no_duplicate_tables.py                            │
│      └── Detects: Duplicate tables in database              │
│                                                               │
│  Layer 3: Enforcement Points                                 │
│  ├── Pre-commit hooks (local)                               │
│  ├── CI/CD workflows (GitHub Actions)                       │
│  └── Manual verification (run_all_gates.sh)                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Gates Reference

### Gate 1: Enhanced SQLite Connect Check

**Script**: `scripts/gates/gate_no_sqlite_connect_enhanced.py`

**Purpose**: Detect direct database connections and dual-table system attempts

**Checks**:
- Direct `sqlite3.connect()` usage
- Direct `apsw.Connection()` usage
- Creation of new Store classes (`SessionStore`, `MessageStore`, etc.)
- Direct SQL table creation (`CREATE TABLE sessions/messages`)
- Direct DB path access (`get_db_path()`, `AGENTOS_DB_PATH`)
- Hardcoded database file paths (`.sqlite`, `.db`)

**Whitelist**: See `WHITELIST` constant in script for approved exceptions

**Fix Violations**:
```python
# ❌ WRONG
import sqlite3
conn = sqlite3.connect("my.db")

# ✅ CORRECT
from agentos.core.db import registry_db
conn = registry_db.get_db()
```

### Gate 2: Schema Duplicate Detection

**Script**: `scripts/gates/gate_no_duplicate_tables.py`

**Purpose**: Verify database schema has no duplicate tables

**Checks**:
- Multiple session tables (only `chat_sessions` allowed)
- Multiple message tables (only `chat_messages` allowed)
- Non-legacy `webui_*` tables
- Similar table names that might indicate duplication

**Severity Levels**:
- **Critical**: Duplicate session/message tables
- **High**: Non-legacy webui_* tables
- **Medium**: Similar table names

**Fix Violations**:
1. Drop duplicate tables (after data migration if needed)
2. Rename `webui_*` tables to `webui_*_legacy`
3. Consolidate data into canonical tables
4. Update code to use canonical table names

### Gate 3: SQL Schema Changes in Code

**Script**: `scripts/gates/gate_no_sql_in_code.py`

**Purpose**: Ensure all schema changes go through migration scripts

**Checks**:
- `CREATE TABLE` statements
- `DROP TABLE` statements
- `ALTER TABLE` statements
- `CREATE INDEX` statements
- `PRAGMA table_info` (often precedes schema changes)

**Whitelist**:
- `agentos/store/migrations/` (migration scripts)
- `tests/` (test files)
- `agentos/core/brain/store/sqlite_schema.py` (read-only schema docs)

**Fix Violations**:
```python
# ❌ WRONG - Schema change in code
def init():
    conn.execute("CREATE TABLE IF NOT EXISTS my_table ...")

# ✅ CORRECT - Create migration script
# agentos/store/migrations/0042_add_my_table.py
def upgrade(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS my_table ...")
```

### Gate 4: Single DB Entry Point

**Script**: `scripts/gates/gate_single_db_entry.py`

**Purpose**: Verify only one `get_db()` function exists

**Checks**:
- Multiple `get_db()` function definitions
- Multiple `_get_conn()` method definitions
- Multiple `get_connection()` functions
- Unauthorized connection pools (thread-local storage)

**Expected Entry Points**:
- `agentos/core/db/registry_db.py` - The ONLY `get_db()` function
- `agentos/core/db/writer.py` - Write operations with `_get_conn()`

**Fix Violations**:
```python
# ❌ WRONG - Creating own entry point
def get_db():
    return sqlite3.connect("my.db")

# ✅ CORRECT - Use official entry point
from agentos.core.db import registry_db

def my_function():
    conn = registry_db.get_db()
```

### Gate 5: Legacy SQLite Connect Check

**Script**: `scripts/gate_no_sqlite_connect.py` (original)

**Purpose**: Legacy gate with extensive whitelist

**Note**: This gate is less strict and exists for backward compatibility during migration period. New code should pass all enhanced gates.

## Running Gates

### Locally (Manual)

Run all gates:
```bash
./scripts/gates/run_all_gates.sh
```

Run individual gates:
```bash
python3 scripts/gates/gate_no_sqlite_connect_enhanced.py
python3 scripts/gates/gate_no_duplicate_tables.py
python3 scripts/gates/gate_no_sql_in_code.py
python3 scripts/gates/gate_single_db_entry.py
```

### Pre-Commit Hook (Automatic)

Install pre-commit hook:
```bash
./scripts/gates/install_pre_commit_hook.sh
```

The hook will automatically run before each commit. To bypass (NOT RECOMMENDED):
```bash
git commit --no-verify
```

### CI/CD (GitHub Actions)

Gates run automatically on:
- Push to `master`, `main`, or `develop` branches
- Pull requests to these branches

Workflow file: `.github/workflows/gate-db-integrity.yml`

## Whitelist Management

### Adding to Whitelist

If you need to add a file to a gate's whitelist:

1. **Verify it's necessary**: Can you refactor to avoid the whitelist?

2. **Add with justification**:
   ```python
   WHITELIST = {
       # ... existing entries ...
       "agentos/new/feature.py",  # TODO PR-X: Migrate to registry_db
   }
   ```

3. **Add migration task**: Create a task to remove the whitelist entry in a future PR

4. **Document**: Add comment explaining why it's whitelisted and when it will be removed

### Removing from Whitelist

When migrating legacy code:

1. **Fix code**: Update to use `registry_db.get_db()`
2. **Test**: Verify functionality unchanged
3. **Remove from whitelist**: Delete entry from gate script
4. **Run gates**: Ensure no violations
5. **Commit**: Include whitelist update in migration PR

## Troubleshooting

### Gate Fails Locally

1. **Read the output**: Gates provide detailed violation reports
2. **Identify the issue**: Check file path and line number
3. **Fix the code**: Follow the "Fix Violations" guidance
4. **Re-run gates**: `./scripts/gates/run_all_gates.sh`
5. **Commit**: Only commit when all gates pass

### Gate Fails in CI

1. **Check CI logs**: Download gate reports from GitHub Actions artifacts
2. **Reproduce locally**: Run the same gate locally
3. **Fix and push**: Fix code and push again
4. **Verify**: Check CI run results

### False Positive

If a gate reports a false positive:

1. **Verify it's truly false**: Are you sure the code is correct?
2. **Check whitelist**: Should the file be whitelisted?
3. **Improve gate**: If the pattern is wrong, update the gate script
4. **Submit issue**: Document the false positive for team review

### Emergency Bypass

**WARNING**: Only use in true emergencies (production down, critical hotfix)

```bash
# Bypass pre-commit hook
git commit --no-verify -m "EMERGENCY: Critical hotfix"

# Bypass CI (cannot bypass - intentionally)
# You must fix the code or update the whitelist
```

After emergency bypass:
1. **Create issue**: Document what was bypassed and why
2. **Create follow-up task**: Fix the violation in next sprint
3. **Notify team**: Ensure everyone knows about the bypass

## Best Practices

### For Developers

1. **Run gates before committing**: `./scripts/gates/run_all_gates.sh`
2. **Install pre-commit hook**: Catches issues early
3. **Use official entry points**: Always use `registry_db.get_db()`
4. **No schema in code**: Use migration scripts for schema changes
5. **Don't create new Store classes**: Extend existing ones

### For Reviewers

1. **Check gate status**: Ensure CI gates passed
2. **Review whitelist changes**: Question any new whitelist entries
3. **Verify migrations**: Ensure schema changes have proper migrations
4. **Look for patterns**: Watch for attempts to bypass gates

### For Architects

1. **Keep whitelist minimal**: Aggressive migration to `registry_db`
2. **Update gates as needed**: Add patterns as new violations emerge
3. **Document exceptions**: Clear justification for whitelisted files
4. **Plan migrations**: Roadmap to remove all whitelist entries

## Architecture Principles

### Single DB Instance

**Principle**: There is exactly one database instance in AgentOS

**Implementation**:
- Single DB file: `store/registry.sqlite`
- Single entry point: `agentos/core/db/registry_db.py`
- Single connection pool: Thread-local in `registry_db.py`

**Violations**:
- Creating a second database file
- Creating duplicate tables for the same data
- Creating custom connection pools

### Schema as Code

**Principle**: Database schema is managed through migration scripts

**Implementation**:
- Migrations in `agentos/store/migrations/`
- Automatic migration on startup
- Version tracking in database

**Violations**:
- `CREATE TABLE` statements in application code
- Direct schema modifications via SQL
- Schema changes without migration scripts

### Unified Access

**Principle**: All database access goes through `registry_db.get_db()`

**Implementation**:
- No direct `sqlite3.connect()` calls
- No custom connection functions
- Consistent PRAGMA settings

**Violations**:
- Multiple `get_db()` functions
- Direct connection creation
- Custom connection pools

## Metrics

### Gate Performance

Current gate run time (typical):
- Gate 1 (Enhanced SQLite): ~2-3 seconds
- Gate 2 (Schema Duplicate): ~0.5 seconds
- Gate 3 (SQL in Code): ~2-3 seconds
- Gate 4 (Single Entry): ~2-3 seconds
- **Total**: ~7-10 seconds

### Coverage

Files monitored:
- All `.py` files in `agentos/`
- Database schema
- Migration scripts

Whitelist size:
- ~70-80 legacy files (to be migrated)
- Goal: <10 permanent whitelist entries

## Future Enhancements

### Planned Improvements

1. **Faster scanning**: Parallel gate execution
2. **Better reporting**: HTML reports with charts
3. **Auto-fix mode**: Automatic correction of simple violations
4. **IDE integration**: Real-time violation detection in editors
5. **Migration assistant**: Tool to help migrate whitelisted files

### Roadmap

**Q2 2026**:
- Reduce whitelist to <50 files
- Add auto-fix for common patterns
- IDE plugin for real-time checking

**Q3 2026**:
- Reduce whitelist to <25 files
- Full migration guide and tools
- Performance optimization (sub-5s total run time)

**Q4 2026**:
- Reduce whitelist to <10 files (permanent only)
- 100% coverage of DB access patterns
- Zero tolerance for new violations

## Support

### Getting Help

1. **Documentation**: Read this guide thoroughly
2. **Examples**: Check existing code that passes gates
3. **Team chat**: Ask in #database or #architecture channels
4. **Office hours**: Thursday 2-3pm (architecture office hours)

### Reporting Issues

If you find a bug in the gate system:

1. **Check existing issues**: Search GitHub issues
2. **Reproduce**: Provide minimal reproduction case
3. **Submit issue**: Use "Gate System" label
4. **Include logs**: Attach gate output

### Contributing

To improve the gate system:

1. **Discuss first**: Propose changes in architecture meeting
2. **Submit PR**: Include tests for new gate logic
3. **Update docs**: Keep this document in sync
4. **Test thoroughly**: Ensure no false positives

## References

- [ADR-001: Single Database Instance](./adr/ADR-001-single-database.md)
- [Registry DB Documentation](../agentos/core/db/README.md)
- [Migration Guide](./MIGRATION_GUIDE.md)
- [CI/CD Documentation](./CI_CD.md)
