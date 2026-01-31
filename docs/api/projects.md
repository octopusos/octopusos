# Projects API 文档

AgentOS Projects API 提供了完整的项目和仓库管理功能,支持多仓库架构、配置继承和审计追踪。

## 基本信息

- **Base URL**: `http://localhost:8000/api`
- **Content-Type**: `application/json`
- **Authentication**: 当前版本无需认证 (本地部署)

## 端点列表

### Projects 管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/projects` | 列出所有项目 |
| POST | `/api/projects` | 创建新项目 |
| GET | `/api/projects/{project_id}` | 获取项目详情 |
| PATCH | `/api/projects/{project_id}` | 更新项目 |
| POST | `/api/projects/{project_id}/archive` | 归档项目 |
| DELETE | `/api/projects/{project_id}` | 删除项目 |

### Repositories 管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/projects/{project_id}/repos` | 列出项目的仓库 |
| POST | `/api/projects/{project_id}/repos` | 添加仓库 |
| GET | `/api/projects/{project_id}/repos/{repo_id}` | 获取仓库详情 |
| PUT | `/api/projects/{project_id}/repos/{repo_id}` | 更新仓库 |
| DELETE | `/api/projects/{project_id}/repos/{repo_id}` | 删除仓库 |

---

## Projects 端点详解

### GET /api/projects

列出所有项目,支持搜索和分页。

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `search` | string | 否 | - | 搜索关键词 (匹配名称、描述、标签) |
| `status` | string | 否 | - | 状态过滤 (`active`/`archived`/`deleted`) |
| `limit` | integer | 否 | 50 | 返回数量 (1-200) |
| `offset` | integer | 否 | 0 | 偏移量 |

**响应示例**:

```json
{
  "projects": [
    {
      "project_id": "proj-01HX123ABC",
      "name": "E-Commerce Platform",
      "description": "电商平台全栈项目",
      "status": "active",
      "tags": ["python", "react", "postgresql"],
      "repo_count": 3,
      "created_at": "2026-01-20T10:00:00Z",
      "updated_at": "2026-01-29T12:00:00Z"
    },
    {
      "project_id": "proj-01HX456DEF",
      "name": "Mobile App",
      "description": "iOS 移动应用",
      "status": "active",
      "tags": ["swift", "ios"],
      "repo_count": 1,
      "created_at": "2026-01-25T14:30:00Z",
      "updated_at": "2026-01-28T09:15:00Z"
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

**错误码**:
- `400`: 无效参数 (如 status 不在允许范围内)
- `500`: 服务器错误

**示例请求**:

```bash
# 列出所有活跃项目
curl http://localhost:8000/api/projects?status=active

# 搜索项目
curl http://localhost:8000/api/projects?search=web

# 分页查询
curl http://localhost:8000/api/projects?limit=10&offset=20
```

---

### POST /api/projects

创建新项目。

**请求体**:

```json
{
  "name": "My Project",
  "description": "项目描述",
  "tags": ["python", "web", "api"],
  "default_workdir": "/Users/you/projects/myapp",
  "settings": {
    "default_runner": "llama.cpp",
    "provider_policy": "prefer-local",
    "env_overrides": {
      "DEBUG": "true",
      "LOG_LEVEL": "info"
    },
    "risk_profile": {
      "allow_shell_write": true,
      "require_admin_token": false,
      "writable_paths": ["/tmp", "./output"]
    }
  }
}
```

**字段说明**:

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `name` | string | 是 | 项目名称 |
| `description` | string | 否 | 项目描述 |
| `tags` | array[string] | 否 | 标签列表 |
| `default_workdir` | string | 否 | 默认工作目录 |
| `settings` | object | 否 | 项目配置 (见下方) |

**Settings 对象**:

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `default_runner` | string | 否 | 默认 Runner (`llama.cpp`/`openai`) |
| `provider_policy` | string | 否 | Provider 策略 (`prefer-local`/`cloud-only`/`balanced`) |
| `env_overrides` | object | 否 | 环境变量覆盖 (键值对) |
| `risk_profile` | object | 否 | 风险配置 (见下方) |

**RiskProfile 对象**:

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `allow_shell_write` | boolean | 否 | 允许 shell 写操作,默认 false |
| `require_admin_token` | boolean | 否 | 需要 admin token,默认 false |
| `writable_paths` | array[string] | 否 | 可写路径白名单 |

**响应示例**:

```json
{
  "project_id": "proj-01HX789GHI",
  "name": "My Project",
  "description": "项目描述",
  "status": "active",
  "tags": ["python", "web", "api"],
  "default_workdir": "/Users/you/projects/myapp",
  "settings": {
    "default_runner": "llama.cpp",
    "provider_policy": "prefer-local",
    "env_overrides": {
      "DEBUG": "true",
      "LOG_LEVEL": "info"
    },
    "risk_profile": {
      "allow_shell_write": true,
      "require_admin_token": false,
      "writable_paths": ["/tmp", "./output"]
    }
  },
  "created_at": "2026-01-29T15:30:00Z",
  "updated_at": "2026-01-29T15:30:00Z"
}
```

**错误码**:
- `400`: 参数错误 (名称重复、无效 status 等)
- `500`: 服务器错误

**示例请求**:

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Project",
    "description": "测试项目",
    "tags": ["test", "demo"]
  }'
```

---

### GET /api/projects/{project_id}

获取项目详情,包含完整的 Settings 和 Repos 列表。

**路径参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `project_id` | string | 是 | 项目 ID |

**响应示例**:

```json
{
  "project_id": "proj-01HX123ABC",
  "name": "E-Commerce Platform",
  "description": "电商平台全栈项目",
  "status": "active",
  "tags": ["python", "react", "postgresql"],
  "default_workdir": "/Users/john/workspace/ecommerce",
  "settings": {
    "default_runner": "llama.cpp",
    "provider_policy": "prefer-local",
    "env_overrides": {
      "DEBUG": "true"
    },
    "risk_profile": {
      "allow_shell_write": true,
      "require_admin_token": false,
      "writable_paths": ["/tmp"]
    }
  },
  "repos": [
    {
      "repo_id": "repo-01HX111AAA",
      "name": "backend",
      "remote_url": "https://github.com/org/backend.git",
      "workspace_relpath": "./backend",
      "role": "code",
      "is_writable": true,
      "default_branch": "main",
      "created_at": "2026-01-20T10:00:00Z",
      "updated_at": "2026-01-20T10:00:00Z"
    },
    {
      "repo_id": "repo-01HX222BBB",
      "name": "frontend",
      "remote_url": "https://github.com/org/frontend.git",
      "workspace_relpath": "./frontend",
      "role": "code",
      "is_writable": true,
      "default_branch": "main",
      "created_at": "2026-01-20T10:05:00Z",
      "updated_at": "2026-01-20T10:05:00Z"
    }
  ],
  "created_at": "2026-01-20T10:00:00Z",
  "updated_at": "2026-01-29T12:00:00Z"
}
```

**错误码**:
- `404`: 项目不存在
- `500`: 服务器错误

**示例请求**:

```bash
curl http://localhost:8000/api/projects/proj-01HX123ABC
```

---

### PATCH /api/projects/{project_id}

更新项目信息和配置。

**路径参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `project_id` | string | 是 | 项目 ID |

**请求体** (所有字段可选):

```json
{
  "name": "Updated Project Name",
  "description": "更新后的描述",
  "tags": ["python", "web", "updated"],
  "default_workdir": "/new/path",
  "settings": {
    "default_runner": "openai",
    "env_overrides": {
      "DEBUG": "false"
    }
  }
}
```

**响应示例**:

```json
{
  "project_id": "proj-01HX123ABC",
  "name": "Updated Project Name",
  "description": "更新后的描述",
  "status": "active",
  "tags": ["python", "web", "updated"],
  "updated_at": "2026-01-29T16:00:00Z"
}
```

**错误码**:
- `400`: 参数错误 (名称重复等)
- `404`: 项目不存在
- `500`: 服务器错误

**示例请求**:

```bash
curl -X PATCH http://localhost:8000/api/projects/proj-01HX123ABC \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Name",
    "description": "New description"
  }'
```

---

### POST /api/projects/{project_id}/archive

归档项目。归档后项目状态变为 `archived`,不会出现在默认列表中。

**路径参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `project_id` | string | 是 | 项目 ID |

**响应示例**:

```json
{
  "message": "Project archived successfully",
  "project_id": "proj-01HX123ABC",
  "status": "archived"
}
```

**错误码**:
- `404`: 项目不存在
- `500`: 服务器错误

**示例请求**:

```bash
curl -X POST http://localhost:8000/api/projects/proj-01HX123ABC/archive
```

**恢复归档项目**: 使用 `PATCH /api/projects/{project_id}` 修改 status 为 `active`。

---

### DELETE /api/projects/{project_id}

删除项目。**注意**: 只能删除没有任务的空项目。

**路径参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `project_id` | string | 是 | 项目 ID |

**响应示例**:

```json
{
  "message": "Project deleted successfully",
  "project_id": "proj-01HX123ABC"
}
```

**错误码**:
- `400`: 项目有任务,无法删除
- `404`: 项目不存在
- `500`: 服务器错误

**示例请求**:

```bash
curl -X DELETE http://localhost:8000/api/projects/proj-01HX123ABC
```

---

## Repositories 端点详解

### GET /api/projects/{project_id}/repos

列出项目的所有仓库。

**路径参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `project_id` | string | 是 | 项目 ID |

**响应示例**:

```json
{
  "repos": [
    {
      "repo_id": "repo-01HX111AAA",
      "name": "backend",
      "remote_url": "https://github.com/org/backend.git",
      "workspace_relpath": "./backend",
      "role": "code",
      "is_writable": true,
      "default_branch": "main",
      "created_at": "2026-01-20T10:00:00Z",
      "updated_at": "2026-01-20T10:00:00Z"
    },
    {
      "repo_id": "repo-01HX222BBB",
      "name": "frontend",
      "remote_url": "https://github.com/org/frontend.git",
      "workspace_relpath": "./frontend",
      "role": "code",
      "is_writable": true,
      "default_branch": "main",
      "created_at": "2026-01-20T10:05:00Z",
      "updated_at": "2026-01-20T10:05:00Z"
    }
  ],
  "total": 2
}
```

**错误码**:
- `404`: 项目不存在
- `500`: 服务器错误

**示例请求**:

```bash
curl http://localhost:8000/api/projects/proj-01HX123ABC/repos
```

---

### POST /api/projects/{project_id}/repos

添加仓库到项目。

**路径参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `project_id` | string | 是 | 项目 ID |

**请求体**:

```json
{
  "name": "backend",
  "remote_url": "https://github.com/org/backend.git",
  "workspace_relpath": "./backend",
  "role": "code",
  "is_writable": true,
  "default_branch": "main",
  "auth_profile": "github-pat",
  "metadata": {
    "description": "Backend API service"
  }
}
```

**字段说明**:

| 字段 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `name` | string | 是 | - | 仓库名称 (项目内唯一) |
| `remote_url` | string | 否 | - | Git 远程 URL |
| `workspace_relpath` | string | 是 | - | 相对路径 (项目内唯一) |
| `role` | string | 否 | `code` | 仓库角色 (`code`/`docs`/`infra`/`mono-subdir`) |
| `is_writable` | boolean | 否 | `true` | 是否可写 |
| `default_branch` | string | 否 | `main` | 默认分支 |
| `auth_profile` | string | 否 | - | 认证配置名称 |
| `metadata` | object | 否 | `{}` | 扩展元数据 |

**响应示例**:

```json
{
  "repo_id": "repo-01HX333CCC",
  "project_id": "proj-01HX123ABC",
  "name": "backend",
  "remote_url": "https://github.com/org/backend.git",
  "workspace_relpath": "./backend",
  "role": "code",
  "is_writable": true,
  "default_branch": "main",
  "auth_profile": "github-pat",
  "created_at": "2026-01-29T16:30:00Z",
  "updated_at": "2026-01-29T16:30:00Z",
  "metadata": {
    "description": "Backend API service"
  }
}
```

**错误码**:
- `400`: 参数错误 (名称/路径重复、无效 role 等)
- `404`: 项目不存在
- `500`: 服务器错误

**示例请求**:

```bash
curl -X POST http://localhost:8000/api/projects/proj-01HX123ABC/repos \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backend",
    "workspace_relpath": "./backend",
    "remote_url": "https://github.com/org/backend.git"
  }'
```

---

### GET /api/projects/{project_id}/repos/{repo_id}

获取仓库详情。

**路径参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `project_id` | string | 是 | 项目 ID |
| `repo_id` | string | 是 | 仓库 ID |

**响应示例**:

```json
{
  "repo_id": "repo-01HX111AAA",
  "project_id": "proj-01HX123ABC",
  "name": "backend",
  "remote_url": "https://github.com/org/backend.git",
  "workspace_relpath": "./backend",
  "role": "code",
  "is_writable": true,
  "default_branch": "main",
  "auth_profile": "github-pat",
  "created_at": "2026-01-20T10:00:00Z",
  "updated_at": "2026-01-20T10:00:00Z",
  "metadata": {},
  "task_count": 15
}
```

**错误码**:
- `404`: 项目或仓库不存在
- `500`: 服务器错误

**示例请求**:

```bash
curl http://localhost:8000/api/projects/proj-01HX123ABC/repos/repo-01HX111AAA
```

---

### PUT /api/projects/{project_id}/repos/{repo_id}

更新仓库配置。

**路径参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `project_id` | string | 是 | 项目 ID |
| `repo_id` | string | 是 | 仓库 ID |

**请求体** (所有字段可选):

```json
{
  "name": "backend-v2",
  "is_writable": false,
  "default_branch": "develop",
  "auth_profile": "github-ssh",
  "metadata": {
    "version": "2.0"
  }
}
```

**响应示例**:

```json
{
  "repo_id": "repo-01HX111AAA",
  "project_id": "proj-01HX123ABC",
  "name": "backend-v2",
  "is_writable": false,
  "default_branch": "develop",
  "auth_profile": "github-ssh",
  "updated_at": "2026-01-29T17:00:00Z",
  "metadata": {
    "version": "2.0"
  }
}
```

**错误码**:
- `400`: 参数错误 (名称重复等)
- `404`: 项目或仓库不存在
- `500`: 服务器错误

**示例请求**:

```bash
curl -X PUT http://localhost:8000/api/projects/proj-01HX123ABC/repos/repo-01HX111AAA \
  -H "Content-Type: application/json" \
  -d '{
    "is_writable": false,
    "default_branch": "develop"
  }'
```

---

### DELETE /api/projects/{project_id}/repos/{repo_id}

删除仓库。**注意**: 不会删除实际代码,只是从项目中移除绑定。

**路径参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `project_id` | string | 是 | 项目 ID |
| `repo_id` | string | 是 | 仓库 ID |

**响应示例**:

```json
{
  "message": "Repository removed successfully",
  "repo_id": "repo-01HX111AAA"
}
```

**错误码**:
- `404`: 项目或仓库不存在
- `500`: 服务器错误

**示例请求**:

```bash
curl -X DELETE http://localhost:8000/api/projects/proj-01HX123ABC/repos/repo-01HX111AAA
```

---

## 数据模型

### Project

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `id` | string | 是 | 项目 ID (ULID) |
| `name` | string | 是 | 项目名称 |
| `description` | string | 否 | 项目描述 |
| `status` | string | 否 | 状态 (`active`/`archived`/`deleted`),默认 `active` |
| `tags` | array[string] | 否 | 标签列表 |
| `default_workdir` | string | 否 | 默认工作目录 |
| `default_repo_id` | string | 否 | 默认仓库 ID |
| `settings` | object | 否 | 项目配置 |
| `created_at` | datetime | 是 | 创建时间 (ISO 8601) |
| `updated_at` | datetime | 是 | 更新时间 (ISO 8601) |
| `created_by` | string | 否 | 创建者 |
| `repos` | array[RepoSpec] | 否 | 仓库列表 |

### ProjectSettings

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `default_runner` | string | 否 | 默认 Runner |
| `provider_policy` | string | 否 | Provider 策略 |
| `env_overrides` | object | 否 | 环境变量覆盖 (键值对) |
| `risk_profile` | RiskProfile | 否 | 风险配置 |

### RiskProfile

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `allow_shell_write` | boolean | 否 | 允许 shell 写操作,默认 `false` |
| `require_admin_token` | boolean | 否 | 需要 admin token,默认 `false` |
| `writable_paths` | array[string] | 否 | 可写路径白名单 |

### RepoSpec

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `repo_id` | string | 是 | 仓库 ID (ULID) |
| `project_id` | string | 是 | 关联项目 ID |
| `name` | string | 是 | 仓库名称 |
| `remote_url` | string | 否 | Git 远程 URL |
| `workspace_relpath` | string | 是 | 相对路径 |
| `role` | string | 否 | 仓库角色,默认 `code` |
| `is_writable` | boolean | 否 | 是否可写,默认 `true` |
| `default_branch` | string | 否 | 默认分支,默认 `main` |
| `auth_profile` | string | 否 | 认证配置名称 |
| `created_at` | datetime | 是 | 创建时间 (ISO 8601) |
| `updated_at` | datetime | 是 | 更新时间 (ISO 8601) |
| `metadata` | object | 否 | 扩展元数据 |

### RepoRole 枚举

| 值 | 描述 |
|----|------|
| `code` | 代码仓库 (默认) |
| `docs` | 文档仓库 |
| `infra` | 基础设施仓库 |
| `mono-subdir` | Monorepo 子目录 |

---

## 错误响应格式

所有 API 端点在出错时返回统一的错误格式:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**HTTP 状态码**:
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 使用示例

### 完整工作流示例

#### 1. 创建项目

```bash
# 创建项目
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-Commerce Platform",
    "description": "电商平台全栈项目",
    "tags": ["python", "react"],
    "settings": {
      "default_runner": "llama.cpp",
      "env_overrides": {
        "DEBUG": "true"
      }
    }
  }'

# 响应:
# {
#   "project_id": "proj-01HX123ABC",
#   "name": "E-Commerce Platform",
#   ...
# }
```

#### 2. 添加仓库

```bash
# 添加 backend 仓库
curl -X POST http://localhost:8000/api/projects/proj-01HX123ABC/repos \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backend",
    "workspace_relpath": "./backend",
    "remote_url": "https://github.com/org/backend.git"
  }'

# 添加 frontend 仓库
curl -X POST http://localhost:8000/api/projects/proj-01HX123ABC/repos \
  -H "Content-Type: application/json" \
  -d '{
    "name": "frontend",
    "workspace_relpath": "./frontend",
    "remote_url": "https://github.com/org/frontend.git"
  }'
```

#### 3. 查看项目详情

```bash
# 获取项目详情 (包含所有仓库)
curl http://localhost:8000/api/projects/proj-01HX123ABC
```

#### 4. 更新项目配置

```bash
# 修改项目配置
curl -X PATCH http://localhost:8000/api/projects/proj-01HX123ABC \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "env_overrides": {
        "DEBUG": "false",
        "LOG_LEVEL": "info"
      }
    }
  }'
```

#### 5. 归档项目

```bash
# 归档项目
curl -X POST http://localhost:8000/api/projects/proj-01HX123ABC/archive
```

### Python 客户端示例

```python
import requests

BASE_URL = "http://localhost:8000/api"

# 创建项目
def create_project(name, description, tags):
    response = requests.post(
        f"{BASE_URL}/projects",
        json={
            "name": name,
            "description": description,
            "tags": tags,
            "settings": {
                "default_runner": "llama.cpp",
                "env_overrides": {"DEBUG": "true"}
            }
        }
    )
    return response.json()

# 添加仓库
def add_repo(project_id, name, path, remote_url):
    response = requests.post(
        f"{BASE_URL}/projects/{project_id}/repos",
        json={
            "name": name,
            "workspace_relpath": path,
            "remote_url": remote_url
        }
    )
    return response.json()

# 获取项目
def get_project(project_id):
    response = requests.get(f"{BASE_URL}/projects/{project_id}")
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 创建项目
    project = create_project(
        name="Test Project",
        description="测试项目",
        tags=["test", "demo"]
    )
    print(f"Created project: {project['project_id']}")

    # 添加仓库
    repo = add_repo(
        project_id=project["project_id"],
        name="backend",
        path="./backend",
        remote_url="https://github.com/org/backend.git"
    )
    print(f"Added repo: {repo['repo_id']}")

    # 获取项目详情
    details = get_project(project["project_id"])
    print(f"Project has {len(details['repos'])} repositories")
```

---

## 相关链接

- [Projects 用户指南](../projects.md)
- [Projects 架构文档](../dev/projects-architecture.md)
- [Task API 参考](./TASK_API_REFERENCE.md)
- [Multi-Repository Projects](../projects/MULTI_REPO_PROJECTS.md)

---

**问题或反馈?**

- 🐛 [报告问题](https://github.com/seacow-technology/agentos/issues)
- 💡 [API 改进建议](https://github.com/seacow-technology/agentos/discussions)
- 📖 [查看更多文档](../index.md)
