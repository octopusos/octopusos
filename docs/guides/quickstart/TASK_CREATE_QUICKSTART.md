# Task Create 快速入门

**目标**: 5 分钟内学会创建任务

---

## 启动 WebUI

```bash
cd /Users/pangge/PycharmProjects/AgentOS
agentos --web
```

访问: `http://localhost:8000`

---

## 方式 1: Web UI (最简单)

### 步骤 1: 打开 Tasks 页面

导航: **Tasks** 或访问 `http://localhost:8000/tasks`

### 步骤 2: 点击 "Create Task"

页面右上角的橙色按钮

### 步骤 3: 填写表单

**必填**:
- Title: "我的第一个任务"

**可选**:
- Created By: "test@example.com"
- Metadata: `{"priority": "high"}`

### 步骤 4: 提交

点击 "Create Task" → 成功提示 → 任务出现在列表中

---

## 方式 2: API (快速脚本)

### 最简示例

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "我的第一个任务"}'
```

### 完整示例

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "实现用户登录",
    "created_by": "dev@example.com",
    "metadata": {
      "priority": "high",
      "tags": ["feature", "auth"]
    }
  }'
```

---

## 常见场景

### 场景 1: 创建 Bug 修复任务

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "修复登录页面 500 错误",
    "created_by": "qa@example.com",
    "metadata": {
      "type": "bug",
      "priority": "urgent",
      "affected_users": 1200
    }
  }'
```

### 场景 2: 创建功能开发任务

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "实现支付功能",
    "created_by": "pm@example.com",
    "metadata": {
      "type": "feature",
      "priority": "high",
      "sprint": "Sprint-2026-W05",
      "estimated_hours": 40
    }
  }'
```

### 场景 3: 创建重构任务

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "重构数据库查询层",
    "created_by": "tech-lead@example.com",
    "metadata": {
      "type": "refactor",
      "priority": "medium",
      "tech_debt_score": 8
    }
  }'
```

---

## 验证任务创建

### 查看响应

成功响应示例:
```json
{
  "task_id": "01KG46KY4ACPDJY92ZASQ377YW",
  "title": "我的第一个任务",
  "status": "draft",
  "session_id": "auto_01KG46KY_1769667688",
  "created_at": "2026-01-29T06:21:28.587018+00:00"
}
```

### 关键字段

- `task_id`: 任务唯一标识
- `status`: 初始状态为 `draft`
- `session_id`: 自动生成，格式 `auto_{task_id}_{timestamp}`

---

## 常见错误

### 错误 1: Title 为空

```bash
# ❌ 错误
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": ""}'

# 响应: 422 Unprocessable Entity
```

**解决**: 提供非空 title

```bash
# ✅ 正确
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "有效的标题"}'
```

### 错误 2: 超出速率限制

```bash
# 连续创建 15 个任务
for i in {1..15}; do
  curl -X POST http://localhost:8000/api/tasks \
    -H "Content-Type: application/json" \
    -d "{\"title\": \"任务 $i\"}"
done

# 第 11 个请求开始返回: 429 Too Many Requests
```

**解决**: 添加延迟

```bash
# ✅ 正确
for i in {1..15}; do
  curl -X POST http://localhost:8000/api/tasks \
    -H "Content-Type: application/json" \
    -d "{\"title\": \"任务 $i\"}"
  sleep 6  # 每分钟最多 10 个请求
done
```

### 错误 3: 手动提供 session_id

```bash
# ❌ 错误
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试任务",
    "session_id": "my-session"
  }'

# 可能导致: FOREIGN KEY constraint failed
```

**解决**: 移除 session_id 字段

```bash
# ✅ 正确
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "测试任务"}'
```

---

## Python 快速示例

```python
import requests

def create_task(title, created_by=None, **metadata):
    """创建任务的便捷函数"""
    payload = {"title": title}
    if created_by:
        payload["created_by"] = created_by
    if metadata:
        payload["metadata"] = metadata

    response = requests.post(
        "http://localhost:8000/api/tasks",
        json=payload
    )
    response.raise_for_status()
    return response.json()

# 使用示例
task = create_task(
    title="实现用户认证",
    created_by="dev@example.com",
    priority="high",
    tags=["feature", "auth"]
)

print(f"✅ 任务已创建: {task['task_id']}")
```

---

## JavaScript 快速示例

```javascript
async function createTask(title, createdBy, metadata) {
  const response = await fetch('http://localhost:8000/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, created_by: createdBy, metadata }),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json();
}

// 使用示例
const task = await createTask(
  '实现支付功能',
  'user@example.com',
  { priority: 'high', tags: ['feature'] }
);

console.log('✅ 任务已创建:', task.task_id);
```

---

## 下一步

- 📖 [完整用户指南](../user/TASK_MANAGEMENT_GUIDE.md)
- 📖 [API 参考文档](../../api/TASK_API_REFERENCE.md)
- 📖 [错误处理最佳实践](../user/TASK_MANAGEMENT_GUIDE.md#错误处理最佳实践)

---

## 快速参考

### 速率限制
- 每分钟: 10 次
- 每小时: 100 次

### 必填字段
- `title` (1-500 字符)

### 可选字段
- `created_by` (字符串)
- `metadata` (JSON 对象)

### 禁止字段
- `session_id` (自动生成)

---

**🎉 开始创建你的第一个任务吧！**
