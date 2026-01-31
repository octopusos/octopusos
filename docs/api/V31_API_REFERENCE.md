# v0.31 API Reference - Project-Aware Task OS

**Version**: v0.4.0
**Date**: 2026-01-29
**Status**: Implementation Complete (Phase 3)

---

## Overview

The v0.31 API implements the Project-Aware Task Operating System (v0.4) as defined in [ADR-V04](../architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md). This API exposes Phase 2 Services as RESTful HTTP endpoints.

### Key Concepts

- **Project ≠ Repository**: Projects are logical containers that can bind multiple repositories
- **Task MUST Bind to Project**: Tasks require `project_id` before entering READY state
- **Spec Freezing**: Task specs must be frozen (immutable) before execution
- **Multi-Repo Support**: Tasks can access multiple repositories within their project

---

## Table of Contents

1. [Projects API](#projects-api)
2. [Repos API](#repos-api)
3. [Tasks API Extensions](#tasks-api-extensions)
4. [Error Codes](#error-codes)
5. [Usage Scenarios](#usage-scenarios)

---

## Projects API

Base path: `/api/projects`

### 1. List Projects

**Endpoint**: `GET /api/projects`

**Description**: List all projects with pagination and tag filtering

**Query Parameters**:
- `limit` (int, optional): Max results (default: 100, max: 500)
- `offset` (int, optional): Pagination offset (default: 0)
- `tags` (string, optional): Filter by tags (comma-separated, OR logic)

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/projects?limit=50&offset=0&tags=backend,api"
```

**Example Response**:
```json
{
  "success": true,
  "projects": [
    {
      "project_id": "proj_01HY6X9ABC123",
      "name": "E-Commerce Platform",
      "description": "Main e-commerce backend",
      "tags": ["backend", "api"],
      "default_repo_id": null,
      "created_at": "2026-01-29T12:34:56Z",
      "updated_at": "2026-01-29T12:34:56Z",
      "metadata": {}
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### 2. Create Project

**Endpoint**: `POST /api/projects`

**Description**: Create a new project

**Request Body**:
```json
{
  "name": "My Project",
  "description": "Optional description",
  "tags": ["backend", "api"],
  "default_repo_id": null
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-Commerce Platform",
    "description": "Main e-commerce backend",
    "tags": ["backend", "api"]
  }'
```

**Example Response**:
```json
{
  "success": true,
  "project": {
    "project_id": "proj_01HY6X9ABC123",
    "name": "E-Commerce Platform",
    "description": "Main e-commerce backend",
    "tags": ["backend", "api"],
    "default_repo_id": null,
    "created_at": "2026-01-29T12:34:56Z",
    "updated_at": "2026-01-29T12:34:56Z",
    "metadata": {}
  }
}
```

**Errors**:
- `400 PROJECT_NAME_CONFLICT`: Name already exists

---

### 3. Get Project

**Endpoint**: `GET /api/projects/{project_id}`

**Description**: Get project details with repos and task count

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/projects/proj_01HY6X9ABC123"
```

**Example Response**:
```json
{
  "success": true,
  "project": {
    "project_id": "proj_01HY6X9ABC123",
    "name": "E-Commerce Platform",
    "description": "Main e-commerce backend",
    "tags": ["backend", "api"],
    "default_repo_id": "repo_01HY6XABCD456",
    "created_at": "2026-01-29T12:34:56Z",
    "updated_at": "2026-01-29T12:34:56Z",
    "metadata": {}
  },
  "repos": [
    {
      "repo_id": "repo_01HY6XABCD456",
      "project_id": "proj_01HY6X9ABC123",
      "name": "backend",
      "local_path": "/Users/dev/backend",
      "vcs_type": "git",
      "remote_url": "https://github.com/org/backend.git",
      "default_branch": "main",
      "created_at": "2026-01-29T12:35:00Z",
      "updated_at": "2026-01-29T12:35:00Z",
      "metadata": {}
    }
  ],
  "tasks_count": 5
}
```

**Errors**:
- `404 PROJECT_NOT_FOUND`: Project doesn't exist

---

### 4. Update Project

**Endpoint**: `PATCH /api/projects/{project_id}`

**Description**: Update project fields (partial update)

**Request Body** (all fields optional):
```json
{
  "name": "New Name",
  "description": "New description",
  "tags": ["new", "tags"],
  "default_repo_id": "repo_xxx"
}
```

**Example Request**:
```bash
curl -X PATCH "http://localhost:8000/api/projects/proj_01HY6X9ABC123" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description"
  }'
```

**Example Response**:
```json
{
  "success": true,
  "project": {
    "project_id": "proj_01HY6X9ABC123",
    "name": "E-Commerce Platform",
    "description": "Updated description",
    "tags": ["backend", "api"],
    "default_repo_id": null,
    "created_at": "2026-01-29T12:34:56Z",
    "updated_at": "2026-01-29T13:00:00Z",
    "metadata": {}
  }
}
```

**Errors**:
- `404 PROJECT_NOT_FOUND`
- `400 PROJECT_NAME_CONFLICT`
- `400 NO_FIELDS_TO_UPDATE`

---

### 5. Delete Project

**Endpoint**: `DELETE /api/projects/{project_id}`

**Description**: Delete project

**Query Parameters**:
- `force` (bool, optional): Force delete even if has tasks (default: false)

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/projects/proj_01HY6X9ABC123?force=false"
```

**Example Response**:
```json
{
  "success": true,
  "message": "Project proj_01HY6X9ABC123 deleted successfully"
}
```

**Errors**:
- `404 PROJECT_NOT_FOUND`
- `400 PROJECT_HAS_TASKS`: Cannot delete project with tasks (when force=false)

---

### 6. Get Project Repos

**Endpoint**: `GET /api/projects/{project_id}/repos`

**Description**: Get all repositories for a project

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/projects/proj_01HY6X9ABC123/repos"
```

**Example Response**:
```json
{
  "success": true,
  "repos": [
    {
      "repo_id": "repo_01HY6XABCD456",
      "project_id": "proj_01HY6X9ABC123",
      "name": "backend",
      "local_path": "/Users/dev/backend",
      "vcs_type": "git",
      "remote_url": "https://github.com/org/backend.git",
      "default_branch": "main",
      "created_at": "2026-01-29T12:35:00Z",
      "updated_at": "2026-01-29T12:35:00Z",
      "metadata": {}
    }
  ]
}
```

**Errors**:
- `404 PROJECT_NOT_FOUND`

---

### 7. Add Repo to Project

**Endpoint**: `POST /api/projects/{project_id}/repos`

**Description**: Add a repository to a project

**Request Body**:
```json
{
  "name": "api-service",
  "local_path": "/absolute/path/to/repo",
  "vcs_type": "git",
  "remote_url": "https://github.com/org/api.git",
  "default_branch": "main"
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/projects/proj_01HY6X9ABC123/repos" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backend",
    "local_path": "/Users/dev/backend",
    "vcs_type": "git",
    "remote_url": "https://github.com/org/backend.git",
    "default_branch": "main"
  }'
```

**Example Response**:
```json
{
  "success": true,
  "repo": {
    "repo_id": "repo_01HY6XABCD456",
    "project_id": "proj_01HY6X9ABC123",
    "name": "backend",
    "local_path": "/Users/dev/backend",
    "vcs_type": "git",
    "remote_url": "https://github.com/org/backend.git",
    "default_branch": "main",
    "created_at": "2026-01-29T12:35:00Z",
    "updated_at": "2026-01-29T12:35:00Z",
    "metadata": {}
  }
}
```

**Errors**:
- `404 PROJECT_NOT_FOUND`
- `400 REPO_NAME_CONFLICT`: Name already exists in project
- `400 INVALID_PATH`: Path is not absolute or unsafe
- `400 PATH_NOT_FOUND`: Path doesn't exist

---

## Repos API

Base path: `/api/repos`

### 1. Get Repo

**Endpoint**: `GET /api/repos/{repo_id}`

**Description**: Get repository details by ID

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/repos/repo_01HY6XABCD456"
```

**Example Response**:
```json
{
  "success": true,
  "repo": {
    "repo_id": "repo_01HY6XABCD456",
    "project_id": "proj_01HY6X9ABC123",
    "name": "backend",
    "local_path": "/Users/dev/backend",
    "vcs_type": "git",
    "remote_url": "https://github.com/org/backend.git",
    "default_branch": "main",
    "created_at": "2026-01-29T12:35:00Z",
    "updated_at": "2026-01-29T12:35:00Z",
    "metadata": {}
  }
}
```

**Errors**:
- `404 REPO_NOT_FOUND`

---

### 2. Update Repo

**Endpoint**: `PATCH /api/repos/{repo_id}`

**Description**: Update repository fields (partial update)

**Request Body** (all fields optional):
```json
{
  "name": "new-name",
  "local_path": "/new/path",
  "remote_url": "https://...",
  "default_branch": "develop"
}
```

**Example Request**:
```bash
curl -X PATCH "http://localhost:8000/api/repos/repo_01HY6XABCD456" \
  -H "Content-Type: application/json" \
  -d '{
    "default_branch": "develop"
  }'
```

**Example Response**:
```json
{
  "success": true,
  "repo": {
    "repo_id": "repo_01HY6XABCD456",
    "project_id": "proj_01HY6X9ABC123",
    "name": "backend",
    "local_path": "/Users/dev/backend",
    "vcs_type": "git",
    "remote_url": "https://github.com/org/backend.git",
    "default_branch": "develop",
    "created_at": "2026-01-29T12:35:00Z",
    "updated_at": "2026-01-29T13:10:00Z",
    "metadata": {}
  }
}
```

**Errors**:
- `404 REPO_NOT_FOUND`
- `400 INVALID_PATH`: Path is not absolute or unsafe
- `400 PATH_NOT_FOUND`: Path doesn't exist
- `400 NO_FIELDS_TO_UPDATE`

---

### 3. Scan Repo (P1 Feature)

**Endpoint**: `POST /api/repos/{repo_id}/scan`

**Description**: Scan Git repository for current state

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/repos/repo_01HY6XABCD456/scan"
```

**Example Response**:
```json
{
  "success": true,
  "info": {
    "vcs_type": "git",
    "current_branch": "main",
    "remote_url": "https://github.com/org/backend.git",
    "last_commit": "abc123def456",
    "is_dirty": false
  }
}
```

**Errors**:
- `404 REPO_NOT_FOUND`
- `400 NOT_A_GIT_REPO`: Repository is not a git repository
- `400 PATH_NOT_FOUND`: Repository path doesn't exist

---

## Tasks API Extensions

Base path: `/api/tasks`

### 1. Freeze Task Spec

**Endpoint**: `POST /api/tasks/{task_id}/spec/freeze`

**Description**: Freeze task spec (DRAFT → PLANNED)

**Process**:
1. Verify spec completeness (title, acceptance_criteria)
2. Create new spec version (version++)
3. Set task.spec_frozen = 1
4. Update task.status = "planned"
5. Write audit event: TASK_SPEC_FROZEN

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/tasks/task_01HY6XA789/spec/freeze"
```

**Example Response**:
```json
{
  "success": true,
  "task": {
    "task_id": "task_01HY6XA789",
    "title": "Implement user authentication",
    "status": "planned",
    "spec_frozen": 1,
    "created_at": "2026-01-29T12:40:00Z",
    "updated_at": "2026-01-29T13:20:00Z"
  },
  "spec": {
    "spec_id": "spec_01HY6XABC890",
    "task_id": "task_01HY6XA789",
    "spec_version": 1,
    "title": "Implement user authentication",
    "intent": "Add JWT-based authentication",
    "constraints": ["no_breaking_changes"],
    "acceptance_criteria": ["Tests pass", "Code review approved"],
    "inputs": {},
    "created_at": "2026-01-29T13:20:00Z",
    "metadata": {}
  }
}
```

**Errors**:
- `404 TASK_NOT_FOUND`
- `404 SPEC_NOT_FOUND`
- `400 SPEC_ALREADY_FROZEN`
- `400 SPEC_INCOMPLETE`: Missing required fields

---

### 2. Bind Task

**Endpoint**: `POST /api/tasks/{task_id}/bind`

**Description**: Create or update task binding to project/repo

**Request Body**:
```json
{
  "project_id": "proj_01HY6X9ABC123",
  "repo_id": "repo_01HY6XABCD456",
  "workdir": "backend/api"
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/tasks/task_01HY6XA789/bind" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_01HY6X9ABC123",
    "repo_id": "repo_01HY6XABCD456",
    "workdir": "backend/api"
  }'
```

**Example Response**:
```json
{
  "success": true,
  "binding": {
    "task_id": "task_01HY6XA789",
    "project_id": "proj_01HY6X9ABC123",
    "repo_id": "repo_01HY6XABCD456",
    "workdir": "backend/api",
    "created_at": "2026-01-29T13:25:00Z",
    "updated_at": "2026-01-29T13:25:00Z"
  }
}
```

**Errors**:
- `404 TASK_NOT_FOUND`
- `404 PROJECT_NOT_FOUND`
- `404 REPO_NOT_FOUND`
- `400 REPO_NOT_IN_PROJECT`
- `400 INVALID_WORKDIR`: Unsafe path

---

### 3. Mark Task Ready

**Endpoint**: `POST /api/tasks/{task_id}/ready`

**Description**: Mark task as ready (PLANNED → READY)

**Validation**:
- spec_frozen = 1
- binding.project_id is not null
- dependencies satisfied

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/tasks/task_01HY6XA789/ready"
```

**Example Response**:
```json
{
  "success": true,
  "task": {
    "task_id": "task_01HY6XA789",
    "title": "Implement user authentication",
    "status": "ready",
    "spec_frozen": 1,
    "project_id": "proj_01HY6X9ABC123",
    "created_at": "2026-01-29T12:40:00Z",
    "updated_at": "2026-01-29T13:30:00Z"
  }
}
```

**Errors**:
- `404 TASK_NOT_FOUND`
- `404 BINDING_NOT_FOUND`
- `400 SPEC_NOT_FROZEN`
- `400 BINDING_INCOMPLETE`

---

### 4. List Task Artifacts

**Endpoint**: `GET /api/tasks/{task_id}/artifacts`

**Description**: List artifacts for a task

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/tasks/task_01HY6XA789/artifacts"
```

**Example Response**:
```json
{
  "success": true,
  "artifacts": [
    {
      "artifact_id": "art_01HY6XABCD123",
      "task_id": "task_01HY6XA789",
      "kind": "file",
      "path": "/tmp/output.txt",
      "display_name": "Test Output",
      "hash": "sha256:abc123...",
      "size_bytes": 1024,
      "created_at": "2026-01-29T14:00:00Z",
      "metadata": {}
    }
  ]
}
```

**Errors**:
- `404 TASK_NOT_FOUND`

---

### 5. Register Artifact

**Endpoint**: `POST /api/tasks/{task_id}/artifacts`

**Description**: Register a task artifact

**Request Body**:
```json
{
  "kind": "file",
  "path": "/path/to/artifact",
  "display_name": "Optional name",
  "hash": "sha256:...",
  "size_bytes": 1024
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/tasks/task_01HY6XA789/artifacts" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "file",
    "path": "/tmp/output.txt",
    "display_name": "Test Output"
  }'
```

**Example Response**:
```json
{
  "success": true,
  "artifact": {
    "artifact_id": "art_01HY6XABCD123",
    "task_id": "task_01HY6XA789",
    "kind": "file",
    "path": "/tmp/output.txt",
    "display_name": "Test Output",
    "hash": null,
    "size_bytes": null,
    "created_at": "2026-01-29T14:00:00Z",
    "metadata": {}
  }
}
```

**Errors**:
- `404 TASK_NOT_FOUND`
- `400 INVALID_KIND`: Kind must be file/dir/url/log/report
- `400 UNSAFE_PATH`
- `400 PATH_NOT_FOUND`

---

## Error Codes

All errors follow a structured format:

```json
{
  "success": false,
  "reason_code": "ERROR_CODE",
  "message": "Human-readable error message",
  "hint": "Helpful hint for resolution",
  "context": {
    "key": "value"
  }
}
```

### Project Errors

| Code | Status | Description | Hint |
|------|--------|-------------|------|
| `PROJECT_NOT_FOUND` | 404 | Project doesn't exist | Verify the project_id is correct. Use GET /api/projects to list all projects. |
| `PROJECT_NAME_CONFLICT` | 400 | Name already exists | Choose a different project name. Names must be unique across all projects. |
| `PROJECT_HAS_TASKS` | 400 | Cannot delete project with tasks | Archive the project instead, or use force=true to attempt deletion (may fail). |

### Repository Errors

| Code | Status | Description | Hint |
|------|--------|-------------|------|
| `REPO_NOT_FOUND` | 404 | Repository doesn't exist | Verify the repo_id is correct. Use GET /api/repos to list repositories. |
| `REPO_NAME_CONFLICT` | 400 | Name already exists in project | Choose a different repository name within this project. |
| `REPO_NOT_IN_PROJECT` | 400 | Repo doesn't belong to project | The repository must belong to the same project as the task. |
| `INVALID_PATH` | 400 | Path is invalid or unsafe | Provide an absolute path (for repos) or relative path without '..' (for workdir). |
| `PATH_NOT_FOUND` | 400 | Path doesn't exist | Ensure the path exists on the filesystem before adding the repository. |

### Spec Errors

| Code | Status | Description | Hint |
|------|--------|-------------|------|
| `SPEC_NOT_FOUND` | 404 | Spec doesn't exist | Create a spec for this task first using the spec service. |
| `SPEC_ALREADY_FROZEN` | 400 | Spec is already frozen | Cannot modify a frozen spec. Create a new task instead. |
| `SPEC_INCOMPLETE` | 400 | Missing required fields | Ensure the spec has a title and at least one acceptance criterion. |
| `SPEC_VALIDATION_ERROR` | 400 | Spec validation failed | Check the spec fields for validation errors. |

### Binding Errors

| Code | Status | Description | Hint |
|------|--------|-------------|------|
| `BINDING_NOT_FOUND` | 404 | Binding doesn't exist | Create a binding for this task first using POST /api/tasks/{id}/bind. |
| `BINDING_ALREADY_EXISTS` | 400 | Binding already exists | A binding already exists for this task. Use update instead. |
| `INVALID_WORKDIR` | 400 | Workdir path is unsafe | Workdir must be a relative path without '..' components. |
| `BINDING_INCOMPLETE` | 400 | Binding validation failed | Ensure project_id is set and spec is frozen before marking task ready. |

### Artifact Errors

| Code | Status | Description | Hint |
|------|--------|-------------|------|
| `ARTIFACT_NOT_FOUND` | 404 | Artifact doesn't exist | Verify the artifact_id is correct. |
| `INVALID_KIND` | 400 | Invalid artifact kind | Kind must be one of: file, dir, url, log, report. |
| `UNSAFE_PATH` | 400 | Path contains unsafe patterns | Path contains unsafe characters or patterns. |
| `ARTIFACT_PATH_NOT_FOUND` | 400 | Artifact file doesn't exist | The artifact file or directory does not exist. |

---

## Usage Scenarios

### Scenario 1: Create Project and Add Repository

```bash
# 1. Create project
curl -X POST "http://localhost:8000/api/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-Commerce Platform",
    "tags": ["backend", "api"]
  }'

# Response: {"success": true, "project": {"project_id": "proj_01HY6X9ABC123", ...}}

# 2. Add repository
curl -X POST "http://localhost:8000/api/projects/proj_01HY6X9ABC123/repos" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backend",
    "local_path": "/Users/dev/backend",
    "remote_url": "https://github.com/org/backend.git"
  }'

# Response: {"success": true, "repo": {"repo_id": "repo_01HY6XABCD456", ...}}
```

### Scenario 2: Create Task → Freeze → Bind → Ready

```bash
# 1. Create task
curl -X POST "http://localhost:8000/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement user authentication",
    "project_id": "proj_01HY6X9ABC123"
  }'

# Response: {"task_id": "task_01HY6XA789", "status": "draft", ...}

# 2. Freeze spec
curl -X POST "http://localhost:8000/api/tasks/task_01HY6XA789/spec/freeze"

# Response: {"success": true, "task": {"status": "planned", "spec_frozen": 1}, ...}

# 3. Bind to project/repo
curl -X POST "http://localhost:8000/api/tasks/task_01HY6XA789/bind" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_01HY6X9ABC123",
    "repo_id": "repo_01HY6XABCD456",
    "workdir": "backend/api"
  }'

# Response: {"success": true, "binding": {...}}

# 4. Mark as ready
curl -X POST "http://localhost:8000/api/tasks/task_01HY6XA789/ready"

# Response: {"success": true, "task": {"status": "ready", ...}}
```

### Scenario 3: Register Task Artifacts

```bash
# Register multiple artifacts
curl -X POST "http://localhost:8000/api/tasks/task_01HY6XA789/artifacts" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "file",
    "path": "/tmp/output.txt",
    "display_name": "Test Output"
  }'

curl -X POST "http://localhost:8000/api/tasks/task_01HY6XA789/artifacts" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "url",
    "path": "https://docs.example.com/report",
    "display_name": "Test Report"
  }'

# List all artifacts
curl -X GET "http://localhost:8000/api/tasks/task_01HY6XA789/artifacts"
```

---

## Best Practices

### 1. Always Validate project_id

Before creating a task, verify the project exists:

```bash
# Check project exists
curl -X GET "http://localhost:8000/api/projects/proj_01HY6X9ABC123"
```

### 2. Freeze Spec Before Execution

Always freeze the spec before marking a task as ready:

```bash
# ❌ Bad: Skip freezing
curl -X POST ".../tasks/{id}/ready"

# ✅ Good: Freeze first
curl -X POST ".../tasks/{id}/spec/freeze"
curl -X POST ".../tasks/{id}/bind" -d '{...}'
curl -X POST ".../tasks/{id}/ready"
```

### 3. Use Relative Paths for Workdir

Always use relative paths (no `..`) for workdir:

```json
// ✅ Good
{
  "workdir": "backend/api"
}

// ❌ Bad
{
  "workdir": "../../../etc/passwd"
}
```

### 4. Handle Errors Gracefully

Always check the `success` field and `reason_code`:

```javascript
const response = await fetch('/api/projects', {
  method: 'POST',
  body: JSON.stringify({name: 'My Project'})
});

const data = await response.json();

if (!data.success) {
  console.error(`Error: ${data.reason_code}`);
  console.log(`Hint: ${data.hint}`);
  // Handle error
}
```

---

## Testing

Test the API with the provided integration test suite:

```bash
# Run integration tests
pytest tests/integration/test_v31_api.py -v

# Test specific scenario
pytest tests/integration/test_v31_api.py::test_create_project_flow -v
```

---

## See Also

- [ADR-V04: Project-Aware Task Operating System](../architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md)
- [Phase 2 Implementation Report](../../PHASE2_IMPLEMENTATION_REPORT.md)
- [Schema v31 Migration](../../agentos/store/migrations/schema_v31_project_aware.sql)

---

**Last Updated**: 2026-01-29
**Status**: ✅ Implementation Complete
