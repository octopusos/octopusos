# Cross-Repository Tracing CLI Guide

This guide explains how to use the CLI commands for tracing cross-repository task activities without needing the WebUI.

## Overview

AgentOS provides powerful CLI tools to track and visualize task activities across multiple repositories:

- **`agentos project trace`** - View all repositories in a project with recent activities
- **`agentos task repo-trace`** - Detailed trace of a single task's cross-repo activities
- **`agentos task dependencies trace`** - Alternative access to task tracing with dependency focus

## Project Trace Command

### Basic Usage

```bash
# View all repositories and recent tasks in a project
agentos project trace <project_id>

# Example
agentos project trace my-app
```

### Output Formats

The command supports three output formats:

#### 1. Table Format (Default)

Human-readable table view with color coding and relative timestamps:

```bash
agentos project trace my-app --format table
```

**Example Output:**

```
Project: my-app

📦 Repositories (3)
┌────────────┬──────────────────────────────┬────────┬──────────┬─────────────┐
│ Name       │ URL                          │ Role   │ Writable │ Last Active │
├────────────┼──────────────────────────────┼────────┼──────────┼─────────────┤
│ backend    │ git@github.com:org/backend   │ code   │ Yes      │ 2h ago      │
│ frontend   │ git@github.com:org/frontend  │ code   │ Yes      │ 5h ago      │
│ docs       │ git@github.com:org/docs      │ docs   │ No       │ 1d ago      │
└────────────┴──────────────────────────────┴────────┴──────────┴─────────────┘

📋 Recent Tasks by Repository

backend (2 tasks):
  • task-123 [completed] - 5 files, +120/-30 lines
  • task-124 [in_progress] - 3 files, +45/-10 lines

frontend (1 task):
  • task-125 [completed] - 8 files, +200/-50 lines

🔗 Cross-Repository Dependencies
  Total: 2
```

#### 2. JSON Format

Machine-readable JSON output for scripting:

```bash
agentos project trace my-app --format json
```

**Example Output:**

```json
{
  "project_id": "my-app",
  "repositories": [
    {
      "repo_id": "repo-001",
      "name": "backend",
      "remote_url": "git@github.com:org/backend",
      "role": "code",
      "is_writable": true,
      "last_active": "2026-01-28T10:00:00Z"
    }
  ],
  "tasks_by_repo": {
    "repo-001": [
      {
        "task_id": "task-123",
        "status": "completed",
        "created_at": "2026-01-28T08:00:00Z",
        "files_changed": 5,
        "lines_added": 120,
        "lines_deleted": 30
      }
    ]
  },
  "dependency_stats": {
    "total": 2,
    "cross_repo": 0
  }
}
```

**Scripting Example:**

```bash
# Extract backend repository tasks
agentos project trace my-app --format json | jq '.tasks_by_repo[] | select(.repo_id=="repo-001")'

# Count total tasks across all repositories
agentos project trace my-app --format json | jq '[.tasks_by_repo[][] | length] | add'
```

#### 3. Tree Format

Hierarchical tree view:

```bash
agentos project trace my-app --format tree
```

**Example Output:**

```
my-app
├── 📦 Repositories
│   ├── backend (code)
│   │   ├── URL: git@github.com:org/backend
│   │   ├── Writable: Yes
│   │   └── Recent tasks (2)
│   │       ├── task-123 - 5 files
│   │       └── task-124 - 3 files
│   └── frontend (code)
│       ├── URL: git@github.com:org/frontend
│       ├── Writable: Yes
│       └── Recent tasks (1)
│           └── task-125 - 8 files
└── 🔗 Dependencies
    └── Total: 2
```

### Options

```bash
# Limit number of tasks per repository
agentos project trace my-app --limit 10

# Combine with format
agentos project trace my-app --format json --limit 5
```

## Task Repo-Trace Command

### Basic Usage

```bash
# Trace a single task's cross-repository activities
agentos task repo-trace <task_id>

# Example
agentos task repo-trace task-123
```

### Output Formats

#### 1. Table Format (Default)

Detailed view with repository changes, artifacts, and dependencies:

```bash
agentos task repo-trace task-123 --format table
```

**Example Output:**

```
Task: task-123
Status: completed
Created: 2h ago

📦 Repositories (2)

backend (FULL access):
  Changes:
    3 files modified
    Total: 3 files, +80/-110 lines
    Commit: abc123de

frontend (READ_ONLY access):
  No changes

🎯 Artifacts (1)
  • commit:abc123def
    Main logic refactoring

🔗 Dependencies

  Depends on:
    • task-120 (requires)

  Depended by:
    • task-125 (suggests)
```

#### 2. Detailed Mode

Show individual file changes and full dependency reasons:

```bash
agentos task repo-trace task-123 --detailed
```

**Additional Output:**

```
backend (FULL access):
  Changes:
    M  src/main.py
    A  src/utils.py
    D  src/legacy.py
    Total: 3 files, +80/-110 lines
    Commit: abc123de

🔗 Dependencies

  Depends on:
    • task-120 (requires)
      Uses commit from task-120

  Depended by:
    • task-125 (suggests)
      Reads files modified by this task
```

#### 3. JSON Format

```bash
agentos task repo-trace task-123 --format json
```

**Example Output:**

```json
{
  "task": {
    "task_id": "task-123",
    "status": "completed",
    "created_at": "2026-01-28T10:00:00Z",
    "updated_at": "2026-01-28T11:00:00Z"
  },
  "repositories": [
    {
      "repo_id": "repo-001",
      "name": "backend",
      "scope": "FULL",
      "changes": {
        "files": ["src/main.py", "src/utils.py", "src/legacy.py"],
        "file_count": 3,
        "lines_added": 80,
        "lines_deleted": 110,
        "commit_hash": "abc123de"
      }
    }
  ],
  "artifacts": [
    {
      "ref_type": "commit",
      "ref_value": "abc123def",
      "summary": "Main logic refactoring",
      "repo_id": "repo-001"
    }
  ],
  "dependencies": {
    "depends_on": [
      {
        "depends_on_task_id": "task-120",
        "dependency_type": "requires",
        "reason": "Uses commit from task-120"
      }
    ],
    "depended_by": [
      {
        "task_id": "task-125",
        "dependency_type": "suggests",
        "reason": "Reads files modified by this task"
      }
    ]
  }
}
```

#### 4. Tree Format (Dependency Tree)

Visualize dependency relationships:

```bash
agentos task repo-trace task-123 --format tree
```

**Example Output:**

```
task-123 (completed)
├── depends on:
│   └── task-120 (requires)
│       └── Uses commit from task-120
├── depended by:
│   └── task-125 (suggests)
│       └── Reads files modified by this task
└── repositories (2)
    ├── backend (FULL)
    │   └── 3 files, +80/-110 lines
    └── frontend (READ_ONLY)
```

## Alternative Access via Dependencies Command

The task trace can also be accessed through the dependencies command group:

```bash
agentos task dependencies trace <task_id>
```

This provides the same functionality as `agentos task repo-trace`.

## Common Use Cases

### 1. Quick Project Overview

Get a quick overview of all repositories and recent activity:

```bash
agentos project trace my-app
```

### 2. Investigate Task Changes

See exactly what a task changed across repositories:

```bash
agentos task repo-trace task-123 --detailed
```

### 3. Find Cross-Repository Dependencies

Identify which tasks depend on each other across repos:

```bash
# View dependency tree
agentos task repo-trace task-123 --format tree

# Or use dedicated dependencies command
agentos task dependencies show task-123
```

### 4. Export for Analysis

Export data to JSON for further analysis:

```bash
# Export project trace
agentos project trace my-app --format json > project-trace.json

# Export task trace
agentos task repo-trace task-123 --format json > task-trace.json

# Analyze with jq
cat task-trace.json | jq '.repositories[] | select(.changes.file_count > 0)'
```

### 5. Monitor Large Projects

Use pagination to avoid overwhelming output:

```bash
# Limit to recent 10 tasks per repository
agentos project trace large-project --limit 10
```

### 6. CI/CD Integration

Check task status and changes in CI pipeline:

```bash
#!/bin/bash
# Check if task completed successfully
TASK_ID="task-123"
STATUS=$(agentos task repo-trace $TASK_ID --format json | jq -r '.task.status')

if [ "$STATUS" = "completed" ]; then
  echo "Task completed successfully"
  # Get list of changed files
  agentos task repo-trace $TASK_ID --format json | jq -r '.repositories[].changes.files[]'
else
  echo "Task not completed: $STATUS"
  exit 1
fi
```

## Performance Considerations

### Caching

The CLI commands use a 15-minute cache for audit data queries. This improves response time when repeatedly querying the same data.

### Large Projects

For projects with many repositories and tasks:

1. **Use `--limit`** to reduce the number of tasks shown per repository
2. **Use `--format json`** for scripting (faster than rich text formatting)
3. **Filter by specific repositories** when analyzing task changes

### Parallel Queries

The implementation queries multiple repositories in parallel to improve performance on large projects.

## Troubleshooting

### Task Not Found

```bash
$ agentos task repo-trace nonexistent-task
✗ Task not found: nonexistent-task
```

**Solution:** Verify the task ID with `agentos task list`

### Project Not Found

```bash
$ agentos project trace nonexistent-project
✗ Project not found: nonexistent-project
```

**Solution:** Check project ID with `agentos project list`

### No Repositories

```bash
$ agentos project trace my-app
⚠ No repositories found for project: my-app
```

**Solution:** Add repositories with `agentos project import-repos`

## Related Commands

- `agentos project list` - List all registered projects
- `agentos project import-repos` - Import multiple repositories
- `agentos task list` - List all tasks
- `agentos task dependencies show` - Show task dependencies
- `agentos task dependencies graph` - Export dependency graph

## Next Steps

- See [MULTI_REPO_GUIDE.md](../MULTI_REPO_GUIDE.md) for overall multi-repository workflow
- See [DEPENDENCY_GUIDE.md](../task/DEPENDENCY_GUIDE.md) for dependency management
- See [AUDIT_TRAIL.md](../task/AUDIT_TRAIL.md) for audit trail details
