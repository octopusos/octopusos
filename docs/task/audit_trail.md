# Task Audit Trail - Cross-Repository Tracking

## Overview

The Task Audit Trail system provides complete traceability for task execution across multiple repositories. It records:

- Operations performed (read, write, commit, push)
- Git changes (status, diff stats, files modified)
- Artifact references (commits, branches, PRs, patches)
- Errors and failures

## Architecture

### Components

1. **TaskAuditService** - Records audit events
2. **TaskArtifactService** - Tracks artifact references
3. **TaskRunnerAuditor** - Integration layer for TaskRunner
4. **API Endpoints** - Query audits and artifacts

### Database Schema

#### Extended `task_audits` Table

```sql
-- v0.20 migration adds repo_id column
ALTER TABLE task_audits ADD COLUMN repo_id TEXT;

-- Indexes for efficient querying
CREATE INDEX idx_task_audits_repo ON task_audits(repo_id);
CREATE INDEX idx_task_audits_task_repo ON task_audits(task_id, repo_id);
```

#### `task_artifact_ref` Table

```sql
-- From v0.18 schema
CREATE TABLE task_artifact_ref (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    repo_id TEXT NOT NULL,
    ref_type TEXT NOT NULL,  -- commit, branch, pr, patch, file, tag
    ref_value TEXT NOT NULL,
    summary TEXT,
    metadata TEXT,           -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage

### Recording Audits

#### Basic Operation

```python
from agentos.core.task.audit_service import TaskAuditService

service = TaskAuditService()

# Record write operation
audit = service.record_operation(
    task_id="task-123",
    repo_id="repo-456",
    operation="write",
    status="success",
    files_changed=["src/main.py", "tests/test_main.py"],
)
```

#### Git Changes

```python
from agentos.core.task.repo_context import TaskRepoContext

# Record Git changes with automatic capture
audit = service.record_git_changes(
    task_id="task-123",
    repo_context=repo_context,
    operation="commit",
    commit_hash="abc123def456",
)

# Audit includes:
# - git_status_summary (porcelain format)
# - git_diff_summary (--stat format, size-limited to 10KB)
# - files_changed (parsed from diff)
# - lines_added, lines_deleted
```

### Creating Artifacts

```python
from agentos.core.task.artifact_service import TaskArtifactService

service = TaskArtifactService()

# Create commit artifact
artifact = service.create_commit_ref(
    task_id="task-123",
    repo_id="repo-456",
    commit_hash="abc123def456",
    summary="Implement feature X",
    metadata={"author": "agent", "files_changed": 5},
)

# Create PR artifact
artifact = service.create_pr_ref(
    task_id="task-123",
    repo_id="repo-456",
    pr_number=42,
    summary="Fix authentication bug",
    metadata={"url": "https://github.com/org/repo/pull/42"},
)

# Create branch artifact
artifact = service.create_branch_ref(
    task_id="task-123",
    repo_id="repo-456",
    branch_name="feature/new-feature",
    summary="Feature branch for task 123",
)
```

### TaskRunner Integration

```python
from agentos.core.task.runner_audit_integration import TaskRunnerAuditor

def execute_task(task: Task):
    # Prepare execution environment
    exec_env = prepare_execution_env(task)

    # Initialize auditor
    auditor = TaskRunnerAuditor(task.task_id)

    try:
        # Record start
        auditor.record_start(exec_env)

        # Execute task
        result = run_task(task, exec_env)

        # Record changes for each repository
        for repo_context in exec_env.repos.values():
            if has_uncommitted_changes(repo_context.path):
                # Commit changes
                git_client = GitClient(repo_context.path)
                git_client.add_all()
                commit_hash = git_client.commit(f"Task {task.task_id}: {task.title}")

                # Record changes and create artifact
                auditor.record_repo_changes(
                    repo_context=repo_context,
                    commit_hash=commit_hash,
                    commit_message=f"Task {task.task_id}: {task.title}"
                )

        # Record completion
        auditor.record_completion(exec_env, status="success")

        return result

    except Exception as e:
        # Record error
        auditor.record_error(str(e))
        auditor.record_completion(exec_env, status="failed", error_message=str(e))
        raise
```

### Querying Audits

#### Python API

```python
from agentos.core.task.audit_service import TaskAuditService

service = TaskAuditService()

# Get all audits for a task
audits = service.get_task_audits(task_id="task-123")

# Filter by repository
audits = service.get_task_audits(task_id="task-123", repo_id="repo-456")

# Filter by event type
audits = service.get_task_audits(task_id="task-123", event_type="repo_commit")

# Get repository audit trail (across all tasks)
audits = service.get_repo_audits(repo_id="repo-456", limit=100)
```

#### REST API

```bash
# Get task audits
GET /api/tasks/{task_id}/audits?repo_id=repo-456&detailed=true

# Get repository audit trail
GET /api/repos/{repo_id}/audits?limit=100

# Get task artifacts
GET /api/tasks/{task_id}/artifacts?ref_type=commit

# Get repository artifacts
GET /api/repos/{repo_id}/artifacts?ref_type=commit&limit=50
```

#### API Response

```json
{
  "audit_id": 1,
  "task_id": "task-123",
  "repo_id": "repo-456",
  "level": "info",
  "event_type": "repo_commit",
  "operation": "commit",
  "status": "success",
  "files_changed": ["src/main.py", "tests/test_main.py"],
  "lines_added": 50,
  "lines_deleted": 10,
  "commit_hash": "abc123def456",
  "git_status_summary": "M  src/main.py\nA  tests/test_main.py",
  "git_diff_summary": "src/main.py | 30 +++---\ntests/test_main.py | 20 +++++",
  "created_at": "2025-01-28T12:00:00Z"
}
```

## Event Types

### Task-Level Events

- `task_start` - Task execution started
- `task_complete` - Task execution completed
- `execute_error` - Task execution error

### Repository Events

- `repo_read` - Read operation on repository
- `repo_write` - Write operation on repository
- `repo_commit` - Commit created
- `repo_push` - Push to remote
- `repo_checkout` - Branch/commit checkout
- `repo_clone` - Repository cloned
- `repo_pull` - Pull from remote
- `repo_{operation}_error` - Repository operation error

## Size Limits

To prevent database bloat:

- **Git Status Summary**: Max 5KB (truncated if larger)
- **Git Diff Summary**: Max 10KB (truncated if larger)
- Truncated summaries include a note: `"... (truncated, total X bytes)"`

## Best Practices

### 1. Record at Key Points

```python
# Record before critical operations
auditor.record_repo_read(repo_context, files_read=["config.yaml"])

# Record after modifications
auditor.record_repo_write(repo_context, files_written=["output.json"])

# Record after commits
auditor.record_repo_changes(repo_context, commit_hash=commit_sha)
```

### 2. Use Appropriate Event Types

```python
# Use specific event types for filtering
service.record_operation(
    task_id="task-123",
    operation="clone",
    event_type="repo_clone",  # Explicit event type
    status="success"
)
```

### 3. Include Context in Metadata

```python
# Add metadata for debugging
artifact = service.create_commit_ref(
    task_id="task-123",
    repo_id="repo-456",
    commit_hash="abc123",
    summary="Feature implementation",
    metadata={
        "author": "agent-name",
        "execution_time_ms": 1500,
        "files_changed": 5,
        "test_results": "passed"
    }
)
```

### 4. Query Efficiently

```python
# Use filters to reduce data transfer
audits = service.get_task_audits(
    task_id="task-123",
    repo_id="repo-456",  # Filter by repo
    event_type="repo_commit",  # Only commits
    limit=50  # Limit results
)
```

## Example Queries

### Find all commits for a task

```python
audits = service.get_task_audits(
    task_id="task-123",
    event_type="repo_commit"
)

for audit in audits:
    print(f"Repo: {audit.repo_id}")
    print(f"Commit: {audit.commit_hash}")
    print(f"Files: {audit.files_changed}")
    print(f"Changes: +{audit.lines_added}/-{audit.lines_deleted}")
```

### Find which tasks modified a repository

```python
audits = service.get_repo_audits(repo_id="repo-456", limit=100)

tasks = set(audit.task_id for audit in audits)
print(f"Tasks that modified repo-456: {tasks}")
```

### Get artifact history

```python
from agentos.core.task.artifact_service import TaskArtifactService, ArtifactRefType

service = TaskArtifactService()

# All commits in a repository
artifacts = service.get_repo_artifacts(
    repo_id="repo-456",
    ref_type=ArtifactRefType.COMMIT,
    limit=50
)

for artifact in artifacts:
    print(f"Task: {artifact.task_id}")
    print(f"Commit: {artifact.ref_value}")
    print(f"Summary: {artifact.summary}")
```

### Find tasks that reference a specific commit

```python
artifacts = service.get_artifact_by_ref(
    ref_type=ArtifactRefType.COMMIT,
    ref_value="abc123def456"
)

print(f"Tasks referencing commit abc123:")
for artifact in artifacts:
    print(f"  - {artifact.task_id}: {artifact.summary}")
```

## Integration Checklist

When integrating audit trail into TaskRunner:

- [ ] Initialize `TaskRunnerAuditor` at task start
- [ ] Record `task_start` event
- [ ] Record repository operations (read/write)
- [ ] Capture Git changes after commits
- [ ] Create commit artifacts with metadata
- [ ] Record push operations if applicable
- [ ] Handle errors and record error audits
- [ ] Record `task_complete` event with status
- [ ] Include error messages for failed tasks

## Testing

Run unit tests:

```bash
pytest tests/unit/task/test_audit_service.py -v
pytest tests/unit/task/test_artifact_service.py -v
pytest tests/unit/task/test_runner_audit_integration.py -v
```

## Migration

Apply the v0.20 migration:

```bash
# Run migration script
sqlite3 agentos.db < agentos/store/migrations/v20_task_audits_repo.sql
```

Or use the migration manager (if available).

## Troubleshooting

### Audits not showing up

1. Check database connection
2. Verify `task_audits` table has `repo_id` column
3. Check audit service is initialized with correct DB
4. Verify commits are being called

### Git summaries are empty

1. Check repository has uncommitted changes
2. Verify Git is installed and accessible
3. Check subprocess timeouts (default: 5s)
4. Review logs for subprocess errors

### Artifacts duplicated

- Artifacts with same `(task_id, repo_id, ref_type, ref_value)` are rejected
- Check for unique constraint violations in logs

## See Also

- [Task Repository Context](./repo_context.md)
- [Multi-Repository Projects](../governance/multi_repo_projects.md)
- [Task Service API](./task_service.md)
