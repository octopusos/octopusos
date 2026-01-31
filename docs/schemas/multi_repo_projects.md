# Multi-Repository Projects Schema (v0.18)

## Overview

The v0.18 migration introduces comprehensive multi-repository support for AgentOS, enabling projects to manage multiple Git repositories with explicit relationships, dependencies, and cross-repository task tracking.

## Schema Design

### 1. `project_repos` - Repository Bindings

Defines which repositories belong to a project and how they're accessed.

```sql
CREATE TABLE project_repos (
    repo_id TEXT PRIMARY KEY,           -- Unique repo identifier (ULID)
    project_id TEXT NOT NULL,           -- FK to projects.id
    name TEXT NOT NULL,                 -- User-friendly name (e.g., "frontend", "backend")
    remote_url TEXT,                    -- Git remote URL (optional)
    default_branch TEXT DEFAULT 'main', -- Default branch
    workspace_relpath TEXT NOT NULL,    -- Relative path from project root
    role TEXT NOT NULL DEFAULT 'code',  -- code | docs | infra | mono-subdir
    is_writable INTEGER NOT NULL DEFAULT 1,  -- 1=writable, 0=read-only
    auth_profile TEXT,                  -- Auth credential reference
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    metadata TEXT                       -- JSON: extended config
)
```

**Key Features:**
- **Unique constraints**: `(project_id, name)` and `(project_id, workspace_relpath)`
- **Role types**: Categorizes repos by purpose (code/docs/infra/mono-subdir)
- **Writability control**: Read-only repos for dependencies or reference
- **Auth profiles**: Decoupled credential management

**Example:**
```sql
-- Monorepo with multiple subdir repos
INSERT INTO project_repos (repo_id, project_id, name, workspace_relpath, role)
VALUES
    ('r1', 'proj1', 'frontend', 'packages/frontend', 'mono-subdir'),
    ('r2', 'proj1', 'backend', 'packages/backend', 'mono-subdir'),
    ('r3', 'proj1', 'docs', 'docs', 'docs');
```

### 2. `task_repo_scope` - Task Repository Scope

Records which repositories a task operates on and with what permissions.

```sql
CREATE TABLE task_repo_scope (
    scope_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,              -- FK to tasks.task_id
    repo_id TEXT NOT NULL,              -- FK to project_repos.repo_id
    scope TEXT NOT NULL DEFAULT 'full', -- full | paths | read_only
    path_filters TEXT,                  -- JSON array: ["src/**", "tests/**"]
    created_at TIMESTAMP,
    metadata TEXT
)
```

**Scope Types:**
- `full`: Complete repository access
- `paths`: Limited to specific paths (via `path_filters`)
- `read_only`: Read-only access regardless of repo's `is_writable`

**Example:**
```sql
-- Task that only modifies frontend code
INSERT INTO task_repo_scope (task_id, repo_id, scope, path_filters)
VALUES ('task123', 'frontend_repo', 'paths', '["src/**", "package.json"]');
```

### 3. `task_dependency` - Task Dependencies

Explicit dependencies between tasks (including cross-repo).

```sql
CREATE TABLE task_dependency (
    dependency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,              -- Dependent task
    depends_on_task_id TEXT NOT NULL,   -- Dependency
    dependency_type TEXT NOT NULL DEFAULT 'blocks',  -- blocks | requires | suggests
    reason TEXT,                        -- Human-readable explanation
    created_at TIMESTAMP,
    created_by TEXT,                    -- user | system | auto
    metadata TEXT
)
```

**Dependency Types:**
- `blocks`: Hard dependency - task cannot start until dependency completes
- `requires`: Soft dependency - can run in parallel, but needs dependency's output
- `suggests`: Informational - no enforcement

**Constraints:**
- No self-dependencies: `CHECK (task_id != depends_on_task_id)`
- Unique per type: `UNIQUE(task_id, depends_on_task_id, dependency_type)`

**Example:**
```sql
-- Frontend task requires backend API to be ready
INSERT INTO task_dependency (task_id, depends_on_task_id, dependency_type, reason)
VALUES ('frontend_task', 'backend_task', 'requires', 'Needs /api endpoints');
```

### 4. `task_artifact_ref` - Cross-Repo Artifacts

References to artifacts produced or used by tasks across repositories.

```sql
CREATE TABLE task_artifact_ref (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    repo_id TEXT NOT NULL,
    ref_type TEXT NOT NULL,             -- commit | branch | pr | patch | file | tag
    ref_value TEXT NOT NULL,            -- SHA, branch name, PR#, file path, etc.
    summary TEXT,                       -- Human-readable description
    created_at TIMESTAMP,
    metadata TEXT
)
```

**Reference Types:**
- `commit`: Git commit SHA (immutable)
- `branch`: Git branch name (mutable)
- `pr`: Pull Request number
- `patch`: Patch file or diff content
- `file`: Specific file path
- `tag`: Git tag (semantic version)

**Example:**
```sql
-- Task produces commits in multiple repos
INSERT INTO task_artifact_ref (task_id, repo_id, ref_type, ref_value, summary)
VALUES
    ('task123', 'frontend_repo', 'commit', 'abc123def', 'UI updates'),
    ('task123', 'backend_repo', 'commit', '456789abc', 'API changes'),
    ('task123', 'frontend_repo', 'pr', '42', 'Code review PR');
```

## Migration Compatibility

### Backward Compatibility

The migration automatically creates a **default repository binding** for all existing projects:

```sql
-- Auto-generated for each existing project
INSERT INTO project_repos (repo_id, project_id, name, workspace_relpath, role)
SELECT
    id || '_default_repo',  -- repo_id
    id,                     -- project_id
    'default',             -- name
    '.',                   -- workspace_relpath (root)
    'code'                 -- role
FROM projects
WHERE id NOT IN (SELECT project_id FROM project_repos);
```

This ensures:
- **Zero breaking changes** for existing single-repo projects
- **No code modifications required** in current workflows
- **Gradual migration path** to multi-repo mode

### Idempotency

The migration uses:
- `CREATE TABLE IF NOT EXISTS`
- `CREATE INDEX IF NOT EXISTS`
- `INSERT OR IGNORE` for data migration

Running the migration multiple times is safe.

## Indexes

The migration creates 17 indexes for optimal query performance:

**Project Repos:**
- `idx_project_repos_project`: `(project_id, created_at DESC)`
- `idx_project_repos_role`: `(role)`
- `idx_project_repos_writable`: `(is_writable)` WHERE `is_writable = 1`
- `idx_project_repos_name`: `(project_id, name)`

**Task Repo Scope:**
- `idx_task_repo_scope_task`: `(task_id)`
- `idx_task_repo_scope_repo`: `(repo_id, created_at DESC)`
- `idx_task_repo_scope_scope`: `(scope)`
- `idx_task_repo_scope_task_repo`: `(task_id, repo_id)`

**Task Dependency:**
- `idx_task_dependency_task`: `(task_id)`
- `idx_task_dependency_depends_on`: `(depends_on_task_id)`
- `idx_task_dependency_type`: `(dependency_type)`
- `idx_task_dependency_reverse`: `(depends_on_task_id, task_id)`

**Task Artifact Ref:**
- `idx_task_artifact_ref_task`: `(task_id)`
- `idx_task_artifact_ref_repo`: `(repo_id, created_at DESC)`
- `idx_task_artifact_ref_type`: `(ref_type)`
- `idx_task_artifact_ref_task_repo`: `(task_id, repo_id)`
- `idx_task_artifact_ref_type_value`: `(ref_type, ref_value)`

## Use Cases

### 1. Monorepo with Package Subdirectories

```sql
-- Register monorepo packages
INSERT INTO project_repos (repo_id, project_id, name, workspace_relpath, role)
VALUES
    ('pkg_ui', 'monorepo', 'ui', 'packages/ui', 'mono-subdir'),
    ('pkg_api', 'monorepo', 'api', 'packages/api', 'mono-subdir'),
    ('pkg_shared', 'monorepo', 'shared', 'packages/shared', 'mono-subdir');

-- Task that modifies shared package
INSERT INTO task_repo_scope (task_id, repo_id, scope)
VALUES ('refactor_types', 'pkg_shared', 'full');

-- Track dependency: UI depends on shared types
INSERT INTO task_dependency (task_id, depends_on_task_id, dependency_type)
VALUES ('ui_update', 'refactor_types', 'blocks');
```

### 2. Multi-Repo Project (Frontend + Backend)

```sql
-- Register separate repos
INSERT INTO project_repos (repo_id, project_id, name, workspace_relpath, role, remote_url)
VALUES
    ('fe', 'webapp', 'frontend', './frontend', 'code', 'git@github.com:org/webapp-frontend'),
    ('be', 'webapp', 'backend', './backend', 'code', 'git@github.com:org/webapp-backend');

-- Task modifies both repos
INSERT INTO task_repo_scope (task_id, repo_id, scope)
VALUES
    ('new_feature', 'fe', 'full'),
    ('new_feature', 'be', 'full');

-- Record artifacts
INSERT INTO task_artifact_ref (task_id, repo_id, ref_type, ref_value, summary)
VALUES
    ('new_feature', 'fe', 'commit', 'abc123', 'UI for new feature'),
    ('new_feature', 'be', 'commit', 'def456', 'Backend API for new feature');
```

### 3. Code Repo + Docs Repo

```sql
-- Separate docs repo (read-only for most tasks)
INSERT INTO project_repos (repo_id, project_id, name, workspace_relpath, role, is_writable)
VALUES
    ('code', 'proj', 'main', '.', 'code', 1),
    ('docs', 'proj', 'docs', '../proj-docs', 'docs', 0);

-- Task reads docs but only writes to code
INSERT INTO task_repo_scope (task_id, repo_id, scope)
VALUES
    ('impl', 'code', 'full'),
    ('impl', 'docs', 'read_only');
```

### 4. Dependency Analysis

```sql
-- Find all tasks that depend on task123
SELECT td.task_id, t.title, td.dependency_type, td.reason
FROM task_dependency td
JOIN tasks t ON td.task_id = t.task_id
WHERE td.depends_on_task_id = 'task123';

-- Find all repos involved in task123
SELECT pr.name, pr.role, trs.scope
FROM task_repo_scope trs
JOIN project_repos pr ON trs.repo_id = pr.repo_id
WHERE trs.task_id = 'task123';

-- Find all commits produced by task123
SELECT pr.name, tar.ref_value, tar.summary
FROM task_artifact_ref tar
JOIN project_repos pr ON tar.repo_id = pr.repo_id
WHERE tar.task_id = 'task123' AND tar.ref_type = 'commit';
```

## Design Principles

1. **Explicit over implicit**: All repository relationships are explicit records
2. **Immutable references**: Artifacts use immutable refs (commits) when possible
3. **Flexibility**: Support monorepo, multi-repo, and hybrid setups
4. **Auditability**: Complete audit trail via `task_artifact_ref` and `task_audits`
5. **Gradual migration**: Zero breaking changes for single-repo projects
6. **Performance**: Comprehensive indexes for all common query patterns

## Future Extensions

Potential extensions (not in v0.18):

- **Workspace sync strategies**: How to sync repos (shallow clone, sparse checkout)
- **Conflict detection**: Path overlap analysis across repos
- **Credential management**: Auth profile implementation
- **Repository caching**: Local clone management
- **Change boundary enforcement**: `.gitignore` integration per-repo

## Testing

Run unit tests:

```bash
# With pytest
pytest tests/unit/store/test_v18_migration.py -v

# Standalone script (no pytest required)
python3 tests/unit/store/run_v18_migration_test.py
```

## Migration

To apply this migration to your AgentOS database:

```bash
# Using AgentOS CLI (when implemented)
agentos migrate

# Manual migration
sqlite3 ~/.agentos/registry.sqlite < agentos/store/migrations/v18_multi_repo_projects.sql
```

## Schema Version

This migration updates `schema_version` to `0.18.0`.

```sql
SELECT version FROM schema_version WHERE version = '0.18.0';
-- Returns: 0.18.0
```
