# v0.4 CLI Guide - Project-Aware Task OS

**Version**: v0.4.0
**Date**: 2026-01-29
**Status**: Implementation Complete (Phase 5)

---

## Overview

The v0.4 CLI implements command-line tools for the Project-Aware Task Operating System. All commands follow the pattern `agentos <group>-v31 <command>`.

### New Command Groups

- `project-v31` - Project management
- `repo-v31` - Repository management
- `task-v31` - Task management extensions

---

## Project Commands

### `agentos project-v31 list`

List all projects with optional tag filtering.

**Usage**:
```bash
# List all projects
agentos project-v31 list

# Filter by tags
agentos project-v31 list --tags backend,api

# Limit results
agentos project-v31 list --limit 50

# JSON output
agentos project-v31 list --json
```

**Output**:
```
ID              Name                Tags              Repos  Tasks  Updated
proj_abc123     E-Commerce          backend,api       2      5      2026-01-29 12:34
proj_def456     Analytics           data,ml           1      3      2026-01-28 10:20
```

---

### `agentos project-v31 create`

Create a new project.

**Usage**:
```bash
# Basic creation
agentos project-v31 create "My Project"

# With description and tags
agentos project-v31 create "E-Commerce" \
  --desc "Main e-commerce backend" \
  --tags backend,api

# Quiet mode (only output project ID)
agentos project-v31 create "Test Project" --quiet
```

**Output**:
```
✓ Project created successfully
  ID: proj_01HY6X9ABC123
  Name: E-Commerce Platform
  Tags: backend, api
```

---

### `agentos project-v31 show`

Show project details with repositories and tasks.

**Usage**:
```bash
# Show project details
agentos project-v31 show proj_abc123

# JSON output
agentos project-v31 show proj_abc123 --json
```

**Output**:
```
╭─ Project Details ─────────────────────────────────────────╮
│ Project ID: proj_01HY6X9ABC123                             │
│ Name: E-Commerce Platform                                  │
│ Description: Main e-commerce backend                       │
│ Tags: backend, api                                         │
│ Created: 2026-01-29T12:34:56Z                             │
│ Updated: 2026-01-29T12:34:56Z                             │
│                                                            │
│ Repositories (2):                                          │
│   - backend (repo_01HY6XABCD456)                          │
│     Path: /Users/dev/backend                              │
│     Remote: https://github.com/org/backend.git            │
│   - frontend (repo_01HY6XABCD789)                         │
│     Path: /Users/dev/frontend                             │
│                                                            │
│ Tasks: 5 total (3 completed, 2 pending)                   │
╰────────────────────────────────────────────────────────────╯
```

---

### `agentos project-v31 delete`

Delete a project.

**Usage**:
```bash
# Delete with confirmation
agentos project-v31 delete proj_abc123

# Force delete (even if has tasks)
agentos project-v31 delete proj_abc123 --force

# Skip confirmation
agentos project-v31 delete proj_abc123 --yes
```

**Output**:
```
⚠ This will delete project 'E-Commerce Platform' and all its data.
Continue? [y/N]: y
✓ Project deleted: proj_abc123
```

---

## Repository Commands

### `agentos repo-v31 add`

Add a repository to a project.

**Usage**:
```bash
# Add repository
agentos repo-v31 add \
  --project proj_abc123 \
  --name api-service \
  --path /Users/dev/api

# With remote and branch
agentos repo-v31 add \
  --project proj_abc123 \
  --name backend \
  --path /Users/dev/backend \
  --vcs git \
  --remote https://github.com/org/backend.git \
  --branch main

# Quiet mode (only output repo ID)
agentos repo-v31 add --project proj_abc123 --name test --path /tmp/test --quiet
```

**Output**:
```
✓ Repository added successfully
  ID: repo_01HY6XABCD456
  Name: api-service
  Path: /Users/dev/api
  Project: E-Commerce Platform (proj_abc123)
```

---

### `agentos repo-v31 list`

List repositories.

**Usage**:
```bash
# List all repositories
agentos repo-v31 list

# Filter by project
agentos repo-v31 list --project proj_abc123

# JSON output
agentos repo-v31 list --json
```

**Output**:
```
ID              Name            Project         Path                    VCS
repo_xyz789     api-service     E-Commerce      /Users/dev/api          git
repo_abc456     frontend        E-Commerce      /Users/dev/web          git
```

---

### `agentos repo-v31 show`

Show repository details.

**Usage**:
```bash
agentos repo-v31 show repo_xyz789
```

---

### `agentos repo-v31 scan`

Scan Git repository for current state.

**Usage**:
```bash
agentos repo-v31 scan repo_xyz789
```

**Output**:
```
╭─ Repository Scan ──────────────────────────────────────────╮
│ Repository: api-service (repo_xyz789)                       │
│ Path: /Users/dev/api                                        │
│ VCS Type: git                                               │
│ Current Branch: main                                        │
│ Remote URL: https://github.com/org/api.git                 │
│ Last Commit: abc1234def...                                  │
│ Status: Clean                                               │
╰─────────────────────────────────────────────────────────────╯
```

---

## Task Commands

### `agentos task-v31 create`

Create a new task (must specify project).

**Usage**:
```bash
# Basic creation
agentos task-v31 create \
  --project proj_abc123 \
  --title "Implement user authentication"

# With intent and acceptance criteria
agentos task-v31 create \
  --project proj_abc123 \
  --title "Add auth module" \
  --intent "Add JWT-based authentication" \
  --ac "Login endpoint returns valid token" \
  --ac "Protected routes verify token"

# Bind to repo immediately
agentos task-v31 create \
  --project proj_abc123 \
  --repo repo_xyz789 \
  --workdir src/auth \
  --title "Add auth module"

# Quiet mode
agentos task-v31 create --project proj_abc123 --title "Test" --quiet
```

**Output**:
```
✓ Task created successfully
  ID: task_01HY6XA789
  Title: Implement user authentication
  Project: E-Commerce Platform (proj_abc123)
  Status: draft

Next steps:
  1. Review spec: agentos task-v31 show task_01HY6XA789
  2. Freeze spec: agentos task-v31 freeze task_01HY6XA789
  3. Mark ready: agentos task-v31 ready task_01HY6XA789
```

---

### `agentos task-v31 freeze`

Freeze task specification (DRAFT → PLANNED).

**Usage**:
```bash
# Freeze spec
agentos task-v31 freeze task_123456

# Add acceptance criteria before freezing
agentos task-v31 freeze task_123456 \
  --ac "All tests pass" \
  --ac "Documentation updated"
```

**Output**:
```
✓ Task spec frozen
  Task: task_123456
  Status: draft → planned

Next step:
  Mark as ready: agentos task-v31 ready task_123456
```

---

### `agentos task-v31 bind`

Bind task to project/repository.

**Usage**:
```bash
# Bind to project only
agentos task-v31 bind task_123456 --project proj_abc123

# Bind to project and repo
agentos task-v31 bind task_123456 \
  --project proj_abc123 \
  --repo repo_xyz789

# With working directory
agentos task-v31 bind task_123456 \
  --project proj_abc123 \
  --repo repo_xyz789 \
  --workdir src/auth
```

**Output**:
```
✓ Task bound successfully
  Task: task_123456
  Project: E-Commerce Platform
  Repository: api-service
  Working Directory: src/auth
```

---

### `agentos task-v31 ready`

Mark task as ready (PLANNED → READY).

**Usage**:
```bash
agentos task-v31 ready task_123456
```

**Output**:
```
✓ Task marked as ready
  Task: task_123456
  Status: planned → ready

Task is now ready for execution.
```

---

### `agentos task-v31 list`

List tasks with project filtering.

**Usage**:
```bash
# List all tasks
agentos task-v31 list

# Filter by project
agentos task-v31 list --project proj_abc123

# Filter by status
agentos task-v31 list --status ready

# Combine filters
agentos task-v31 list --project proj_abc123 --status ready

# Limit results
agentos task-v31 list --limit 50

# JSON output
agentos task-v31 list --json
```

**Output**:
```
ID              Title                      Project         Status    Updated
task_123456     Implement auth             E-Commerce      ready     2026-01-29 12:34
task_789012     Add user profile           E-Commerce      planned   2026-01-29 10:20
```

---

### `agentos task-v31 show`

Show task details with project/repo info.

**Usage**:
```bash
agentos task-v31 show task_123456
```

**Output**:
```
╭─ Task Details ─────────────────────────────────────────────╮
│ Task ID: task_01HY6XA789                                    │
│ Title: Implement user authentication                        │
│ Status: ready                                               │
│ Spec Frozen: Yes                                            │
│ Project: E-Commerce Platform (proj_abc123)                  │
│ Repository: api-service (repo_xyz789)                       │
│ Working Directory: src/auth                                 │
│                                                             │
│ Created: 2026-01-29T10:00:00Z                              │
│ Updated: 2026-01-29T12:34:56Z                              │
│                                                             │
│ Intent:                                                     │
│   Add JWT-based authentication to API                       │
│                                                             │
│ Acceptance Criteria:                                        │
│   1. Login endpoint returns valid token                     │
│   2. Protected routes verify token                          │
│   3. All tests pass                                         │
╰─────────────────────────────────────────────────────────────╯
```

---

## Complete Workflow Example

### Scenario: Create and Execute a Task

```bash
# 1. Create project
PROJECT_ID=$(agentos project-v31 create "E-Commerce" --tags backend --quiet)
echo "Created project: $PROJECT_ID"

# 2. Add repository
REPO_ID=$(agentos repo-v31 add \
  --project $PROJECT_ID \
  --name backend \
  --path /Users/dev/backend \
  --remote https://github.com/org/backend.git \
  --quiet)
echo "Added repo: $REPO_ID"

# 3. Create task
TASK_ID=$(agentos task-v31 create \
  --project $PROJECT_ID \
  --title "Implement auth" \
  --intent "Add JWT authentication" \
  --ac "Tests pass" \
  --quiet)
echo "Created task: $TASK_ID"

# 4. Freeze spec
agentos task-v31 freeze $TASK_ID

# 5. Bind to repo
agentos task-v31 bind $TASK_ID \
  --project $PROJECT_ID \
  --repo $REPO_ID \
  --workdir src/auth

# 6. Mark ready
agentos task-v31 ready $TASK_ID

# 7. View task
agentos task-v31 show $TASK_ID

echo "✓ Task is ready for execution!"
```

---

## Error Handling

All commands provide clear error messages with hints:

### Example: Missing Project
```
✗ Error: Project not found: proj_abc123
```

### Example: Name Conflict
```
✗ Error: Project name 'E-Commerce' already exists
Hint: Project name must be unique
```

### Example: Invalid Transition
```
✗ Error: Cannot transition from draft to ready
Hint: Task must be in PLANNED state to mark as ready
```

---

## Output Formats

All list and show commands support multiple output formats:

### 1. Rich Table (Default)
Human-readable tables with colors and formatting.

### 2. JSON Output (`--json`)
Machine-readable JSON for scripting:
```bash
agentos project-v31 list --json | jq '.[] | .name'
```

### 3. Quiet Mode (`--quiet`)
Only output the created ID for scripting:
```bash
PROJECT_ID=$(agentos project-v31 create "Test" --quiet)
```

---

## Tips

1. **Use `--json` for scripting**: Combine with `jq` for powerful automation
2. **Use `--quiet` for pipelines**: Extract IDs for chaining commands
3. **Always specify project**: Task creation requires `--project` parameter
4. **Check help**: Use `--help` on any command for detailed options

---

## Related Documentation

- [V31 API Reference](../api/V31_API_REFERENCE.md) - RESTful API documentation
- [ADR v0.4](../architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md) - Architecture decisions
- [State Machine](../architecture/TASK_STATE_MACHINE.md) - Task lifecycle

---

**Created**: 2026-01-29
**Last Updated**: 2026-01-29
**Version**: v0.4.0
