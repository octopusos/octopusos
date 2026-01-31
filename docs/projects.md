# Projects 功能指南

## 什么是 Projects

Projects 是 AgentOS 中用于组织和管理工作的容器。每个 Project 可以包含:

- **一个或多个代码仓库 (Repos)**: 支持多仓库架构,如前端 + 后端 + 文档
- **相关的任务 (Tasks)**: 所有任务可以按项目组织和过滤
- **执行配置 (Settings)**: 每个项目有独立的 Runner、环境变量和权限设置
- **审计日志 (Events)**: 所有操作都有明确的项目归属,便于追踪

## 为什么使用 Projects

### 传统方式的痛点

在没有 Projects 之前:
- ❌ 任务孤立分散,难以按业务线组织
- ❌ 每个任务都需要重新配置 Runner 和环境变量
- ❌ 多仓库项目(如微服务架构)需要创建多个孤立任务
- ❌ 无法按项目统计工作量和进度

### Projects 带来的价值

- ✅ **组织管理**: 按项目组织代码和任务,而不是孤立的 Tasks
- ✅ **配置隔离**: 每个项目有独立的执行配置(runner、环境变量、权限)
- ✅ **多仓库支持**: 一个项目可以包含多个仓库,支持微服务和 Monorepo 架构
- ✅ **团队协作**: 多人可以在同一 Project 下工作,共享配置
- ✅ **审计追踪**: 所有操作都有明确的项目归属

## 创建你的第一个 Project

### 步骤 1: 打开 Projects 页面

在 AgentOS WebUI 中,点击侧边栏的 "Projects"。

### 步骤 2: 点击 "New Project"

在页面顶部,点击 "New Project" 按钮打开创建表单。

### 步骤 3: 填写基本信息

**Basic Info 标签页**:

- **Name** (必填): 项目名称,如 "My Web App"
- **Description** (可选): 项目描述,如 "电商平台前后端项目"
- **Tags** (可选): 标签,用逗号分隔,如 "python, web, api"
- **Default Workdir** (可选): 默认工作目录,如 "/Users/you/projects/myapp"

示例:
```
Name: E-Commerce Platform
Description: 电商平台全栈项目,包含 React 前端和 Python 后端
Tags: react, python, postgresql, production
Default Workdir: /Users/john/workspace/ecommerce
```

### 步骤 4: 配置 Settings (可选)

点击 "Settings" 标签页,配置高级选项:

#### Execution Settings

- **Default Runner**: 选择 AI 引擎
  - `llama.cpp`: 本地 LLM (默认)
  - `openai`: OpenAI API
  - 留空: 使用全局默认配置

- **Provider Policy**: 控制 provider 使用策略
  - `prefer-local`: 优先使用本地模型
  - `cloud-only`: 仅使用云端 API
  - `balanced`: 自动负载均衡

#### Environment Variables

添加环境变量键值对,这些变量会在任务执行时自动注入:

```
DEBUG = true
LOG_LEVEL = info
DATABASE_URL = postgresql://localhost/mydb
API_KEY = your-api-key  (注意: 敏感信息应使用密钥管理)
```

**白名单机制**: 只有以下环境变量被允许:
- `PYTHONPATH`, `DEBUG`, `LOG_LEVEL`, `TZ`
- `LANG`, `LC_ALL`, `PATH`, `HOME`, `USER`
- `TMPDIR`, `NODE_ENV`, `EDITOR`, `PAGER`
- `TERM`, `SHELL`

#### Risk Profile

控制项目的安全风险配置:

- **Allow shell write operations**:
  - ✅ 勾选: 允许任务写文件 (开发环境推荐)
  - ❌ 不勾选: 禁止写操作 (生产环境推荐)

- **Require admin token**:
  - ✅ 勾选: 高危操作需要管理员 token (生产环境推荐)
  - ❌ 不勾选: 无需额外验证 (开发环境)

- **Writable Paths** (路径白名单):
  - 指定允许写入的路径,每行一个
  - 例如: `/tmp`, `./output`, `/var/log/myapp`
  - 空表示无限制 (不推荐)

示例配置 (开发环境):
```
✅ Allow shell write operations
❌ Require admin token
Writable Paths:
  /tmp
  ./output
  ./logs
```

示例配置 (生产环境):
```
❌ Allow shell write operations
✅ Require admin token
Writable Paths:
  /var/log/myapp
```

### 步骤 5: 保存

点击 "Save" 按钮创建项目。创建成功后,您会看到项目卡片出现在列表中。

## 管理 Repositories

Projects 支持多仓库架构,您可以为一个项目添加多个代码仓库。

### 添加仓库

1. 点击项目卡片,打开详情 drawer
2. 在 "Repositories" 区域,点击 "Add Repository" 按钮
3. 填写仓库信息:

**必填字段**:
- **Name**: 仓库名称,如 "backend", "frontend", "docs"
- **Workspace Path**: 相对路径,如 `.` (根目录), `./src`, `./backend`

**可选字段**:
- **Remote URL**: Git 仓库 URL,如 `https://github.com/user/repo.git`
- **Default Branch**: 默认分支,默认为 "main"
- **Role**: 仓库角色,可选值:
  - `code`: 代码仓库 (默认)
  - `docs`: 文档仓库
  - `infra`: 基础设施仓库 (Terraform, K8s)
  - `mono-subdir`: Monorepo 子目录
- **Is Writable**: 是否可写,默认为 true

示例 1 - 前后端分离项目:
```
Repository 1:
  Name: backend
  Remote URL: https://github.com/myorg/ecommerce-backend.git
  Workspace Path: ./backend
  Role: code
  Is Writable: true

Repository 2:
  Name: frontend
  Remote URL: https://github.com/myorg/ecommerce-frontend.git
  Workspace Path: ./frontend
  Role: code
  Is Writable: true

Repository 3:
  Name: docs
  Remote URL: https://github.com/myorg/ecommerce-docs.git
  Workspace Path: ./docs
  Role: docs
  Is Writable: false  (只读)
```

示例 2 - Monorepo 项目:
```
Repository 1:
  Name: api
  Remote URL: https://github.com/myorg/monorepo.git
  Workspace Path: ./packages/api
  Role: mono-subdir

Repository 2:
  Name: ui
  Remote URL: https://github.com/myorg/monorepo.git
  Workspace Path: ./packages/ui
  Role: mono-subdir
```

4. 点击 "Save" 保存仓库

### 编辑/删除仓库

在仓库列表中,点击操作按钮:
- ✏️ **编辑**: 修改仓库配置 (Name、Default Branch、Is Writable 等)
- 🗑️ **删除**: 从项目中移除仓库 (不会删除实际代码)

**注意**: 删除仓库会影响关联的任务,请谨慎操作。

## 创建 Tasks

在 Project 下创建的 Task 会自动关联到该项目,并继承项目的配置。

### 方法 1: 从 Projects 页面

1. 打开项目详情 drawer
2. 点击 "View Tasks" 按钮跳转到 Tasks 页面
3. 在 Tasks 页面点击 "New Task"
4. Task 会自动关联当前项目

### 方法 2: 从 Tasks 页面

1. 打开 Tasks 页面
2. 在 "Project" 筛选器中选择项目
3. 点击 "New Task" 创建任务
4. 任务会自动关联选中的项目

### 配置继承

Task 创建时会自动继承 Project 的配置:

```
Task 配置优先级: Task Settings > Project Settings > Global Settings
```

示例:
```
Global Settings:
  default_runner: llama.cpp

Project Settings:
  default_runner: openai
  env_overrides: {DEBUG: "true"}

Task Settings:
  default_runner: (未设置)
  env_overrides: {LOG_LEVEL: "debug"}

最终 Task 配置:
  default_runner: openai  (继承自 Project)
  env_overrides: {DEBUG: "true", LOG_LEVEL: "debug"}  (合并)
```

## 过滤和搜索

### 搜索项目

在 Projects 页面顶部的搜索框中输入关键词,支持搜索:
- 项目名称 (Name)
- 项目描述 (Description)
- 项目标签 (Tags)

示例:
- 搜索 "web" → 匹配名称或描述中包含 "web" 的项目
- 搜索 "react" → 匹配标签中包含 "react" 的项目

### 按 Project 过滤 Tasks

在 Tasks 页面,使用 "Project" 下拉筛选器过滤任务:

1. 点击 "Project" 下拉框
2. 选择项目名称
3. 任务列表会自动过滤,只显示该项目下的任务

**快捷操作**: 在 Projects 页面点击 "View Tasks" 按钮,会自动过滤到该项目的任务。

### 按状态过滤

Projects 支持状态筛选:
- **Active**: 活跃项目 (默认)
- **Archived**: 已归档项目
- **All**: 所有状态

在 Projects 页面使用 "Status" 下拉框切换。

## 归档和删除

### 归档项目

归档项目后:
- ✅ 项目状态变为 "Archived"
- ✅ 仍可查看历史任务和数据
- ✅ 可以随时恢复 (改回 Active 状态)
- ❌ 不会出现在默认列表中 (需切换到 "Archived" 筛选)

**操作步骤**:
1. 打开项目详情 drawer
2. 点击右上角菜单按钮
3. 选择 "Archive Project"
4. 确认操作

**恢复归档项目**:
1. 在 Status 筛选器中选择 "Archived"
2. 找到归档的项目
3. 打开详情 drawer,点击 "Restore"

### 删除项目

**限制**: 只能删除没有任务的空项目。

**操作步骤**:
1. 打开项目详情 drawer
2. 点击右上角菜单按钮
3. 选择 "Delete Project"
4. 如果项目有任务,会提示错误

**如何删除有任务的项目**:
1. 先删除项目下的所有任务
2. 再删除项目

**推荐**: 对于有历史数据的项目,建议使用 "归档" 而不是 "删除"。

## 最佳实践

### 1. 按团队/产品组织项目

**推荐命名方式**:
- ✅ "Frontend Team - E-Commerce"
- ✅ "Backend API - User Service"
- ✅ "Mobile App - iOS"
- ✅ "Infrastructure - AWS"

**不推荐命名方式**:
- ❌ "Test Project 1"
- ❌ "Temp"
- ❌ "试试看"
- ❌ "New Project" (太泛化)

### 2. 使用标签分类

标签可以用于横向分类,便于搜索和筛选:

```
开发语言:
tags: ["python", "flask", "postgresql"]
tags: ["javascript", "react", "typescript"]
tags: ["go", "grpc", "kubernetes"]

环境:
tags: ["development", "staging"]
tags: ["production", "critical"]

业务线:
tags: ["e-commerce", "payment"]
tags: ["user-service", "auth"]
```

### 3. 配置合理的 Risk Profile

#### 开发环境配置

适用于本地开发、测试环境:

```
Settings:
  allow_shell_write: true
  require_admin_token: false
  writable_paths: ["/tmp", "./output", "./logs"]

理由:
- 允许写操作,方便快速迭代
- 无需额外验证,提升效率
- 限制路径白名单,避免误操作
```

#### 生产环境配置

适用于生产环境、敏感数据处理:

```
Settings:
  allow_shell_write: false
  require_admin_token: true
  writable_paths: ["/var/log/myapp"]

理由:
- 禁止写操作,防止误修改
- 需要 admin token,提升安全性
- 严格限制路径白名单
```

### 4. 多仓库项目建议

#### 前后端分离架构

```
Project: "E-Commerce Platform"
Repos:
  - backend (code, ./backend)
  - frontend (code, ./frontend)
  - shared-types (code, ./shared)  # 共享类型定义
  - docs (docs, ./docs, read-only)
```

#### 微服务架构

```
Project: "Microservices Cluster"
Repos:
  - user-service (code, ./services/user)
  - order-service (code, ./services/order)
  - payment-service (code, ./services/payment)
  - infra (infra, ./infra, read-only)  # K8s 配置
```

#### Monorepo 架构

```
Project: "Company Monorepo"
Repos:
  - packages-api (mono-subdir, ./packages/api)
  - packages-ui (mono-subdir, ./packages/ui)
  - packages-shared (mono-subdir, ./packages/shared)
```

### 5. 环境变量管理

**推荐做法**:
- ✅ 使用环境变量白名单
- ✅ 不要在 Settings 中存储敏感信息 (如密码、API Key)
- ✅ 使用外部密钥管理工具 (如 AWS Secrets Manager、HashiCorp Vault)
- ✅ 为不同环境创建不同的 Project (dev-project, prod-project)

**不推荐做法**:
- ❌ 直接在 Settings 中存储明文密码
- ❌ 所有环境共用一个 Project
- ❌ 设置过多的环境变量 (超过 10 个)

## 常见问题

### Q: 可以创建没有仓库的项目吗?

A: 可以,但创建 Task 时会提示添加仓库。建议创建项目时至少添加一个仓库。

### Q: 一个项目可以有多个仓库吗?

A: 可以,这是 Projects 的核心功能。支持多仓库架构,如:
- 前后端分离 (frontend + backend)
- 微服务 (service-a + service-b + service-c)
- 代码 + 文档 (code + docs)

**最佳实践**: 建议一个项目不超过 5-10 个仓库,以保持管理复杂度可控。

### Q: 如何删除有任务的项目?

A: 无法直接删除有任务的项目。有两个选择:

1. **归档项目** (推荐):
   - 保留历史数据
   - 可以随时恢复
   - 不影响审计日志

2. **删除所有任务后删除项目**:
   - 先在 Tasks 页面删除项目下的所有任务
   - 再删除项目
   - 会丢失历史数据

### Q: Project Settings 会影响现有任务吗?

A: **不会**。Settings 只在任务创建时应用。修改 Project Settings 不影响已创建的任务。

如果需要更新现有任务的配置:
1. 编辑任务,手动修改配置
2. 或删除任务后重新创建

### Q: 多个仓库有相同的 Remote URL,可以吗?

A: 可以,这是 Monorepo 架构的典型场景。通过不同的 `workspace_relpath` 区分:

```
Repo 1:
  Name: api
  Remote URL: https://github.com/org/monorepo.git
  Workspace Path: ./packages/api

Repo 2:
  Name: ui
  Remote URL: https://github.com/org/monorepo.git  (相同 URL)
  Workspace Path: ./packages/ui  (不同路径)
```

### Q: 如何查看项目的所有任务?

A: 两种方式:

1. **快捷方式**: 在 Projects 页面点击项目的 "View Tasks" 按钮
2. **手动过滤**: 在 Tasks 页面使用 "Project" 下拉框筛选

### Q: Tags 和 Description 有什么区别?

A:
- **Tags**: 用于分类和筛选,支持搜索,格式化为标签样式
- **Description**: 用于详细说明项目内容,自由文本,不用于筛选

示例:
```
Name: E-Commerce Backend
Description: 基于 Python Flask 的电商平台后端 API,支持用户、订单、支付等核心功能
Tags: ["python", "flask", "api", "production"]
```

### Q: 如何批量修改多个项目的配置?

A: 目前不支持批量修改。需要逐个项目修改。

**计划中的功能**:
- 项目模板 (v27)
- 批量操作 (v28)
- 配置导入/导出 (v29)

### Q: Project Settings 的环境变量白名单是否可以自定义?

A: 目前不支持。白名单硬编码在代码中,只允许安全的环境变量。

如果需要添加自定义变量到白名单:
1. 修改 `agentos/core/project/settings_inheritance.py`
2. 重新部署

**安全提示**: 不建议随意扩展白名单,可能引入安全风险。

## 相关链接

- [Multi-Repository Projects 架构文档](./projects/MULTI_REPO_PROJECTS.md)
- [Projects API 参考](./api/projects.md)
- [Projects 开发文档](./dev/projects-architecture.md)
- [Task Management Guide](./guides/user/TASK_MANAGEMENT_GUIDE.md)

---

**问题或反馈?**

- 🐛 [报告问题](https://github.com/seacow-technology/agentos/issues)
- 💡 [功能建议](https://github.com/seacow-technology/agentos/discussions)
- 📖 [查看更多文档](./index.md)
