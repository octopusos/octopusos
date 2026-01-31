# Quick Compatibility Reference Card

**TL;DR**: Existing single-repo code works unchanged. Multi-repo projects get warnings. Migration tools available.

## For Users: Is My Code Safe?

### ✅ Yes, if you have single-repo projects

```python
# All these still work, no changes needed:
project.path
project.workspace_path
project.remote_url
project.default_branch
```

### ⚠️ Maybe, if you have multi-repo projects

You'll see warnings like:
```
DeprecationWarning: Accessing .workspace_path on multi-repo project is deprecated.
Use get_default_repo().workspace_relpath or iterate over repos.
```

**Action**: Code still works, but consider updating to new API.

## Quick Check

```bash
# Check if your projects need attention
agentos project migrate check --all
```

## Quick Migration

```bash
# Migrate a legacy project
agentos project migrate to-multi-repo PROJECT_ID

# Dry-run first (recommended)
agentos project migrate to-multi-repo PROJECT_ID --dry-run
```

## API Quick Reference

### Old Way (Still Works)
```python
# Single property access
path = project.workspace_path
url = project.remote_url
branch = project.default_branch
```

### New Way (Recommended)
```python
# Explicit repo access
default_repo = project.get_default_repo()
if default_repo:
    path = default_repo.workspace_relpath
    url = default_repo.remote_url
    branch = default_repo.default_branch
```

### Best Way (Multi-Repo)
```python
# Support multiple repos
for repo in project.repos:
    path = workspace_root / repo.workspace_relpath
    process_repo(path, repo)
```

## Common Scenarios

### Scenario 1: Scanner Pipeline
```python
# Old code (still works)
project_path = Path(project["path"])
scanner = ScannerPipeline(project_id, project_path)

# New code (recommended)
from agentos.core.project.compat import get_project_workspace_path
project_path = get_project_workspace_path(project, workspace_root)
scanner = ScannerPipeline(project_id, project_path)
```

### Scenario 2: Task Execution
```python
# Old code (still works)
workspace = project.workspace_path

# New code (recommended)
default_repo = project.get_default_repo()
workspace = default_repo.workspace_relpath if default_repo else project.path
```

### Scenario 3: Project Creation
```python
# Old code (still works)
cursor.execute(
    "INSERT INTO projects (id, path) VALUES (?, ?)",
    (project_id, str(project_path))
)

# New code (add default repo)
cursor.execute("INSERT INTO projects (id, path) VALUES (?, ?)", ...)
from agentos.core.project.compat import ensure_default_repo
ensure_default_repo(project)
```

## Troubleshooting

### "Project has no repositories and no legacy path"
```python
# Fix: Add a default repo
from agentos.schemas.project import RepoSpec
from ulid import ULID

default_repo = RepoSpec(
    repo_id=str(ULID()),
    project_id=project_id,
    name="default",
    workspace_relpath=".",
)
project.repos.append(default_repo)
```

### "Too many deprecation warnings"
```python
# Short-term: Suppress warnings (not recommended)
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Better: Update to new API
default_repo = project.get_default_repo()
path = default_repo.workspace_relpath if default_repo else project.path
```

## When to Migrate

| Situation | Action | Urgency |
|-----------|--------|---------|
| Single-repo project, no warnings | No action needed | None |
| Single-repo project, occasional warnings | Optional update | Low |
| Multi-repo project, many warnings | Update code | Medium |
| Legacy project (no repos) | Migrate project | High |
| Broken project (no repos, no path) | Fix immediately | Critical |

## Support

- **Full Guide**: [COMPATIBILITY_GUIDE.md](./COMPATIBILITY_GUIDE.md)
- **Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **API Guide**: [API_GUIDE.md](./API_GUIDE.md)
- **Tests**: `tests/unit/project/test_compat.py`
- **Examples**: `examples/multi_repo_usage.py`

## Bottom Line

**Nothing breaks.** Existing code works. Warnings help you improve. Migration tools available.

**Default strategy**: Do nothing now, migrate when convenient.
