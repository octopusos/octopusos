# Schema v0.31 Quick Reference

**Version**: v0.4.0
**Migration**: v0.30 → v0.31
**Status**: ✅ Production Ready

---

## 5 New Tables

### 1. projects
```sql
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    tags TEXT,  -- JSON array
    default_repo_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 2. repos
```sql
CREATE TABLE repos (
    repo_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    local_path TEXT NOT NULL,  -- absolute path
    vcs_type TEXT DEFAULT 'git',
    remote_url TEXT,
    default_branch TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    UNIQUE(project_id, name)
);
```

### 3. task_specs
```sql
CREATE TABLE task_specs (
    spec_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    spec_version INTEGER NOT NULL,
    title TEXT NOT NULL,
    intent TEXT,
    constraints TEXT,  -- JSON
    acceptance_criteria TEXT,  -- JSON
    inputs TEXT,  -- JSON
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    UNIQUE(task_id, spec_version)
);
```

### 4. task_bindings
```sql
CREATE TABLE task_bindings (
    task_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    repo_id TEXT,
    workdir TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE RESTRICT,
    FOREIGN KEY (repo_id) REFERENCES repos(repo_id) ON DELETE SET NULL
);
```

### 5. task_artifacts
```sql
CREATE TABLE task_artifacts (
    artifact_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    kind TEXT NOT NULL,  -- file/dir/url/log/report
    path TEXT NOT NULL,
    display_name TEXT,
    hash TEXT,
    size_bytes INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);
```

---

## tasks Table Changes

### New Fields
```sql
ALTER TABLE tasks ADD COLUMN project_id TEXT;
ALTER TABLE tasks ADD COLUMN repo_id TEXT;
ALTER TABLE tasks ADD COLUMN workdir TEXT;
ALTER TABLE tasks ADD COLUMN spec_frozen INTEGER DEFAULT 0;
```

---

## Hard Constraints (Enforced by Triggers)

### Constraint 1: project_id required for READY+
```
READY+ states = ready, running, verifying, verified, done, succeeded

ERROR: Tasks in READY+ states must have project_id
```

### Constraint 2: spec_frozen required for READY+
```
READY+ tasks must have spec_frozen = 1

ERROR: Tasks in READY+ states must have frozen spec
```

---

## Common Operations

### Create Project and Repo
```sql
-- Create project
INSERT INTO projects (project_id, name, description, created_at, updated_at)
VALUES ('proj_api', 'API Service', 'Backend API', datetime('now'), datetime('now'));

-- Create repo
INSERT INTO repos (repo_id, project_id, name, local_path, vcs_type, created_at, updated_at)
VALUES ('repo_api', 'proj_api', 'api-service', '/workspace/api', 'git', datetime('now'), datetime('now'));
```

### Create Task with Binding
```sql
-- Create task (DRAFT)
INSERT INTO tasks (task_id, title, status, project_id, spec_frozen, created_at, updated_at)
VALUES ('task_01', 'Update API', 'draft', 'proj_api', 0, datetime('now'), datetime('now'));

-- Create binding
INSERT INTO task_bindings (task_id, project_id, repo_id, created_at)
VALUES ('task_01', 'proj_api', 'repo_api', datetime('now'));
```

### Freeze Spec
```sql
-- Create spec version
INSERT INTO task_specs (spec_id, task_id, spec_version, title, intent, created_at)
VALUES ('spec_01_v1', 'task_01', 1, 'Update API', 'Add pagination', datetime('now'));

-- Mark as frozen
UPDATE tasks SET spec_frozen = 1 WHERE task_id = 'task_01';
```

### Transition to READY
```sql
-- Now safe to transition (has project_id + spec_frozen)
UPDATE tasks SET status = 'ready' WHERE task_id = 'task_01';
```

### Record Artifact
```sql
INSERT INTO task_artifacts (artifact_id, task_id, kind, path, display_name, created_at)
VALUES ('art_01', 'task_01', 'file', '/workspace/api/docs/openapi.yaml', 'API Spec', datetime('now'));
```

---

## Common Queries

### List projects with repo count
```sql
SELECT
    p.project_id,
    p.name,
    COUNT(r.repo_id) as repo_count
FROM projects p
LEFT JOIN repos r ON p.project_id = r.project_id
GROUP BY p.project_id, p.name;
```

### List tasks by project
```sql
SELECT
    t.task_id,
    t.title,
    t.status,
    t.spec_frozen,
    r.name as repo_name
FROM tasks t
JOIN task_bindings tb ON t.task_id = tb.task_id
LEFT JOIN repos r ON tb.repo_id = r.repo_id
WHERE tb.project_id = 'proj_api'
ORDER BY t.created_at DESC;
```

### List task artifacts
```sql
SELECT
    artifact_id,
    kind,
    path,
    display_name,
    created_at
FROM task_artifacts
WHERE task_id = 'task_01'
ORDER BY created_at DESC;
```

### List spec history
```sql
SELECT
    spec_version,
    title,
    intent,
    created_at
FROM task_specs
WHERE task_id = 'task_01'
ORDER BY spec_version DESC;
```

---

## Migration Verification

### Check no NULL project_id
```sql
SELECT COUNT(*) FROM tasks WHERE project_id IS NULL;
-- Expected: 0
```

### Check default project exists
```sql
SELECT * FROM projects WHERE project_id = 'proj_default';
-- Expected: 1 row
```

### Check task bindings
```sql
SELECT COUNT(*) FROM task_bindings;
-- Expected: >= number of tasks
```

### Check schema version
```sql
SELECT version FROM schema_version ORDER BY version DESC LIMIT 1;
-- Expected: '0.31.0'
```

---

## Constraint Testing

### Test: READY without project_id (should fail)
```sql
INSERT INTO tasks (task_id, title, status, project_id, spec_frozen, created_at, updated_at)
VALUES ('fail1', 'Test', 'ready', NULL, 1, datetime('now'), datetime('now'));
-- Expected: ERROR: Tasks in READY+ states must have project_id
```

### Test: READY without spec_frozen (should fail)
```sql
INSERT INTO tasks (task_id, title, status, project_id, spec_frozen, created_at, updated_at)
VALUES ('fail2', 'Test', 'ready', 'proj_api', 0, datetime('now'), datetime('now'));
-- Expected: ERROR: Tasks in READY+ states must have frozen spec
```

### Test: Valid READY task (should succeed)
```sql
INSERT INTO tasks (task_id, title, status, project_id, spec_frozen, created_at, updated_at)
VALUES ('valid1', 'Test', 'ready', 'proj_api', 1, datetime('now'), datetime('now'));
-- Expected: SUCCESS
```

---

## Foreign Key Behavior

### CASCADE DELETE (projects → repos)
```sql
DELETE FROM projects WHERE project_id = 'proj_api';
-- Result: All repos with project_id='proj_api' are also deleted
```

### RESTRICT DELETE (projects with task_bindings)
```sql
DELETE FROM projects WHERE project_id = 'proj_api';
-- If task_bindings exist: ERROR: FOREIGN KEY constraint failed
-- Must delete tasks first
```

### SET NULL (repos deletion)
```sql
DELETE FROM repos WHERE repo_id = 'repo_api';
-- Result: task_bindings.repo_id set to NULL for affected tasks
```

---

## Performance Tips

### Use indexes for queries
```sql
-- Fast: uses idx_tasks_project_status
SELECT * FROM tasks WHERE project_id = 'proj_api' AND status = 'ready';

-- Fast: uses idx_repos_project_id
SELECT * FROM repos WHERE project_id = 'proj_api';

-- Fast: uses idx_task_artifacts_task_id
SELECT * FROM task_artifacts WHERE task_id = 'task_01';
```

### Avoid full table scans
```sql
-- Bad: full table scan
SELECT * FROM tasks WHERE workdir LIKE '%src%';

-- Good: use project_id first
SELECT * FROM tasks WHERE project_id = 'proj_api' AND workdir LIKE '%src%';
```

---

## API Integration (Future Phases)

### POST /api/projects
```json
{
  "name": "E-Commerce Platform",
  "description": "Main project",
  "tags": ["backend", "api"]
}
```

### POST /api/tasks (v0.4+)
```json
{
  "title": "Update API",
  "project_id": "proj_api",  // REQUIRED
  "repo_id": "repo_api"      // Optional
}
```

### POST /api/tasks/{task_id}/freeze
```json
{
  "title": "Update API",
  "intent": "Add pagination",
  "constraints": ["no_breaking_changes"],
  "acceptance_criteria": ["tests_pass", "docs_updated"]
}
```

---

## Troubleshooting

### Error: "Tasks in READY+ states must have project_id"
**Cause**: Trying to create/update READY task without project_id
**Solution**: Set project_id before transitioning to READY

### Error: "Tasks in READY+ states must have frozen spec"
**Cause**: Trying to create/update READY task without spec_frozen = 1
**Solution**: Freeze spec before transitioning to READY

### Error: "FOREIGN KEY constraint failed"
**Cause**: Trying to delete project with active task_bindings
**Solution**: Delete tasks first, or use CASCADE

### Error: "UNIQUE constraint failed: projects.name"
**Cause**: Project name already exists
**Solution**: Use different name or update existing project

---

## Files

- **Migration**: `agentos/store/migrations/schema_v31_project_aware.sql`
- **Summary**: `agentos/store/migrations/schema_v31_summary.txt`
- **Tests**: `tests/integration/test_schema_v31_migration.py`
- **Verification**: `verify_schema_v31.py`
- **Deliverables**: `PHASE1_SCHEMA_V31_DELIVERABLES.md`

---

## Next Steps

1. **Phase 2**: Implement core services (TaskService, ProjectService, etc.)
2. **Phase 3**: Update API endpoints (add project_id validation)
3. **Phase 4**: Update WebUI (add project selector)
4. **Phase 5**: Implement CLI commands
5. **Phase 6**: Write tests and documentation

---

**Version**: v0.4.0
**Last Updated**: 2026-01-29
**Status**: ✅ Production Ready
