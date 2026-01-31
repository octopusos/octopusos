# Multi-Repository Project Support

**AgentOS Multi-Repo Architecture Documentation**

Version: 0.18.0
Status: Production Ready
Last Updated: 2026-01-28

---

## Table of Contents

- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Architecture](#architecture)
- [Data Model](#data-model)
- [Security and Permissions](#security-and-permissions)
- [Performance Considerations](#performance-considerations)
- [Limitations and Constraints](#limitations-and-constraints)
- [Quick Start](#quick-start)

---

## Overview

### What is Multi-Repository Project Support?

AgentOS Multi-Repository Project Support enables managing **projects that span multiple Git repositories** with unified task management, cross-repo dependency tracking, and comprehensive audit trails.

Traditional single-repository approaches break down when dealing with:

- **Microservices architectures** (backend + frontend + infra in separate repos)
- **Monorepos with subdirectories** (packages/ui, packages/api, packages/shared)
- **Documentation repositories** (code in one repo, docs in another)
- **Private dependency libraries** (internal packages across multiple repos)

Multi-repo support solves this by:

1. **Unified Project Binding**: A single project can bind multiple repositories
2. **Cross-Repo Task Management**: Tasks can span multiple repositories with controlled scope
3. **Audit Trails**: Track changes across all repositories in a single lineage
4. **Flexible Workspace**: Each repo can have its own path, role, and permissions

### Why Multi-Repository Support?

**Problem**: Traditional AI agents assume single-repo projects. When working on multi-repo systems, they either:
- Fail to see the full context (only one repo at a time)
- Mix repositories incorrectly (path conflicts, wrong permissions)
- Can't track dependencies between repos

**Solution**: AgentOS provides:
- ✅ **Project-level context**: All repos visible to tasks
- ✅ **Repository isolation**: Each repo has its own workspace path
- ✅ **Controlled access**: Per-repo permissions (read-only vs writable)
- ✅ **Cross-repo dependencies**: Automatic dependency detection
- ✅ **Audit trail**: Unified tracking across all repos

---

## Core Concepts

### 1. Project = Repos + Workspace + Auth + Policies

A **Project** is the top-level entity that binds multiple repositories together:

```
Project "my-app"
  ├── Repo: backend (code, writable, ./be)
  ├── Repo: frontend (code, writable, ./fe)
  └── Repo: docs (docs, read-only, ./docs)
```

**Key Properties**:
- **Project ID**: Unique identifier (e.g., "my-app")
- **Repositories**: List of bound repos (1 or more)
- **Workspace**: Base path for all repo workspaces
- **Metadata**: Extended project configuration (JSON)

### 2. Repository Binding (RepoSpec)

Each repository in a project has a **RepoSpec** that defines:

| Field | Description | Example |
|-------|-------------|---------|
| `repo_id` | Unique identifier (ULID) | `01HX123ABC...` |
| `project_id` | Parent project | `my-app` |
| `name` | User-friendly name | `backend` |
| `remote_url` | Git remote URL | `git@github.com:org/backend` |
| `default_branch` | Default branch | `main` |
| `workspace_relpath` | Relative workspace path | `./be` |
| `role` | Repository role | `code` |
| `is_writable` | Writable flag | `true` |
| `auth_profile` | Auth profile name | `github-ssh` |

### 3. Repository Roles

Repositories are classified by **role** to enable role-specific handling:

| Role | Description | Use Case |
|------|-------------|----------|
| `code` | Source code repository (default) | Backend API, frontend app |
| `docs` | Documentation repository | GitBook, MkDocs, Wiki |
| `infra` | Infrastructure repository | Terraform, Kubernetes configs |
| `mono-subdir` | Monorepo subdirectory | packages/ui, packages/api |

**Role-Based Behavior**:
- **code**: Full file operations (read/write/execute)
- **docs**: Markdown-optimized tooling, no build steps
- **infra**: Infrastructure-as-Code validation
- **mono-subdir**: Path-scoped operations within subdirectory

### 4. Task Repository Scope

When a task operates on a project, it specifies **repo scope** for each repository:

| Scope | Description | Permissions |
|-------|-------------|-------------|
| `FULL` | Full repository access | Read + Write (if repo.is_writable) |
| `READ_ONLY` | Read-only access | Read only, write blocked |
| `PATHS` | Path-filtered access | Limited to specific paths |

**Example: Task with Mixed Scopes**

```
Task: "Update API and sync docs"
  ├── Repo: backend (FULL) - Can read and write
  ├── Repo: frontend (READ_ONLY) - Can read API types
  └── Repo: docs (FULL, paths=["api/**"]) - Can only update api/ folder
```

**Path Filters**:
- Glob patterns: `["src/**", "tests/**"]`
- Exclusions: `["!node_modules/**", "!*.log"]`
- Security: Changes outside filters are rejected

### 5. Cross-Repository Dependencies

Tasks can depend on other tasks, especially when working across repos:

```
Task A (backend): Implement API endpoint
  ↓ blocks
Task B (frontend): Consume API endpoint
  ↓ requires
Task C (docs): Document API endpoint
```

**Dependency Types**:
- **blocks**: Must complete before dependent task can start
- **requires**: Parallel execution OK, but needs artifacts
- **suggests**: Weak dependency, informational only

**Automatic Detection**:
- Artifact references (commit SHAs, PR numbers)
- File dependencies (imports, includes)
- Configuration references (API URLs, schemas)

### 6. Cross-Repository Artifacts

Tasks generate **artifacts** that can be referenced across repos:

| Ref Type | Description | Example |
|----------|-------------|---------|
| `commit` | Git commit SHA | `abc123...` |
| `branch` | Git branch name | `feature/api-v2` |
| `pr` | Pull request number | `#123` |
| `patch` | Patch file or diff | `api-changes.patch` |
| `file` | Specific file path | `src/api/schema.json` |
| `tag` | Git tag | `v1.2.3` |

**Example: Cross-Repo Artifact Flow**

```
Task A (backend):
  - Commits API changes → Artifact: commit(abc123)
  - Creates PR #456 → Artifact: pr(456)

Task B (frontend):
  - References: commit(abc123) from backend
  - Updates frontend to consume new API
```

### 7. Audit Trail

Every task action across all repositories is recorded in the **audit trail**:

```
Task T1: "Add user authentication"
  ├── backend: Commit abc123 (src/auth.py, 15 changes)
  ├── frontend: Commit def456 (src/login.tsx, 8 changes)
  └── docs: Commit ghi789 (api/auth.md, 3 changes)

Audit Record:
  - Task: T1
  - Repos: [backend, frontend, docs]
  - Commits: [abc123, def456, ghi789]
  - Timestamp: 2026-01-28T10:30:00Z
  - Author: agent-os
```

**Query Capabilities**:
- Find all tasks that modified repo X
- Find all repos modified by task Y
- Trace changes across repos for a feature
- Detect cross-repo conflicts

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         AgentOS                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐  │
│  │   Project    │      │     Task     │      │  Audit   │  │
│  │   Registry   │◄─────┤   Manager    │─────►│  Trail   │  │
│  └───────┬──────┘      └───────┬──────┘      └──────────┘  │
│          │                     │                             │
│          │                     │                             │
│  ┌───────▼──────┐      ┌───────▼──────┐                    │
│  │   RepoSpec   │      │  RepoScope   │                     │
│  │  (Binding)   │      │  (Task-Repo) │                     │
│  └───────┬──────┘      └───────┬──────┘                    │
│          │                     │                             │
└──────────┼─────────────────────┼─────────────────────────────┘
           │                     │
           │                     │
┌──────────▼─────────────────────▼─────────────────────────────┐
│                     Workspace Layout                          │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  workspace/                                                   │
│    └── projects/                                              │
│        └── my-app/                                            │
│            ├── be/          (backend repo)                    │
│            │   ├── .git/                                      │
│            │   └── src/                                       │
│            ├── fe/          (frontend repo)                   │
│            │   ├── .git/                                      │
│            │   └── src/                                       │
│            └── docs/        (docs repo)                       │
│                ├── .git/                                      │
│                └── api/                                       │
│                                                               │
└───────────────────────────────────────────────────────────────┘
           │                     │
           │                     │
┌──────────▼─────────────────────▼─────────────────────────────┐
│                     Git Remotes                               │
├───────────────────────────────────────────────────────────────┤
│  git@github.com:org/backend   (with auth: github-ssh)        │
│  git@github.com:org/frontend  (with auth: github-ssh)        │
│  git@github.com:org/docs      (with auth: github-ssh)        │
└───────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
┌─────────┐
│  User   │ 1. Import project config
└────┬────┘
     │
     ▼
┌────────────────┐
│  CLI Import    │ 2. Validate config (auth, paths, conflicts)
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ ProjectRepo    │ 3. Create project + repo bindings
│   (CRUD)       │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ WorkspaceLayout│ 4. Setup workspace paths
└────┬───────────┘
     │
     ▼
┌────────────────┐
│  GitClient     │ 5. Clone/pull repositories (with auth)
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Task Execution │ 6. Execute task with repo scope
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ ChangeGuardRail│ 7. Validate changes (path filters, security)
└────┬───────────┘
     │
     ▼
┌────────────────┐
│  Audit Trail   │ 8. Record commits + artifacts
└────────────────┘
```

### Data Flow: Task Execution Across Repos

```
┌─────────────────────────────────────────────────────────────┐
│ Task: "Implement user authentication"                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Task Manager creates task with repo scopes:              │
│     - backend: FULL                                           │
│     - frontend: FULL                                          │
│     - docs: PATHS (paths=["api/**"])                         │
│                                                               │
│  2. Runner initializes workspace contexts:                   │
│     - backend @ workspace/projects/my-app/be                 │
│     - frontend @ workspace/projects/my-app/fe                │
│     - docs @ workspace/projects/my-app/docs                  │
│                                                               │
│  3. Agent operates in each repo:                             │
│     ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│     │  backend   │  │  frontend  │  │    docs    │         │
│     │  (write)   │  │  (write)   │  │  (write)   │         │
│     └─────┬──────┘  └─────┬──────┘  └─────┬──────┘         │
│           │               │               │                  │
│           ▼               ▼               ▼                  │
│     ┌─────────────────────────────────────────┐             │
│     │     ChangeGuardRail validates:          │             │
│     │     - Path filters                       │             │
│     │     - Security rules                     │             │
│     │     - Writable permissions               │             │
│     └─────────────────────────────────────────┘             │
│                                                               │
│  4. Commits are created in each repo:                        │
│     - backend: abc123 (src/auth.py)                          │
│     - frontend: def456 (src/login.tsx)                       │
│     - docs: ghi789 (api/auth.md)                             │
│                                                               │
│  5. Artifacts are recorded:                                  │
│     - task_artifact_ref: [abc123, def456, ghi789]           │
│                                                               │
│  6. Dependencies auto-detected:                              │
│     - Frontend imports backend types → requires dependency   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Database Schema (v0.18)

```sql
-- Project Repos: Repository bindings within a project
CREATE TABLE project_repos (
    repo_id TEXT PRIMARY KEY,              -- ULID
    project_id TEXT NOT NULL,              -- FK: projects(id)
    name TEXT NOT NULL,                    -- e.g., "backend", "frontend"
    remote_url TEXT,                       -- e.g., "git@github.com:org/backend"
    default_branch TEXT DEFAULT 'main',    -- e.g., "main", "develop"
    workspace_relpath TEXT NOT NULL,       -- e.g., ".", "./be", "../shared"
    role TEXT NOT NULL DEFAULT 'code',     -- code | docs | infra | mono-subdir
    is_writable INTEGER NOT NULL DEFAULT 1,-- 1=writable, 0=read-only
    auth_profile TEXT,                     -- e.g., "github-ssh", "gitlab-pat"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                         -- JSON: extended metadata

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, name),              -- No duplicate names per project
    UNIQUE(project_id, workspace_relpath), -- No path conflicts
    CHECK (role IN ('code', 'docs', 'infra', 'mono-subdir'))
);

-- Task Repo Scope: Per-task repository access control
CREATE TABLE task_repo_scope (
    scope_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,                 -- FK: tasks(task_id)
    repo_id TEXT NOT NULL,                 -- FK: project_repos(repo_id)
    scope TEXT NOT NULL DEFAULT 'full',    -- full | paths | read_only
    path_filters TEXT,                     -- JSON: ["src/**", "tests/**"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                         -- JSON: access stats, etc.

    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (repo_id) REFERENCES project_repos(repo_id) ON DELETE CASCADE,
    UNIQUE(task_id, repo_id),              -- One scope per task+repo
    CHECK (scope IN ('full', 'paths', 'read_only'))
);

-- Task Dependency: Cross-repo task dependencies
CREATE TABLE task_dependency (
    dependency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,                 -- FK: tasks(task_id)
    depends_on_task_id TEXT NOT NULL,      -- FK: tasks(task_id)
    dependency_type TEXT NOT NULL DEFAULT 'blocks', -- blocks | requires | suggests
    reason TEXT,                           -- Why this dependency exists
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,                       -- user | system | auto
    metadata TEXT,                         -- JSON: strength, detection rules

    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    UNIQUE(task_id, depends_on_task_id, dependency_type),
    CHECK (task_id != depends_on_task_id), -- No self-dependency
    CHECK (dependency_type IN ('blocks', 'requires', 'suggests'))
);

-- Task Artifact Ref: Cross-repo artifact references
CREATE TABLE task_artifact_ref (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,                 -- FK: tasks(task_id)
    repo_id TEXT NOT NULL,                 -- FK: project_repos(repo_id)
    ref_type TEXT NOT NULL,                -- commit | branch | pr | patch | file | tag
    ref_value TEXT NOT NULL,               -- SHA | branch name | PR# | path
    summary TEXT,                          -- Artifact description
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                         -- JSON: commit msg, stats, etc.

    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (repo_id) REFERENCES project_repos(repo_id) ON DELETE CASCADE,
    UNIQUE(task_id, repo_id, ref_type, ref_value),
    CHECK (ref_type IN ('commit', 'branch', 'pr', 'patch', 'file', 'tag'))
);
```

### Python Models

**RepoSpec** (`agentos/schemas/project.py`):

```python
from pydantic import BaseModel, Field
from enum import Enum

class RepoRole(str, Enum):
    CODE = "code"
    DOCS = "docs"
    INFRA = "infra"
    MONO_SUBDIR = "mono-subdir"

class RepoSpec(BaseModel):
    repo_id: str
    project_id: str
    name: str
    remote_url: Optional[str] = None
    default_branch: str = "main"
    workspace_relpath: str
    role: RepoRole = RepoRole.CODE
    is_writable: bool = True
    auth_profile: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**Project** (`agentos/schemas/project.py`):

```python
class Project(BaseModel):
    id: str
    name: str
    path: Optional[str] = None  # Legacy field
    repos: List[RepoSpec] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_multi_repo(self) -> bool:
        """Check if this is a multi-repository project"""
        return len(self.repos) > 1

    def get_repo_by_name(self, name: str) -> Optional[RepoSpec]:
        """Get repository by name"""
        for repo in self.repos:
            if repo.name == name:
                return repo
        return None
```

### Indexing Strategy

**Performance-Critical Indexes**:

```sql
-- Project-repo lookup (most common query)
CREATE INDEX idx_project_repos_project
ON project_repos(project_id, created_at DESC);

-- Task-repo scope lookup
CREATE INDEX idx_task_repo_scope_task_repo
ON task_repo_scope(task_id, repo_id);

-- Dependency traversal (forward + reverse)
CREATE INDEX idx_task_dependency_task
ON task_dependency(task_id);
CREATE INDEX idx_task_dependency_reverse
ON task_dependency(depends_on_task_id, task_id);

-- Artifact reverse lookup (which tasks modified commit X?)
CREATE INDEX idx_task_artifact_ref_type_value
ON task_artifact_ref(ref_type, ref_value);
```

---

## Security and Permissions

### Authentication Profiles

Repositories can use **auth profiles** for Git operations:

```bash
# Create SSH key auth profile
agentos auth add --name github-ssh --type ssh_key --key-path ~/.ssh/id_rsa

# Create GitHub PAT auth profile
agentos auth add --name github-pat --type pat --token ghp_abc123...

# Use in project config
repos:
  - name: backend
    url: git@github.com:org/backend
    auth_profile: github-ssh
```

**Supported Auth Types**:
- `ssh_key`: SSH private key authentication
- `pat`: Personal Access Token (GitHub, GitLab)
- `oauth`: OAuth token flow (future)

### Path Filters (Security Boundary)

Path filters enforce **least-privilege access** for tasks:

```yaml
repos:
  - name: backend
    path: ./be
    role: code
    writable: true
    path_filters:
      - "src/**"           # Allow src/
      - "tests/**"         # Allow tests/
      - "!src/secrets.py"  # Deny secrets.py
```

**Validation Rules**:
1. Changes outside `path_filters` → **REJECTED**
2. Changes to forbidden files (`.env`, `.git/`) → **REJECTED**
3. Read-only repos with write attempts → **REJECTED**

### Read-Only Enforcement

Repositories can be marked as **read-only** to prevent accidental modifications:

```yaml
repos:
  - name: docs
    writable: false  # Read-only enforcement
```

**Enforcement Points**:
- CLI: Warns before write operations
- Runner: Blocks write operations at runtime
- Git: Uses read-only auth profiles

### Security Best Practices

1. **Least Privilege**: Mark repos as read-only unless write is required
2. **Path Filters**: Restrict task access to specific paths
3. **Auth Profiles**: Use separate profiles for read vs write access
4. **Audit Trail**: Review cross-repo changes regularly
5. **Dry-Run**: Use `--dry-run` to preview operations before execution

---

## Performance Considerations

### Database Performance

**Query Patterns**:
- **Hot path**: Task → Repos (indexed on `task_repo_scope.task_id`)
- **Reverse lookup**: Repo → Tasks (indexed on `task_repo_scope.repo_id`)
- **Dependency graph**: Task → Dependencies (indexed on both directions)

**Optimization Tips**:
1. Use `EXPLAIN QUERY PLAN` to verify index usage
2. Batch queries for multiple tasks/repos
3. Cache frequently accessed projects in memory
4. Use SQLite `PRAGMA` tuning for large datasets

### Git Operations

**Clone/Pull Performance**:
- **Parallel cloning**: Clone repos in parallel (use `ThreadPoolExecutor`)
- **Shallow clones**: Use `--depth 1` for large repos
- **Incremental pulls**: Only pull changed repos

**Example: Parallel Clone**

```python
from concurrent.futures import ThreadPoolExecutor

def clone_repos(project: Project):
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(git_client.clone, repo.remote_url, repo.workspace_relpath)
            for repo in project.repos
        ]
        for future in futures:
            future.result()  # Wait for all clones
```

### Workspace Caching

**Layout Caching**:
- Cache workspace paths (avoid repeated `Path.resolve()`)
- Cache repo existence checks (avoid repeated `Path.exists()`)
- Invalidate cache on repo add/remove

### Audit Trail Pagination

For projects with **many tasks**, paginate audit queries:

```sql
-- Paginated audit query (50 records per page)
SELECT * FROM task_artifact_ref
WHERE repo_id = ?
ORDER BY created_at DESC
LIMIT 50 OFFSET ?;
```

---

## Limitations and Constraints

### Design Constraints

1. **No Nested Repositories**
   - Repo A cannot be inside Repo B's workspace path
   - Example: `backend/frontend/` is NOT allowed if `backend/` and `frontend/` are separate repos
   - Workaround: Use sibling paths (`./be`, `./fe`)

2. **Unique Workspace Paths**
   - Each repo must have a unique `workspace_relpath` within a project
   - Example: Two repos cannot both use `./services/api`
   - Workaround: Use suffixes (`./services/api-v1`, `./services/api-v2`)

3. **No Circular Dependencies**
   - Task dependency graph must be a DAG (Directed Acyclic Graph)
   - Example: Task A → Task B → Task A is **rejected**
   - Detection: Import validation checks for cycles

4. **Git Repository Requirement**
   - All repos must be valid Git repositories
   - Non-Git directories are not supported
   - Workaround: Initialize with `git init` if needed

### Performance Limits

| Limit | Recommended | Maximum |
|-------|-------------|---------|
| Repos per project | 3-5 | 20 |
| Tasks per repo | 100 | 1000 |
| Path filters per repo | 5 | 50 |
| Dependency depth | 3 levels | 10 levels |

**Why These Limits?**:
- **20 repos**: Database query performance degrades with too many joins
- **1000 tasks**: UI pagination and filtering become necessary
- **50 path filters**: Regex compilation overhead
- **10 dependency levels**: Graph traversal complexity

### Known Issues

1. **Submodule Conflicts**
   - Git submodules inside a multi-repo project may cause path conflicts
   - Status: Known limitation, no immediate fix
   - Workaround: Use multi-repo binding instead of submodules

2. **Symlink Support**
   - Symlinks in `workspace_relpath` may cause issues
   - Status: Limited testing, use with caution
   - Workaround: Use absolute paths or avoid symlinks

3. **Large Monorepos**
   - Monorepos with >10,000 files may have slow git operations
   - Status: Performance optimization ongoing
   - Workaround: Use path filters to limit scope

---

## Quick Start

### 3-Step Import

```bash
# 1. Configure authentication
agentos auth add --name github-ssh --type ssh_key --key-path ~/.ssh/id_rsa

# 2. Create project config
cat > my-app.yaml <<EOF
name: my-app
repos:
  - name: backend
    url: git@github.com:org/backend
    path: ./be
    role: code
    auth_profile: github-ssh
  - name: frontend
    url: git@github.com:org/frontend
    path: ./fe
    role: code
    auth_profile: github-ssh
EOF

# 3. Import project
agentos project import --from my-app.yaml
```

### Next Steps

- **CLI Usage**: See [CLI Usage Guide](../cli/PROJECT_IMPORT.md)
- **Examples**: See [Multi-Repo Examples](../../examples/multi-repo/)
- **Migration**: See [Migration Guide](../migration/SINGLE_TO_MULTI_REPO.md)
- **Troubleshooting**: See [Troubleshooting Guide](../troubleshooting/MULTI_REPO.md)

---

## References

- [Schema Migration v0.18](../../agentos/store/migrations/v18_multi_repo_projects.sql)
- [RepoSpec Schema](../../agentos/schemas/project.py)
- [ProjectRepository CRUD](../../agentos/core/project/repository.py)
- [CLI Import Command](../../agentos/cli/project.py)

---

**Questions or Feedback?**

- 🐛 [Report Issues](https://github.com/your-org/AgentOS/issues)
- 💡 [Feature Requests](https://github.com/your-org/AgentOS/discussions)
- 📖 [Documentation](https://github.com/your-org/AgentOS/wiki)
