# Multi-Repository Project API Guide

快速参考指南，介绍如何使用多仓库项目管理 API。

---

## 🚀 快速开始

### 1. 导入模块

```python
from pathlib import Path
from agentos.core.project.repository import (
    ProjectRepository,
    RepoContext,
    RepoRegistry,
)
from agentos.schemas.project import Project, RepoRole, RepoSpec
from agentos.core.task.models import (
    TaskRepoScope,
    TaskDependency,
    TaskArtifactRef,
    RepoScopeType,
    DependencyType,
    ArtifactRefType,
)
```

---

## 📦 核心模型

### RepoSpec - 仓库规格

表示一个绑定到项目的仓库。

```python
backend_repo = RepoSpec(
    repo_id="repo-backend",           # 唯一仓库 ID（ULID 或 UUID）
    project_id="proj-001",            # 关联的项目 ID
    name="backend",                   # 用户友好的名称
    remote_url="https://github.com/myorg/backend.git",  # 远程仓库 URL（可选）
    default_branch="main",            # 默认分支
    workspace_relpath="services/backend",  # 相对于项目工作区的路径
    role=RepoRole.CODE,               # 仓库角色（code/docs/infra/mono-subdir）
    is_writable=True,                 # 是否可写
    auth_profile="github-pat",        # 认证配置名称（可选）
    metadata={"language": "python"},  # 扩展元数据（JSON）
)
```

**仓库角色 (RepoRole)**:
- `CODE`: 代码仓库（默认）
- `DOCS`: 文档仓库
- `INFRA`: 基础设施仓库（Terraform, K8s 等）
- `MONO_SUBDIR`: Monorepo 子目录

---

### Project - 项目模型

表示一个包含多个仓库的项目。

```python
project = Project(
    id="proj-001",
    name="My Awesome Project",
    repos=[backend_repo, frontend_repo, docs_repo],
    metadata={"version": "1.0.0"},
)

# 检查项目类型
project.is_multi_repo()    # True if len(repos) > 1
project.is_single_repo()   # True if len(repos) == 1
project.has_repos()        # True if len(repos) > 0

# 获取默认仓库（name="default" 或第一个仓库）
default = project.get_default_repo()

# 按名称查询仓库
backend = project.get_repo_by_name("backend")

# 按 ID 查询仓库
repo = project.get_repo_by_id("repo-backend")
```

---

### RepoContext - 运行时上下文

表示仓库的运行时状态（不持久化到数据库）。

```python
workspace_root = Path("/workspace/my-project")
context = RepoContext.from_repo_spec(backend_repo, workspace_root)

print(context.path)         # 绝对路径: /workspace/my-project/services/backend
print(context.remote_url)   # https://github.com/myorg/backend.git
print(context.branch)       # main
print(context.writable)     # True
print(context.role)         # RepoRole.CODE
```

---

## 🔧 CRUD 操作

### ProjectRepository - 仓库绑定管理

```python
db_path = Path("store/registry.sqlite")
repo_crud = ProjectRepository(db_path)

# 添加仓库
repo_id = repo_crud.add_repo(backend_repo)

# 列出所有仓库（按 created_at DESC）
repos = repo_crud.list_repos("proj-001")

# 获取指定仓库
repo = repo_crud.get_repo("proj-001", "repo-backend")

# 按名称查询
repo = repo_crud.get_repo_by_name("proj-001", "backend")

# 更新仓库
backend_repo.default_branch = "develop"
repo_crud.update_repo(backend_repo)

# 删除仓库（级联删除相关的 task_repo_scope 和 task_artifact_ref）
repo_crud.remove_repo("proj-001", "repo-backend")

# 过滤操作
writable_repos = repo_crud.get_writable_repos("proj-001")
code_repos = repo_crud.get_repos_by_role("proj-001", RepoRole.CODE)
```

---

### RepoRegistry - 统一入口

结合 CRUD 和运行时上下文解析。

```python
workspace_root = Path("/workspace/my-project")
registry = RepoRegistry(db_path, workspace_root)

# 添加仓库（委托给 ProjectRepository）
registry.add_repo(backend_repo)

# 获取运行时上下文
context = registry.get_context("proj-001", "repo-backend")
print(context.path)  # 绝对路径

# 获取默认仓库的上下文
default_context = registry.get_default_context("proj-001")

# 获取所有仓库的上下文
all_contexts = registry.get_all_contexts("proj-001")
for ctx in all_contexts:
    print(f"{ctx.name}: {ctx.path}")
```

---

## 🔗 任务关联模型

### TaskRepoScope - 任务仓库作用域

定义任务可以访问的仓库和路径范围。

```python
scope = TaskRepoScope(
    task_id="task-001",
    repo_id="repo-backend",
    scope=RepoScopeType.PATHS,          # full | paths | read_only
    path_filters=["src/**", "tests/**"],  # 路径过滤器（glob 模式）
    metadata={"reason": "Only modify Python files"},
)

# 转换为数据库字典
db_dict = scope.to_dict()

# 从数据库行创建
loaded_scope = TaskRepoScope.from_db_row(db_row)
```

**作用域类型 (RepoScopeType)**:
- `FULL`: 完整仓库访问权限
- `PATHS`: 限定路径访问（通过 path_filters 指定）
- `READ_ONLY`: 只读访问

---

### TaskDependency - 任务依赖关系

定义任务之间的依赖关系（包括跨仓库依赖）。

```python
dep = TaskDependency(
    task_id="task-frontend",
    depends_on_task_id="task-backend",
    dependency_type=DependencyType.BLOCKS,  # blocks | requires | suggests
    reason="Frontend needs backend API to be deployed first",
    created_by="system",
    metadata={"auto_detected": False},
)
```

**依赖类型 (DependencyType)**:
- `BLOCKS`: 阻塞依赖（必须等待依赖任务完成才能开始）
- `REQUIRES`: 需要依赖（可以并行，但需要依赖任务的产物）
- `SUGGESTS`: 建议依赖（弱依赖，不影响执行）

---

### TaskArtifactRef - 跨仓库产物引用

记录任务产生的跨仓库产物（提交、分支、PR、补丁等）。

```python
artifact = TaskArtifactRef(
    task_id="task-001",
    repo_id="repo-backend",
    ref_type=ArtifactRefType.COMMIT,      # commit | branch | pr | patch | file | tag
    ref_value="abc123def456789",          # Git commit SHA
    summary="Fixed authentication bug in login endpoint",
    metadata={"lines_changed": 42, "files_modified": 3},
)
```

**引用类型 (ArtifactRefType)**:
- `COMMIT`: Git commit SHA（最常用，不可变引用）
- `BRANCH`: Git 分支名（可变引用）
- `PR`: Pull Request 号（用于代码审查）
- `PATCH`: 补丁文件路径或内容（用于跨仓库应用变更）
- `FILE`: 文件路径（用于引用特定文件）
- `TAG`: Git tag（语义化版本引用）

---

## 🔄 数据库映射

所有模型提供双向映射方法：

### 写入数据库

```python
# Pydantic 模型 -> 数据库字典
db_dict = repo_spec.to_db_dict()

cursor.execute(
    """
    INSERT INTO project_repos (
        repo_id, project_id, name, remote_url, default_branch,
        workspace_relpath, role, is_writable, auth_profile,
        created_at, updated_at, metadata
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        db_dict["repo_id"],
        db_dict["project_id"],
        db_dict["name"],
        db_dict["remote_url"],
        db_dict["default_branch"],
        db_dict["workspace_relpath"],
        db_dict["role"],
        db_dict["is_writable"],
        db_dict["auth_profile"],
        db_dict["created_at"],
        db_dict["updated_at"],
        db_dict["metadata"],
    ),
)
```

### 读取数据库

```python
# 数据库行 -> Pydantic 模型
cursor.execute("SELECT * FROM project_repos WHERE repo_id = ?", (repo_id,))
row = cursor.fetchone()

repo_spec = RepoSpec.from_db_row(dict(row))
```

---

## 💡 最佳实践

### 1. 向后兼容单仓项目

对于现有的单仓项目，使用 `get_default_repo()` 透明适配：

```python
# 单仓项目（v17 迁移后自动生成 name="default" 的仓库）
project = load_project("proj-001")
default_repo = project.get_default_repo()

# 无需判断是否为多仓，总能获取到默认仓库
if default_repo:
    context = RepoContext.from_repo_spec(default_repo, workspace_root)
    run_task_in_repo(context)
```

### 2. 多仓项目明确指定仓库

对于多仓项目，明确指定要操作的仓库：

```python
# 列出所有仓库供用户选择
repos = repo_crud.list_repos("proj-001")
for repo in repos:
    print(f"- {repo.name}: {repo.workspace_relpath}")

# 用户选择后获取上下文
selected_repo = project.get_repo_by_name(user_selection)
context = RepoContext.from_repo_spec(selected_repo, workspace_root)
```

### 3. 使用 RepoRegistry 简化操作

```python
# 推荐：使用 RepoRegistry 一站式操作
registry = RepoRegistry(db_path, workspace_root)

# 自动解析默认仓库
context = registry.get_default_context("proj-001")

# 自动解析绝对路径
context = registry.get_context("proj-001", "repo-backend")
print(context.path)  # 已解析为绝对路径
```

### 4. 路径过滤器语法

使用 glob 模式指定路径过滤器：

```python
path_filters = [
    "src/**/*.py",           # 所有 Python 文件在 src 目录下
    "tests/**/*.py",         # 所有测试文件
    "!**/__pycache__/**",    # 排除 __pycache__
    "docs/**/*.md",          # 所有 Markdown 文档
]

scope = TaskRepoScope(
    task_id="task-001",
    repo_id="repo-backend",
    scope=RepoScopeType.PATHS,
    path_filters=path_filters,
)
```

---

## 🧪 测试

完整的单元测试套件位于：`tests/unit/project/test_repository.py`

运行测试：

```bash
.venv/bin/python -m pytest tests/unit/project/test_repository.py -v
```

预期输出：
```
============================== 22 passed in 0.17s ==============================
```

---

## 📚 更多资源

- **完整示例**: `examples/multi_repo_usage.py`
- **Schema 定义**: `agentos/store/migrations/v18_multi_repo_projects.sql`
- **完成报告**: `docs/multi_repo/PHASE_1_2_COMPLETION.md`

---

## ⚠️ 注意事项

1. **唯一性约束**: 同一 project 内，repo `name` 和 `workspace_relpath` 必须唯一
2. **级联删除**: 删除仓库会自动删除相关的 task_repo_scope 和 task_artifact_ref
3. **路径解析**: `workspace_relpath` 支持相对路径（如 ".", "../shared", "services/api"）
4. **时间戳**: 自动使用 UTC 时间戳，无需手动设置

---

## 🎯 下一步

- **Phase 1.3**: 实现兼容层，确保现有单仓项目无缝迁移
- **Phase 2.1**: 实现多仓库导入 CLI 命令（`agentos project add-repo`）
- **Phase 5.1**: Runner 支持跨仓库工作区选择
