# Projects API v0.31 快速参考

## 概述

Projects API v0.31 是Project-Aware Task OS (v0.4)的核心API，提供完整的项目管理功能。

**基础路径**: `/api/v0.31`

**版本**: v0.31 (Task #33实施)

## 端点列表

| 方法 | 端点 | 功能 | 状态码 |
|------|------|------|--------|
| POST | `/projects` | 创建项目 | 200/201 |
| GET | `/projects` | 列出项目（分页） | 200 |
| GET | `/projects/{id}` | 获取项目详情 | 200/404 |
| PATCH | `/projects/{id}` | 更新项目 | 200/404 |
| DELETE | `/projects/{id}` | 删除项目 | 200/404 |
| GET | `/projects/{id}/repos` | 列出仓库 | 200/404 |
| POST | `/projects/{id}/repos` | 添加仓库 | 200/201 |

## 快速示例

### 1. 创建项目

```bash
curl -X POST http://localhost:8000/api/v0.31/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-Commerce Platform",
    "description": "Main e-commerce backend",
    "tags": ["backend", "api", "production"]
  }'
```

**响应**:
```json
{
  "success": true,
  "project": {
    "project_id": "01KG80SEBS1WMBAK0EYMYXHJCH",
    "name": "E-Commerce Platform",
    "description": "Main e-commerce backend",
    "tags": ["backend", "api", "production"],
    "default_repo_id": null,
    "created_at": "2026-01-30T18:00:00+00:00",
    "updated_at": "2026-01-30T18:00:00+00:00",
    "metadata": null
  }
}
```

### 2. 列出所有项目

```bash
curl "http://localhost:8000/api/v0.31/projects?limit=100&offset=0"
```

**响应**:
```json
{
  "success": true,
  "projects": [
    {
      "project_id": "01KG80...",
      "name": "E-Commerce Platform",
      ...
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### 3. 获取项目详情

```bash
curl http://localhost:8000/api/v0.31/projects/01KG80SEBS1WMBAK0EYMYXHJCH
```

**响应**:
```json
{
  "success": true,
  "project": {
    "project_id": "01KG80...",
    "name": "E-Commerce Platform",
    ...
  },
  "repos": [],
  "tasks_count": 0
}
```

### 4. 更新项目

```bash
curl -X PATCH http://localhost:8000/api/v0.31/projects/01KG80... \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description",
    "tags": ["backend", "api", "staging"]
  }'
```

### 5. 添加仓库到项目

```bash
curl -X POST http://localhost:8000/api/v0.31/projects/01KG80.../repos \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backend-api",
    "local_path": "/Users/dev/backend",
    "vcs_type": "git",
    "remote_url": "https://github.com/user/backend.git",
    "default_branch": "main"
  }'
```

### 6. 删除项目

```bash
curl -X DELETE http://localhost:8000/api/v0.31/projects/01KG80...?force=false
```

## 请求参数

### POST /projects - 创建项目

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 项目名称（1-200字符，唯一） |
| description | string | ❌ | 项目描述 |
| tags | string[] | ❌ | 标签列表 |
| default_repo_id | string | ❌ | 默认仓库ID |

### GET /projects - 列出项目

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | int | 100 | 最大结果数（1-500） |
| offset | int | 0 | 分页偏移 |
| tags | string | - | 标签过滤（逗号分隔，OR逻辑） |

### PATCH /projects/{id} - 更新项目

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ❌ | 新项目名称 |
| description | string | ❌ | 新描述 |
| tags | string[] | ❌ | 新标签列表 |
| default_repo_id | string | ❌ | 新默认仓库ID |

**注意**: 至少提供一个字段

### POST /projects/{id}/repos - 添加仓库

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 仓库名称（项目内唯一） |
| local_path | string | ✅ | 本地绝对路径 |
| vcs_type | string | ❌ | VCS类型（默认"git"） |
| remote_url | string | ❌ | 远程仓库URL |
| default_branch | string | ❌ | 默认分支（默认"main"） |

## 错误处理

### 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功（GET/PATCH/DELETE） |
| 201 | 资源创建成功（POST） |
| 400 | 业务逻辑错误 |
| 404 | 资源不存在 |
| 422 | 输入验证失败 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "success": false,
  "reason_code": "PROJECT_NAME_CONFLICT",
  "message": "Project name already exists [name=Test Project]",
  "hint": "Choose a different project name"
}
```

### 常见错误码

| 错误码 | HTTP状态 | 说明 |
|--------|----------|------|
| PROJECT_NOT_FOUND | 404 | 项目不存在 |
| PROJECT_NAME_CONFLICT | 400 | 项目名称已存在 |
| PROJECT_HAS_TASKS | 400 | 项目包含任务（删除时） |
| REPO_NAME_CONFLICT | 400 | 仓库名称已存在 |
| INVALID_PATH | 400 | 路径不合法 |
| PATH_NOT_FOUND | 400 | 路径不存在 |
| NO_FIELDS_TO_UPDATE | 400 | 未提供更新字段 |

## Python客户端示例

```python
import requests

BASE_URL = "http://localhost:8000/api/v0.31"

# 创建项目
response = requests.post(
    f"{BASE_URL}/projects",
    json={
        "name": "My Project",
        "description": "Test project",
        "tags": ["test"]
    }
)

if response.status_code in [200, 201]:
    project = response.json()["project"]
    project_id = project["project_id"]
    print(f"Created project: {project_id}")

    # 获取详情
    response = requests.get(f"{BASE_URL}/projects/{project_id}")
    if response.status_code == 200:
        print(f"Project details: {response.json()}")

    # 列出所有项目
    response = requests.get(f"{BASE_URL}/projects?limit=10")
    if response.status_code == 200:
        projects = response.json()["projects"]
        print(f"Found {len(projects)} projects")

    # 更新项目
    response = requests.patch(
        f"{BASE_URL}/projects/{project_id}",
        json={"description": "Updated description"}
    )

    # 删除项目
    response = requests.delete(f"{BASE_URL}/projects/{project_id}")
    print(f"Delete status: {response.status_code}")
```

## JavaScript/TypeScript客户端示例

```typescript
const BASE_URL = "http://localhost:8000/api/v0.31";

// 创建项目
const createProject = async (name: string, description?: string, tags?: string[]) => {
  const response = await fetch(`${BASE_URL}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description, tags }),
  });

  if (!response.ok) {
    throw new Error(`Failed to create project: ${response.statusText}`);
  }

  const data = await response.json();
  return data.project;
};

// 列出项目
const listProjects = async (limit = 100, offset = 0, tags?: string) => {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  if (tags) {
    params.append("tags", tags);
  }

  const response = await fetch(`${BASE_URL}/projects?${params}`);
  const data = await response.json();
  return data.projects;
};

// 获取详情
const getProject = async (projectId: string) => {
  const response = await fetch(`${BASE_URL}/projects/${projectId}`);
  const data = await response.json();
  return data.project;
};

// 使用示例
(async () => {
  try {
    // 创建
    const project = await createProject("Test Project", "Description", ["test"]);
    console.log("Created:", project.project_id);

    // 列出
    const projects = await listProjects(10, 0);
    console.log("Projects:", projects.length);

    // 获取
    const details = await getProject(project.project_id);
    console.log("Details:", details);
  } catch (error) {
    console.error("Error:", error);
  }
})();
```

## 最佳实践

### 1. 唯一名称
项目名称必须唯一。创建前可以先列出现有项目检查重名。

### 2. 分页查询
使用limit和offset进行分页，避免一次性加载大量数据。

```bash
# 第一页
curl "http://localhost:8000/api/v0.31/projects?limit=50&offset=0"

# 第二页
curl "http://localhost:8000/api/v0.31/projects?limit=50&offset=50"
```

### 3. 标签过滤
使用tags参数进行高效过滤：

```bash
# 查找所有backend项目
curl "http://localhost:8000/api/v0.31/projects?tags=backend"

# 查找backend或api项目（OR逻辑）
curl "http://localhost:8000/api/v0.31/projects?tags=backend,api"
```

### 4. 错误处理
始终检查`success`字段和HTTP状态码：

```python
response = requests.post(BASE_URL + "/projects", json=data)

if response.status_code == 200:
    if response.json().get("success"):
        # 成功
        project = response.json()["project"]
    else:
        # 业务错误
        print(response.json().get("message"))
elif response.status_code == 400:
    # 客户端错误（如重名）
    error = response.json()
    print(f"{error['reason_code']}: {error['message']}")
elif response.status_code == 404:
    # 资源不存在
    print("Project not found")
else:
    # 其他错误
    print(f"Error: {response.status_code}")
```

### 5. 删除保护
删除项目时使用`force`参数控制行为：

```bash
# 安全删除（如果有任务会失败）
curl -X DELETE "http://localhost:8000/api/v0.31/projects/{id}?force=false"

# 强制删除（会尝试删除，但可能因FK约束失败）
curl -X DELETE "http://localhost:8000/api/v0.31/projects/{id}?force=true"
```

## API版本说明

系统支持两套Projects API：

### 旧API (`/api/projects`)
- 文件: `agentos/webui/api/projects.py`
- 用途: 遗留多仓库项目管理
- 状态: 维护模式

### 新API (`/api/v0.31/projects`) ⭐ 推荐
- 文件: `agentos/webui/api/projects_v31.py`
- 用途: Project-Aware Task OS (v0.4)
- 状态: 活跃开发
- 特性: 更完整的功能和更好的错误处理

**建议**: 新项目使用 `/api/v0.31/projects`

## 相关文档

- [Projects API详细文档](./V31_API_REFERENCE.md)
- [Project-Aware Task OS架构](../architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md)
- [v0.4发布说明](../releases/V04_RELEASE_NOTES.md)
- [Task #33实施总结](../../TASK_33_IMPLEMENTATION_SUMMARY.md)

## 支持

如有问题，请参考：
- [故障排除指南](../troubleshooting/)
- [GitHub Issues](https://github.com/your-org/agentos/issues)
- [API测试用例](../../tests/acceptance/test_projects_v31_acceptance.py)

---

**最后更新**: 2026-01-30
**API版本**: v0.31
**状态**: ✅ 生产就绪
