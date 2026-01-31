# AgentOS v0.4 快速入门指南

**版本**: v0.4.0
**预计时间**: 5-10 分钟

---

## 目录

1. [安装](#1-安装)
2. [创建第一个项目](#2-创建第一个项目)
3. [添加仓库](#3-添加仓库)
4. [创建并执行任务](#4-创建并执行任务)
5. [查看结果](#5-查看结果)
6. [常见问题](#6-常见问题)

---

## 1. 安装

### 环境要求

- Python 3.13+
- Git (可选，用于仓库管理)

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yourorg/agentos.git
cd agentos

# 2. 安装依赖
pip install -e .

# 3. 验证安装
agentos --version
# 输出: AgentOS v0.4.0
```

---

## 2. 创建第一个项目

v0.4 引入了 **Project-Aware** 架构，所有任务必须绑定到项目。让我们先创建一个项目。

### 使用 CLI

```bash
# 创建项目
agentos project-v31 create "My First Project" \
  --description "Learning AgentOS v0.4" \
  --tags tutorial,beginner

# 输出:
# ✓ Project created: 01HXYZ1234567890
# Name: My First Project
# Tags: tutorial, beginner
```

### 使用 Python API

```python
from agentos.core.project.service import ProjectService

# 创建 ProjectService
project_service = ProjectService()

# 创建项目
project = project_service.create_project(
    name="My First Project",
    description="Learning AgentOS v0.4",
    tags=["tutorial", "beginner"]
)

print(f"Project ID: {project.project_id}")
print(f"Name: {project.name}")
```

### 使用 REST API

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Project",
    "description": "Learning AgentOS v0.4",
    "tags": ["tutorial", "beginner"]
  }'
```

### 列出所有项目

```bash
# CLI
agentos project-v31 list

# 输出 (Rich Table):
# ┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
# ┃ Project ID         ┃ Name              ┃ Tags              ┃
# ┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
# │ 01HXYZ1234567890   │ My First Project  │ tutorial,beginner │
# └────────────────────┴───────────────────┴───────────────────┘
```

---

## 3. 添加仓库

项目创建后，我们需要添加一个代码仓库。

### 准备工作

创建一个测试仓库目录：

```bash
# 创建测试目录
mkdir -p ~/projects/my-first-repo
cd ~/projects/my-first-repo

# 初始化 Git (可选)
git init
echo "# My First Repo" > README.md
git add README.md
git commit -m "Initial commit"
```

### 添加仓库到项目

#### 使用 CLI

```bash
# 添加仓库（使用项目 ID）
agentos repo-v31 add \
  01HXYZ1234567890 \
  my-first-repo \
  ~/projects/my-first-repo \
  --remote https://github.com/yourorg/my-first-repo.git

# 输出:
# ✓ Repository added: 01HXAB9876543210
# Name: my-first-repo
# Path: /Users/you/projects/my-first-repo
# Remote: https://github.com/yourorg/my-first-repo.git
```

#### 使用 Python API

```python
from agentos.core.project.repo_service import RepoService
import os

repo_service = RepoService()

# 添加仓库
repo = repo_service.add_repo(
    project_id=project.project_id,
    name="my-first-repo",
    local_path=os.path.expanduser("~/projects/my-first-repo"),
    vcs_type="git",
    remote_url="https://github.com/yourorg/my-first-repo.git",
    branch="main"
)

print(f"Repo ID: {repo.repo_id}")
print(f"Name: {repo.name}")
```

#### 使用 REST API

```bash
curl -X POST http://localhost:8000/api/projects/01HXYZ1234567890/repos \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-first-repo",
    "local_path": "/Users/you/projects/my-first-repo",
    "vcs_type": "git",
    "remote_url": "https://github.com/yourorg/my-first-repo.git",
    "branch": "main"
  }'
```

### 查看项目的仓库

```bash
# CLI
agentos project-v31 show 01HXYZ1234567890

# 输出:
# Project: My First Project
# Description: Learning AgentOS v0.4
# Tags: tutorial, beginner
#
# Repositories (1):
#   - my-first-repo (01HXAB9876543210)
#     Path: ~/projects/my-first-repo
#     Remote: https://github.com/yourorg/my-first-repo.git
```

---

## 4. 创建并执行任务

现在我们有了项目和仓库，可以创建任务了。

### 4.1 创建任务（DRAFT）

#### 使用 CLI

```bash
agentos task-v31 create \
  "Add README documentation" \
  --project-id 01HXYZ1234567890 \
  --repo-id 01HXAB9876543210 \
  --workdir docs \
  --intent "Create comprehensive README with setup instructions" \
  --acceptance-criteria "README includes installation steps" \
  --acceptance-criteria "README includes usage examples" \
  --acceptance-criteria "README includes troubleshooting section"

# 输出:
# ✓ Task created: 01HXCD1111111111
# Title: Add README documentation
# Status: draft
# Project: My First Project
# Repo: my-first-repo
# Workdir: docs
```

#### 使用 Python API

```python
from agentos.core.task.service import TaskService

task_service = TaskService()

# 创建任务
task = task_service.create_task(
    title="Add README documentation",
    project_id=project.project_id,
    repo_id=repo.repo_id,
    workdir="docs",
    intent="Create comprehensive README with setup instructions",
    acceptance_criteria=[
        "README includes installation steps",
        "README includes usage examples",
        "README includes troubleshooting section"
    ]
)

print(f"Task ID: {task.task_id}")
print(f"Status: {task.status}")  # draft
```

#### 使用 REST API

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Add README documentation",
    "project_id": "01HXYZ1234567890",
    "repo_id": "01HXAB9876543210",
    "workdir": "docs",
    "intent": "Create comprehensive README with setup instructions",
    "acceptance_criteria": [
      "README includes installation steps",
      "README includes usage examples",
      "README includes troubleshooting section"
    ]
  }'
```

### 4.2 冻结规格（DRAFT → PLANNED）

在任务进入 READY 状态前，必须先**冻结规格**。

#### 使用 CLI

```bash
agentos task-v31 freeze 01HXCD1111111111

# 输出:
# ✓ Spec frozen
# Status: planned
# Frozen at: 2026-01-29T10:30:00Z
```

#### 使用 Python API

```python
from agentos.core.project.spec_service import TaskSpecService

spec_service = TaskSpecService()

# 冻结规格
spec_service.freeze_spec(
    task_id=task.task_id,
    frozen_by="user@example.com"
)

# 检查状态
task = task_service.get_task(task.task_id)
print(f"Status: {task.status}")  # planned
```

#### 使用 REST API

```bash
curl -X POST http://localhost:8000/api/tasks/01HXCD1111111111/spec/freeze \
  -H "Content-Type: application/json" \
  -d '{
    "frozen_by": "user@example.com"
  }'
```

### 4.3 标记为 READY（PLANNED → READY）

规格冻结后，可以标记任务为 READY。

#### 使用 CLI

```bash
agentos task-v31 ready 01HXCD1111111111

# 输出:
# ✓ Task marked as ready
# Status: ready
```

#### 使用 Python API

```python
from agentos.core.task.state_machine import TaskStateMachine

state_machine = TaskStateMachine()

# 标记为 ready
state_machine.transition(
    task_id=task.task_id,
    to_status="ready"
)
```

#### 使用 REST API

```bash
curl -X POST http://localhost:8000/api/tasks/01HXCD1111111111/ready
```

### 4.4 执行任务

```bash
# 使用 AgentOS 执行任务
agentos task execute 01HXCD1111111111

# 任务会自动执行，生成 README 文档
```

---

## 5. 查看结果

### 5.1 查看任务状态

```bash
# CLI
agentos task-v31 show 01HXCD1111111111

# 输出:
# Task: Add README documentation
# Status: done
# Project: My First Project (01HXYZ1234567890)
# Repo: my-first-repo (01HXAB9876543210)
# Workdir: docs
#
# Spec:
#   Intent: Create comprehensive README with setup instructions
#   Acceptance Criteria:
#     ✓ README includes installation steps
#     ✓ README includes usage examples
#     ✓ README includes troubleshooting section
#   Spec Frozen: Yes (2026-01-29T10:30:00Z)
#
# Binding:
#   Project: My First Project
#   Repo: my-first-repo
#   Workdir: docs
```

### 5.2 查看任务产物

任务完成后，可以查看生成的产物：

```bash
# CLI (如果实现了)
agentos task artifacts 01HXCD1111111111

# REST API
curl http://localhost:8000/api/tasks/01HXCD1111111111/artifacts
```

### 5.3 查看审计日志

```bash
# REST API
curl http://localhost:8000/api/tasks/01HXCD1111111111/audits

# 输出:
# {
#   "audits": [
#     {
#       "event_type": "TASK_CREATED",
#       "timestamp": "2026-01-29T10:00:00Z",
#       "actor": "user@example.com"
#     },
#     {
#       "event_type": "TASK_SPEC_FROZEN",
#       "timestamp": "2026-01-29T10:30:00Z",
#       "actor": "user@example.com"
#     },
#     {
#       "event_type": "TASK_READY",
#       "timestamp": "2026-01-29T10:31:00Z",
#       "actor": "system"
#     },
#     {
#       "event_type": "TASK_COMPLETED",
#       "timestamp": "2026-01-29T10:45:00Z",
#       "actor": "agent"
#     }
#   ]
# }
```

---

## 6. 常见问题

### Q1: 为什么创建任务时必须提供 project_id？

**A**: v0.4 引入了 **Project-Aware** 架构。所有任务必须绑定到项目，以支持多仓库项目管理。

**解决方案**: 先创建项目，再创建任务。

```bash
# 1. 创建项目
agentos project-v31 create "My Project"

# 2. 使用项目 ID 创建任务
agentos task-v31 create "My Task" --project-id <PROJECT_ID>
```

### Q2: 什么是 "Spec Freezing"？为什么需要？

**A**: **Spec Freezing（规格冻结）** 是 v0.4 引入的机制，用于确保任务规格稳定：

- 任务创建时处于 `DRAFT` 状态（规格可修改）
- 冻结规格后进入 `PLANNED` 状态（规格锁定）
- 只有冻结规格后才能进入 `READY` 状态

**好处**:
- 防止任务执行中途修改目标
- 提供清晰的状态转换流程
- 便于审计和追溯

### Q3: 如何添加仓库到项目？

**A**: 使用 `agentos repo-v31 add` 命令：

```bash
agentos repo-v31 add <PROJECT_ID> <REPO_NAME> <REPO_PATH>
```

**注意**:
- `<REPO_PATH>` 必须是**绝对路径**
- 路径必须存在
- 路径会经过安全验证（防止路径穿越）

### Q4: 如何查看项目的所有任务？

**A**: 有多种方法：

```bash
# 方法 1: 使用 project-v31 show
agentos project-v31 show <PROJECT_ID>

# 方法 2: 使用 task-v31 list 过滤
agentos task-v31 list --project-id <PROJECT_ID>

# 方法 3: REST API
curl http://localhost:8000/api/projects/<PROJECT_ID>/tasks
```

### Q5: 如何删除项目？

**A**: 使用 `project-v31 delete` 命令：

```bash
# 如果项目没有任务
agentos project-v31 delete <PROJECT_ID>

# 如果项目有任务（强制删除）
agentos project-v31 delete <PROJECT_ID> --force
```

**警告**: `--force` 会删除所有关联的任务和仓库！

### Q6: v0.3 的代码还能用吗？

**A**: **部分兼容**，但有破坏性变更：

**不兼容**:
- `POST /api/tasks` 现在需要 `project_id`
- 直接访问 `tasks.project_id` 字段（已移到 `task_bindings`）

**兼容**:
- 其他 API 端点基本兼容
- CLI 基本命令兼容（但推荐使用 `*-v31` 版本）

**迁移建议**: 参考 [V04_RELEASE_NOTES.md](../../releases/V04_RELEASE_NOTES.md#迁移指南)

### Q7: 如何使用 WebUI？

**A**: 启动 WebUI 服务器：

```bash
# 启动 WebUI
agentos webui start

# 默认地址: http://localhost:8000
```

在浏览器中打开 `http://localhost:8000`，使用：
- **Projects** 页面：管理项目
- **Tasks** 页面：创建和管理任务
- **Create Task Wizard**: 4 步创建任务流程

### Q8: 如何查看审计日志？

**A**: 使用 REST API：

```bash
# 查看任务的审计日志
curl http://localhost:8000/api/tasks/<TASK_ID>/audits

# 输出包含所有关键操作：
# - TASK_CREATED
# - TASK_SPEC_FROZEN
# - TASK_BOUND
# - TASK_READY
# - TASK_COMPLETED
# - ARTIFACT_REGISTERED
```

### Q9: 什么是 task_bindings？

**A**: `task_bindings` 表记录任务与项目/仓库的绑定关系：

```sql
task_bindings {
  task_id: 唯一任务 ID
  project_id: 所属项目（必填）
  repo_id: 绑定的仓库（可选）
  workdir: 工作目录（可选，如 "src/auth"）
  bound_at: 绑定时间
}
```

**用途**:
- 支持任务按项目过滤
- 支持多仓库项目
- 提供清晰的绑定关系

### Q10: 如何批量创建任务？

**A**: v0.4 暂不支持批量创建，计划在 v0.5 实现。

**临时方案**: 使用脚本调用 API：

```python
import requests

project_id = "01HXYZ1234567890"
tasks = [
    {"title": "Task 1", "intent": "..."},
    {"title": "Task 2", "intent": "..."},
    {"title": "Task 3", "intent": "..."},
]

for task_data in tasks:
    task_data["project_id"] = project_id
    response = requests.post(
        "http://localhost:8000/api/tasks",
        json=task_data
    )
    print(f"Created: {response.json()['task']['task_id']}")
```

---

## 下一步

完成快速入门后，你可以：

1. **阅读完整文档**:
   - [API 参考](../../api/V31_API_REFERENCE.md)
   - [CLI 参考](../../cli/CLI_V31_REFERENCE.md)
   - [架构文档](../../architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md)

2. **尝试高级功能**:
   - 多仓库项目管理
   - 任务依赖关系
   - 自定义审计日志

3. **参与开发**:
   - 查看 [CONTRIBUTING.md](../../../CONTRIBUTING.md)
   - 提交 Issue 或 PR

---

## 反馈

如有问题或建议，欢迎：
- GitHub Issues: [github.com/yourorg/agentos/issues](https://github.com/yourorg/agentos/issues)
- Email: support@agentos.dev

---

**祝使用愉快！**

*AgentOS Team*
