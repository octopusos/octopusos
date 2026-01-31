# WebUI 多仓库功能快速指南

## 启动 WebUI

```bash
# 启动 AgentOS WebUI
agentos webui

# 或指定端口
agentos webui --port 8080
```

访问: http://localhost:8080

---

## 功能导航

### 1. 项目管理 (Projects View)

**访问路径**: 侧边栏 → Observability → **Projects**

**功能**:
- 查看所有项目卡片
- 点击项目卡片查看详情
- 查看项目的仓库列表
- 点击仓库 "View" 查看仓库详情

**页面结构**:
```
Projects View
├── Project Cards (Grid)
│   ├── Project Name
│   ├── Repository Count
│   └── Created Time
├── Project Detail Drawer
│   ├── Basic Information
│   └── Repositories Table
│       ├── Name
│       ├── Remote URL
│       ├── Role Badge (code/docs/tests/...)
│       ├── Writable Status (✓ / Read-only)
│       └── Actions (View)
└── Repository Detail Drawer
    ├── Basic Information
    ├── Statistics (Files, Lines +/-)
    └── Tasks Timeline
```

### 2. 任务仓库视图 (Task Repos & Changes)

**访问路径**: 侧边栏 → Observability → **Tasks** → 点击任务 → **"Repos & Changes"** 标签

**功能**:
- 查看任务涉及的所有仓库
- 查看每个仓库的变更摘要
- 展开查看文件列表
- 查看 Commit Hash

**显示内容**:
```
Repositories (2)

📦 backend (FULL access) [code]
  ✓ 3 files changed (+80, -110 lines)
  📄 src/main.py (+50, -10)
  📄 src/utils.py (+30, -0)
  📄 src/legacy.py (deleted)
  🔗 Commit: abc123def

📦 frontend (READ_ONLY) [code]
  No changes
```

### 3. 任务依赖视图 (Task Dependencies)

**访问路径**: 侧边栏 → Observability → **Tasks** → 点击任务 → **"Dependencies"** 标签

**功能**:
- 查看任务依赖的其他任务 (Depends on)
- 查看依赖本任务的其他任务 (Depended by)
- 查看依赖类型 (requires/suggests/blocks)
- 点击跳转到依赖任务

**显示内容**:
```
🔗 Dependencies

Depends on (1):
  ↓ task-120 [requires]
    Reason: Uses commit from task-120
    [View Task]

Depended by (1):
  ↑ task-125 [suggests]
    Reason: Reads files modified by this task
    [View Task]
```

---

## API 端点参考

### 项目 API

```bash
# 列出所有项目
GET /api/projects

# 获取项目详情
GET /api/projects/{project_id}

# 列出项目仓库
GET /api/projects/{project_id}/repos

# 获取仓库详情
GET /api/projects/{project_id}/repos/{repo_id}

# 获取仓库涉及的任务
GET /api/projects/{project_id}/repos/{repo_id}/tasks
```

### 任务依赖 API

```bash
# 获取任务依赖
GET /api/tasks/{task_id}/dependencies?include_reverse=true

# 获取任务仓库（摘要）
GET /api/tasks/{task_id}/repos

# 获取任务仓库（详细）
GET /api/tasks/{task_id}/repos?detailed=true
```

---

## UI 组件说明

### 角色徽章 (Role Badges)

- **code**: 代码仓库（蓝色）
- **docs**: 文档仓库（绿色）
- **tests**: 测试仓库（橙色）
- **config**: 配置仓库（紫色）
- **data**: 数据仓库（粉色）

### 依赖类型徽章

- **requires** (红色): 强依赖，必须先完成
- **suggests** (黄色): 建议依赖，可以参考
- **blocks** (深红色): 阻塞依赖，会阻止任务执行

### 访问权限标识

- **✓ Writable**: 可读写
- **Read-only**: 只读

---

## 快速示例

### 示例 1: 查看项目仓库

1. 启动 WebUI: `agentos webui`
2. 访问 http://localhost:8080
3. 点击侧边栏 **"Projects"**
4. 点击项目卡片（如 "MyProject"）
5. 在抽屉中查看仓库列表
6. 点击仓库 "View" 按钮查看详情

### 示例 2: 查看任务的仓库变更

1. 点击侧边栏 **"Tasks"**
2. 点击任意任务查看详情
3. 点击 **"Repos & Changes"** 标签
4. 查看仓库变更摘要
5. 点击仓库卡片头部展开文件列表

### 示例 3: 查看任务依赖

1. 在任务详情中点击 **"Dependencies"** 标签
2. 查看 "Depends on" 部分（本任务依赖的任务）
3. 查看 "Depended by" 部分（依赖本任务的任务）
4. 点击 **"View Task"** 跳转到依赖任务

---

## 常见问题

### Q1: 没有看到 Projects 导航项？
**A**: 确保已更新到最新版本并重启 WebUI。检查浏览器是否缓存旧版本（Ctrl+Shift+R 强制刷新）。

### Q2: Task 页面没有 "Repos & Changes" 标签？
**A**: 确保已更新 TasksView.js 并刷新浏览器。检查浏览器控制台是否有错误。

### Q3: API 返回 404 错误？
**A**: 确保已注册新 API 路由（projects 和 task_dependencies）并重启 WebUI。

### Q4: 仓库列表为空？
**A**: 检查数据库中是否有 `project_repos` 表和数据。可以使用 CLI 命令添加仓库：
```bash
agentos repo add --project-id myproject --name backend --url git@github.com:user/repo.git
```

### Q5: 依赖关系为空？
**A**: 依赖关系需要任务执行后自动生成，或手动创建。检查 `task_dependencies` 表。

---

## 浏览器支持

- ✅ Chrome/Edge 90+ (推荐)
- ✅ Firefox 88+
- ✅ Safari 14+
- ⚠️ IE 11 不支持

---

## 性能建议

1. **大量仓库**: 如果项目有超过 50 个仓库，考虑使用过滤功能
2. **大量任务**: 任务列表超过 100 个时，使用筛选器缩小范围
3. **移动端**: 建议在桌面端使用，移动端主要用于查看
4. **网络**: 首次加载可能较慢，后续会使用浏览器缓存

---

## 反馈与支持

如有问题或建议，请通过以下方式反馈：
- GitHub Issues
- 开发团队邮件
- Slack 频道

---

**文档版本**: 1.0
**更新日期**: 2026-01-28
