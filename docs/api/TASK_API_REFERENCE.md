# Task API 参考文档

**版本**: 1.0
**端点**: `/api/tasks`
**最后更新**: 2026-01-29

---

## 概述

Task API 提供了创建、查询和管理任务的 RESTful 接口。本文档详细说明了 `POST /api/tasks` 端点的使用方法。

---

## POST /api/tasks

创建新任务。

### 端点信息

```
POST /api/tasks
Content-Type: application/json
```

### 速率限制

| 时间窗口 | 限制 | 响应码 |
|----------|------|--------|
| 每分钟 | 10 次 | 429 |
| 每小时 | 100 次 | 429 |

**配置**: 可通过环境变量调整
- `RATE_LIMIT_PER_MINUTE` (默认: 10)
- `RATE_LIMIT_PER_HOUR` (默认: 100)

---

## 请求参数

### Body Parameters

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `title` | string | ✅ 是 | 任务标题，1-500 字符 |
| `created_by` | string | ❌ 否 | 创建者标识（邮箱、用户名等）|
| `metadata` | object | ❌ 否 | 附加元数据（JSON 对象）|
| `session_id` | string | ⛔ 禁止 | 不要提供此字段，由后端自动生成 |

### 参数详细说明

#### title (必填)

**类型**: `string`

**约束**:
- 长度: 1-500 字符
- 不能为空或只包含空格
- 前后空格会被自动去除

**示例**:
```json
{"title": "实现用户登录功能"}
```

**验证规则**:
```python
@field_validator('title')
def validate_title(cls, v: str) -> str:
    if not v.strip():
        raise ValueError("Title cannot be empty or contain only whitespace")
    return v.strip()
```

#### created_by (可选)

**类型**: `string`

**说明**: 创建者的标识信息，用于审计和追踪

**示例**:
```json
{"created_by": "user@example.com"}
{"created_by": "张三"}
{"created_by": "user-12345"}
```

#### metadata (可选)

**类型**: `object` (JSON)

**说明**: 任意结构的 JSON 对象，用于存储自定义字段

**支持的数据类型**:
- 字符串、数字、布尔值
- 数组
- 嵌套对象
- `null`

**示例**:
```json
{
  "metadata": {
    "priority": "high",
    "tags": ["feature", "auth"],
    "deadline": "2026-02-15",
    "estimated_hours": 8,
    "team": "backend",
    "technical_details": {
      "framework": "FastAPI",
      "database": "PostgreSQL"
    }
  }
}
```

#### session_id (禁止提供)

⚠️ **重要**: 不要在请求中提供 `session_id` 字段！

**原因**:
- Session ID 由后端自动生成
- 手动提供可能导致 FOREIGN KEY 约束错误
- 格式: `auto_{task_id}_{timestamp}`

---

## 响应

### 成功响应 (HTTP 200)

```json
{
  "task_id": "01KG46KY4ACPDJY92ZASQ377YW",
  "title": "实现用户登录功能",
  "status": "draft",
  "session_id": "auto_01KG46KY_1769667688",
  "created_by": "user@example.com",
  "created_at": "2026-01-29T06:21:28.587018+00:00",
  "updated_at": null,
  "metadata": {
    "priority": "high",
    "tags": ["feature", "auth"]
  }
}
```

#### 响应字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `task_id` | string | 任务 ID (ULID 格式) |
| `title` | string | 任务标题 |
| `status` | string | 任务状态（新任务为 `draft`）|
| `session_id` | string | 自动生成的会话 ID |
| `created_by` | string\|null | 创建者标识 |
| `created_at` | string | 创建时间 (ISO 8601 格式) |
| `updated_at` | string\|null | 更新时间 |
| `metadata` | object | 元数据 |

---

### 错误响应

#### 422 Unprocessable Entity - 参数验证失败

**场景 1: Title 为空**

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "title"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {"min_length": 1}
    }
  ]
}
```

**场景 2: Title 超过长度限制**

```json
{
  "detail": [
    {
      "type": "string_too_long",
      "loc": ["body", "title"],
      "msg": "String should have at most 500 characters",
      "input": "很长很长的标题...",
      "ctx": {"max_length": 500}
    }
  ]
}
```

**场景 3: Title 只包含空格**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "title"],
      "msg": "Value error, Title cannot be empty or contain only whitespace",
      "input": "   "
    }
  ]
}
```

#### 429 Too Many Requests - 速率限制

**场景 1: 每分钟限制**

```json
{
  "detail": "Rate limit exceeded: 10 per 1 minute"
}
```

**响应头**:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1706515288
Retry-After: 45
```

**场景 2: 每小时限制**

```json
{
  "detail": "Rate limit exceeded: 100 per 1 hour"
}
```

#### 500 Internal Server Error - 服务器错误

```json
{
  "detail": "Internal server error"
}
```

**可能原因**:
- 数据库连接失败
- 服务内部异常
- 配置错误

---

## 使用示例

### cURL

#### 基本示例

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "实现用户登录功能"
  }'
```

#### 完整示例

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "重构支付模块",
    "created_by": "dev-team@example.com",
    "metadata": {
      "priority": "high",
      "tags": ["refactor", "payment"],
      "deadline": "2026-02-15",
      "estimated_hours": 16
    }
  }'
```

#### 带详细输出

```bash
curl -v -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试任务"
  }'
```

---

### Python

#### 使用 requests 库

```python
import requests

API_BASE = "http://localhost:8000"

def create_task(title, created_by=None, metadata=None):
    """创建任务"""
    url = f"{API_BASE}/api/tasks"
    payload = {"title": title}

    if created_by:
        payload["created_by"] = created_by
    if metadata:
        payload["metadata"] = metadata

    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

# 使用示例
try:
    task = create_task(
        title="实现用户认证",
        created_by="dev@example.com",
        metadata={"priority": "high"}
    )
    print(f"任务创建成功: {task['task_id']}")
except requests.exceptions.HTTPError as e:
    print(f"创建失败: {e.response.status_code}")
    print(e.response.json())
```

#### 使用 httpx (async)

```python
import httpx
import asyncio

async def create_task_async(title, created_by=None, metadata=None):
    """异步创建任务"""
    url = "http://localhost:8000/api/tasks"
    payload = {"title": title}

    if created_by:
        payload["created_by"] = created_by
    if metadata:
        payload["metadata"] = metadata

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

# 使用示例
async def main():
    task = await create_task_async(
        title="测试异步任务",
        created_by="async-user@example.com"
    )
    print(f"任务创建成功: {task['task_id']}")

asyncio.run(main())
```

---

### JavaScript/TypeScript

#### 使用 fetch

```javascript
async function createTask(title, createdBy, metadata) {
  const response = await fetch('http://localhost:8000/api/tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title,
      created_by: createdBy,
      metadata,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create task');
  }

  return response.json();
}

// 使用示例
createTask(
  '实现支付功能',
  'user@example.com',
  { priority: 'high', tags: ['feature'] }
)
  .then(task => console.log('任务创建成功:', task.task_id))
  .catch(error => console.error('创建失败:', error.message));
```

#### TypeScript 类型定义

```typescript
interface TaskCreateRequest {
  title: string;
  created_by?: string;
  metadata?: Record<string, any>;
}

interface Task {
  task_id: string;
  title: string;
  status: string;
  session_id: string;
  created_by?: string;
  created_at: string;
  updated_at?: string;
  metadata?: Record<string, any>;
}

async function createTask(request: TaskCreateRequest): Promise<Task> {
  const response = await fetch('/api/tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create task');
  }

  return response.json();
}
```

---

### 批量创建

#### Bash 脚本

```bash
#!/bin/bash

API_BASE="http://localhost:8000"

# 批量创建任务（注意速率限制）
for i in {1..5}; do
  echo "创建任务 $i..."

  curl -X POST "$API_BASE/api/tasks" \
    -H "Content-Type: application/json" \
    -d "{
      \"title\": \"批量任务 $i\",
      \"created_by\": \"batch-script\",
      \"metadata\": {\"batch_id\": \"batch-001\", \"index\": $i}
    }"

  echo ""

  # 避免速率限制（每分钟 10 个）
  sleep 6
done
```

#### Python 脚本

```python
import requests
import time

API_BASE = "http://localhost:8000"

def batch_create_tasks(task_titles, created_by="batch-script"):
    """批量创建任务"""
    results = []

    for i, title in enumerate(task_titles, 1):
        try:
            response = requests.post(
                f"{API_BASE}/api/tasks",
                json={
                    "title": title,
                    "created_by": created_by,
                    "metadata": {"batch_id": "batch-001", "index": i}
                }
            )
            response.raise_for_status()
            task = response.json()
            results.append({"success": True, "task_id": task["task_id"]})
            print(f"✅ 任务 {i} 创建成功: {task['task_id']}")
        except Exception as e:
            results.append({"success": False, "error": str(e)})
            print(f"❌ 任务 {i} 创建失败: {e}")

        # 避免速率限制（每分钟 10 个）
        if i < len(task_titles):
            time.sleep(6)

    return results

# 使用示例
tasks = [
    "实现用户注册",
    "实现用户登录",
    "实现密码重置",
    "实现邮箱验证",
    "实现双因素认证",
]

results = batch_create_tasks(tasks)
print(f"\n成功: {sum(1 for r in results if r['success'])}/{len(results)}")
```

---

## 错误处理

### 推荐的错误处理模式

#### Python

```python
import requests
from requests.exceptions import HTTPError, RequestException

def create_task_safe(title, **kwargs):
    """安全的任务创建（带完整错误处理）"""
    try:
        response = requests.post(
            "http://localhost:8000/api/tasks",
            json={"title": title, **kwargs},
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "task": response.json()}

    except HTTPError as e:
        status_code = e.response.status_code

        if status_code == 422:
            # 参数验证失败
            details = e.response.json()
            return {
                "success": False,
                "error": "validation_error",
                "message": "参数验证失败",
                "details": details
            }

        elif status_code == 429:
            # 速率限制
            retry_after = e.response.headers.get('Retry-After', '60')
            return {
                "success": False,
                "error": "rate_limit",
                "message": "超出速率限制",
                "retry_after": int(retry_after)
            }

        elif status_code == 500:
            # 服务器错误
            return {
                "success": False,
                "error": "server_error",
                "message": "服务器内部错误"
            }

        else:
            return {
                "success": False,
                "error": "http_error",
                "message": f"HTTP {status_code}",
                "details": e.response.text
            }

    except RequestException as e:
        # 网络错误
        return {
            "success": False,
            "error": "network_error",
            "message": "网络连接失败",
            "details": str(e)
        }

# 使用示例
result = create_task_safe(
    title="测试任务",
    created_by="test@example.com"
)

if result["success"]:
    print(f"✅ 成功: {result['task']['task_id']}")
else:
    print(f"❌ 失败: {result['message']}")
    if "retry_after" in result:
        print(f"   请在 {result['retry_after']} 秒后重试")
```

#### JavaScript

```javascript
class TaskAPIError extends Error {
  constructor(message, code, details) {
    super(message);
    this.name = 'TaskAPIError';
    this.code = code;
    this.details = details;
  }
}

async function createTaskSafe(title, createdBy, metadata) {
  try {
    const response = await fetch('http://localhost:8000/api/tasks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title,
        created_by: createdBy,
        metadata,
      }),
    });

    if (!response.ok) {
      const error = await response.json();

      if (response.status === 422) {
        throw new TaskAPIError(
          '参数验证失败',
          'VALIDATION_ERROR',
          error.detail
        );
      } else if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After') || '60';
        throw new TaskAPIError(
          `超出速率限制，请在 ${retryAfter} 秒后重试`,
          'RATE_LIMIT',
          { retry_after: parseInt(retryAfter) }
        );
      } else if (response.status === 500) {
        throw new TaskAPIError(
          '服务器内部错误',
          'SERVER_ERROR',
          error.detail
        );
      } else {
        throw new TaskAPIError(
          error.detail || 'Unknown error',
          'HTTP_ERROR',
          { status: response.status }
        );
      }
    }

    return await response.json();

  } catch (error) {
    if (error instanceof TaskAPIError) {
      throw error;
    } else {
      throw new TaskAPIError(
        '网络连接失败',
        'NETWORK_ERROR',
        { original: error.message }
      );
    }
  }
}

// 使用示例
try {
  const task = await createTaskSafe(
    '测试任务',
    'test@example.com',
    { priority: 'high' }
  );
  console.log('✅ 成功:', task.task_id);
} catch (error) {
  console.error('❌ 失败:', error.message);
  console.error('   错误码:', error.code);
  if (error.details) {
    console.error('   详情:', error.details);
  }
}
```

---

## 审计日志

所有任务创建操作会自动记录到审计日志表 `task_audits`。

### 审计记录结构

```json
{
  "task_id": "01KG46KY4ACPDJY92ZASQ377YW",
  "operation": "post",
  "event_type": "task_created",
  "status": "success",
  "level": "info",
  "payload": {
    "method": "POST",
    "path": "/api/tasks",
    "status_code": 200,
    "duration_ms": 45,
    "title": "实现用户登录功能",
    "created_by": "user@example.com"
  },
  "created_at": "2026-01-29T06:21:28.587018+00:00"
}
```

### 查询审计日志

```sql
-- 查看最近创建的任务
SELECT * FROM task_audits
WHERE event_type = 'task_created'
ORDER BY created_at DESC
LIMIT 10;

-- 统计每小时的任务创建数
SELECT
  strftime('%Y-%m-%d %H:00', created_at) as hour,
  COUNT(*) as count
FROM task_audits
WHERE event_type = 'task_created'
  AND created_at > datetime('now', '-24 hours')
GROUP BY hour
ORDER BY hour DESC;

-- 查看失败的创建尝试
SELECT * FROM task_audits
WHERE event_type = 'task_created'
  AND status = 'failed'
ORDER BY created_at DESC;
```

---

## 性能考虑

### 响应时间

典型响应时间:
- P50: < 50ms
- P95: < 100ms
- P99: < 200ms

### 并发限制

- 单实例建议并发: 100 请求/秒
- 数据库连接池: 20 连接
- 速率限制: 10 请求/分钟/IP

### 优化建议

1. **批量创建**: 避免短时间内大量单个请求
2. **错误重试**: 实现指数退避重试策略
3. **超时设置**: 建议设置 10 秒超时
4. **连接复用**: 使用 HTTP keep-alive

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-29 | 初始版本，支持任务创建 |

---

## 相关文档

- [Task Management 用户指南](../guides/user/TASK_MANAGEMENT_GUIDE.md)
- [API Contract](../../agentos/webui/api/API_CONTRACT_README.md)
- [审计日志文档](../task/audit_trail.md)

---

## 支持与反馈

- 🐛 Bug 报告: [GitHub Issues](https://github.com/seacow-technology/agentos/issues)
- 💡 功能建议: [GitHub Discussions](https://github.com/seacow-technology/agentos/discussions)
- 📧 邮件支持: support@agentos.dev

---

**维护者**: AgentOS API Team
**最后更新**: 2026-01-29
