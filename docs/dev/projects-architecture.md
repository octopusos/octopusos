# Projects 架构设计文档

本文档面向 AgentOS 开发者,详细说明 Projects 功能的架构设计、数据模型、扩展点和性能优化策略。

## 目录

- [概述](#概述)
- [数据模型](#数据模型)
- [关联关系](#关联关系)
- [配置继承流程](#配置继承流程)
- [扩展点](#扩展点)
- [性能考虑](#性能考虑)
- [安全考虑](#安全考虑)
- [已知限制](#已知限制)
- [未来改进](#未来改进)

---

## 概述

### 设计目标

Projects 功能旨在解决以下问题:

1. **任务组织**: 将任务按项目分组,而不是孤立管理
2. **配置复用**: 项目级配置自动继承到任务,减少重复配置
3. **多仓库支持**: 支持微服务、Monorepo 等多仓库架构
4. **审计追踪**: 所有操作都有明确的项目归属

### 核心原则

- **向后兼容**: 保留 `projects.path` 字段,兼容旧版本
- **渐进式迁移**: 支持单仓库和多仓库两种模式
- **配置继承**: Task > Project > Global 三级配置优先级
- **安全第一**: 环境变量白名单、路径白名单、权限控制

### 架构分层

```
┌─────────────────────────────────────────┐
│         WebUI / REST API                │  用户界面层
├─────────────────────────────────────────┤
│     ProjectRepository (CRUD)            │  业务逻辑层
│     RepoRegistry (Multi-Repo)           │
│     TaskRepoService (Task-Repo Link)    │
├─────────────────────────────────────────┤
│     Project, RepoSpec (Pydantic)        │  数据模型层
│     ProjectSettings, RiskProfile        │
├─────────────────────────────────────────┤
│     projects, project_repos (Tables)    │  数据存储层
│     task_repo_scope, tasks.project_id   │
└─────────────────────────────────────────┘
```

---

## 数据模型

### ER 图

```
projects (1) ----< (N) project_repos
    |                       |
    | 1                     | N
    |                       |
   (N)                     (N)
  tasks <------- task_repo_scope
```

**关系说明**:
- **projects → project_repos**: 一对多 (一个项目有多个仓库)
- **projects → tasks**: 一对多 (一个项目有多个任务,通过 `tasks.project_id`)
- **project_repos → task_repo_scope**: 一对多 (一个仓库被多个任务使用)
- **tasks → task_repo_scope**: 一对多 (一个任务涉及多个仓库)

### 表结构

#### projects 表 (v25)

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,                       -- 项目 ID (ULID)
    name TEXT NOT NULL,                        -- 项目名称
    description TEXT,                          -- 项目描述
    status TEXT DEFAULT 'active',              -- 状态: active/archived/deleted
    tags TEXT,                                 -- 标签 (JSON 数组)
    default_repo_id TEXT,                      -- 默认仓库 ID
    default_workdir TEXT,                      -- 默认工作目录
    settings TEXT,                             -- 配置 (JSON 对象)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,                           -- 创建者
    path TEXT,                                 -- 遗留字段 (向后兼容)
    metadata TEXT,                             -- 遗留字段 (JSON 对象)
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 遗留字段
);
```

**索引**:
```sql
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_name ON projects(name);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);
```

**字段说明**:
- `status`: 控制项目生命周期,支持软删除
- `tags`: JSON 数组,用于分类和搜索
- `settings`: JSON 对象,包含 ProjectSettings 的序列化数据
- `path`, `metadata`, `added_at`: 向后兼容字段,新代码应使用 v25 字段

#### project_repos 表 (v18)

```sql
CREATE TABLE project_repos (
    repo_id TEXT PRIMARY KEY,                  -- 仓库 ID (ULID)
    project_id TEXT NOT NULL,                  -- 关联项目 ID
    name TEXT NOT NULL,                        -- 仓库名称 (项目内唯一)
    remote_url TEXT,                           -- Git 远程 URL
    default_branch TEXT DEFAULT 'main',        -- 默认分支
    workspace_relpath TEXT NOT NULL,           -- 相对路径 (项目内唯一)
    role TEXT NOT NULL DEFAULT 'code',         -- 仓库角色
    is_writable INTEGER NOT NULL DEFAULT 1,    -- 是否可写 (1=是, 0=否)
    auth_profile TEXT,                         -- 认证配置名称
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                             -- 扩展元数据 (JSON)

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, name),                  -- 名称唯一
    UNIQUE(project_id, workspace_relpath),     -- 路径唯一
    CHECK (role IN ('code', 'docs', 'infra', 'mono-subdir'))
);
```

**索引**:
```sql
CREATE INDEX idx_project_repos_project
ON project_repos(project_id, created_at DESC);

CREATE INDEX idx_project_repos_role
ON project_repos(role);

CREATE INDEX idx_project_repos_writable
ON project_repos(is_writable) WHERE is_writable = 1;

CREATE INDEX idx_project_repos_name
ON project_repos(project_id, name);
```

**约束说明**:
- `UNIQUE(project_id, name)`: 同一项目内仓库名称唯一
- `UNIQUE(project_id, workspace_relpath)`: 同一项目内路径唯一,防止路径冲突
- `CHECK (role IN ...)`: 限制仓库角色枚举值

#### task_repo_scope 表 (v18)

```sql
CREATE TABLE task_repo_scope (
    scope_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,                     -- 关联任务 ID
    repo_id TEXT NOT NULL,                     -- 涉及的仓库 ID
    scope TEXT NOT NULL DEFAULT 'full',        -- 作用域: full/paths/read_only
    path_filters TEXT,                         -- 路径过滤器 (JSON 数组)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                             -- 扩展元数据 (JSON)

    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (repo_id) REFERENCES project_repos(repo_id) ON DELETE CASCADE,
    UNIQUE(task_id, repo_id),                  -- 任务+仓库唯一
    CHECK (scope IN ('full', 'paths', 'read_only'))
);
```

**索引**:
```sql
CREATE INDEX idx_task_repo_scope_task
ON task_repo_scope(task_id);

CREATE INDEX idx_task_repo_scope_repo
ON task_repo_scope(repo_id, created_at DESC);

CREATE INDEX idx_task_repo_scope_task_repo
ON task_repo_scope(task_id, repo_id);
```

**作用域说明**:
- `full`: 完整访问 (根据 `repo.is_writable` 决定是否可写)
- `paths`: 限制在特定路径 (由 `path_filters` 定义)
- `read_only`: 只读访问

#### tasks.project_id 字段 (v26)

```sql
-- 添加 project_id 字段到 tasks 表
ALTER TABLE tasks ADD COLUMN project_id TEXT;

-- 创建索引
CREATE INDEX idx_tasks_project_id
ON tasks(project_id);

CREATE INDEX idx_tasks_project_status
ON tasks(project_id, status, created_at DESC);

CREATE INDEX idx_tasks_project_created
ON tasks(project_id, created_at DESC);
```

**外键验证触发器** (SQLite 不支持 ALTER TABLE 添加外键,使用触发器):

```sql
-- 插入时验证 project_id 存在
CREATE TRIGGER check_tasks_project_id_insert
BEFORE INSERT ON tasks
FOR EACH ROW
WHEN NEW.project_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: project_id does not exist')
    WHERE NOT EXISTS (SELECT 1 FROM projects WHERE id = NEW.project_id);
END;

-- 更新时验证 project_id 存在
CREATE TRIGGER check_tasks_project_id_update
BEFORE UPDATE ON tasks
FOR EACH ROW
WHEN NEW.project_id IS NOT NULL AND NEW.project_id != OLD.project_id
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: project_id does not exist')
    WHERE NOT EXISTS (SELECT 1 FROM projects WHERE id = NEW.project_id);
END;

-- 删除项目时检查是否有关联任务
CREATE TRIGGER check_projects_delete
BEFORE DELETE ON projects
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete project with existing tasks')
    WHERE EXISTS (SELECT 1 FROM tasks WHERE project_id = OLD.id);
END;
```

### Python 数据模型

#### Project (agentos/schemas/project.py)

```python
class Project(BaseModel):
    # 核心字段
    id: str                                    # 项目 ID (ULID)
    name: str                                  # 项目名称

    # 元数据字段 (v25)
    description: Optional[str] = None
    status: Literal["active", "archived", "deleted"] = "active"
    tags: List[str] = Field(default_factory=list)

    # 仓库配置 (v25)
    default_repo_id: Optional[str] = None
    default_workdir: Optional[str] = None

    # 项目设置 (v25)
    settings: Optional[ProjectSettings] = None

    # 时间戳 (v25)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

    # 向后兼容字段
    path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 多仓库支持
    repos: List[RepoSpec] = Field(default_factory=list)
```

**关键方法**:
- `get_default_repo()`: 获取默认仓库 (优先 name="default",否则第一个)
- `get_repo_by_name(name)`: 按名称查找仓库
- `get_repo_by_id(repo_id)`: 按 ID 查找仓库
- `is_multi_repo()`: 判断是否多仓库项目
- `to_db_dict()`: 转换为数据库兼容格式 (JSON 序列化)
- `from_db_row(row, repos)`: 从数据库行创建对象

#### ProjectSettings (agentos/schemas/project.py)

```python
class ProjectSettings(BaseModel):
    default_runner: Optional[str] = None       # 默认 Runner
    provider_policy: Optional[str] = None      # Provider 策略
    env_overrides: Dict[str, str] = Field(default_factory=dict)
    risk_profile: Optional[RiskProfile] = None
```

**配置字段**:
- `default_runner`: 如 "llama.cpp", "openai"
- `provider_policy`: 如 "prefer-local", "cloud-only", "balanced"
- `env_overrides`: 环境变量覆盖 (白名单机制)
- `risk_profile`: 安全风险配置

#### RiskProfile (agentos/schemas/project.py)

```python
class RiskProfile(BaseModel):
    allow_shell_write: bool = False            # 允许 shell 写操作
    require_admin_token: bool = False          # 需要 admin token
    writable_paths: List[str] = Field(default_factory=list)  # 路径白名单
```

**安全设计**:
- `allow_shell_write`: 默认 `False`,开发环境可设为 `True`
- `require_admin_token`: 生产环境建议 `True`
- `writable_paths`: 空列表表示无限制 (不推荐)

#### RepoSpec (agentos/schemas/project.py)

```python
class RepoSpec(BaseModel):
    repo_id: str                               # 仓库 ID (ULID)
    project_id: str                            # 关联项目 ID
    name: str                                  # 仓库名称
    remote_url: Optional[str] = None           # Git 远程 URL
    default_branch: str = "main"               # 默认分支
    workspace_relpath: str                     # 相对路径
    role: RepoRole = RepoRole.CODE             # 仓库角色
    is_writable: bool = True                   # 是否可写
    auth_profile: Optional[str] = None         # 认证配置
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**RepoRole 枚举**:
```python
class RepoRole(str, Enum):
    CODE = "code"              # 代码仓库
    DOCS = "docs"              # 文档仓库
    INFRA = "infra"            # 基础设施仓库
    MONO_SUBDIR = "mono-subdir"  # Monorepo 子目录
```

---

## 关联关系

### Task → Project 直接关联 (v26)

```sql
-- tasks 表添加 project_id 字段
ALTER TABLE tasks ADD COLUMN project_id TEXT;

-- 创建索引
CREATE INDEX idx_tasks_project_id ON tasks(project_id);

-- 创建外键触发器
CREATE TRIGGER check_tasks_project_id_insert ...
```

**优点**:
- 直接查询任务的项目: `SELECT * FROM tasks WHERE project_id = ?`
- 避免通过 `task_repo_scope` 间接查询
- 提升性能 (单表查询 vs 多表 JOIN)

**查询示例**:
```sql
-- 获取项目的所有任务 (高效)
SELECT * FROM tasks
WHERE project_id = 'proj-123'
ORDER BY created_at DESC;

-- 统计项目任务数 (高效)
SELECT COUNT(*) FROM tasks
WHERE project_id = 'proj-123';
```

### Task → Repos 间接关联 (v18)

```sql
-- task_repo_scope 表
CREATE TABLE task_repo_scope (
    task_id TEXT NOT NULL,
    repo_id TEXT NOT NULL,
    scope TEXT DEFAULT 'full',
    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (repo_id) REFERENCES project_repos(repo_id)
);
```

**用途**:
- 记录任务涉及的仓库 (多仓库任务)
- 控制每个仓库的访问范围 (full/paths/read_only)
- 支持路径过滤 (如只修改 `src/**`)

**查询示例**:
```sql
-- 获取任务涉及的所有仓库
SELECT pr.*
FROM task_repo_scope trs
JOIN project_repos pr ON trs.repo_id = pr.repo_id
WHERE trs.task_id = 'task-456';

-- 获取仓库被哪些任务使用
SELECT t.*
FROM task_repo_scope trs
JOIN tasks t ON trs.task_id = t.task_id
WHERE trs.repo_id = 'repo-789';
```

---

## 配置继承流程

### 优先级规则

```
Task Settings > Project Settings > Global Settings
```

### 继承逻辑

```python
def resolve_task_settings(task_id: str) -> Dict[str, Any]:
    """解析任务的最终配置 (三级继承)"""

    # 1. 加载全局配置
    global_settings = load_global_config()

    # 2. 加载项目配置
    task = get_task(task_id)
    if task.project_id:
        project = get_project(task.project_id)
        project_settings = project.settings or {}
    else:
        project_settings = {}

    # 3. 加载任务配置
    task_settings = task.settings or {}

    # 4. 合并配置 (Task > Project > Global)
    final_settings = {
        **global_settings,
        **project_settings,
        **task_settings,
    }

    # 5. 特殊处理: env_overrides 合并 (不覆盖)
    final_env = {}
    final_env.update(global_settings.get("env_overrides", {}))
    final_env.update(project_settings.get("env_overrides", {}))
    final_env.update(task_settings.get("env_overrides", {}))
    final_settings["env_overrides"] = final_env

    return final_settings
```

### 创建任务时的配置应用

```python
def create_task(title: str, project_id: str, settings: Dict) -> Task:
    """创建任务,自动继承项目配置"""

    # 1. 加载项目配置
    project = get_project(project_id)
    project_settings = project.settings.model_dump() if project.settings else {}

    # 2. 合并任务配置
    final_settings = {**project_settings, **settings}

    # 3. 创建任务
    task = Task(
        title=title,
        project_id=project_id,
        settings=final_settings,
    )

    return task
```

**注意**: 配置在任务创建时应用,后续修改项目配置不影响已创建的任务。

---

## 扩展点

### 1. 添加新的 Settings 字段

假设需要添加 `max_execution_time` 配置:

**步骤**:

1. 更新 `ProjectSettings` Schema (`agentos/schemas/project.py`):

```python
class ProjectSettings(BaseModel):
    default_runner: Optional[str] = None
    provider_policy: Optional[str] = None
    env_overrides: Dict[str, str] = Field(default_factory=dict)
    risk_profile: Optional[RiskProfile] = None
    max_execution_time: Optional[int] = Field(None, description="Max execution time in seconds")  # 新增
```

2. 更新前端表单 (`agentos/webui/static/js/components/ProjectsView.js`):

```javascript
// 在 Settings 标签页添加输入框
<div class="form-group">
  <label>Max Execution Time (seconds)</label>
  <input type="number" id="maxExecutionTime" class="form-control" placeholder="3600">
</div>
```

3. 更新配置继承逻辑 (`agentos/core/project/settings_inheritance.py`):

```python
def apply_project_settings_to_task(task, project):
    if project.settings and project.settings.max_execution_time:
        task.max_execution_time = project.settings.max_execution_time
```

4. 添加测试 (`tests/unit/test_project_settings.py`):

```python
def test_max_execution_time_inheritance():
    project = Project(
        name="Test",
        settings=ProjectSettings(max_execution_time=7200)
    )
    task = create_task_with_project(project)
    assert task.max_execution_time == 7200
```

### 2. 添加新的 RepoRole

假设需要添加 `scripts` 角色:

**步骤**:

1. 更新 `RepoRole` 枚举 (`agentos/schemas/project.py`):

```python
class RepoRole(str, Enum):
    CODE = "code"
    DOCS = "docs"
    INFRA = "infra"
    MONO_SUBDIR = "mono-subdir"
    SCRIPTS = "scripts"  # 新增
```

2. 更新数据库 CHECK 约束 (`schema_vXX.sql`):

```sql
-- 创建新的触发器验证 role
CREATE TRIGGER check_project_repos_role_insert
BEFORE INSERT ON project_repos
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Invalid role')
    WHERE NEW.role NOT IN ('code', 'docs', 'infra', 'mono-subdir', 'scripts');
END;
```

3. 更新前端下拉框 (`ProjectsView.js`):

```javascript
const roleOptions = [
  { value: "code", label: "Code" },
  { value: "docs", label: "Documentation" },
  { value: "infra", label: "Infrastructure" },
  { value: "mono-subdir", label: "Monorepo Subdirectory" },
  { value: "scripts", label: "Scripts" }  // 新增
];
```

### 3. 添加新的 Scope 类型

假设需要添加 `write_only` 作用域:

**步骤**:

1. 更新 `task_repo_scope` 表 (`schema_vXX.sql`):

```sql
-- 更新 CHECK 约束
ALTER TABLE task_repo_scope DROP CONSTRAINT check_scope;
ALTER TABLE task_repo_scope ADD CONSTRAINT check_scope
    CHECK (scope IN ('full', 'paths', 'read_only', 'write_only'));
```

2. 更新业务逻辑 (`agentos/core/task/task_repo_service.py`):

```python
def validate_repo_access(task_id, repo_id, operation):
    scope = get_repo_scope(task_id, repo_id)
    if scope == "write_only" and operation == "read":
        raise PermissionError("Repo is write-only")
```

---

## 性能考虑

### 查询优化

#### 1. 按项目过滤任务

**低效查询** (通过 JOIN):
```sql
SELECT DISTINCT t.*
FROM tasks t
JOIN task_repo_scope trs ON t.task_id = trs.task_id
JOIN project_repos pr ON trs.repo_id = pr.repo_id
WHERE pr.project_id = 'proj-123';
```

**高效查询** (直接过滤):
```sql
SELECT * FROM tasks
WHERE project_id = 'proj-123';
```

**性能提升**: ~10x (避免多表 JOIN)

#### 2. 统计项目任务数

**使用索引**:
```sql
CREATE INDEX idx_tasks_project_id ON tasks(project_id);

SELECT COUNT(*) FROM tasks WHERE project_id = 'proj-123';
-- 使用索引: idx_tasks_project_id (覆盖索引)
```

#### 3. 获取项目最近任务

**使用复合索引**:
```sql
CREATE INDEX idx_tasks_project_created
ON tasks(project_id, created_at DESC);

SELECT * FROM tasks
WHERE project_id = 'proj-123'
ORDER BY created_at DESC
LIMIT 10;
-- 使用索引: idx_tasks_project_created (无需排序)
```

### 缓存策略

#### Project Settings 缓存

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_project_settings(project_id: str) -> ProjectSettings:
    """缓存项目配置 (最多 1000 个项目)"""
    project = get_project(project_id)
    return project.settings

# 缓存失效
def invalidate_project_cache(project_id: str):
    get_project_settings.cache_clear()
```

**优点**:
- 减少数据库查询
- 配置继承时复用缓存

**注意**:
- 项目更新时需清除缓存
- 多进程场景需考虑分布式缓存 (如 Redis)

### N+1 查询优化

**问题**: 列出项目时,逐个查询仓库数量

```python
# BAD: N+1 查询
projects = get_all_projects()
for project in projects:
    repo_count = count_repos(project.id)  # 每次查询一次
```

**优化**: 使用 JOIN 或批量查询

```python
# GOOD: 单次查询
projects = get_all_projects_with_repo_count()
# SELECT p.*, COUNT(pr.repo_id) as repo_count
# FROM projects p
# LEFT JOIN project_repos pr ON p.id = pr.project_id
# GROUP BY p.id;
```

---

## 安全考虑

### 环境变量白名单

只允许以下环境变量:

```python
ALLOWED_ENV_VARS = [
    'PYTHONPATH', 'DEBUG', 'LOG_LEVEL', 'TZ',
    'LANG', 'LC_ALL', 'PATH', 'HOME', 'USER',
    'TMPDIR', 'NODE_ENV', 'EDITOR', 'PAGER',
    'TERM', 'SHELL'
]

def validate_env_overrides(env_overrides: Dict[str, str]):
    """验证环境变量白名单"""
    for key in env_overrides.keys():
        if key not in ALLOWED_ENV_VARS:
            raise ValueError(f"Environment variable '{key}' is not allowed")
```

**风险**: 危险的环境变量可能导致安全问题,如:
- `LD_PRELOAD`: 注入恶意库
- `AWS_ACCESS_KEY_ID`: 泄露凭证
- `DATABASE_PASSWORD`: 泄露密码

### 路径白名单

Shell 写操作必须在白名单路径中:

```python
def is_path_allowed(target_path: str, writable_paths: List[str]) -> bool:
    """检查路径是否在白名单中"""
    target = Path(target_path).resolve()
    for allowed in writable_paths:
        allowed_path = Path(allowed).resolve()
        if target.is_relative_to(allowed_path):
            return True
    return False

# 使用示例
if not is_path_allowed("/etc/passwd", ["/tmp", "./output"]):
    raise PermissionError("Path not in writable whitelist")
```

**防护**: 防止任务修改敏感文件,如:
- `/etc/passwd`: 系统用户配置
- `~/.ssh/id_rsa`: SSH 私钥
- `/var/log/system.log`: 系统日志

### SQL 注入防护

使用参数化查询,避免 SQL 注入:

```python
# BAD: SQL 注入风险
def get_project_by_name(name: str):
    query = f"SELECT * FROM projects WHERE name = '{name}'"
    cursor.execute(query)  # 如果 name = "'; DROP TABLE projects; --" 会导致删表

# GOOD: 参数化查询
def get_project_by_name(name: str):
    query = "SELECT * FROM projects WHERE name = ?"
    cursor.execute(query, (name,))  # 安全
```

---

## 已知限制

### 1. SQLite 外键限制

**问题**: SQLite 的 `ALTER TABLE` 不支持添加外键约束

**解决方案**: 使用触发器实现外键验证

```sql
-- 无法直接添加外键
-- ALTER TABLE tasks ADD FOREIGN KEY (project_id) REFERENCES projects(id);  -- 不支持

-- 使用触发器
CREATE TRIGGER check_tasks_project_id_insert
BEFORE INSERT ON tasks
FOR EACH ROW
WHEN NEW.project_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: project_id does not exist')
    WHERE NOT EXISTS (SELECT 1 FROM projects WHERE id = NEW.project_id);
END;
```

**影响**: 需要手动维护触发器,代码复杂度增加

### 2. 环境变量白名单

**限制**: 白名单硬编码在代码中,不支持动态配置

**原因**: 安全考虑,避免用户设置危险变量

**改进方向**:
- 支持管理员配置白名单 (需要权限控制)
- 提供预设白名单模板 (如 Python、Node.js、Go)

### 3. Settings 缓存无分布式支持

**问题**: `@lru_cache` 是进程内缓存,多实例场景缓存不一致

**场景**:
```
实例 A 修改项目配置 → A 的缓存失效
实例 B 仍使用旧缓存 → 配置不一致
```

**解决方案** (未来):
- 使用 Redis 作为分布式缓存
- 使用消息队列广播缓存失效事件

---

## 未来改进

### v27: tasks.project_id NOT NULL

**目标**: 强制所有任务关联项目

**步骤**:
1. 为现有未关联任务创建 "Default Project"
2. 迁移所有任务到项目
3. 修改表结构: `ALTER TABLE tasks MODIFY COLUMN project_id TEXT NOT NULL`

**优点**: 简化代码逻辑,所有任务都有项目归属

### v28: 项目级权限控制 (RBAC)

**目标**: 支持多用户协作,控制项目访问权限

**功能**:
- 项目所有者 (Owner): 完全控制
- 项目成员 (Member): 读写权限
- 项目查看者 (Viewer): 只读权限

**表结构**:
```sql
CREATE TABLE project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- owner/member/viewer
    FOREIGN KEY (project_id) REFERENCES projects(id),
    UNIQUE(project_id, user_id)
);
```

### v29: 项目模板

**目标**: 快速创建预配置项目

**功能**:
- 内置模板: "Python Web App", "React Frontend", "Microservices"
- 自定义模板: 保存项目为模板
- 模板导入: 从 YAML/JSON 导入

**示例**:
```yaml
template: "Python Web App"
settings:
  default_runner: llama.cpp
  env_overrides:
    PYTHONPATH: "./src"
repos:
  - name: backend
    workspace_relpath: ./backend
  - name: frontend
    workspace_relpath: ./frontend
```

### v30: 配置导入/导出

**目标**: 项目配置的备份和迁移

**功能**:
- 导出: `agentos project export proj-123 > config.yaml`
- 导入: `agentos project import config.yaml`
- 批量迁移: 支持多个项目

**格式** (YAML):
```yaml
projects:
  - id: proj-123
    name: "My Project"
    settings:
      default_runner: llama.cpp
    repos:
      - name: backend
        path: ./backend
```

---

## 参考资料

### 相关文档
- [Projects 用户指南](../projects.md)
- [Projects API 参考](../api/projects.md)
- [Multi-Repository Projects](../projects/MULTI_REPO_PROJECTS.md)

### 相关代码
- `agentos/schemas/project.py`: 数据模型
- `agentos/core/project/repository.py`: CRUD 操作
- `agentos/core/project/repo_registry.py`: 仓库管理
- `agentos/webui/api/projects.py`: REST API
- `agentos/store/migrations/schema_v18.sql`: 多仓库表结构
- `agentos/store/migrations/schema_v25.sql`: 项目元数据
- `agentos/store/migrations/schema_v26.sql`: tasks.project_id

### 测试覆盖
- `tests/unit/test_project_schema.py`: Schema 验证
- `tests/unit/test_project_settings.py`: 配置继承
- `tests/integration/test_projects_api.py`: API 集成测试
- `tests/integration/test_multi_repo.py`: 多仓库功能测试

---

**问题或反馈?**

- 🐛 [报告问题](https://github.com/seacow-technology/agentos/issues)
- 💡 [架构讨论](https://github.com/seacow-technology/agentos/discussions)
- 📖 [查看更多文档](../index.md)
