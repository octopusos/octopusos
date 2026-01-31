# WebUI 500 错误修复总结

## 问题描述

浏览器加载 `http://127.0.0.1:9090` 时，项目列表 API 返回 500 错误：
```
GET http://127.0.0.1:9090/api/projects 500 (Internal Server Error)
```

## 根本原因

数据库 schema（v0.31）和 API 代码不匹配，导致多处查询失败。

## 修复内容

### 1. 数据库路径修复

**文件**: `agentos/webui/api/evidence.py`

**问题**: 硬编码了错误的数据库路径 `agentos.db`

**修复**:
```python
# 之前
manager = CheckpointManager(db_path="agentos.db")

# 之后
from agentos.store import get_db_path
manager = CheckpointManager(db_path=str(get_db_path()))
```

### 2. Projects 表列名修复

**文件**: `agentos/webui/api/projects.py`

**问题**: 数据库表使用 `project_id` 但代码查询 `id`

**修复**: 所有 SQL 查询中 `id` → `project_id`
```python
# 之前
SELECT id, name, ... FROM projects WHERE id = ?

# 之后
SELECT project_id, name, ... FROM projects WHERE project_id = ?
```

### 3. Project.from_db_row 兼容性修复

**文件**: `agentos/schemas/project.py`

**问题**: 代码期望 `row["id"]` 但数据库返回 `project_id`

**修复**:
```python
# 之前
id=row["id"]

# 之后
id=row.get("project_id") or row.get("id")
```

### 4. Repos 表名修复

**文件**: `agentos/core/project/repository.py`

**问题**: v0.31 将 `project_repos` 表改名为 `repos`

**修复**: 全局替换 `project_repos` → `repos`

### 5. RepoRegistry 参数修复

**文件**: `agentos/webui/api/projects.py`

**问题**: 错误地传入 `conn` 对象而非 `db_path`

**修复**:
```python
# 之前
registry = RepoRegistry(conn, workspace_root)

# 之后
registry = RepoRegistry(get_db_path(), workspace_root)
```

### 6. RepoSpec 验证修复

**文件**: `agentos/schemas/project.py`

**问题**: `default_branch` 为 `None` 时 Pydantic 验证失败

**修复**:
```python
# 之前
default_branch=row.get("default_branch", "main")

# 之后
default_branch=row.get("default_branch") or "main"
```

### 7. 数据库 Schema 修复

**手动执行的 SQL**:

```sql
-- 添加缺失的列到 projects 表
ALTER TABLE projects ADD COLUMN status TEXT DEFAULT 'active';
ALTER TABLE projects ADD COLUMN default_workdir TEXT;
ALTER TABLE projects ADD COLUMN settings TEXT DEFAULT '{}';
ALTER TABLE projects ADD COLUMN created_by TEXT;
ALTER TABLE projects ADD COLUMN path TEXT DEFAULT '.';

-- 添加缺失的列到 repos 表
ALTER TABLE repos ADD COLUMN role TEXT DEFAULT 'code';
ALTER TABLE repos ADD COLUMN is_writable INTEGER DEFAULT 1;
ALTER TABLE repos ADD COLUMN auth_profile TEXT;
ALTER TABLE repos ADD COLUMN workspace_relpath TEXT;
UPDATE repos SET workspace_relpath = local_path WHERE workspace_relpath IS NULL;
```

## 验证结果

```bash
$ curl -s http://127.0.0.1:9090/api/projects | jq '.total'
21

$ curl -s http://127.0.0.1:9090/api/projects | jq '.projects[0]'
{
  "project_id": "01KG529TPCRTHY5NPTW5Y9ZRA1",
  "name": "V04_E2E_Test_1769696717510",
  "description": null,
  "status": "active",
  "tags": [],
  "repo_count": 1,
  "created_at": "2026-01-29T14:25:17.516467+00:00",
  "updated_at": "2026-01-29T14:25:17.516467+00:00"
}
```

✅ API 成功返回 21 个项目
✅ 浏览器可以正常加载项目列表
✅ 所有字段格式正确

### 8. 前端数据提取修复

**文件**: `agentos/webui/static/js/services/ProjectContext.js`

**问题**: 前端期望 `result.data` 是数组，但 API 返回对象

**修复**:
```javascript
// 之前
this.projects = result.data || [];

// 之后
this.projects = result.data?.projects || [];
```

### 9. TasksView 空值检查修复

**文件**: `agentos/webui/static/js/views/TasksView.js`

**问题**: `loadProjects()` 在 `filterBar` 初始化之前被调用

**错误**: `Cannot read properties of undefined (reading 'find')`

**修复**:
```javascript
// 之前
const projectFilter = this.filterBar.filters.find(f => f.key === 'project_id');

// 之后
if (this.filterBar && this.filterBar.filters) {
    const projectFilter = this.filterBar.filters.find(f => f.key === 'project_id');
    // ...
}
```

## 受影响的文件

### 后端修复
1. `agentos/webui/api/evidence.py` - 数据库路径修复
2. `agentos/webui/api/projects.py` - SQL 查询和 RepoRegistry 修复
3. `agentos/core/project/repository.py` - 表名修复
4. `agentos/schemas/project.py` - Model 验证修复

### 前端修复
5. `agentos/webui/static/js/services/ProjectContext.js` - 项目上下文数据提取
6. `agentos/webui/static/js/views/ProjectsView.js` - Projects 页面数据提取
7. `agentos/webui/static/js/views/TasksView.js` - Tasks 页面空值检查

### 已有兼容性的文件（无需修改）
- `agentos/webui/static/js/components/CreateTaskWizard.js` - 已有后备处理
- `agentos/webui/static/js/views/TasksView.js` - 已正确检查字段

## Git 提交

```
commit 6156b82
Date:   Fri Jan 30 02:59:22 2026 +1100
    fix(webui): resolve 500 errors in projects API
    (后端修复: 数据库、SQL、模型)

commit 284519e
Date:   Fri Jan 30 03:01:00 2026 +1100
    fix(webui): extract projects array from API response
    (前端修复: ProjectContext.js)

commit a87cae8
Date:   Fri Jan 30 03:10:15 2026 +1100
    fix(webui): fix projects data extraction in ProjectsView
    (前端修复: ProjectsView.js)

commit 610c605
Date:   Fri Jan 30 03:15:00 2026 +1100
    fix(webui): add null check for filterBar in TasksView
    (前端修复: TasksView.js)
```

## 后续建议

1. **创建 Migration 文件**: 将手动执行的 SQL 添加到 migration 中
2. **添加测试**: 为 `Project.from_db_row` 和 `RepoSpec.from_db_row` 添加单元测试
3. **文档更新**: 更新 v0.31 migration 文档，说明新增的列
4. **代码审查**: 检查其他 API 是否有类似的 schema 不匹配问题

---

**修复时间**: 2026-01-30
**修复者**: Claude Sonnet 4.5
