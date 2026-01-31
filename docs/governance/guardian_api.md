# Guardian API 使用指南

## API 概览

Guardian 提供以下 REST API 端点：

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/guardian/reviews` | 创建验收记录 |
| GET | `/api/guardian/reviews` | 查询验收记录列表 |
| GET | `/api/guardian/reviews/{review_id}` | 获取单个验收记录 |
| GET | `/api/guardian/statistics` | 获取统计数据 |
| GET | `/api/guardian/targets/{target_type}/{target_id}/reviews` | 获取目标的所有验收记录 |
| GET | `/api/guardian/targets/{target_type}/{target_id}/verdict` | 获取目标的验收摘要 |

## 创建验收记录

### POST /api/guardian/reviews

创建一个新的 Guardian 验收审查记录。

#### 请求参数

```json
{
  "target_type": "task",           // 必需: task | decision | finding
  "target_id": "task_123",         // 必需: 目标 ID
  "guardian_id": "guardian.v1",    // 必需: Guardian ID
  "review_type": "AUTO",           // 必需: AUTO | MANUAL
  "verdict": "PASS",               // 必需: PASS | FAIL | NEEDS_REVIEW
  "confidence": 0.92,              // 必需: 0.0 - 1.0
  "rule_snapshot_id": "rule:v1@sha256:abc",  // 可选: 规则快照 ID
  "evidence": {                    // 必需: 验收证据
    "checks": ["all_pass"],
    "metrics": {"coverage": 0.85}
  }
}
```

#### 请求示例

```bash
curl -X POST "http://localhost:8080/api/guardian/reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "target_type": "task",
    "target_id": "task_123",
    "guardian_id": "guardian.security.v1",
    "review_type": "AUTO",
    "verdict": "PASS",
    "confidence": 0.95,
    "rule_snapshot_id": "security:v2.1@sha256:abc123",
    "evidence": {
      "checks": ["no_secrets", "dependency_scan_clean"],
      "scan_id": "scan_12345",
      "timestamp": "2026-01-29T10:00:00Z"
    }
  }'
```

#### 响应示例

```json
{
  "review_id": "review_a1b2c3d4e5f6",
  "status": "created"
}
```

#### 状态码

- `201 Created` - 创建成功
- `400 Bad Request` - 参数无效
- `422 Unprocessable Entity` - 请求格式错误
- `500 Internal Server Error` - 服务器错误

---

## 查询验收记录列表

### GET /api/guardian/reviews

查询验收记录列表，支持多维度过滤。

#### 查询参数

| 参数 | 类型 | 描述 | 默认值 |
|------|------|------|--------|
| `target_type` | string | 过滤目标类型 | - |
| `target_id` | string | 过滤目标 ID | - |
| `guardian_id` | string | 过滤 Guardian ID | - |
| `verdict` | string | 过滤验收结论 | - |
| `limit` | integer | 结果数量限制 (1-500) | 100 |

#### 请求示例

```bash
# 查询所有 FAIL 的记录
curl "http://localhost:8080/api/guardian/reviews?verdict=FAIL"

# 查询某个任务的所有记录
curl "http://localhost:8080/api/guardian/reviews?target_type=task&target_id=task_123"

# 查询某个 Guardian 的所有记录
curl "http://localhost:8080/api/guardian/reviews?guardian_id=guardian.security.v1"

# 组合过滤条件
curl "http://localhost:8080/api/guardian/reviews?target_type=task&verdict=PASS&limit=50"
```

#### 响应示例

```json
{
  "reviews": [
    {
      "review_id": "review_abc123",
      "target_type": "task",
      "target_id": "task_123",
      "guardian_id": "guardian.security.v1",
      "review_type": "AUTO",
      "verdict": "PASS",
      "confidence": 0.95,
      "rule_snapshot_id": "security:v2.1@sha256:abc123",
      "evidence": {
        "checks": ["all_pass"],
        "metrics": {"coverage": 0.85}
      },
      "created_at": "2026-01-29T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

## 获取单个验收记录

### GET /api/guardian/reviews/{review_id}

根据 ID 获取单个验收记录的详细信息。

#### 请求示例

```bash
curl "http://localhost:8080/api/guardian/reviews/review_abc123"
```

#### 响应示例

```json
{
  "review_id": "review_abc123",
  "target_type": "task",
  "target_id": "task_123",
  "guardian_id": "guardian.security.v1",
  "review_type": "AUTO",
  "verdict": "PASS",
  "confidence": 0.95,
  "rule_snapshot_id": "security:v2.1@sha256:abc123",
  "evidence": {
    "checks": ["all_pass"],
    "metrics": {"coverage": 0.85}
  },
  "created_at": "2026-01-29T10:00:00Z"
}
```

#### 状态码

- `200 OK` - 查询成功
- `404 Not Found` - 记录不存在
- `500 Internal Server Error` - 服务器错误

---

## 获取统计数据

### GET /api/guardian/statistics

获取 Guardian 系统的统计数据，包括通过率、Guardian 活跃度等。

#### 查询参数

| 参数 | 类型 | 描述 | 默认值 |
|------|------|------|--------|
| `target_type` | string | 过滤目标类型 | - |
| `since_hours` | integer | 统计最近 N 小时 | - |

#### 请求示例

```bash
# 获取所有时间的统计
curl "http://localhost:8080/api/guardian/statistics"

# 获取最近 24 小时的统计
curl "http://localhost:8080/api/guardian/statistics?since_hours=24"

# 获取任务类型的统计
curl "http://localhost:8080/api/guardian/statistics?target_type=task"
```

#### 响应示例

```json
{
  "total_reviews": 150,
  "pass_rate": 0.85,
  "guardians": {
    "guardian.security.v1": 50,
    "guardian.quality.v1": 45,
    "human.alice": 30,
    "human.bob": 25
  },
  "by_verdict": {
    "PASS": 128,
    "FAIL": 15,
    "NEEDS_REVIEW": 7
  },
  "by_target_type": {
    "task": 120,
    "decision": 20,
    "finding": 10
  }
}
```

---

## 获取目标的所有验收记录

### GET /api/guardian/targets/{target_type}/{target_id}/reviews

获取特定目标（task/decision/finding）的完整审查历史。

#### 路径参数

- `target_type` - 目标类型: `task` | `decision` | `finding`
- `target_id` - 目标 ID

#### 请求示例

```bash
# 获取任务的所有验收记录
curl "http://localhost:8080/api/guardian/targets/task/task_123/reviews"

# 获取决策的所有验收记录
curl "http://localhost:8080/api/guardian/targets/decision/dec_456/reviews"
```

#### 响应示例

```json
{
  "reviews": [
    {
      "review_id": "review_xyz789",
      "target_type": "task",
      "target_id": "task_123",
      "guardian_id": "human.alice",
      "review_type": "MANUAL",
      "verdict": "PASS",
      "confidence": 1.0,
      "rule_snapshot_id": null,
      "evidence": {
        "reviewer": "alice",
        "notes": "Approved"
      },
      "created_at": "2026-01-29T11:00:00Z"
    },
    {
      "review_id": "review_abc123",
      "target_type": "task",
      "target_id": "task_123",
      "guardian_id": "guardian.security.v1",
      "review_type": "AUTO",
      "verdict": "PASS",
      "confidence": 0.95,
      "rule_snapshot_id": "security:v2.1@sha256:abc123",
      "evidence": {
        "checks": ["all_pass"]
      },
      "created_at": "2026-01-29T10:00:00Z"
    }
  ],
  "total": 2
}
```

---

## 获取目标的验收摘要

### GET /api/guardian/targets/{target_type}/{target_id}/verdict

获取目标的验收结论快速概览。

#### 路径参数

- `target_type` - 目标类型: `task` | `decision` | `finding`
- `target_id` - 目标 ID

#### 请求示例

```bash
curl "http://localhost:8080/api/guardian/targets/task/task_123/verdict"
```

#### 响应示例

```json
{
  "target_type": "task",
  "target_id": "task_123",
  "total_reviews": 3,
  "latest_verdict": "PASS",
  "latest_review_id": "review_xyz789",
  "latest_guardian_id": "human.alice",
  "all_verdicts": ["PASS", "PASS", "NEEDS_REVIEW"]
}
```

---

## 使用 Python SDK

Guardian 提供 Python SDK，简化 API 调用。

### 安装

```bash
pip install agentos
```

### 初始化服务

```python
from agentos.core.guardian import GuardianService

# 创建服务实例（使用系统默认数据库）
guardian_service = GuardianService()

# 或指定数据库路径
from pathlib import Path
guardian_service = GuardianService(db_path=Path("/path/to/db.sqlite"))
```

### 创建验收记录

```python
# 创建自动验收记录
review = guardian_service.create_review(
    target_type="task",
    target_id="task_123",
    guardian_id="guardian.security.v1",
    review_type="AUTO",
    verdict="PASS",
    confidence=0.95,
    evidence={
        "checks": ["no_secrets", "dependency_scan_clean"],
        "scan_id": "scan_12345"
    },
    rule_snapshot_id="security:v2.1@sha256:abc123"
)

print(f"Created review: {review.review_id}")

# 创建人工验收记录
review = guardian_service.create_review(
    target_type="task",
    target_id="task_123",
    guardian_id="human.alice",
    review_type="MANUAL",
    verdict="PASS",
    confidence=1.0,
    evidence={
        "reviewer": "alice",
        "notes": "Code looks good"
    }
)
```

### 查询验收记录

```python
# 获取单个记录
review = guardian_service.get_review("review_abc123")
if review:
    print(f"Verdict: {review.verdict}")

# 查询列表（支持过滤）
reviews = guardian_service.list_reviews(
    target_type="task",
    verdict="PASS",
    limit=50
)

for review in reviews:
    print(f"{review.guardian_id}: {review.verdict}")

# 获取目标的所有记录
reviews = guardian_service.get_reviews_by_target("task", "task_123")
print(f"Total reviews: {len(reviews)}")

# 获取验收摘要
summary = guardian_service.get_verdict_summary("task", "task_123")
print(f"Latest verdict: {summary['latest_verdict']}")
```

### 统计分析

```python
# 获取整体统计
stats = guardian_service.get_statistics()
print(f"Total reviews: {stats['total_reviews']}")
print(f"Pass rate: {stats['pass_rate']:.2%}")

# 按目标类型统计
task_stats = guardian_service.get_statistics(target_type="task")
print(f"Task reviews: {task_stats['total_reviews']}")

# 获取最近 7 天的统计
from datetime import datetime, timedelta, timezone
since = datetime.now(timezone.utc) - timedelta(days=7)
recent_stats = guardian_service.get_statistics(since=since)
print(f"Recent pass rate: {recent_stats['pass_rate']:.2%}")
```

---

## 错误处理

### 常见错误码

| 状态码 | 描述 | 处理建议 |
|--------|------|----------|
| 400 | 参数无效 | 检查请求参数是否符合规范 |
| 404 | 资源不存在 | 确认 review_id 是否正确 |
| 422 | 请求格式错误 | 检查 JSON 格式和字段类型 |
| 500 | 服务器错误 | 查看服务器日志，联系管理员 |

### 错误响应格式

```json
{
  "detail": "Invalid target_type: invalid. Must be one of: task, decision, finding"
}
```

### Python SDK 错误处理

```python
try:
    review = guardian_service.create_review(
        target_type="invalid",  # Invalid
        target_id="task_123",
        guardian_id="guardian.v1",
        review_type="AUTO",
        verdict="PASS",
        confidence=0.9,
        evidence={}
    )
except ValueError as e:
    print(f"Validation error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## 性能优化建议

### 1. 使用过滤条件

```python
# ❌ 避免：查询所有记录后在应用层过滤
all_reviews = guardian_service.list_reviews()
pass_reviews = [r for r in all_reviews if r.verdict == "PASS"]

# ✅ 推荐：在数据库层过滤
pass_reviews = guardian_service.list_reviews(verdict="PASS")
```

### 2. 合理使用 limit

```python
# 对于大量数据，使用 limit 限制结果数量
reviews = guardian_service.list_reviews(limit=100)
```

### 3. 使用专用端点

```python
# ❌ 避免：使用通用查询
reviews = guardian_service.list_reviews(
    target_type="task",
    target_id="task_123"
)

# ✅ 推荐：使用专用端点（有索引优化）
reviews = guardian_service.get_reviews_by_target("task", "task_123")
```

### 4. 批量查询

```python
# 获取多个目标的 verdict
targets = [("task", "task_1"), ("task", "task_2"), ("task", "task_3")]

for target_type, target_id in targets:
    summary = guardian_service.get_verdict_summary(target_type, target_id)
    print(f"{target_id}: {summary['latest_verdict']}")
```

---

## 鉴权（如适用）

当前 Guardian API 暂不要求鉴权（开发版本）。

生产环境部署时，建议：
1. 启用 API Key 认证
2. 使用 OAuth 2.0
3. 实施 IP 白名单
4. 启用 HTTPS

---

## API 版本管理

当前 API 版本：`v1`

API 端点前缀：`/api/guardian`

版本变更将通过文档和 CHANGELOG 通知。
