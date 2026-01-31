# AgentOS v0.4.0 Release Notes

**Release Date**: 2026-01-29
**Codename**: Project-Aware Task Operating System

---

## 概述

AgentOS v0.4.0 是一个重大架构升级，引入了**Project-Aware Task Operating System**架构。这是自 v0.1 以来最大的重构，将任务管理从单仓库模式升级到多仓库项目模式。

### 核心理念

```
v0.3:  Task → Repository (1:1)
v0.4:  Project → Task → Repository (1:N:N)
```

**关键变化**:
- ✅ Project ≠ Repository（语义分离）
- ✅ Task 必须绑定到 Project（强约束）
- ✅ Spec Freezing（规格冻结机制）
- ✅ Multi-Repo Support（多仓库支持）
- ✅ Audit Trail（审计日志）

---

## 5 个核心原则

### 1. Project ≠ Repository

**v0.3 问题**: 项目和仓库混为一谈，无法支持微服务等多仓库场景

**v0.4 解决方案**:
- `Project`: 逻辑概念，代表一个业务项目
- `Repository`: 物理概念，代表一个代码仓库
- 一个 Project 可以包含多个 Repositories

**示例**:
```
Project: E-Commerce Platform
├── Repository: frontend (React)
├── Repository: backend (Python)
├── Repository: mobile (React Native)
└── Repository: infrastructure (Terraform)
```

### 2. Task 绑定强制性

**v0.3 问题**: Task 可以脱离 Project 存在，导致管理混乱

**v0.4 解决方案**:
- 所有 Task 必须绑定到 Project
- 通过 `task_bindings` 表强制外键约束
- API 层面强制要求 `project_id`

**示例**:
```python
# ❌ v0.3: Task 可以独立存在
task = create_task(title="Fix bug")

# ✅ v0.4: Task 必须绑定到 Project
project = create_project(name="My Project")
task = create_task(title="Fix bug", project_id=project.id)
```

### 3. Chat 边界清晰

**v0.3 问题**: Chat 和 Task 职责不清

**v0.4 解决方案**:
- Chat: 对话和探索阶段
- Task: 执行和交付阶段
- Chat → Task 是单向转换（不可逆）

### 4. 状态机规范

**v0.3 问题**: Task 状态转换不规范

**v0.4 解决方案**:
- 严格的状态转换流程
- Spec 冻结是进入 READY 的必要条件

**状态机**:
```
DRAFT → (freeze spec) → PLANNED → (validate) → READY → RUNNING → DONE
                                                    ↓
                                                 FAILED
```

### 5. Spec 冻结机制

**v0.3 问题**: Task 规格可以随时修改，导致目标不稳定

**v0.4 解决方案**:
- 引入 `spec_frozen` 标志
- Spec 冻结后不可修改
- 冻结是进入 READY 的前置条件

**示例**:
```python
# 1. 创建 Task (DRAFT)
task = create_task(
    title="Add authentication",
    intent="Implement JWT-based auth",
    acceptance_criteria=["Login works", "Tests pass"]
)

# 2. 冻结 Spec (DRAFT → PLANNED)
freeze_spec(task.id)

# 3. 标记为 READY (PLANNED → READY)
mark_ready(task.id)
```

---

## 新增功能

### 1. Project Management

**新增表**: `projects`

**功能**:
- 创建和管理项目
- 项目标签分类
- 设置默认仓库
- 查看项目下的所有任务和仓库

**API**:
- `POST /api/projects` - 创建项目
- `GET /api/projects` - 列出项目
- `GET /api/projects/{id}` - 获取项目详情
- `PATCH /api/projects/{id}` - 更新项目
- `DELETE /api/projects/{id}` - 删除项目
- `GET /api/projects/{id}/repos` - 获取项目仓库
- `POST /api/projects/{id}/repos` - 添加仓库到项目

**CLI**:
- `agentos project-v31 list` - 列出项目
- `agentos project-v31 create` - 创建项目
- `agentos project-v31 show <id>` - 查看项目详情
- `agentos project-v31 delete <id>` - 删除项目

### 2. Repository Management

**新增表**: `repos`

**功能**:
- 将仓库添加到项目
- 管理仓库路径和远程地址
- 路径安全验证（防止路径穿越）
- VCS 类型支持（git/none）

**API**:
- `GET /api/repos/{id}` - 获取仓库详情
- `PATCH /api/repos/{id}` - 更新仓库
- `DELETE /api/repos/{id}` - 删除仓库

**CLI**:
- `agentos repo-v31 add` - 添加仓库
- `agentos repo-v31 list` - 列出仓库
- `agentos repo-v31 show <id>` - 查看仓库详情
- `agentos repo-v31 scan <id>` - 扫描 Git 状态

### 3. Task Specifications

**新增表**: `task_specs`

**功能**:
- 规格冻结（freeze spec）
- 意图（intent）和验收标准（acceptance_criteria）分离
- 规格版本化（spec_version）
- 冻结时间和冻结人记录

**API**:
- `POST /api/tasks/{id}/spec/freeze` - 冻结规格
- `GET /api/tasks/{id}/spec` - 获取规格

**CLI**:
- `agentos task-v31 freeze <id>` - 冻结规格

### 4. Task Bindings

**新增表**: `task_bindings`

**功能**:
- 任务与项目绑定
- 任务与仓库绑定（可选）
- 工作目录（workdir）指定
- 绑定时间记录

**API**:
- `POST /api/tasks/{id}/bind` - 绑定任务
- `GET /api/tasks/{id}/binding` - 获取绑定信息

**CLI**:
- `agentos task-v31 bind <id>` - 绑定任务

### 5. Task Artifacts

**新增表**: `task_artifacts`

**功能**:
- 登记任务产物（文件/URL）
- 产物元数据管理
- 路径安全验证

**API**:
- `POST /api/tasks/{id}/artifacts` - 登记产物
- `GET /api/tasks/{id}/artifacts` - 列出产物

### 6. Audit Trail

**新增表**: `task_audits`

**功能**:
- 记录关键操作
- 事件类型：CREATED, SPEC_FROZEN, BOUND, READY, COMPLETED 等
- 操作人和时间戳记录

**API**:
- `GET /api/tasks/{id}/audits` - 获取审计日志

---

## API 变更

### 新增 API 端点

#### Projects (7 个端点)
- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{id}`
- `PATCH /api/projects/{id}`
- `DELETE /api/projects/{id}`
- `GET /api/projects/{id}/repos`
- `POST /api/projects/{id}/repos`

#### Repos (3 个端点)
- `GET /api/repos/{id}`
- `PATCH /api/repos/{id}`
- `DELETE /api/repos/{id}`

#### Tasks v31 Extension (6 个端点)
- `POST /api/tasks/{id}/spec/freeze`
- `POST /api/tasks/{id}/bind`
- `POST /api/tasks/{id}/ready`
- `POST /api/tasks/{id}/artifacts`
- `GET /api/tasks/{id}/artifacts`
- `GET /api/tasks/{id}/audits`

**总计**: 16 个新端点

### 修改的 API 端点

#### `POST /api/tasks`

**v0.3**:
```json
{
  "title": "Fix bug",
  "intent": "..."
}
```

**v0.4** (破坏性变更):
```json
{
  "title": "Fix bug",
  "project_id": "01HXYZ...",  // ⚠️ 新增必填字段
  "intent": "..."
}
```

**错误响应**（缺少 project_id）:
```json
{
  "success": false,
  "reason_code": "PROJECT_ID_REQUIRED",
  "message": "Task creation requires project_id",
  "hint": "Use POST /api/projects first to create a project"
}
```

#### `GET /api/tasks`

**新增查询参数**:
- `project_id`: 按项目过滤
- `spec_frozen`: 按规格冻结状态过滤

**示例**:
```bash
GET /api/tasks?project_id=01HXYZ&status=ready
```

---

## CLI 变更

### 新增命令集

#### Project Commands (4 个)
- `agentos project-v31 list [--tags TAG1,TAG2] [--limit N]`
- `agentos project-v31 create <name> [--description DESC] [--tags TAG1,TAG2]`
- `agentos project-v31 show <project-id>`
- `agentos project-v31 delete <project-id> [--force]`

#### Repo Commands (4 个)
- `agentos repo-v31 add <project-id> <name> <path> [--remote URL]`
- `agentos repo-v31 list [--project-id ID]`
- `agentos repo-v31 show <repo-id>`
- `agentos repo-v31 scan <repo-id>`

#### Task v31 Commands (6 个)
- `agentos task-v31 create <title> --project-id ID [--repo-id ID] [--workdir PATH]`
- `agentos task-v31 freeze <task-id>`
- `agentos task-v31 bind <task-id> --project-id ID [--repo-id ID]`
- `agentos task-v31 ready <task-id>`
- `agentos task-v31 list [--project-id ID] [--status STATUS]`
- `agentos task-v31 show <task-id>`

**总计**: 14 个新命令

### 输出格式

所有命令支持：
- `--json`: JSON 输出（用于脚本）
- `--quiet`: 安静模式（只输出 ID）
- 默认: Rich table 格式（彩色表格）

---

## WebUI 变更

### 1. Create Task Wizard

**新增组件**: `CreateTaskWizard.js`

**功能**:
- 4 步创建流程
  1. Basic Info (项目绑定)
  2. Repository (仓库选择)
  3. Specification (规格定义)
  4. Review & Create
- 项目选择器
- 仓库选择器（根据项目动态加载）
- 验收标准编辑器

**文件**:
- `agentos/webui/static/js/components/CreateTaskWizard.js`
- `agentos/webui/static/css/wizard.css`

### 2. Projects View

**新增功能**:
- 项目列表展示
- 项目详情页（包含仓库和任务列表）
- 项目创建和编辑
- 项目删除（带确认）

**文件**:
- `agentos/webui/static/js/views/ProjectsView.js`

### 3. Tasks View 增强

**新增功能**:
- 按项目过滤任务
- 显示任务绑定信息
- Spec 冻结状态显示
- 审计日志查看

**文件**:
- `agentos/webui/static/js/views/TasksView.js`

---

## 数据库变更

### Schema 版本

- **旧版本**: v30
- **新版本**: v31

### 新增表 (6 个)

1. **projects** - 项目表
   - project_id (PK)
   - name (UNIQUE)
   - description, tags, default_repo_id
   - created_at, updated_at, metadata

2. **repos** - 仓库表
   - repo_id (PK)
   - project_id (FK)
   - name, local_path, vcs_type, remote_url
   - created_at, updated_at, metadata
   - UNIQUE(project_id, name)

3. **task_specs** - 任务规格表
   - task_id (PK, FK)
   - intent, acceptance_criteria
   - spec_frozen, frozen_at, frozen_by
   - spec_version
   - created_at, updated_at

4. **task_bindings** - 任务绑定表
   - task_id (PK, FK)
   - project_id (FK, NOT NULL)
   - repo_id (FK, nullable)
   - workdir
   - bound_at

5. **task_artifacts** - 任务产物表
   - artifact_id (PK)
   - task_id (FK)
   - kind (file/url), path, url
   - display_name, metadata
   - created_at

6. **task_audits** - 审计日志表
   - audit_id (PK)
   - task_id (FK)
   - event_type, event_data
   - timestamp, actor

### 修改的表

**tasks 表**:
- 移除: project_id（移到 task_bindings）
- 移除: intent, acceptance_criteria（移到 task_specs）
- 保留: task_id, title, status, created_at, updated_at

### 索引

新增索引:
- `idx_projects_name`
- `idx_projects_created_at`
- `idx_repos_project_id`
- `idx_task_bindings_project_id`
- `idx_task_bindings_repo_id`
- `idx_task_artifacts_task_id`
- `idx_task_audits_task_id`

---

## 破坏性变更

### 1. API 变更

#### ⚠️ `POST /api/tasks` 现在需要 `project_id`

**影响**: 所有创建任务的代码

**迁移示例**:
```python
# v0.3
response = requests.post("/api/tasks", json={
    "title": "Fix bug"
})

# v0.4
# 先创建项目
project = requests.post("/api/projects", json={
    "name": "My Project"
}).json()["project"]

# 再创建任务
response = requests.post("/api/tasks", json={
    "title": "Fix bug",
    "project_id": project["project_id"]  # 必填
})
```

### 2. 数据库变更

#### ⚠️ `tasks` 表结构变更

**影响**: 直接访问数据库的代码

**迁移**:
- `tasks.project_id` → `task_bindings.project_id`
- `tasks.intent` → `task_specs.intent`
- `tasks.acceptance_criteria` → `task_specs.acceptance_criteria`

### 3. Service 层变更

#### ⚠️ TaskService 签名变更

**旧**:
```python
task_service.create_task(title, intent, acceptance_criteria)
```

**新**:
```python
task_service.create_task(
    title,
    project_id,  # 新增必填参数
    intent,
    acceptance_criteria
)
```

---

## 迁移指南

### 自动迁移

**步骤**:
```bash
# 1. 备份数据库
cp agentos.db agentos.db.backup

# 2. 运行 AgentOS（自动迁移）
agentos --version  # 会自动运行迁移

# 3. 验证迁移
sqlite3 agentos.db ".tables"  # 应该看到新表
```

**自动迁移逻辑**:
1. 检测 schema 版本
2. 如果 < v31，运行 `schema_v31_project_aware.sql`
3. 创建新表
4. 迁移现有数据（如果有）
5. 更新 schema_version

### 手动迁移

如果需要手动控制：

```bash
# 1. 导出现有数据
sqlite3 agentos.db ".dump tasks" > tasks_backup.sql

# 2. 运行迁移脚本
sqlite3 agentos.db < agentos/store/migrations/schema_v31_project_aware.sql

# 3. 验证
sqlite3 agentos.db "SELECT COUNT(*) FROM projects;"
sqlite3 agentos.db "SELECT COUNT(*) FROM task_bindings;"
```

### 代码迁移

#### 1. 创建任务

**v0.3**:
```python
from agentos.core.task.service import TaskService

task_service = TaskService()
task = task_service.create_task(
    title="Fix authentication bug",
    intent="Fix JWT token validation"
)
```

**v0.4**:
```python
from agentos.core.project.service import ProjectService
from agentos.core.task.service import TaskService

# 先创建项目
project_service = ProjectService()
project = project_service.create_project(
    name="Authentication Service"
)

# 再创建任务
task_service = TaskService()
task = task_service.create_task(
    title="Fix authentication bug",
    project_id=project.project_id,  # 必填
    intent="Fix JWT token validation"
)
```

#### 2. 查询任务

**v0.3**:
```python
tasks = task_service.list_tasks(status="ready")
```

**v0.4**:
```python
# 按项目查询
project_service = ProjectService()
tasks = project_service.get_project_tasks(
    project_id=project.project_id,
    status="ready"
)

# 或者用新的 API
tasks = task_service.list_tasks(
    project_id=project.project_id,
    status="ready"
)
```

---

## 已知限制

### 1. 测试环境隔离

**问题**: ProjectService 使用全局 SQLiteWriter，单元测试难以完全隔离

**影响**: 测试主要依赖集成测试

**计划**: v0.5 重构 Service 层支持依赖注入

### 2. 并发写入性能

**问题**: SQLite 的写入是序列化的，高并发场景有瓶颈

**影响**: 10+ 并发写入时可能有延迟

**计划**: v0.5 支持 PostgreSQL

### 3. Spec 冻结不可逆

**问题**: Spec 冻结后无法修改

**影响**: 需要修改规格时必须创建新任务

**计划**: v0.5 考虑 Spec 版本化

---

## 性能

### API 响应时间

| 端点 | v0.3 | v0.4 | 备注 |
|------|------|------|------|
| GET /api/tasks | 80ms | 100ms | 增加了 JOIN 查询 |
| POST /api/tasks | 120ms | 150ms | 增加了多表写入 |
| GET /api/projects | N/A | 50ms | 新端点 |

### 数据库大小

| 项目 | 表数量 | 索引数量 | 备注 |
|------|--------|----------|------|
| v0.3 | 18 | 25 | 基础表 |
| v0.4 | 24 (+6) | 32 (+7) | 增加 v31 表 |

---

## 文档

### 新增文档

1. **架构文档**:
   - `docs/architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md` (73 KB)
   - `docs/V04_CONSTRAINTS_AND_GATES.md`
   - `docs/V04_SEMANTIC_LOCK.md`

2. **实现报告**:
   - `PHASE2_IMPLEMENTATION_REPORT.md` - Service 层
   - `PHASE3_API_IMPLEMENTATION_REPORT.md` - API 层
   - `PHASE4_WEBUI_IMPLEMENTATION_REPORT.md` - WebUI 层
   - `TASK6_PHASE5_CLI_IMPLEMENTATION.md` - CLI 层
   - `tests/validation/V04_ACCEPTANCE_TEST_REPORT.md` - 验收测试

3. **API 参考**:
   - `docs/api/V31_API_REFERENCE.md` - 完整 API 文档

4. **CLI 参考**:
   - `docs/cli/CLI_V31_REFERENCE.md` - CLI 命令文档

### 更新的文档

- `README.md` - 更新版本号和功能列表
- `docs/guides/quickstart/V04_QUICKSTART.md` - 快速开始指南

---

## 下一步 (v0.5 路线图)

### 计划功能

1. **PostgreSQL 支持**
   - 更好的并发性能
   - 更丰富的查询能力
   - 生产环境推荐

2. **Task 模板**
   - 预定义任务模板
   - 快速创建常见任务
   - 团队共享模板

3. **批量操作**
   - 批量创建任务
   - 批量绑定/更新
   - 批量导入/导出

4. **WebUI 增强**
   - 项目看板视图
   - 任务依赖关系图
   - 甘特图时间线

5. **Spec 版本化**
   - Spec 历史记录
   - Spec 对比
   - Spec 回滚

---

## 升级建议

### 谁应该升级？

✅ **推荐升级**:
- 管理多个仓库的项目
- 需要严格规格管理的团队
- 需要审计日志的场景
- 需要 WebUI 的用户

⚠️ **暂缓升级**:
- 只有单个仓库的简单项目
- 重度依赖 v0.3 API 的现有系统（需要改造成本）

### 升级步骤

1. **准备阶段** (1 day)
   - 备份数据库
   - 阅读迁移指南
   - 测试环境试运行

2. **迁移阶段** (1-2 days)
   - 运行数据库迁移
   - 更新代码调用
   - 运行测试验证

3. **验证阶段** (1 day)
   - 功能回归测试
   - 性能基准测试
   - 监控生产环境

**总计**: 3-4 days

---

## 致谢

### 开发团队

- **架构设计**: Claude Sonnet 4.5
- **核心开发**: Claude Sonnet 4.5
- **测试验证**: Claude Sonnet 4.5
- **文档编写**: Claude Sonnet 4.5

### 技术栈

- Python 3.13+
- SQLite 3.x
- FastAPI 0.109+
- Rich 13.9+
- Click 8.1+

---

## 反馈和支持

### 报告问题

- GitHub Issues: [github.com/yourorg/agentos/issues](https://github.com/yourorg/agentos/issues)
- Email: support@agentos.dev

### 获取帮助

- 文档: `docs/`
- 快速开始: `docs/guides/quickstart/V04_QUICKSTART.md`
- API 参考: `docs/api/V31_API_REFERENCE.md`
- CLI 参考: `docs/cli/CLI_V31_REFERENCE.md`

---

**Release v0.4.0 - Project-Aware Task Operating System**

*Built with ❤️ by the AgentOS Team*
