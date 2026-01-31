# Multi-Repo Compatibility Guide

## Overview

This guide explains how the AgentOS multi-repository architecture maintains backward compatibility with existing single-repo projects, ensuring zero breaking changes during the migration.

## Compatibility Guarantees

### ✅ What Continues to Work

All existing single-repo code patterns continue to work without modification:

```python
# Old pattern: Direct path access
project_path = project.path  # Still works

# Old pattern: Getting workspace path
workspace = project.workspace_path  # Still works

# Old pattern: Getting remote URL
remote = project.remote_url  # Still works

# Old pattern: Getting default branch
branch = project.default_branch  # Still works
```

### ⚠️ Deprecation Warnings

Multi-repo projects using single-repo APIs will receive deprecation warnings:

```python
# Multi-repo project (2+ repos)
project = Project(id="multi", name="Multi", repos=[repo1, repo2])

# This will issue a deprecation warning:
workspace = project.workspace_path
# Warning: "Accessing .workspace_path on multi-repo project is deprecated.
#          Use get_default_repo().workspace_relpath or iterate over repos."
```

### 🔄 Migration Path

The compatibility layer provides tools for gradual migration:

1. **Check Compatibility**: Analyze projects for issues
2. **Migrate Projects**: Convert legacy projects to multi-repo
3. **Update Code**: Gradually adopt new APIs

## Architecture

### Legacy Single-Repo Model

```
Project
├─ id: "proj-001"
├─ name: "My Project"
└─ path: "/workspace/my-project"  # Single path
```

### New Multi-Repo Model

```
Project
├─ id: "proj-001"
├─ name: "My Project"
├─ path: "/workspace/my-project"  # Legacy field (optional)
└─ repos: [
    ├─ RepoSpec(name="default", workspace_relpath=".")
    ├─ RepoSpec(name="backend", workspace_relpath="services/backend")
    └─ RepoSpec(name="frontend", workspace_relpath="services/frontend")
]
```

### Compatibility Layer

The `SingleRepoCompatAdapter` provides automatic API mapping:

```
Old API (project.workspace_path)
         ↓
SingleRepoCompatAdapter
         ↓
New API (project.get_default_repo().workspace_relpath)
```

## Usage Guide

### 1. Check Compatibility

Analyze existing projects for potential issues:

```python
from agentos.core.project.compat import check_compatibility_warnings

# Load project
project = load_project("proj-001")

# Check for warnings
warnings = check_compatibility_warnings(project)
for warning in warnings:
    print(f"⚠️  {warning}")
```

**Output Examples:**
```
⚠️  Project 'proj-001' has no repositories bound. Using legacy path: /workspace/proj-001.
    Consider migrating to multi-repo model.

⚠️  Project 'proj-002' is multi-repo but still has legacy 'path' field.
    Consider removing it after migration is complete.
```

### 2. Migrate Legacy Projects

Convert single-repo projects to the new model:

```python
from pathlib import Path
from agentos.core.project.compat import migrate_project_to_multi_repo
from agentos.core.project.repository import ProjectRepository

# Load legacy project (has path but no repos)
project = load_project("proj-legacy")

# Migrate
repo_crud = ProjectRepository(db_path)
success, messages = migrate_project_to_multi_repo(
    project,
    repo_crud,
    workspace_root=Path("/workspace")
)

# Review migration results
for message in messages:
    print(message)
```

**Expected Output:**
```
Created default repository: repo-01GHW... at workspace_relpath='.'
Persisted default repository to database
✓ Project 'proj-legacy' successfully migrated to multi-repo model
```

### 3. Use Compatibility Adapter

For gradual code migration, use the adapter:

```python
from agentos.core.project.compat import SingleRepoCompatAdapter

# Wrap project with adapter
adapter = SingleRepoCompatAdapter(project)

# Access legacy properties safely
workspace_path = adapter.workspace_path
remote_url = adapter.remote_url
is_writable = adapter.is_writable

# Get absolute path
abs_path = adapter.get_absolute_path(workspace_root)
```

### 4. Update Code to New API

Gradually migrate code to use the new multi-repo API:

#### Before (Single-Repo API)
```python
# Old: Assumes single repository
project_path = project.path
scanner = ScannerPipeline(project_id, Path(project_path))
```

#### After (Multi-Repo API)
```python
# New: Explicit repository access
default_repo = project.get_default_repo()
if default_repo:
    repo_path = workspace_root / default_repo.workspace_relpath
    scanner = ScannerPipeline(project_id, repo_path)
else:
    # Fallback to legacy path
    repo_path = Path(project.path)
    scanner = ScannerPipeline(project_id, repo_path)
```

#### Better: Support Multiple Repositories
```python
# Best: Iterate over all repositories
for repo in project.repos:
    repo_path = workspace_root / repo.workspace_relpath
    scanner = ScannerPipeline(project_id, repo_path, repo_id=repo.repo_id)
    scanner.scan()
```

## API Reference

### Project Model Properties

#### Backward Compatible Properties

```python
@property
def workspace_path(self) -> Optional[str]:
    """Get workspace path of default repository

    Returns:
        Workspace path of default repo, or legacy path field

    Deprecated:
        For multi-repo projects, use get_default_repo().workspace_relpath
    """
```

```python
@property
def remote_url(self) -> Optional[str]:
    """Get remote URL of default repository

    Deprecated:
        For multi-repo projects, use get_default_repo().remote_url
    """
```

```python
@property
def default_branch(self) -> str:
    """Get default branch of default repository

    Deprecated:
        For multi-repo projects, use get_default_repo().default_branch
    """
```

#### New Multi-Repo Methods

```python
def get_default_repo(self) -> Optional[RepoSpec]:
    """Get the default repository

    Priority:
    1. Repo with name="default"
    2. First repo in the list
    3. None if no repos bound

    Note:
        Issues deprecation warning for multi-repo projects
    """
```

```python
def get_repo_by_name(self, name: str) -> Optional[RepoSpec]:
    """Get repository by name"""
```

```python
def get_repo_by_id(self, repo_id: str) -> Optional[RepoSpec]:
    """Get repository by ID"""
```

```python
def is_multi_repo(self) -> bool:
    """Check if this is a multi-repository project"""
```

```python
def is_single_repo(self) -> bool:
    """Check if this is a single-repository project"""
```

### Compatibility Functions

#### `get_project_workspace_path()`
```python
def get_project_workspace_path(
    project: Project,
    workspace_root: Optional[Path] = None
) -> Optional[Path]:
    """Get workspace path for a project (compatibility function)

    Args:
        project: Project instance
        workspace_root: Optional workspace root path

    Returns:
        Path to the default repository workspace
    """
```

#### `ensure_default_repo()`
```python
def ensure_default_repo(project: Project) -> RepoSpec:
    """Ensure project has a default repository

    Creates a default repository from legacy path field if needed.

    Args:
        project: Project instance

    Returns:
        The default repository spec

    Raises:
        ValueError: If project has no repos and no legacy path field
    """
```

#### `check_compatibility_warnings()`
```python
def check_compatibility_warnings(project: Project) -> list[str]:
    """Check project for potential compatibility issues

    Args:
        project: Project to check

    Returns:
        List of warning messages (empty if no issues)
    """
```

#### `migrate_project_to_multi_repo()`
```python
def migrate_project_to_multi_repo(
    project: Project,
    project_repository: ProjectRepository,
    workspace_root: Path,
    create_default_repo: bool = True
) -> tuple[bool, list[str]]:
    """Migrate a legacy single-repo project to multi-repo model

    Args:
        project: Project to migrate
        project_repository: ProjectRepository instance
        workspace_root: Root path for workspace resolution
        create_default_repo: Whether to create default repo if missing

    Returns:
        Tuple of (success: bool, messages: list[str])
    """
```

## Code Patterns

### Pattern 1: Scanner Pipeline (Existing Code)

**Current Code (CLI/Orchestrator):**
```python
# agentos/cli/scan.py, agentos/core/orchestrator/run.py
project = cursor.execute(
    "SELECT path FROM projects WHERE id = ?", (project_id,)
).fetchone()

project_path = Path(project["path"])
scanner = ScannerPipeline(project_id, project_path)
```

**What Happens:**
- Still works! The database `projects.path` field is preserved
- For legacy projects, this continues unchanged
- For migrated projects, `path` can point to workspace root

**Migration Path:**
```python
from agentos.core.project.compat import get_project_workspace_path

# Load project with repos
project = load_full_project(project_id)  # Loads Project with repos

# Get workspace path (backward compatible)
project_path = get_project_workspace_path(project, workspace_root)
scanner = ScannerPipeline(project_id, project_path)
```

### Pattern 2: Task Execution

**Current Code:**
```python
# Tasks refer to project_id, assume single workspace
task = Task(project_id="proj-001", ...)
workspace = get_project_workspace(project_id)
execute_in_workspace(workspace)
```

**Migration Path:**
```python
# Tasks can now specify repo_id
task = Task(project_id="proj-001", repo_id="repo-backend", ...)

# Load project and get specific repo
project = load_project(task.project_id)
if task.repo_id:
    repo = project.get_repo_by_id(task.repo_id)
else:
    repo = project.get_default_repo()

workspace = workspace_root / repo.workspace_relpath
execute_in_workspace(workspace)
```

### Pattern 3: Project Creation

**Old Code:**
```python
# CLI: agentos project add /path/to/repo
cursor.execute(
    "INSERT INTO projects (id, path) VALUES (?, ?)",
    (project_id, str(project_path))
)
```

**New Code (Backward Compatible):**
```python
from agentos.core.project.repository import ProjectRepository
from agentos.schemas.project import RepoSpec
from ulid import ULID

# 1. Create project record
cursor.execute(
    "INSERT INTO projects (id, name, path) VALUES (?, ?, ?)",
    (project_id, project_name, str(project_path))
)

# 2. Create default repository binding
repo_crud = ProjectRepository(db_path)
default_repo = RepoSpec(
    repo_id=str(ULID()),
    project_id=project_id,
    name="default",
    workspace_relpath=".",
    is_writable=True
)
repo_crud.add_repo(default_repo)
```

## Testing

### Unit Tests

Run compatibility tests:
```bash
pytest tests/unit/project/test_compat.py -v
```

**Coverage Areas:**
- SingleRepoCompatAdapter properties
- Project backward compatible properties
- Migration helpers
- Deprecation warnings
- End-to-end compatibility scenarios

### Integration Tests

Test existing workflows still work:
```bash
# Test existing single-repo tests (should all pass)
pytest tests/ -k "not multi_repo" -v
```

## Troubleshooting

### Issue: "Project has no repositories and no legacy path"

**Symptom:**
```
ValueError: Project 'proj-001' has no repositories and no legacy path field.
```

**Solution:**
```python
# Check project state
warnings = check_compatibility_warnings(project)
print(warnings)

# Fix: Add legacy path or bind a repository
if not project.path and not project.repos:
    # Option 1: Set legacy path
    project.path = "/workspace/proj-001"

    # Option 2: Bind default repository
    default_repo = RepoSpec(
        repo_id=str(ULID()),
        project_id=project.id,
        name="default",
        workspace_relpath=".",
    )
    project.repos.append(default_repo)
```

### Issue: Deprecation Warnings Everywhere

**Symptom:**
```
DeprecationWarning: Accessing .workspace_path on multi-repo project is deprecated.
```

**Solution:**
This is expected for multi-repo projects. To fix:

1. **Short-term**: Suppress warnings (not recommended)
   ```python
   import warnings
   warnings.filterwarnings("ignore", category=DeprecationWarning)
   ```

2. **Long-term**: Update code to new API
   ```python
   # Old
   path = project.workspace_path

   # New
   default_repo = project.get_default_repo()
   path = default_repo.workspace_relpath if default_repo else project.path
   ```

### Issue: Legacy Path Field Mismatch

**Symptom:**
```
⚠️  Project 'proj-001' is multi-repo but still has legacy 'path' field.
```

**Solution:**
After migration, you can clear the legacy `path` field:

```python
# Update project in database
cursor.execute(
    "UPDATE projects SET path = NULL WHERE id = ?",
    (project_id,)
)
```

## Migration Checklist

- [ ] Run compatibility checker on all projects
- [ ] Migrate legacy projects to multi-repo model
- [ ] Update code to use new APIs (gradual)
- [ ] Test existing workflows still work
- [ ] Monitor deprecation warnings
- [ ] Update documentation
- [ ] Remove legacy `path` fields (optional)

## Best Practices

1. **Preserve Backward Compatibility**: Don't break existing code
2. **Issue Clear Warnings**: Help users understand deprecations
3. **Provide Migration Tools**: Make migration easy and safe
4. **Test Thoroughly**: Ensure zero regressions
5. **Document Everything**: Guide users through the transition

## References

- [Multi-Repo Architecture](./ARCHITECTURE.md)
- [API Guide](./API_GUIDE.md)
- [Migration Examples](../../examples/multi_repo_usage.py)
- [Unit Tests](../../tests/unit/project/test_compat.py)
