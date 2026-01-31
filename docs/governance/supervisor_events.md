# Supervisor Events 文档

## 概述

本文档定义 Supervisor 的事件契约，包括事件格式、支持的事件类型、事件来源、以及审计事件列表。

## SupervisorEvent 格式

### 数据结构

```python
@dataclass
class SupervisorEvent:
    """
    统一的 Supervisor 事件模型

    无论来自 EventBus 还是 Polling，都映射成这个统一格式。
    这是 Supervisor 的"输入契约"。
    """
    event_id: str                      # 全局唯一 ID（UUID 或 DB ID）
    source: EventSource                # 事件来源（EVENTBUS / POLLING）
    task_id: str                       # 关联的任务 ID
    event_type: str                    # 事件类型
    ts: str                            # ISO 8601 时间戳
    payload: Dict[str, Any]            # 事件载荷（可选字段）
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `event_id` | string | 是 | 全局唯一 ID，用于去重。EventBus 事件使用 UUID，Polling 事件使用数据库 ID |
| `source` | EventSource | 是 | 事件来源：`EVENTBUS`（实时）或 `POLLING`（兜底） |
| `task_id` | string | 是 | 关联的任务 ID，用于追溯和关联 |
| `event_type` | string | 是 | 事件类型，决定路由到哪个 Policy |
| `ts` | string | 是 | ISO 8601 格式的时间戳，如 `2025-01-28T10:30:00Z` |
| `payload` | object | 否 | 事件携带的额外数据，不同事件类型有不同的 payload 结构 |

### 示例

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "eventbus",
  "task_id": "task_abc123",
  "event_type": "TASK_CREATED",
  "ts": "2025-01-28T10:30:00Z",
  "payload": {
    "agent_spec": {
      "name": "my-agent",
      "description": "An example agent"
    },
    "intent_set_path": "/path/to/intent_set.yaml"
  }
}
```

## 事件来源

### EventSource 枚举

```python
class EventSource(str, Enum):
    EVENTBUS = "eventbus"  # 来自 EventBus 的实时事件
    POLLING = "polling"     # 来自 Polling 的兜底事件
```

### EVENTBUS (快路径)

**特点：**
- 实时推送，延迟低（毫秒级）
- 由 EventBus 订阅器接收
- 适合需要快速响应的场景

**转换逻辑：**

```python
@classmethod
def from_eventbus(cls, event: Any) -> "SupervisorEvent":
    """从 EventBus 事件转换"""
    return cls(
        event_id=str(uuid.uuid4()),
        source=EventSource.EVENTBUS,
        task_id=event.entity.id,
        event_type=event.type.value if hasattr(event.type, 'value') else str(event.type),
        ts=event.ts,
        payload=event.payload or {}
    )
```

**EventBus 事件格式：**

```python
# EventBus 原始事件
class Event:
    type: EventType          # 事件类型枚举
    entity: Entity           # 关联实体（如 Task）
    ts: str                  # 时间戳
    payload: Dict[str, Any]  # 载荷
```

### POLLING (慢路径)

**特点：**
- 定时扫描数据库（默认 10 秒间隔）
- 兜底机制，确保不遗漏事件
- 适合不依赖 EventBus 的场景

**转换逻辑：**

```python
@classmethod
def from_db_row(cls, row: Dict[str, Any]) -> "SupervisorEvent":
    """从数据库行转换（用于 Polling）"""
    return cls(
        event_id=str(row.get("audit_id") or row.get("id")),
        source=EventSource.POLLING,
        task_id=row["task_id"],
        event_type=row["event_type"],
        ts=row.get("created_at", datetime.now(timezone.utc).isoformat()),
        payload=row.get("payload", {})
    )
```

**数据库表结构：**

```sql
-- Polling 从 task_audits 表拉取事件
SELECT audit_id, task_id, event_type, payload, created_at
FROM task_audits
WHERE event_type IN (
    'TASK_CREATED',
    'TASK_STEP_COMPLETED',
    'TASK_FAILED',
    'TASK_STATE_CHANGED'
)
AND created_at > ?  -- 上次扫描时间
ORDER BY created_at ASC;
```

### 去重机制

无论来自 EventBus 还是 Polling，事件都会通过 `supervisor_inbox` 表的 `event_id UNIQUE` 约束自动去重。

```python
# InboxManager.insert_event() 中的去重
try:
    cursor.execute(
        """
        INSERT INTO supervisor_inbox (
            event_id, task_id, event_type, source, payload, received_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
        (event.event_id, event.task_id, event.event_type,
         event.source.value, payload_json, now, )
    )
    return True  # 插入成功
except sqlite3.IntegrityError as e:
    if "UNIQUE constraint failed" in str(e):
        return False  # 事件已存在（重复）
```

## 支持的事件类型

### TASK_CREATED

任务创建事件，触发任务创建时的预检。

**触发时机：** 任务被创建时

**Payload 结构：**

```python
{
    "agent_spec": {              # Agent 规范（可选）
        "name": str,
        "description": str,
        "capabilities": List[str],
        # ... 其他 agent 字段
    },
    "command_spec": {            # Command 规范（可选）
        "name": str,
        "command": str,
        "args": List[str],
        # ... 其他 command 字段
    },
    "rule_spec": {               # Rule 规范（可选）
        "name": str,
        "condition": str,
        "action": str,
        # ... 其他 rule 字段
    },
    "intent_set_path": str,      # Intent Set 文件路径（可选）
    "metadata": Dict[str, Any]   # 其他元数据（可选）
}
```

**处理 Policy：** `OnTaskCreatedPolicy`

**可能的决策：**
- `ALLOW` - 通过所有检查，允许继续
- `PAUSE` - 发现中等问题，暂停等待审批
- `BLOCK` - 发现严重问题（如红线违规），阻塞任务

**示例：**

```json
{
  "event_id": "evt_123",
  "source": "eventbus",
  "task_id": "task_abc",
  "event_type": "TASK_CREATED",
  "ts": "2025-01-28T10:30:00Z",
  "payload": {
    "agent_spec": {
      "name": "my-agent",
      "description": "Test agent"
    },
    "intent_set_path": "/workspace/intent_set.yaml"
  }
}
```

### TASK_STEP_COMPLETED

任务步骤完成事件，触发步骤完成后的风险再评估。

**触发时机：** 任务的某个步骤执行完成时

**Payload 结构：**

```python
{
    "step_id": str,                  # 步骤 ID
    "step_name": str,                # 步骤名称（可选）
    "result": {                      # 步骤执行结果
        "status": str,               # 状态（success/failed）
        "output": Any,               # 输出
        "warnings": List[str],       # 警告列表
        "errors": List[str],         # 错误列表
    },
    "risk_indicators": {             # 风险指标（可选）
        "error_rate": float,         # 错误率（0.0-1.0）
        "resource_usage": float,     # 资源使用率（0.0-1.0）
        "security_score": float,     # 安全评分（0-100）
    },
    "run_id": str,                   # Run ID（用于 runtime enforcer 检查）
    "metadata": Dict[str, Any]       # 其他元数据
}
```

**处理 Policy：** `OnStepCompletedPolicy`

**可能的决策：**
- `ALLOW` - 风险可控，允许继续
- `PAUSE` - 检测到风险上升，暂停等待审查

**示例：**

```json
{
  "event_id": "evt_456",
  "source": "eventbus",
  "task_id": "task_abc",
  "event_type": "TASK_STEP_COMPLETED",
  "ts": "2025-01-28T10:35:00Z",
  "payload": {
    "step_id": "step_002",
    "step_name": "execute_command",
    "result": {
      "status": "success",
      "warnings": ["High memory usage detected"]
    },
    "risk_indicators": {
      "error_rate": 0.15,
      "resource_usage": 0.85,
      "security_score": 75
    },
    "run_id": "run_xyz"
  }
}
```

### TASK_FAILED

任务失败事件，触发失败归因和重试决策。

**触发时机：** 任务执行失败时

**Payload 结构：**

```python
{
    "error": str,                    # 错误信息
    "error_code": str,               # 错误代码（可选）
    "error_type": str,               # 错误类型（可选）
    "stack_trace": str,              # 堆栈跟踪（可选）
    "failed_step_id": str,           # 失败的步骤 ID（可选）
    "retry_count": int,              # 当前重试次数（可选）
    "metadata": Dict[str, Any]       # 其他元数据
}
```

**处理 Policy：** `OnTaskFailedPolicy`

**可能的决策：**
- `RETRY` - 可重试的错误，建议重试
- `BLOCK` - 不可重试的错误或已超过最大重试次数，阻塞任务

**错误类型分类：**

**不可重试错误：**
- `redline_violation` - 红线违规
- `permission_denied` - 权限拒绝
- `invalid_config` - 配置无效
- `quota_exceeded` - 配额超限
- `auth_failed` - 认证失败

**可重试错误：**
- `network_timeout` - 网络超时
- `connection_refused` - 连接拒绝
- `rate_limited` - 限流
- `service_unavailable` - 服务不可用
- `temporary_failure` - 临时失败

**示例：**

```json
{
  "event_id": "evt_789",
  "source": "polling",
  "task_id": "task_abc",
  "event_type": "TASK_FAILED",
  "ts": "2025-01-28T10:40:00Z",
  "payload": {
    "error": "Network timeout after 30s",
    "error_type": "network_timeout",
    "error_code": "TIMEOUT_001",
    "failed_step_id": "step_003",
    "retry_count": 1
  }
}
```

### TASK_STATE_CHANGED

任务状态变化事件（保留用于未来扩展）。

**触发时机：** 任务状态发生变化时

**Payload 结构：**

```python
{
    "old_state": str,           # 旧状态
    "new_state": str,           # 新状态
    "reason": str,              # 状态变化原因（可选）
    "metadata": Dict[str, Any]  # 其他元数据
}
```

**处理 Policy：** 当前未实现，保留用于未来扩展

**示例：**

```json
{
  "event_id": "evt_012",
  "source": "eventbus",
  "task_id": "task_abc",
  "event_type": "TASK_STATE_CHANGED",
  "ts": "2025-01-28T10:45:00Z",
  "payload": {
    "old_state": "running",
    "new_state": "paused",
    "reason": "Manual pause by user"
  }
}
```

## 审计事件类型

Supervisor 在处理过程中会生成以下审计事件，写入 `task_audits` 表。

### SUPERVISOR_ALLOWED

决策为"允许"，任务可以继续执行。

**日志级别：** `info`

**Payload：**

```python
{
    "decision_id": str,
    "decision_type": "allow",
    "reason": str,
    "findings": [],             # 通常为空（没有发现问题）
    "actions": [],
    "timestamp": str
}
```

### SUPERVISOR_PAUSED

决策为"暂停"，任务被暂停等待审批。

**日志级别：** `warn`

**Payload：**

```python
{
    "decision_id": str,
    "decision_type": "pause",
    "reason": str,
    "findings": [               # 发现的问题
        {
            "finding_id": str,
            "category": str,    # risk|conflict|constraint
            "severity": str,    # medium|high
            "description": str,
            "evidence": List[str]
        }
    ],
    "actions": [
        {
            "action_type": "pause_gate",
            "target": str,
            "params": {
                "checkpoint": str,
                "reason": str
            }
        }
    ],
    "timestamp": str
}
```

### SUPERVISOR_BLOCKED

决策为"阻塞"，任务被阻止执行。

**日志级别：** `warn`

**Payload：**

```python
{
    "decision_id": str,
    "decision_type": "block",
    "reason": str,
    "findings": [               # 发现的严重问题
        {
            "finding_id": str,
            "category": str,    # redline|constraint
            "severity": str,    # high|critical
            "description": str,
            "evidence": List[str]
        }
    ],
    "actions": [
        {
            "action_type": "mark_blocked",
            "target": str,
            "params": {
                "reason": str
            }
        }
    ],
    "timestamp": str
}
```

### SUPERVISOR_RETRY_RECOMMENDED

决策为"建议重试"。

**日志级别：** `info`

**Payload：**

```python
{
    "decision_id": str,
    "decision_type": "retry",
    "reason": str,
    "findings": [
        {
            "finding_id": str,
            "category": "failure",
            "severity": "high",
            "description": str,
            "evidence": List[str]
        }
    ],
    "actions": [
        {
            "action_type": "write_audit",
            "target": str,
            "params": {
                "event_type": "SUPERVISOR_RETRY_RECOMMENDED",
                "retry_count": int,
                "reason": str
            }
        }
    ],
    "timestamp": str
}
```

### SUPERVISOR_DECISION

通用决策记录，用于不属于以上类型的决策。

**日志级别：** `info`

**Payload：**

```python
{
    "decision_id": str,
    "decision_type": str,
    "reason": str,
    "findings": List[Dict],
    "actions": List[Dict],
    "timestamp": str
}
```

### SUPERVISOR_ERROR

Supervisor 内部处理错误。

**日志级别：** `error`

**Payload：**

```python
{
    "error": str,               # 错误信息
    "context": {                # 错误上下文
        "policy": str,          # 出错的 Policy
        "event_type": str,      # 正在处理的事件类型
        "task_id": str          # 关联的任务 ID
    },
    "timestamp": str
}
```

## 事件处理流程

### 完整流程

```
1. 事件产生
   ├─── Task Lifecycle Event (EventBus)
   └─── Task Audit Record (Database)

2. 事件摄入
   ├─── EventBus Subscriber 接收 → SupervisorEvent.from_eventbus()
   └─── Polling Timer 扫描 → SupervisorEvent.from_db_row()

3. 写入 Inbox
   └─── InboxManager.insert_event() (去重)

4. 唤醒 Supervisor
   └─── SupervisorService.wake()

5. 处理事件
   ├─── SupervisorProcessor.process_pending_events()
   ├─── 拉取 pending 事件
   ├─── 标记为 processing
   └─── PolicyRouter.route() → Policy.evaluate()

6. 生成决策
   └─── Policy 返回 Decision (with Findings and Actions)

7. 执行动作
   ├─── 调用 Adapters (Gate/Evaluator/Audit)
   ├─── 更新任务状态
   └─── 写入审计日志

8. 标记完成
   └─── InboxManager 更新 status = 'completed'
```

### 状态转换

```
supervisor_inbox.status:

pending ────▶ processing ────▶ completed
              │
              └────▶ failed (可重试)
```

## 事件查询

### 查询 Inbox 中的事件

```python
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询待处理事件
cursor.execute("""
    SELECT event_id, task_id, event_type, source, received_at
    FROM supervisor_inbox
    WHERE status = 'pending'
    ORDER BY received_at ASC
""")

for row in cursor.fetchall():
    print(row)
```

### 查询审计轨迹

```python
audit_adapter = AuditAdapter(db_path)

# 获取任务的 Supervisor 审计轨迹
events = audit_adapter.get_audit_trail(
    task_id="task_abc",
    event_type_prefix="SUPERVISOR_",
    limit=100
)

for event in events:
    print(f"{event['created_at']}: {event['event_type']} - {event['payload']['reason']}")
```

### 查询特定决策

```python
cursor.execute("""
    SELECT audit_id, level, event_type, payload, created_at
    FROM task_audits
    WHERE task_id = ?
      AND event_type = 'SUPERVISOR_BLOCKED'
    ORDER BY created_at DESC
""", (task_id,))

for row in cursor.fetchall():
    payload = json.loads(row[3])
    print(f"Blocked at {row[4]}: {payload['reason']}")
```

## 最佳实践

### 事件设计

1. **保持 payload 轻量**
   - 不要在 payload 中存储大量数据
   - 使用引用（如文件路径）而不是内嵌完整内容

2. **提供足够的上下文**
   - 确保 Policy 能从 payload 中获取足够的信息做决策
   - 包含必要的 ID 和引用

3. **使用标准化的字段名**
   - 统一字段命名风格（如 `snake_case`）
   - 保持字段语义一致

### 事件处理

1. **幂等性**
   - Policy 的 `evaluate()` 方法应该是幂等的
   - 同一事件多次处理应产生相同结果

2. **容错性**
   - 处理 payload 字段缺失的情况
   - 使用 `payload.get(key, default)` 而不是 `payload[key]`

3. **性能考虑**
   - 避免在 Policy 中执行耗时操作
   - 异步处理大数据量操作

### 审计追溯

1. **记录完整上下文**
   - 在审计事件中包含决策依据（Findings）
   - 记录执行的动作（Actions）

2. **使用结构化日志**
   - payload 使用 JSON 格式
   - 便于后续查询和分析

3. **保留审计轨迹**
   - 至少保留 30 天
   - 重要任务永久保留

## 相关文档

- [Supervisor 主文档](./supervisor.md)
- [Supervisor Policies](./supervisor_policies.md)
- [Supervisor Runbook](./supervisor_runbook.md)
- [Validation Layers](./VALIDATION_LAYERS.md)
