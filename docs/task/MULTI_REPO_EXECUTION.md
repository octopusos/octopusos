# Multi-Repository Task Execution

**Phase 5.1: Runner Support for Cross-Repository Workspace Selection**

## Overview

This document describes the multi-repository execution support in AgentOS Task Runner. Tasks can now operate across multiple repositories with fine-grained access control, path filtering, and security boundaries.

## Key Features

### 1. Repository Scopes

Tasks can declare which repositories they need to access and how:

- **FULL**: Complete repository access (read + write if repo is writable)
- **PATHS**: Limited to specific paths via glob patterns
- **READ_ONLY**: Read-only access (overrides repository writable flag)

### 2. Path Security

All file operations are validated against:

- Repository boundaries (prevents directory traversal)
- Scope restrictions (enforces path filters)
- Write permissions (respects read-only flags)

### 3. Execution Environment

Tasks execute in an `ExecutionEnv` that encapsulates:

- Multiple `TaskRepoContext` objects (one per repository)
- Default repository selection
- Context switching utilities
- Path validation helpers

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Task                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ project_id: "my-project"                               │ │
│  │ repo_scopes: [                                         │ │
│  │   {repo_id: "backend", scope: FULL},                  │ │
│  │   {repo_id: "frontend", scope: READ_ONLY},            │ │
│  │   {repo_id: "docs", scope: PATHS, filters: ["*.md"]}  │ │
│  │ ]                                                      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   ExecutionEnv                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ TaskRepoContext  │  │ TaskRepoContext  │  ...           │
│  │ ─────────────────│  │ ─────────────────│                │
│  │ repo_id: backend │  │ repo_id: frontend│                │
│  │ path: /workspace │  │ path: /workspace │                │
│  │      /backend    │  │      /frontend   │                │
│  │ writable: true   │  │ writable: false  │                │
│  │ scope: FULL      │  │ scope: READ_ONLY │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 File Operations                             │
│  • Path validation (within repo bounds)                     │
│  • Scope enforcement (path filters)                         │
│  • Permission checks (read/write)                           │
└─────────────────────────────────────────────────────────────┘
```

## Usage Guide

### Basic Usage

#### 1. Create Task with Repository Scopes

```python
from agentos.core.task.models import Task, TaskRepoScope, RepoScopeType

# Create task
task = Task(
    task_id="feature-123",
    title="Cross-repo feature",
    metadata={"project_id": "my-app"}
)

# Define repository scopes
from agentos.core.task.task_repo_service import TaskRepoService

service = TaskRepoService(db_path, workspace_root)

# Backend: full access
service.add_repo_scope(TaskRepoScope(
    task_id=task.task_id,
    repo_id="repo-backend",
    scope=RepoScopeType.FULL
))

# Frontend: read-only
service.add_repo_scope(TaskRepoScope(
    task_id=task.task_id,
    repo_id="repo-frontend",
    scope=RepoScopeType.READ_ONLY
))

# Docs: only Markdown files
service.add_repo_scope(TaskRepoScope(
    task_id=task.task_id,
    repo_id="repo-docs",
    scope=RepoScopeType.PATHS,
    path_filters=["**/*.md", "*.md"]
))
```

#### 2. Build Execution Environment

```python
from agentos.core.task.runner_integration import prepare_execution_env

# Prepare execution environment
exec_env = prepare_execution_env(task)

# Get summary
from agentos.core.task.runner_integration import get_repo_summary
summary = get_repo_summary(exec_env)
print(f"Task has {summary['total_repos']} repos")
print(f"Writable repos: {summary['writable_repos']}")
```

#### 3. Execute with Repository Context

```python
from agentos.core.task.runner_integration import with_repo_context

# Work in backend repo
with with_repo_context(exec_env, repo_name="backend") as backend:
    print(f"Working in: {backend.path}")

    # Read file
    config = (backend.path / "config.py").read_text()

    # Write file (allowed - backend is writable)
    (backend.path / "output.txt").write_text("Results")

# Work in frontend repo
with with_repo_context(exec_env, repo_name="frontend") as frontend:
    # Read file (allowed - read-only means can still read)
    html = (frontend.path / "index.html").read_text()

    # Write file (BLOCKED - frontend is read-only)
    # This would raise PathSecurityError:
    # (frontend.path / "new.html").write_text("<html></html>")
```

#### 4. Safe File Operations

```python
from agentos.core.task.runner_integration import (
    safe_file_read,
    safe_file_write,
    validate_file_operation
)

# Safe read (automatically validates access)
content = safe_file_read(exec_env, "backend/src/main.py")

# Safe write (automatically validates access)
safe_file_write(
    exec_env,
    "backend/src/generated.py",
    "# Generated code"
)

# Explicit validation
context = validate_file_operation(
    exec_env,
    "backend/src/config.py",
    operation="write"  # or "read"
)
print(f"Operation allowed in repo: {context.name}")
```

### Advanced Usage

#### Path Filtering

Path filters use glob patterns to restrict access:

```python
# Only Python files in src/
path_filters = ["src/**/*.py"]

# Multiple patterns
path_filters = [
    "src/**",      # All files in src/
    "tests/**",    # All files in tests/
    "*.md",        # Markdown at root
    "**/*.json"    # JSON files anywhere
]

scope = TaskRepoScope(
    task_id=task.task_id,
    repo_id="repo-backend",
    scope=RepoScopeType.PATHS,
    path_filters=path_filters
)
```

#### Auto-Detection

If no scopes are defined, all project repositories are included with FULL scope:

```python
# No scopes defined - uses all repos
exec_env = service.build_execution_env(task_id, project_id)
# Result: All project repos with FULL scope
```

#### Default Repository

The first repository added becomes the default, unless one is named "default":

```python
default_repo = exec_env.get_default_repo()
print(f"Default repo: {default_repo.name}")

# Use default repo
with with_repo_context(exec_env) as repo:  # No repo_id/name = uses default
    # Operations in default repo
    pass
```

## Security Model

### Path Validation

All file paths are validated to prevent security issues:

1. **Directory Traversal Prevention**
   ```python
   # BLOCKED: Attempts to escape repository
   context.validate_read_access("../../etc/passwd")
   # Raises: PathSecurityError
   ```

2. **Symlink Resolution**
   ```python
   # Symlinks are resolved and validated
   # If symlink points outside repo, access is denied
   symlink = repo_path / "evil_link"  # -> /etc/passwd
   context.validate_read_access(symlink)
   # Raises: PathSecurityError
   ```

3. **Scope Enforcement**
   ```python
   # With path_filters=["src/**"]
   context.validate_write_access("src/main.py")  # OK
   context.validate_write_access("tests/test.py")  # BLOCKED
   ```

### Write Protection

Write operations are validated against:

1. Repository writable flag
2. Task scope (READ_ONLY overrides repository settings)
3. Path filters (if scope is PATHS)

```python
# Repository is writable BUT scope is READ_ONLY
context = TaskRepoContext(
    repo_id="repo-1",
    writable=True,  # Repository allows writes
    scope=RepoScopeType.READ_ONLY  # Task scope denies writes
)

context.validate_write_access("file.txt")
# Raises: PathSecurityError (read-only for this task)
```

## Integration with TaskRunner

### In Task Execution

```python
from agentos.core.task.runner_integration import prepare_execution_env

def _execute_stage(self, task: Task) -> str:
    """Execute task stage with multi-repo support"""

    # 1. Prepare execution environment
    exec_env = prepare_execution_env(task)

    # 2. Validate environment
    from agentos.core.task.task_repo_service import TaskRepoService
    service = TaskRepoService(self.db_path, self.workspace_root)
    warnings = service.validate_execution_env(exec_env)

    if warnings:
        for warning in warnings:
            logger.warning(f"ExecutionEnv validation: {warning}")

    # 3. Execute task logic
    result = self._run_task_with_env(task, exec_env)

    return result

def _run_task_with_env(self, task: Task, exec_env: ExecutionEnv):
    """Run task with execution environment"""
    from agentos.core.task.runner_integration import with_repo_context

    # Access different repos as needed
    with with_repo_context(exec_env, repo_name="backend") as backend:
        # Execute backend operations
        pass

    with with_repo_context(exec_env, repo_name="frontend") as frontend:
        # Execute frontend operations
        pass

    return "success"
```

## Error Handling

### PathSecurityError

Raised when a file operation violates security constraints:

```python
from agentos.core.task.repo_context import PathSecurityError

try:
    context.validate_write_access("protected/file.txt")
except PathSecurityError as e:
    logger.error(f"Security violation: {e}")
    # Handle gracefully (e.g., skip file, report error)
```

### ValueError

Raised when configuration is invalid:

```python
try:
    exec_env = service.build_execution_env(task_id, project_id)
except ValueError as e:
    logger.error(f"Invalid configuration: {e}")
    # E.g., repository not found, no project_id, etc.
```

## Testing

### Unit Tests

```python
def test_path_validation():
    """Test path validation"""
    context = TaskRepoContext(
        repo_id="repo-1",
        task_id="task-1",
        name="test",
        path=Path("/workspace/test"),
        scope=RepoScopeType.FULL
    )

    # Valid path
    assert context.is_path_within_repo("src/main.py")

    # Invalid path (outside repo)
    assert not context.is_path_within_repo("../../etc/passwd")
```

### Integration Tests

```python
def test_cross_repo_execution(test_db, test_workspace):
    """Test cross-repository task execution"""
    # Create task
    task = Task(task_id="task-1", metadata={"project_id": "proj-1"})

    # Prepare environment
    exec_env = prepare_execution_env(task, workspace_root=test_workspace)

    # Read from repo A
    content_a = safe_file_read(exec_env, "repoA/file.txt")

    # Write to repo B
    safe_file_write(exec_env, "repoB/output.txt", content_a)

    # Verify
    assert (test_workspace / "repoB" / "output.txt").exists()
```

## Migration Guide

### From Single-Repo to Multi-Repo

#### Before (Single-Repo)

```python
# Task executes in single repository
task = Task(task_id="task-1", title="Fix bug")

# All operations in one repo
with open("src/main.py", "r") as f:
    content = f.read()
```

#### After (Multi-Repo)

```python
# Task declares repository scopes
task = Task(
    task_id="task-1",
    title="Fix bug",
    metadata={"project_id": "my-project"}
)

# Add scopes
service.add_repo_scope(TaskRepoScope(
    task_id=task.task_id,
    repo_id="repo-backend",
    scope=RepoScopeType.FULL
))

# Execute with context
exec_env = prepare_execution_env(task)
with with_repo_context(exec_env, repo_name="backend") as backend:
    file_path = backend.path / "src" / "main.py"
    with open(file_path, "r") as f:
        content = f.read()
```

### Backward Compatibility

**Single-repository projects work unchanged:**

- If no repo scopes are defined, all project repos get FULL scope
- Default repository is automatically selected
- Existing code continues to work

## Performance Considerations

1. **Path Resolution**: Paths are resolved once and cached
2. **Validation**: Validation is fast (no file I/O for path checks)
3. **Context Switching**: Lightweight (no state maintained between contexts)

## Limitations

1. **No Nested Repositories**: Submodules must be separate repository entries
2. **No Dynamic Scopes**: Scopes must be defined before execution starts
3. **Single Workspace Root**: All repositories must be under one workspace root

## Future Enhancements

1. **Dynamic Scope Adjustment**: Change scopes during execution
2. **Repo-to-Repo Dependencies**: Explicit dependency tracking
3. **Audit Trail**: Record all file operations per repository
4. **Remote Repository Support**: Work with remote repos without local clone

## See Also

- [Task Models](./models.md) - Task and TaskRepoScope data models
- [Project Repository](../project/repository.md) - Repository management
- [Runner Integration](./runner_integration.md) - TaskRunner integration guide
- [Security Model](../security/path_validation.md) - Security design details

## Support

For issues or questions:

- File an issue: [AgentOS Issues](https://github.com/yourusername/agentos/issues)
- Documentation: [Multi-Repo Guide](./MULTI_REPO_GUIDE.md)
- Examples: [examples/task_service_usage.py](../../examples/task_service_usage.py)
