# Multi-Repository Schema Quick Start

A 5-minute guide to understanding and using the v0.18 multi-repository schema.

## TL;DR

AgentOS now supports managing multiple Git repositories per project with explicit tracking of:
- **Repository bindings** (`project_repos`)
- **Task scope** per repository (`task_repo_scope`)
- **Task dependencies** across repos (`task_dependency`)
- **Cross-repo artifacts** (`task_artifact_ref`)

**Existing single-repo projects work unchanged** - they get a default repo binding automatically.

## Quick Examples

### 1. Register a New Repository

```sql
INSERT INTO project_repos (repo_id, project_id, name, workspace_relpath, role)
VALUES ('fe_repo', 'myproject', 'frontend', './frontend', 'code');
```

### 2. Assign Task to Repository

```sql
INSERT INTO task_repo_scope (task_id, repo_id, scope)
VALUES ('task123', 'fe_repo', 'full');
```

### 3. Create Task Dependency

```sql
INSERT INTO task_dependency (task_id, depends_on_task_id, dependency_type, reason)
VALUES ('ui_task', 'api_task', 'requires', 'UI needs API endpoints');
```

### 4. Record Task Artifact

```sql
INSERT INTO task_artifact_ref (task_id, repo_id, ref_type, ref_value, summary)
VALUES ('task123', 'fe_repo', 'commit', 'abc123def', 'Implemented feature X');
```

## Common Queries

### Find All Repos in a Project

```sql
SELECT name, workspace_relpath, role, is_writable
FROM project_repos
WHERE project_id = 'myproject';
```

### Find All Tasks Touching a Repo

```sql
SELECT t.task_id, t.title, trs.scope
FROM task_repo_scope trs
JOIN tasks t ON trs.task_id = t.task_id
WHERE trs.repo_id = 'fe_repo';
```

### Find What a Task Depends On

```sql
SELECT depends_on_task_id, dependency_type, reason
FROM task_dependency
WHERE task_id = 'task123';
```

### Find All Commits from a Task

```sql
SELECT pr.name AS repo, tar.ref_value AS commit, tar.summary
FROM task_artifact_ref tar
JOIN project_repos pr ON tar.repo_id = pr.repo_id
WHERE tar.task_id = 'task123' AND tar.ref_type = 'commit';
```

## Schema Cheat Sheet

### `project_repos` Fields

| Field | Type | Description |
|-------|------|-------------|
| `repo_id` | TEXT | Primary key (ULID) |
| `project_id` | TEXT | FK to projects.id |
| `name` | TEXT | User-friendly name |
| `workspace_relpath` | TEXT | Path from project root |
| `role` | TEXT | `code` \| `docs` \| `infra` \| `mono-subdir` |
| `is_writable` | INT | 1=writable, 0=read-only |

### `task_repo_scope` Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | TEXT | FK to tasks.task_id |
| `repo_id` | TEXT | FK to project_repos.repo_id |
| `scope` | TEXT | `full` \| `paths` \| `read_only` |
| `path_filters` | TEXT | JSON array (for `paths` scope) |

### `task_dependency` Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | TEXT | Dependent task |
| `depends_on_task_id` | TEXT | Dependency task |
| `dependency_type` | TEXT | `blocks` \| `requires` \| `suggests` |
| `reason` | TEXT | Why this dependency exists |

### `task_artifact_ref` Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | TEXT | Task that produced artifact |
| `repo_id` | TEXT | Repo containing artifact |
| `ref_type` | TEXT | `commit` \| `branch` \| `pr` \| `patch` \| `file` \| `tag` |
| `ref_value` | TEXT | SHA, branch name, PR#, path, etc. |

## Use Cases

### Monorepo (Single Git Repo, Multiple Logical Repos)

```sql
-- Register logical repos as mono-subdir
INSERT INTO project_repos (repo_id, project_id, name, workspace_relpath, role)
VALUES
    ('pkg_ui', 'mono', 'ui', 'packages/ui', 'mono-subdir'),
    ('pkg_api', 'mono', 'api', 'packages/api', 'mono-subdir');
```

### Multi-Repo (Separate Git Repos)

```sql
-- Register physically separate repos
INSERT INTO project_repos (repo_id, project_id, name, workspace_relpath, role, remote_url)
VALUES
    ('fe', 'app', 'frontend', './fe', 'code', 'git@github.com:org/app-fe'),
    ('be', 'app', 'backend', './be', 'code', 'git@github.com:org/app-be');
```

### Read-Only Dependency Repo

```sql
-- Reference-only repo (docs, shared libs)
INSERT INTO project_repos (repo_id, project_id, name, workspace_relpath, role, is_writable)
VALUES ('docs', 'app', 'docs', '../app-docs', 'docs', 0);
```

## Migration

### Automatic Migration

When you run the v0.18 migration, **existing projects automatically get a default repo**:

```sql
-- Auto-created for project "proj1"
{
  "repo_id": "proj1_default_repo",
  "project_id": "proj1",
  "name": "default",
  "workspace_relpath": ".",
  "role": "code",
  "is_writable": 1
}
```

### Manual Migration

To migrate an existing database:

```bash
# Using AgentOS CLI
agentos migrate

# Manual SQLite
sqlite3 ~/.agentos/registry.sqlite < agentos/store/migrations/v18_multi_repo_projects.sql
```

## Constraints

### Enforced Constraints

- **No duplicate repo names** per project
- **No duplicate workspace paths** per project
- **No task self-dependencies**
- **Valid role**: must be `code`, `docs`, `infra`, or `mono-subdir`
- **Valid scope**: must be `full`, `paths`, or `read_only`
- **Valid ref_type**: must be `commit`, `branch`, `pr`, `patch`, `file`, or `tag`
- **Valid dependency_type**: must be `blocks`, `requires`, or `suggests`

### Cascade Deletion

- Deleting a **project** → deletes all its repos
- Deleting a **repo** → deletes all task scopes and artifacts referencing it
- Deleting a **task** → deletes all its dependencies, scopes, and artifacts

## Performance

All common queries are indexed:

```sql
-- Fast: Find repos by project
SELECT * FROM project_repos WHERE project_id = 'proj1';  -- idx_project_repos_project

-- Fast: Find writable repos
SELECT * FROM project_repos WHERE is_writable = 1;  -- idx_project_repos_writable

-- Fast: Find task scopes
SELECT * FROM task_repo_scope WHERE task_id = 'task123';  -- idx_task_repo_scope_task

-- Fast: Find dependencies (forward)
SELECT * FROM task_dependency WHERE task_id = 'task123';  -- idx_task_dependency_task

-- Fast: Find dependencies (reverse: who depends on me?)
SELECT * FROM task_dependency WHERE depends_on_task_id = 'task123';  -- idx_task_dependency_reverse

-- Fast: Find artifacts by ref type
SELECT * FROM task_artifact_ref WHERE ref_type = 'commit' AND ref_value = 'abc123';  -- idx_task_artifact_ref_type_value
```

## Testing

Run tests to verify schema:

```bash
# With pytest
pytest tests/unit/store/test_v18_migration.py -v

# Standalone (no pytest)
python3 tests/unit/store/run_v18_migration_test.py
```

## Next Steps

1. **Read full docs**: `docs/schemas/multi_repo_projects.md`
2. **Implement Python models**: Phase 1.2 (coming next)
3. **Add CLI commands**: `agentos repo add/list/remove` (Phase 2.1)

## Questions?

- **Q: Do I need to change existing code?**
  - A: No. Single-repo projects work unchanged.

- **Q: Can I mix monorepo and multi-repo?**
  - A: Yes. Use `mono-subdir` role for monorepo packages.

- **Q: How do I model Git submodules?**
  - A: Store submodule config in `project_repos.metadata` (JSON).

- **Q: Can tasks span multiple repos?**
  - A: Yes. Add multiple entries to `task_repo_scope`.

- **Q: How do I track cross-repo patches?**
  - A: Use `task_artifact_ref` with `ref_type='patch'` and store diff in `metadata`.

---

**Schema Version**: v0.18.0
**Last Updated**: 2026-01-28
**Full Docs**: `docs/schemas/multi_repo_projects.md`
