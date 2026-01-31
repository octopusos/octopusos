# Task Management 用户指南

**版本**: 1.0
**状态**: Active
**最后更新**: 2026-01-29

---

## 概述

AgentOS Task Management 提供了强大的任务创建、管理和追踪功能。本指南将帮助你快速掌握如何通过 WebUI 和 API 创建和管理任务。

**核心特性**:
- 🎯 简单直观的任务创建界面
- 🔄 自动生成会话 ID，无需手动管理
- 📊 丰富的元数据支持
- 🔒 API 速率限制保护
- 📝 完整的审计日志记录

---

## 快速开始

### 启动 WebUI

```bash
# 启动 AgentOS WebUI
agentos --web

# 或指定端口
agentos --web --port 8000
```

访问: `http://localhost:8000`

---

## 创建任务

### 方式 1: 通过 Web UI 创建（推荐）

1. **打开 Task Management 页面**
   - 在主导航栏点击 "Tasks" 或 "任务管理"
   - 或直接访问 `http://localhost:8000/tasks`

2. **点击 "Create Task" 按钮**
   - 页面右上角的橙色按钮
   - 或使用快捷键 `Ctrl+N` (未来支持)

3. **填写任务信息**

   弹出对话框包含以下字段:

   - **Title（必填）** ⭐
     - 任务的标题或简短描述
     - 长度限制: 1-500 字符
     - 示例: "实现用户登录功能"

   - **Created By（可选）**
     - 创建者的标识信息
     - 可以是邮箱、用户名或任何标识符
     - 示例: "user@example.com" 或 "张三"

   - **Metadata（可选）**
     - JSON 格式的附加信息
     - 支持嵌套对象和数组
     - 用于存储优先级、标签、截止时间等自定义字段

4. **点击 "Create Task" 提交**
   - 系统会自动验证输入
   - 成功后显示绿色通知
   - 任务会立即出现在列表中

5. **查看创建的任务**
   - 新任务默认状态为 `draft`
   - 包含自动生成的 `session_id`
   - 可点击任务查看详情

---

### 方式 2: 通过 REST API 创建

#### 基本示例

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "实现用户认证功能"
  }'
```

#### 完整示例（带所有可选字段）

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
      "estimated_hours": 16,
      "team": "backend",
      "jira_ticket": "PROJ-1234"
    }
  }'
```

#### 响应示例

**成功响应 (HTTP 200)**:
```json
{
  "task_id": "01KG46KY4ACPDJY92ZASQ377YW",
  "title": "重构支付模块",
  "status": "draft",
  "session_id": "auto_01KG46KY_1769667688",
  "created_by": "dev-team@example.com",
  "created_at": "2026-01-29T06:21:28.587018+00:00",
  "updated_at": null,
  "metadata": {
    "priority": "high",
    "tags": ["refactor", "payment"],
    "deadline": "2026-02-15",
    "estimated_hours": 16,
    "team": "backend",
    "jira_ticket": "PROJ-1234"
  }
}
```

**错误响应 (HTTP 422)**:
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

---

## 字段详细说明

### Title（必填）⭐

**说明**: 任务的标题或简短描述

**要求**:
- 必须提供，不能为空
- 长度: 1-500 字符
- 不能只包含空格
- 前后空格会被自动去除

**示例**:
```json
{
  "title": "实现用户登录功能"
}
```

**常见错误**:
```json
// ❌ 错误：空字符串
{"title": ""}

// ❌ 错误：只有空格
{"title": "   "}

// ❌ 错误：超过500字符
{"title": "很长很长很长... (501个字符)"}

// ✅ 正确
{"title": "实现用户登录功能"}
```

---

### Created By（可选）

**说明**: 创建者的标识信息

**用途**:
- 追踪任务创建者
- 用于审计和统计
- 便于团队协作

**格式建议**:
- 邮箱地址: `user@example.com`
- 用户名: `张三` 或 `zhangsan`
- 用户 ID: `user-12345`
- 部门: `backend-team`

**示例**:
```json
{
  "title": "修复登录 bug",
  "created_by": "user@example.com"
}
```

---

### Metadata（可选）

**说明**: JSON 格式的附加信息，用于存储自定义字段

**支持的数据类型**:
- 字符串: `"value"`
- 数字: `42`, `3.14`
- 布尔值: `true`, `false`
- 数组: `["tag1", "tag2"]`
- 嵌套对象: `{"nested": {"field": "value"}}`
- `null` 值

**常用字段建议**:

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `priority` | string | 优先级 | `"high"`, `"medium"`, `"low"` |
| `tags` | array | 标签列表 | `["bug", "urgent"]` |
| `deadline` | string | 截止时间 | `"2026-02-15"` |
| `estimated_hours` | number | 预计工时 | `8` |
| `team` | string | 负责团队 | `"backend"` |
| `status_label` | string | 自定义状态 | `"待审核"` |
| `related_tasks` | array | 关联任务 | `["task-123", "task-456"]` |

**示例**:

```json
{
  "title": "实现支付功能",
  "metadata": {
    "priority": "high",
    "tags": ["feature", "payment"],
    "deadline": "2026-02-28",
    "estimated_hours": 40,
    "team": "backend",
    "epic": "Q1-Payment-System",
    "related_tasks": ["task-001", "task-002"],
    "technical_details": {
      "payment_gateway": "stripe",
      "supported_currencies": ["USD", "EUR", "CNY"],
      "requires_pci_compliance": true
    },
    "stakeholders": [
      {"name": "Alice", "role": "PM"},
      {"name": "Bob", "role": "Tech Lead"}
    ]
  }
}
```

**注意事项**:
- Metadata 是完全可选的，可以为空或省略
- 可以存储任意结构的 JSON 数据
- 没有字段名限制，可以自定义任何字段
- 建议在团队内统一 metadata 字段规范

---

### Session ID（自动生成）🤖

**重要**: **不要在请求中提供 `session_id` 字段！**

**说明**:
- Session ID 由后端自动生成
- 格式: `auto_{task_id}_{timestamp}`
- 例如: `auto_01KG46KY4ACPDJY92ZASQ377YW_1769667688`

**为什么自动生成？**
- 避免外键约束错误
- 保证 ID 唯一性
- 简化客户端逻辑
- 统一 ID 格式

**如果手动提供会怎样？**
```bash
# ❌ 错误示例：手动提供 session_id
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试任务",
    "session_id": "my-custom-session"
  }'

# 可能导致：
# - FOREIGN KEY constraint failed
# - Session not found 错误
# - 任务创建失败
```

**正确做法**: 完全省略 `session_id` 字段，让后端处理。

---

## API 速率限制

为保护系统资源，API 实施了速率限制：

### 限制规则

| 时间窗口 | 最大请求数 | 环境变量 |
|----------|------------|----------|
| 每分钟 | 10 次 | `RATE_LIMIT_PER_MINUTE` |
| 每小时 | 100 次 | `RATE_LIMIT_PER_HOUR` |

### 超出限制时的响应

**HTTP 429 Too Many Requests**:
```json
{
  "detail": "Rate limit exceeded: 10 per 1 minute"
}
```

### 查看剩余配额

响应头包含速率限制信息:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1706515288
```

### 自定义速率限制

可通过环境变量调整限制:

```bash
# 每分钟 20 次
export RATE_LIMIT_PER_MINUTE=20

# 每小时 500 次
export RATE_LIMIT_PER_HOUR=500

# 重启服务生效
agentos --web
```

---

## 常见问题

### Q1: 为什么没有 Session ID 输入框？

**A**: Session ID 由后端自动生成，格式为 `auto_{task_id}_{timestamp}`。这样设计的原因：
- 避免外键约束错误
- 简化用户操作
- 保证 ID 唯一性

### Q2: 创建任务失败，提示速率限制怎么办？

**A**: 系统限制每分钟最多创建 10 个任务。请稍等片刻再试，或联系管理员调整限制。

### Q3: Metadata 支持哪些数据类型？

**A**: Metadata 支持 JSON 的所有数据类型：
- 字符串、数字、布尔值
- 数组和嵌套对象
- `null` 值

### Q4: 如何批量创建任务？

**A**: 目前需要逐个调用 API。未来版本将支持批量创建端点。

示例脚本:
```bash
#!/bin/bash
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/tasks \
    -H "Content-Type: application/json" \
    -d "{\"title\": \"任务 $i\"}"
  sleep 6  # 避免速率限制
done
```

### Q5: 如何修改已创建的任务？

**A**: 使用 PATCH 或 PUT 端点（具体取决于 API 设计）：
```bash
curl -X PATCH http://localhost:8000/api/tasks/{task_id} \
  -H "Content-Type: application/json" \
  -d '{
    "title": "更新后的标题",
    "metadata": {"priority": "urgent"}
  }'
```

### Q6: 任务创建后的初始状态是什么？

**A**: 新创建的任务初始状态为 `draft`（草稿）。需要通过其他操作将任务推进到后续状态。

### Q7: 如何删除任务？

**A**: 使用 DELETE 端点（需要管理员权限）：
```bash
curl -X DELETE http://localhost:8000/api/tasks/{task_id} \
  -H "X-Admin-Token: your-admin-token"
```

### Q8: Metadata 可以为空吗？

**A**: 可以。Metadata 是可选字段，可以省略、设为空对象 `{}` 或 `null`。

---

## 高级用法

### 使用 Python 客户端

```python
import requests

API_BASE = "http://localhost:8000"

def create_task(title, created_by=None, metadata=None):
    """创建任务"""
    payload = {"title": title}
    if created_by:
        payload["created_by"] = created_by
    if metadata:
        payload["metadata"] = metadata

    response = requests.post(
        f"{API_BASE}/api/tasks",
        json=payload
    )
    response.raise_for_status()
    return response.json()

# 使用示例
task = create_task(
    title="实现用户认证",
    created_by="dev@example.com",
    metadata={"priority": "high", "tags": ["feature"]}
)
print(f"任务已创建: {task['task_id']}")
```

### 使用 JavaScript/TypeScript

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
  created_at: string;
  updated_at?: string;
  created_by?: string;
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

// 使用示例
const task = await createTask({
  title: '实现支付功能',
  created_by: 'user@example.com',
  metadata: {
    priority: 'high',
    tags: ['feature', 'payment'],
  },
});
console.log('任务已创建:', task.task_id);
```

### 错误处理最佳实践

```python
import requests
from requests.exceptions import HTTPError

def create_task_safe(title, **kwargs):
    """安全的任务创建（带错误处理）"""
    try:
        payload = {"title": title, **kwargs}
        response = requests.post(
            "http://localhost:8000/api/tasks",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "task": response.json()}

    except HTTPError as e:
        if e.response.status_code == 422:
            return {
                "success": False,
                "error": "验证失败",
                "details": e.response.json()
            }
        elif e.response.status_code == 429:
            return {
                "success": False,
                "error": "速率限制",
                "hint": "请稍后再试"
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}",
                "details": e.response.text
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": "网络错误",
            "details": str(e)
        }

# 使用示例
result = create_task_safe(
    title="测试任务",
    created_by="test@example.com"
)

if result["success"]:
    print(f"成功: {result['task']['task_id']}")
else:
    print(f"失败: {result['error']}")
```

---

## 审计日志

所有任务创建操作会自动记录审计日志。

### 查询审计日志

```sql
-- 查看最近的任务创建记录
SELECT * FROM task_audits
WHERE event_type = 'task_created'
ORDER BY created_at DESC
LIMIT 10;

-- 查看特定任务的所有审计记录
SELECT * FROM task_audits
WHERE task_id = '01KG46KY4ACPDJY92ZASQ377YW'
ORDER BY created_at ASC;

-- 统计每小时的任务创建数
SELECT
  strftime('%Y-%m-%d %H:00', created_at) as hour,
  COUNT(*) as task_count
FROM task_audits
WHERE event_type = 'task_created'
GROUP BY hour
ORDER BY hour DESC;
```

---

## 最佳实践

### 1. Title 命名规范

✅ **推荐**:
- "实现用户登录功能"
- "修复订单列表分页 bug"
- "重构支付模块以支持多币种"

❌ **不推荐**:
- "任务1" (不具描述性)
- "bug" (过于简单)
- "做这个做那个还要做那个还有很多很多事情要做..." (过长)

### 2. Metadata 结构化

建议团队内统一 metadata 字段规范：

```json
{
  "priority": "high|medium|low",
  "tags": ["feature|bug|refactor|test|docs"],
  "team": "backend|frontend|devops|qa",
  "deadline": "YYYY-MM-DD",
  "estimated_hours": 0,
  "epic": "史诗或大功能名称",
  "sprint": "Sprint-2026-W05"
}
```

### 3. 使用 Created By 追踪

为便于追踪和统计，建议始终提供 `created_by`：

```json
{
  "title": "实现功能 X",
  "created_by": "user@example.com"
}
```

### 4. 分阶段创建大型任务

对于复杂任务，建议拆分成多个小任务：

```bash
# 父任务
curl -X POST /api/tasks -d '{
  "title": "实现支付系统",
  "metadata": {"type": "epic"}
}'

# 子任务 1
curl -X POST /api/tasks -d '{
  "title": "集成 Stripe SDK",
  "metadata": {"parent": "task-001", "type": "subtask"}
}'

# 子任务 2
curl -X POST /api/tasks -d '{
  "title": "实现支付回调处理",
  "metadata": {"parent": "task-001", "type": "subtask"}
}'
```

---

## 故障排查

### 问题 1: 创建失败，提示 "Title cannot be empty"

**原因**: Title 字段为空或只包含空格

**解决**:
```json
// ❌ 错误
{"title": ""}
{"title": "   "}

// ✅ 正确
{"title": "实现功能 X"}
```

### 问题 2: HTTP 429 错误

**原因**: 超出速率限制（每分钟 10 次或每小时 100 次）

**解决**:
- 等待 60 秒后重试
- 减少请求频率
- 联系管理员调整限制

### 问题 3: Metadata 格式错误

**原因**: Metadata 不是有效的 JSON 对象

**解决**:
```json
// ❌ 错误：字符串而非对象
{"metadata": "priority: high"}

// ❌ 错误：单引号
{"metadata": {'priority': 'high'}}

// ✅ 正确：双引号的 JSON 对象
{"metadata": {"priority": "high"}}
```

### 问题 4: FOREIGN KEY constraint failed

**原因**: 手动提供了 `session_id`

**解决**: 完全移除 `session_id` 字段，让后端自动生成。

---

## 相关文档

- [API Contract](../../webui/api/API_CONTRACT_README.md) - API 规范
- [任务状态机](../../task/task_state_machine.md) - 任务生命周期
- [审计日志](../../task/audit_trail.md) - 审计追踪
- [WebUI 快速开始](./webui-quickstart.md) - WebUI 使用指南

---

## 反馈与支持

- 🐛 报告 Bug: [GitHub Issues](https://github.com/seacow-technology/agentos/issues)
- 💡 功能建议: [GitHub Discussions](https://github.com/seacow-technology/agentos/discussions)
- 📖 更多文档: `docs/` 目录

---

**版本**: 1.0
**最后更新**: 2026-01-29
**维护者**: AgentOS Team

**🎉 享受使用 AgentOS Task Management！**
