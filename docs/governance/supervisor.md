# Supervisor 系统文档

## 概述

Supervisor 是 AgentOS 的治理中心，负责在任务执行的关键生命周期节点进行安全检查、风险评估和决策执行。它通过双通道事件摄入（EventBus + Polling）确保不遗漏任何治理检查点，并通过 Policy 机制实现可扩展的决策逻辑。

## 职责和边界

### 核心职责

1. **事件摄入 (Event Ingestion)**
   - 订阅 EventBus 获取实时事件（快路径）
   - Polling 数据库兜底未及时处理的事件（慢路径）
   - 事件去重和持久化到 inbox

2. **决策执行 (Decision Making)**
   - 任务创建时的红线预检和冲突检测
   - 步骤完成后的风险再评估
   - 任务失败时的归因和重试建议

3. **Gate 触发 (Gate Triggering)**
   - 触发 pause gate（暂停任务等待审批）
   - 触发 runtime enforcer（运行时约束检查）
   - 标记任务状态（BLOCKED / VERIFYING）

4. **审计记录 (Audit Logging)**
   - 记录所有决策和发现（Findings）
   - 提供完整的治理轨迹
   - 支持事后分析和合规审查

### 职责边界

**Supervisor 负责：**
- 监听事件并做出决策
- 调用 gates 和 evaluator 进行验证
- 写入审计日志
- 管理 inbox 和事件处理状态

**Supervisor 不负责：**
- 具体的验证逻辑（由 gates/evaluator 实现）
- Task 的生命周期管理（由 Coordinator 负责）
- 执行计划的生成（由 Planner 负责）
- 用户交互和审批（由 WebUI/CLI 负责）

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Supervisor                              │
│                                                                 │
│  ┌────────────────┐                    ┌────────────────┐      │
│  │  EventBus      │                    │   Polling      │      │
│  │  Subscriber    │                    │   Timer        │      │
│  │  (快路径)       │                    │   (慢路径)      │      │
│  └───────┬────────┘                    └───────┬────────┘      │
│          │                                     │               │
│          │    wake()                           │               │
│          ├────────────────┐  wake()  ┌─────────┤               │
│          ▼                ▼          ▼         ▼               │
│  ┌──────────────────────────────────────────────────┐          │
│  │            SupervisorService                     │          │
│  │         (Main Processing Loop)                   │          │
│  └──────────────────┬───────────────────────────────┘          │
│                     │                                          │
│                     ▼                                          │
│  ┌──────────────────────────────────────────────────┐          │
│  │         SupervisorProcessor                      │          │
│  │  (Pull from inbox, Route to policies)           │          │
│  └──────────────────┬───────────────────────────────┘          │
│                     │                                          │
│                     ▼                                          │
│  ┌──────────────────────────────────────────────────┐          │
│  │            PolicyRouter                          │          │
│  └──────────────────┬───────────────────────────────┘          │
│                     │                                          │
│         ┌───────────┼───────────┐                              │
│         ▼           ▼           ▼                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                       │
│  │OnTask    │ │OnStep    │ │OnTask    │                       │
│  │Created   │ │Completed │ │Failed    │                       │
│  │Policy    │ │Policy    │ │Policy    │                       │
│  └──────────┘ └──────────┘ └──────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
           │              │              │
           ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  Gates   │  │Evaluator │  │  Audit   │
    │ Adapter  │  │ Adapter  │  │ Adapter  │
    └──────────┘  └──────────┘  └──────────┘
```

### 双通道事件摄入

Supervisor 采用双通道设计确保事件不丢失：

1. **快路径 (EventBus Subscriber)**
   - 订阅 EventBus 的实时事件
   - 立即写入 inbox 并唤醒 Supervisor
   - 适合延迟敏感的场景

2. **慢路径 (Polling Timer)**
   - 定时扫描数据库（默认 10 秒）
   - 补漏未及时处理的事件
   - 提供兜底保障

**去重机制：**
- 通过 inbox 表的 `event_id UNIQUE` 约束自动去重
- EventBus 和 Polling 可能产生相同事件，只处理一次

### 数据流

```
Task Lifecycle Event
        │
        ├─────────────┐
        ▼             ▼
   EventBus        Database
        │             │
        ▼             ▼
   Subscriber      Poller
        │             │
        └──────┬──────┘
               ▼
         supervisor_inbox (去重)
               │
               ▼
        Processor (拉取 pending 事件)
               │
               ▼
        PolicyRouter (路由到 policy)
               │
        ┌──────┼──────┐
        ▼      ▼      ▼
     Policy  Policy  Policy
        │      │      │
        └──────┼──────┘
               ▼
           Decision
               │
        ┌──────┼──────┐
        ▼      ▼      ▼
      Gates  Task   Audit
            Status
```

## Decision 类型和映射规则

### Decision 类型

```python
class DecisionType(str, Enum):
    ALLOW = "allow"                    # 允许继续
    PAUSE = "pause"                    # 暂停等待
    BLOCK = "block"                    # 阻塞
    RETRY = "retry"                    # 建议重试（不强制）
    REQUIRE_REVIEW = "require_review"  # 需要人工审查
```

### Decision 到 Action 的映射

| Decision Type | Action Type | 说明 |
|--------------|-------------|------|
| `ALLOW` | `MARK_VERIFYING` | 标记任务为验证通过状态 |
| `PAUSE` | `PAUSE_GATE` | 触发 pause gate，任务进入等待审批状态 |
| `BLOCK` | `MARK_BLOCKED` | 标记任务为 BLOCKED，停止执行 |
| `RETRY` | `WRITE_AUDIT` | 写入重试建议到审计日志（不强制执行） |
| `REQUIRE_REVIEW` | `WRITE_AUDIT` | 写入审计日志，等待外部审查 |

### Action 类型

```python
class ActionType(str, Enum):
    PAUSE_GATE = "pause_gate"              # 触发 pause gate
    RUNTIME_ENFORCE = "runtime_enforce"    # 触发 runtime enforcer
    REDLINE_VIOLATION = "redline_violation"  # 红线违规
    MARK_BLOCKED = "mark_blocked"          # 标记任务为 BLOCKED
    MARK_VERIFYING = "mark_verifying"      # 标记任务为 VERIFYING
    WRITE_AUDIT = "write_audit"            # 写审计日志
    NOOP = "noop"                          # 无操作
```

## 与 Gates/Evaluator 的关系

### 层次关系

```
┌─────────────────────────────────────────┐
│           Supervisor                    │  ← 编排层
│  (Orchestration & Decision Making)      │
└───────────────┬─────────────────────────┘
                │
        ┌───────┼───────┐
        ▼       ▼       ▼
    ┌──────┐ ┌──────┐ ┌──────┐
    │Gates │ │Eval  │ │Audit │             ← 能力层
    └──────┘ └──────┘ └──────┘
```

### 调用关系

**Supervisor 通过 Adapters 调用下层能力：**

1. **GateAdapter**
   - `check_redline_violation()` - 红线验证
   - `trigger_pause()` - 触发暂停
   - `enforce_runtime_gates()` - 运行时检查

2. **EvaluatorAdapter**
   - `evaluate_intent_set()` - 意图集评估
   - `detect_conflicts()` - 冲突检测
   - `compare_risks()` - 风险比较

3. **AuditAdapter**
   - `write_decision()` - 写入决策审计
   - `write_error()` - 写入错误审计
   - `get_audit_trail()` - 查询审计轨迹

### 职责分离

| 组件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| **Gates** | 验证规则（redlines）<br>暂停机制（pause）<br>运行时约束（enforcer） | Entity Spec<br>Task Metadata | Validation Result<br>Pause State |
| **Evaluator** | 意图评估<br>冲突检测<br>风险比较 | Intent Set | Conflicts<br>Risk Matrix |
| **Supervisor** | 事件监听<br>策略路由<br>决策执行 | Events | Decisions<br>Actions |

## 数据模型

### SupervisorEvent

统一的事件契约，是 Supervisor 的输入。

```python
@dataclass
class SupervisorEvent:
    event_id: str          # 全局唯一 ID
    source: EventSource    # EVENTBUS / POLLING
    task_id: str           # 关联的任务 ID
    event_type: str        # 事件类型
    ts: str                # ISO 时间戳
    payload: Dict[str, Any]  # 事件载荷
```

### Finding

发现的问题（风险、冲突、红线违规）。

```python
@dataclass
class Finding:
    finding_id: str
    category: str          # risk|conflict|redline|constraint
    severity: str          # low|medium|high|critical
    description: str       # 问题描述
    evidence: List[str]    # 证据引用
    source: str            # evaluator|gate|policy
```

### Decision

Supervisor 的决策结果。

```python
@dataclass
class Decision:
    decision_id: str
    decision_type: DecisionType
    reason: str            # 决策理由
    findings: List[Finding]  # 相关发现
    actions: List[Action]    # 要执行的动作
    timestamp: str
```

### Action

要执行的具体动作。

```python
@dataclass
class Action:
    action_id: str
    action_type: ActionType
    target: str            # 目标（task_id / gate_name / ...）
    params: Dict[str, Any]  # 动作参数
```

## 数据库表结构

### supervisor_inbox

事件收件箱，用于去重和持久化。

```sql
CREATE TABLE supervisor_inbox (
    event_id TEXT PRIMARY KEY,        -- 事件 ID（唯一，用于去重）
    task_id TEXT NOT NULL,            -- 关联的任务 ID
    event_type TEXT NOT NULL,         -- 事件类型
    source TEXT NOT NULL,             -- 事件来源（eventbus/polling）
    payload TEXT,                     -- JSON 载荷
    received_at TEXT NOT NULL,        -- 接收时间
    status TEXT DEFAULT 'pending',    -- 状态（pending/processing/completed/failed）
    processed_at TEXT,                -- 处理时间
    retry_count INTEGER DEFAULT 0,    -- 重试次数
    error_message TEXT                -- 错误信息（如果失败）
);

CREATE INDEX idx_supervisor_inbox_status ON supervisor_inbox(status);
CREATE INDEX idx_supervisor_inbox_task_id ON supervisor_inbox(task_id);
CREATE INDEX idx_supervisor_inbox_received_at ON supervisor_inbox(received_at);
```

### task_audits

任务审计日志（复用现有表）。

```sql
CREATE TABLE task_audits (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    level TEXT NOT NULL,              -- info/warn/error
    event_type TEXT NOT NULL,         -- 事件类型（如 SUPERVISOR_BLOCKED）
    payload TEXT,                     -- JSON 载荷
    created_at TEXT NOT NULL
);
```

## 配置

### 启动参数

```python
supervisor_service = SupervisorService(
    db_path=Path("/path/to/agentos.db"),
    processor=processor,
    poll_interval=10  # Polling 间隔（秒）
)
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SUPERVISOR_POLL_INTERVAL` | Polling 间隔（秒） | 10 |
| `SUPERVISOR_BATCH_SIZE` | 批处理大小 | 50 |
| `SUPERVISOR_ENABLE_EVENTBUS` | 是否启用 EventBus 订阅 | true |

## 监控指标

### Inbox Backlog

```python
metrics = inbox_manager.get_backlog_metrics()
# {
#   "pending_count": 5,              # 待处理事件数
#   "processing_count": 2,           # 正在处理事件数
#   "failed_count": 1,               # 失败事件数
#   "completed_count": 100,          # 已完成事件数
#   "oldest_pending_age_seconds": 15.2  # 最老待处理事件年龄
# }
```

### Processing Lag

通过 `oldest_pending_age_seconds` 监控处理延迟：
- `< 5s` - 正常
- `5s - 30s` - 警告
- `> 30s` - 严重

### Event Throughput

```python
processed_count = processor.process_pending_events()
logger.info(f"Processed {processed_count} events")
```

## 扩展指南

### 添加新的 Policy

1. 继承 `BasePolicy`
2. 实现 `evaluate()` 方法
3. 在 `PolicyRouter` 中注册

```python
from agentos.core.supervisor.policies.base import BasePolicy

class OnTaskCanceledPolicy(BasePolicy):
    def evaluate(self, event: SupervisorEvent, cursor: sqlite3.Cursor) -> Optional[Decision]:
        # 实现评估逻辑
        return Decision(
            decision_type=DecisionType.ALLOW,
            reason="Task canceled by user",
            findings=[],
            actions=[]
        )

# 注册
policy_router.register("TASK_CANCELED", OnTaskCanceledPolicy(db_path))
```

### 添加新的 Decision Type

1. 在 `models.py` 的 `DecisionType` 枚举中添加
2. 在 `AuditAdapter` 中添加对应的事件类型映射
3. 更新相关 Policy 的决策逻辑

### 添加新的 Action Type

1. 在 `models.py` 的 `ActionType` 枚举中添加
2. 在相关 Adapter 中实现执行逻辑
3. 更新 Policy 中的 Action 构造代码

## 相关文档

- [Supervisor Events](./supervisor_events.md) - 事件契约和类型
- [Supervisor Runbook](./supervisor_runbook.md) - 运维手册
- [Supervisor Policies](./supervisor_policies.md) - Policy 详解
- [Validation Layers](./VALIDATION_LAYERS.md) - 治理层级
