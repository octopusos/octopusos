# Mode-Task 集成技术指南

**版本**: 1.0
**更新日期**: 2026年1月30日
**适用范围**: AgentOS v0.4+ with Phase 1 Mode Integration

---

## 目录

- [1. 概述](#1-概述)
- [2. 架构](#2-架构)
- [3. Mode Gateway Protocol](#3-mode-gateway-protocol)
- [4. 集成点详解](#4-集成点详解)
- [5. Gateway Registry](#5-gateway-registry)
- [6. 配置指南](#6-配置指南)
- [7. 错误处理](#7-错误处理)
- [8. 性能优化](#8-性能优化)
- [9. API 参考](#9-api-参考)
- [10. 示例代码](#10-示例代码)
- [11. FAQ](#11-faq)

---

## 1. 概述

### 1.1 什么是 Mode-Task 集成

Mode-Task 集成是 AgentOS 中的智能任务治理机制，它允许系统根据任务的 **Mode**（运行模式）动态控制任务的状态转换。

通过在任务生命周期的关键点引入 **Mode Gateway**，系统可以：

- **自动阻止**: 阻止特定 Mode 的任务执行某些操作（如 design mode 不能执行）
- **需要审批**: 特定转换需要人工或系统审批（如 autonomous mode 需要批准后才能运行）
- **灵活策略**: 支持自定义的 Mode 决策逻辑
- **可审计**: 所有 Mode 决策都有完整的审计追踪

### 1.2 为什么需要它

**问题**:
- 某些任务（如 design mode）应该只用于规划，不应该实际执行
- 某些任务（如 autonomous mode）需要人工审批后才能运行
- 需要灵活的任务治理策略，而不是硬编码规则

**解决方案**:
- 引入 Mode Gateway Protocol，将任务治理逻辑与状态机解耦
- 提供可扩展的 Gateway 实现机制
- 支持多种决策类型（批准/拒绝/阻止/延迟）
- Fail-safe 设计保证系统在 Gateway 故障时仍可运行

### 1.3 核心概念

#### Mode（运行模式）
任务的运行模式，定义任务的执行特征：
- **implementation**: 标准实施模式，可以完整执行
- **design**: 设计模式，用于规划，不执行
- **chat**: 对话模式，用于交互，不执行
- **autonomous**: 自主模式，需要审批

#### Mode Gateway（Mode 网关）
负责验证任务状态转换是否符合 Mode 约束的组件。

#### Mode Decision（Mode 决策）
Gateway 对状态转换的决策结果：
- **APPROVED**: 批准，允许转换
- **REJECTED**: 拒绝，阻止转换
- **BLOCKED**: 阻止，等待外部批准
- **DEFERRED**: 延迟，稍后重试

#### Integration Point（集成点）
Mode Gateway 与 Task 状态机的集成位置，Phase 1 选择了 **Transition Validation**。

---

## 2. 架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Application Layer                            │
│  (TaskService, CLI, WebUI, API)                                     │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          │ Task Lifecycle Operations
                          │ (create, transition, query)
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│                      Task Lifecycle Layer                            │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              TaskStateMachine                                 │  │
│  │                                                               │  │
│  │  - transition(task_id, to_state, ...)                        │  │
│  │  - validate_or_raise(from, to)                               │  │
│  │  - _validate_mode_transition() ◄──── Integration Point #1   │  │
│  │  - _check_state_entry_gates()                                │  │
│  │  - _record_audit()                                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────┬────────────────────────────────────────┬──┘
                          │                                        │
                          │ Mode Validation                        │ Database
                          │ (if mode_id exists)                    │ Operations
                          │                                        │
┌─────────────────────────▼───────────────────────────────────────┐  │
│                   Mode Gateway Layer                             │  │
│                                                                  │  │
│  ┌──────────────────────────────────────────────────────────┐  │  │
│  │         ModeGatewayProtocol (Protocol)                   │  │  │
│  │                                                          │  │  │
│  │  def validate_transition(                               │  │  │
│  │      task_id, mode_id, from_state, to_state, metadata   │  │  │
│  │  ) -> ModeDecision                                      │  │  │
│  └──────────────────────────────────────────────────────────┘  │  │
│                          │                                      │  │
│                          │ implements                           │  │
│                          ▼                                      │  │
│  ┌─────────────────────────────────────────────────────────┐   │  │
│  │           Gateway Implementations                        │   │  │
│  │                                                          │   │  │
│  │  ┌──────────────────────┐  ┌─────────────────────────┐ │   │  │
│  │  │ DefaultModeGateway   │  │RestrictedModeGateway    │ │   │  │
│  │  │                      │  │                         │ │   │  │
│  │  │ - Always APPROVED    │  │ - Blocks specific       │ │   │  │
│  │  │ - Fail-safe default  │  │   transitions           │ │   │  │
│  │  │                      │  │ - Approval required     │ │   │  │
│  │  └──────────────────────┘  └─────────────────────────┘ │   │  │
│  │                                                          │   │  │
│  │  ┌──────────────────────┐                               │   │  │
│  │  │ CustomGateway        │  (user-defined)               │   │  │
│  │  └──────────────────────┘                               │   │  │
│  └─────────────────────────────────────────────────────────┘   │  │
│                          │                                      │  │
│                          │ managed by                           │  │
│                          ▼                                      │  │
│  ┌─────────────────────────────────────────────────────────┐   │  │
│  │           Gateway Registry                               │   │  │
│  │                                                          │   │  │
│  │  - register_mode_gateway(mode_id, gateway)             │   │  │
│  │  - get_mode_gateway(mode_id) -> gateway                │   │  │
│  │  - Gateway cache (LRU)                                 │   │  │
│  │  - Fail-safe default gateway                            │   │  │
│  └─────────────────────────────────────────────────────────┘   │  │
│                                                                  │  │
└─────────────────────────┬────────────────────────────────────────┘  │
                          │                                           │
                          │ Decision Flow                             │
                          ▼                                           │
┌─────────────────────────────────────────────────────────────────┐  │
│                  Decision Processing                             │  │
│                                                                  │  │
│  ┌──────────────┐                                               │  │
│  │ APPROVED     │ ──▶ Continue transition                       │  │
│  └──────────────┘                                               │  │
│                                                                  │  │
│  ┌──────────────┐                                               │  │
│  │ REJECTED     │ ──▶ Raise ModeViolationError                 │  │
│  └──────────────┘     - Emit error log                          │  │
│                       - Record in audit trail                   │  │
│                                                                  │  │
│  ┌──────────────┐                                               │  │
│  │ BLOCKED      │ ──▶ Raise ModeViolationError                 │  │
│  └──────────────┘     - Emit MODE_VIOLATION alert (ERROR)       │  │
│                       - Emit error log                          │  │
│                       - Record in audit trail                   │  │
│                       - Requires external approval              │  │
│                                                                  │  │
│  ┌──────────────┐                                               │  │
│  │ DEFERRED     │ ──▶ Raise ModeViolationError                 │  │
│  └──────────────┘     - Emit info log                           │  │
│                       - Will be retried later                   │  │
│                                                                  │  │
└─────────────────────────┬───────────────────────────────────────┘  │
                          │                                           │
                          │ Alert & Audit                             │
                          ▼                                           │
┌─────────────────────────────────────────────────────────────────┐  │
│               Observability Layer                                │  │
│                                                                  │  │
│  ┌──────────────────────┐  ┌──────────────────────┐            │  │
│  │  Mode Alerts         │  │  Audit Logs          │            │  │
│  │  - MODE_VIOLATION    │  │  - Transition history│            │  │
│  │  - MODE_APPROVED     │  │  - Mode decisions    │            │  │
│  │  - MODE_BLOCKED      │  │  - Gateway failures  │            │  │
│  └──────────────────────┘  └──────────────────────┘            │  │
│                                                                  │  │
│  ┌──────────────────────┐                                       │  │
│  │  Metrics             │                                       │  │
│  │  - Gateway latency   │                                       │  │
│  │  - Cache hit rate    │                                       │  │
│  │  - Violation rate    │                                       │  │
│  └──────────────────────┘                                       │  │
└──────────────────────────────────────────────────────────────────┘  │
                                                                      │
┌─────────────────────────────────────────────────────────────────┐  │
│                       Storage Layer                              │  │
│  (SQLite / PostgreSQL)                                          │  │
│                                                                  │◄─┘
│  - Tasks table                                                  │
│  - Audit trail                                                  │
│  - Mode decisions (via audit metadata)                          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 组件交互序列图

```
Task Service    State Machine    Gateway Registry    Mode Gateway    Database
     │                │                  │                 │            │
     │ transition()   │                  │                 │            │
     ├───────────────▶│                  │                 │            │
     │                │                  │                 │            │
     │                │ Load task        │                 │            │
     │                ├──────────────────────────────────────────────▶ │
     │                │                  │                 │            │
     │                │ Get mode_id      │                 │            │
     │                │ from metadata    │                 │            │
     │                │                  │                 │            │
     │                │ get_mode_gateway(mode_id)          │            │
     │                ├─────────────────▶│                 │            │
     │                │                  │                 │            │
     │                │                  │ Check cache     │            │
     │                │                  │ ───┐            │            │
     │                │                  │    │            │            │
     │                │                  │ ◄──┘            │            │
     │                │                  │                 │            │
     │                │                  │ Cache miss      │            │
     │                │                  │ Load gateway    │            │
     │                │                  │ ───┐            │            │
     │                │                  │    │            │            │
     │                │                  │ ◄──┘            │            │
     │                │                  │                 │            │
     │                │ ◄────────────────┤ Return gateway  │            │
     │                │                  │                 │            │
     │                │ validate_transition()              │            │
     │                ├────────────────────────────────────▶│            │
     │                │                  │                 │            │
     │                │                  │   Evaluate mode │            │
     │                │                  │   constraints   │            │
     │                │                  │         ───┐    │            │
     │                │                  │            │    │            │
     │                │                  │         ◄──┘    │            │
     │                │                  │                 │            │
     │                │ ◄────────────────────────────────┤ │            │
     │                │                  │   ModeDecision  │            │
     │                │                  │                 │            │
     │                │ Process decision │                 │            │
     │                │ ───┐             │                 │            │
     │                │    │             │                 │            │
     │                │ ◄──┘             │                 │            │
     │                │                  │                 │            │
     │                │ IF APPROVED:     │                 │            │
     │                │   Continue       │                 │            │
     │                │                  │                 │            │
     │                │ Check gates      │                 │            │
     │                │ ───┐             │                 │            │
     │                │    │             │                 │            │
     │                │ ◄──┘             │                 │            │
     │                │                  │                 │            │
     │                │ Update task state│                 │            │
     │                ├──────────────────────────────────────────────▶ │
     │                │                  │                 │            │
     │                │ Record audit     │                 │            │
     │                ├──────────────────────────────────────────────▶ │
     │                │                  │                 │            │
     │ ◄──────────────┤ Return updated   │                 │            │
     │                │ task             │                 │            │
     │                │                  │                 │            │
```

### 2.3 数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Task Transition Request                      │
│  {                                                               │
│    task_id: "task-001",                                         │
│    to_state: "RUNNING",                                         │
│    actor_id: "user-123",                                        │
│    reason: "Start execution"                                    │
│  }                                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Load Task from Database                       │
│  Task {                                                          │
│    task_id: "task-001",                                         │
│    status: "QUEUED",                                            │
│    metadata: {                                                  │
│      mode_id: "design",          ◄──── Extract mode_id         │
│      ...                                                        │
│    }                                                            │
│  }                                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               Mode Gateway Validation (if mode_id)               │
│                                                                  │
│  Input:                                                          │
│    task_id: "task-001"                                          │
│    mode_id: "design"                                            │
│    from_state: "QUEUED"                                         │
│    to_state: "RUNNING"                                          │
│    metadata: {...}                                              │
│                                                                  │
│  Gateway Logic:                                                  │
│    IF mode_id == "design" AND to_state == "RUNNING":            │
│      RETURN BLOCKED                                             │
│                                                                  │
│  Output:                                                         │
│    ModeDecision {                                               │
│      verdict: BLOCKED,                                          │
│      reason: "Design mode tasks cannot execute",                │
│      metadata: {...}                                            │
│    }                                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Decision Processing                          │
│                                                                  │
│  IF verdict == APPROVED:                                         │
│    ├─▶ Continue to state transition                            │
│    ├─▶ Check entry gates                                       │
│    ├─▶ Update database                                         │
│    └─▶ Return success                                          │
│                                                                  │
│  IF verdict == REJECTED:                                         │
│    ├─▶ Log error                                               │
│    ├─▶ Record audit                                            │
│    └─▶ Raise ModeViolationError                                │
│                                                                  │
│  IF verdict == BLOCKED:                                          │
│    ├─▶ Emit MODE_VIOLATION alert (ERROR)                       │
│    ├─▶ Log error                                               │
│    ├─▶ Record audit                                            │
│    └─▶ Raise ModeViolationError                                │
│                                                                  │
│  IF verdict == DEFERRED:                                         │
│    ├─▶ Log info                                                │
│    └─▶ Raise ModeViolationError (retry later)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Error or Success                            │
│                                                                  │
│  Success:                                                        │
│    Task {                                                        │
│      task_id: "task-001",                                       │
│      status: "RUNNING",     ◄──── Updated                       │
│      ...                                                        │
│    }                                                             │
│                                                                  │
│  Error (BLOCKED):                                                │
│    ModeViolationError {                                         │
│      task_id: "task-001",                                       │
│      mode_id: "design",                                         │
│      from_state: "QUEUED",                                      │
│      to_state: "RUNNING",                                       │
│      reason: "Design mode tasks cannot execute",                │
│      metadata: {...}                                            │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Mode Gateway Protocol

### 3.1 协议定义

Mode Gateway Protocol 是一个 Python Protocol，定义了 Mode Gateway 必须实现的接口。

**文件**: `agentos/core/mode/gateway.py`

```python
from typing import Protocol, Dict, Any
from dataclasses import dataclass
from enum import Enum

class ModeDecisionVerdict(str, Enum):
    """Mode 决策类型"""
    APPROVED = "approved"   # 批准，允许转换
    REJECTED = "rejected"   # 拒绝，阻止转换
    BLOCKED = "blocked"     # 阻止，等待外部批准
    DEFERRED = "deferred"   # 延迟，稍后重试

@dataclass
class ModeDecision:
    """Mode 决策结果"""
    verdict: ModeDecisionVerdict
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    gateway_id: str = "default"

    def is_approved(self) -> bool:
        """是否批准"""
        return self.verdict == ModeDecisionVerdict.APPROVED

    def is_rejected(self) -> bool:
        """是否拒绝"""
        return self.verdict == ModeDecisionVerdict.REJECTED

    def is_blocked(self) -> bool:
        """是否阻止"""
        return self.verdict == ModeDecisionVerdict.BLOCKED

    def is_deferred(self) -> bool:
        """是否延迟"""
        return self.verdict == ModeDecisionVerdict.DEFERRED

class ModeGatewayProtocol(Protocol):
    """Mode Gateway 协议"""

    def validate_transition(
        self,
        task_id: str,
        mode_id: str,
        from_state: str,
        to_state: str,
        metadata: dict
    ) -> ModeDecision:
        """验证任务状态转换

        Args:
            task_id: 任务 ID
            mode_id: Mode ID
            from_state: 当前状态
            to_state: 目标状态
            metadata: 任务元数据

        Returns:
            ModeDecision: 决策结果

        Note:
            - 实现应该快速返回 (<10ms)
            - 不应该阻塞
            - 异步操作应返回 DEFERRED
        """
        ...
```

### 3.2 ModeDecisionVerdict 详解

#### APPROVED（批准）

**语义**: 允许状态转换继续执行

**使用场景**:
- 转换符合 Mode 约束
- 不需要特殊审批
- 默认许可策略

**示例**:
```python
ModeDecision(
    verdict=ModeDecisionVerdict.APPROVED,
    reason="Implementation mode allows all transitions",
    gateway_id="default"
)
```

**系统行为**:
- 继续执行状态转换
- 检查其他门（entry gates）
- 更新数据库
- 记录审计日志
- 返回成功

#### REJECTED（拒绝）

**语义**: 拒绝状态转换，转换无效

**使用场景**:
- 转换违反 Mode 约束
- 永久性拒绝（不会通过重试改变）
- 策略不允许

**示例**:
```python
ModeDecision(
    verdict=ModeDecisionVerdict.REJECTED,
    reason="Design mode tasks cannot transition to RUNNING",
    metadata={"mode_rule": "design_no_execution"},
    gateway_id="restricted_design"
)
```

**系统行为**:
- 抛出 `ModeViolationError`
- 记录错误日志
- 记录审计追踪
- 任务状态不变
- 不触发告警（因为是预期的拒绝）

#### BLOCKED（阻止）

**语义**: 阻止状态转换，等待外部批准

**使用场景**:
- 需要人工审批
- 需要系统审批
- 检查点机制
- 临时阻止（可能在获得批准后通过）

**示例**:
```python
ModeDecision(
    verdict=ModeDecisionVerdict.BLOCKED,
    reason="Autonomous mode requires approval before execution",
    metadata={
        "requires_approval": True,
        "approval_type": "human",
        "checkpoint_id": "exec-001"
    },
    gateway_id="autonomous_approval_gate"
)
```

**系统行为**:
- 抛出 `ModeViolationError`
- **触发告警**: 发送 MODE_VIOLATION alert（严重性: ERROR）
- 记录错误日志
- 记录审计追踪
- 任务保持当前状态
- 等待外部系统解除阻止

**告警内容**:
```python
{
    "severity": "ERROR",
    "category": "mode_violation",
    "message": "Mode blocked transition: Autonomous mode requires approval",
    "context": {
        "task_id": "task-001",
        "mode_id": "autonomous",
        "from_state": "QUEUED",
        "to_state": "RUNNING",
        "requires_approval": True
    }
}
```

#### DEFERRED（延迟）

**语义**: 延迟决策，稍后重试

**使用场景**:
- 异步决策（需要外部系统响应）
- 临时不可用（依赖服务未就绪）
- 速率限制
- 资源不足

**示例**:
```python
ModeDecision(
    verdict=ModeDecisionVerdict.DEFERRED,
    reason="Waiting for external approval service response",
    metadata={
        "retry_after": "60s",
        "approval_request_id": "req-12345"
    },
    gateway_id="async_approval_gate"
)
```

**系统行为**:
- 抛出 `ModeViolationError`
- 记录 INFO 级别日志（不是错误）
- 任务保持当前状态
- 调用方应该稍后重试
- 不触发告警（正常的延迟）

**重试策略** (由调用方实现):
```python
import time

max_retries = 3
retry_delay = 60  # seconds

for attempt in range(max_retries):
    try:
        task = state_machine.transition(task_id, "RUNNING", ...)
        break
    except ModeViolationError as e:
        if "Deferred" in str(e) and attempt < max_retries - 1:
            time.sleep(retry_delay)
            continue
        raise
```

### 3.3 ModeDecision 数据结构

```python
@dataclass
class ModeDecision:
    verdict: ModeDecisionVerdict   # 决策类型
    reason: str                    # 人类可读的原因
    metadata: Dict[str, Any]       # 额外的决策元数据
    timestamp: str                 # 决策时间（ISO 8601）
    gateway_id: str                # Gateway 标识符
```

**字段说明**:

#### verdict
- **类型**: `ModeDecisionVerdict`
- **必需**: 是
- **说明**: 决策类型（APPROVED/REJECTED/BLOCKED/DEFERRED）

#### reason
- **类型**: `str`
- **必需**: 是
- **说明**: 人类可读的决策原因，用于日志和审计
- **最佳实践**:
  - 使用清晰简洁的语言
  - 包含关键信息（如 Mode, 状态）
  - 避免技术术语
  - 示例: "Design mode tasks cannot execute"

#### metadata
- **类型**: `Dict[str, Any]`
- **必需**: 否（默认 `{}`）
- **说明**: 额外的决策元数据，用于审计、调试、集成
- **常用字段**:
  - `mode_rule`: 应用的 Mode 规则 ID
  - `requires_approval`: 是否需要审批（BLOCKED 时）
  - `approval_type`: 审批类型（"human", "system", "auto"）
  - `checkpoint_id`: 检查点 ID
  - `retry_after`: 重试延迟（DEFERRED 时）
  - `approval_request_id`: 审批请求 ID
  - `gateway_version`: Gateway 版本

#### timestamp
- **类型**: `str`
- **必需**: 否（自动生成）
- **格式**: ISO 8601（如 "2026-01-30T12:34:56.789Z"）
- **说明**: 决策时间，用于审计和排序

#### gateway_id
- **类型**: `str`
- **必需**: 否（默认 "default"）
- **说明**: Gateway 标识符，用于追踪决策来源
- **示例**: "default", "autonomous_approval_gate", "custom_gate_v1"

### 3.4 ModeGatewayProtocol 实现指南

#### 实现要求

1. **快速响应** (<10ms)
   - Gateway 在状态转换的关键路径上
   - 慢的 Gateway 会影响整体性能
   - 如果需要长时间操作，返回 DEFERRED

2. **无阻塞**
   - 不应该进行阻塞 I/O
   - 不应该等待网络响应
   - 异步操作应该在后台进行

3. **无状态**
   - Gateway 应该基于输入参数做决策
   - 不应该依赖全局状态
   - 易于测试和缓存

4. **幂等**
   - 相同输入应该返回相同决策
   - 不应该有副作用
   - 可以安全地重试

#### 实现模板

```python
class CustomModeGateway:
    """自定义 Mode Gateway 实现"""

    def __init__(self, gateway_id: str = "custom"):
        self.gateway_id = gateway_id
        # 初始化配置、缓存等

    def validate_transition(
        self,
        task_id: str,
        mode_id: str,
        from_state: str,
        to_state: str,
        metadata: dict
    ) -> ModeDecision:
        """验证状态转换"""

        # 1. 提取相关信息
        task_type = metadata.get("task_type")
        priority = metadata.get("priority", "normal")

        # 2. 应用 Mode 规则
        if mode_id == "my_mode":
            # 检查特定转换
            if from_state == "QUEUED" and to_state == "RUNNING":
                # 应用自定义逻辑
                if priority == "high":
                    return ModeDecision(
                        verdict=ModeDecisionVerdict.APPROVED,
                        reason="High priority task approved",
                        metadata={"priority": priority},
                        gateway_id=self.gateway_id
                    )
                else:
                    return ModeDecision(
                        verdict=ModeDecisionVerdict.BLOCKED,
                        reason="Normal priority requires approval",
                        metadata={
                            "requires_approval": True,
                            "approval_type": "supervisor"
                        },
                        gateway_id=self.gateway_id
                    )

        # 3. 默认批准
        return ModeDecision(
            verdict=ModeDecisionVerdict.APPROVED,
            reason=f"No restrictions for mode {mode_id}",
            gateway_id=self.gateway_id
        )
```

#### 最佳实践

**1. 使用明确的规则**

```python
# 好：明确的规则，易于理解和维护
BLOCKED_TRANSITIONS = {
    "design": [("QUEUED", "RUNNING")],
    "chat": [("QUEUED", "RUNNING")],
}

def validate_transition(self, ...):
    if (from_state, to_state) in BLOCKED_TRANSITIONS.get(mode_id, []):
        return ModeDecision(verdict=BLOCKED, ...)
```

```python
# 不好：复杂的嵌套逻辑，难以理解
def validate_transition(self, ...):
    if mode_id == "design":
        if from_state == "QUEUED":
            if to_state == "RUNNING":
                if not metadata.get("allow_execution"):
                    return ModeDecision(verdict=BLOCKED, ...)
```

**2. 提供详细的元数据**

```python
# 好：丰富的元数据，便于审计和调试
return ModeDecision(
    verdict=ModeDecisionVerdict.BLOCKED,
    reason="Autonomous mode requires human approval before execution",
    metadata={
        "mode_rule": "autonomous_execution_gate",
        "requires_approval": True,
        "approval_type": "human",
        "checkpoint_id": f"exec-{task_id}",
        "estimated_approval_time": "5m",
        "approval_url": f"https://ui.example.com/approvals/{task_id}"
    },
    gateway_id=self.gateway_id
)
```

```python
# 不好：缺少上下文信息
return ModeDecision(
    verdict=ModeDecisionVerdict.BLOCKED,
    reason="Blocked",
    gateway_id=self.gateway_id
)
```

**3. 使用配置驱动**

```python
# 好：配置驱动，易于修改和测试
class ConfigDrivenGateway:
    def __init__(self, config: dict):
        self.config = config

    def validate_transition(self, ...):
        rules = self.config.get("mode_rules", {}).get(mode_id, [])
        for rule in rules:
            if rule.matches(from_state, to_state, metadata):
                return rule.apply()
        return ModeDecision(verdict=APPROVED, ...)
```

**4. 记录决策日志**

```python
def validate_transition(self, ...):
    logger.info(
        f"Gateway {self.gateway_id}: Validating transition",
        extra={
            "task_id": task_id,
            "mode_id": mode_id,
            "transition": f"{from_state} -> {to_state}"
        }
    )

    decision = self._make_decision(...)

    logger.info(
        f"Gateway {self.gateway_id}: Decision {decision.verdict}",
        extra={
            "task_id": task_id,
            "verdict": decision.verdict,
            "reason": decision.reason
        }
    )

    return decision
```

**5. 错误处理**

```python
def validate_transition(self, ...):
    try:
        # 决策逻辑
        return self._make_decision(...)
    except Exception as e:
        # 记录错误，但不抛出（fail-safe）
        logger.error(
            f"Gateway {self.gateway_id} failed: {e}",
            exc_info=True
        )
        # 返回安全的默认决策
        return ModeDecision(
            verdict=ModeDecisionVerdict.APPROVED,
            reason=f"Gateway failed, fail-safe approved: {e}",
            metadata={"gateway_error": str(e)},
            gateway_id=self.gateway_id
        )
```

---

## 4. 集成点详解

### 4.1 Integration Point #1: Transition Validation

Phase 1 选择了 **Transition Validation** 作为主要集成点，在任务状态转换前验证 Mode 约束。

#### 位置

**文件**: `agentos/core/task/state_machine.py`
**方法**: `TaskStateMachine.transition()`

#### 集成代码

```python
def transition(
    self,
    task_id: str,
    to: str,
    actor_id: str,
    reason: str = ""
) -> Task:
    """执行任务状态转换

    集成点：在转换前验证 Mode 约束
    """
    # 1. 加载任务
    task = self._load_task(task_id)
    current_state = task.status

    # 2. 基本转换验证
    self.validate_or_raise(current_state, to)

    # 3. Mode 集成点：验证 Mode 约束
    task_metadata = json.loads(task.metadata or "{}")
    mode_id = task_metadata.get("mode_id")

    if mode_id:
        self._validate_mode_transition(
            task_id=task_id,
            mode_id=mode_id,
            from_state=current_state,
            to_state=to,
            metadata=task_metadata
        )

    # 4. 检查状态入口门
    self._check_state_entry_gates(task_id, to, task)

    # 5. 更新任务状态
    task = self._update_task_state(task_id, to, actor_id, reason)

    # 6. 记录审计追踪
    self._record_audit(task_id, current_state, to, actor_id, reason)

    return task
```

#### Mode 验证逻辑

```python
def _validate_mode_transition(
    self,
    task_id: str,
    mode_id: str,
    from_state: str,
    to_state: str,
    metadata: dict
) -> None:
    """验证 Mode 约束

    Raises:
        ModeViolationError: 如果 Mode gateway 拒绝转换
    """
    try:
        # 获取 Mode Gateway（带 fail-safe）
        gateway = self._get_mode_gateway(mode_id)

        # 验证转换
        decision = gateway.validate_transition(
            task_id=task_id,
            mode_id=mode_id,
            from_state=from_state,
            to_state=to_state,
            metadata=metadata
        )

        # 处理决策
        if decision.is_approved():
            # 批准：继续
            logger.debug(
                f"Mode gateway approved transition for task {task_id}: "
                f"{from_state} -> {to_state}"
            )
            return

        elif decision.is_rejected():
            # 拒绝：抛出错误
            logger.error(
                f"Mode gateway rejected transition for task {task_id}: "
                f"{decision.reason}"
            )
            raise ModeViolationError(
                task_id=task_id,
                mode_id=mode_id,
                from_state=from_state,
                to_state=to_state,
                reason=decision.reason,
                metadata=decision.metadata
            )

        elif decision.is_blocked():
            # 阻止：触发告警并抛出错误
            logger.warning(
                f"Mode gateway blocked transition for task {task_id}: "
                f"{decision.reason}"
            )

            # 发送告警
            self._emit_mode_alert(
                severity="ERROR",
                category="mode_violation",
                message=f"Mode blocked transition: {decision.reason}",
                context={
                    "task_id": task_id,
                    "mode_id": mode_id,
                    "from_state": from_state,
                    "to_state": to_state,
                    "decision": decision.to_dict()
                }
            )

            # 抛出错误
            raise ModeViolationError(
                task_id=task_id,
                mode_id=mode_id,
                from_state=from_state,
                to_state=to_state,
                reason=f"Blocked: {decision.reason}",
                metadata=decision.metadata
            )

        elif decision.is_deferred():
            # 延迟：记录并抛出错误（稍后重试）
            logger.info(
                f"Mode gateway deferred transition for task {task_id}: "
                f"{decision.reason}"
            )
            raise ModeViolationError(
                task_id=task_id,
                mode_id=mode_id,
                from_state=from_state,
                to_state=to_state,
                reason=f"Deferred: {decision.reason}",
                metadata=decision.metadata
            )

    except ModeViolationError:
        # 重新抛出 Mode 违规错误
        raise
    except Exception as e:
        # Fail-safe：如果 Mode gateway 失败，记录警告并允许转换
        logger.warning(
            f"Mode gateway failed for task {task_id}: {str(e)}, "
            f"allowing transition (fail-safe)"
        )
```

#### Fail-Safe 机制

```python
def _get_mode_gateway(self, mode_id: str):
    """获取 Mode Gateway（带 fail-safe）"""
    try:
        from agentos.core.mode.gateway_registry import get_mode_gateway
        return get_mode_gateway(mode_id)
    except Exception as e:
        logger.warning(
            f"Failed to load mode gateway for mode '{mode_id}': {str(e)}, "
            f"using fail-safe default"
        )
        # 返回默认的许可 Gateway
        from agentos.core.mode.gateway_registry import DefaultModeGateway
        return DefaultModeGateway(gateway_id="fail_safe")
```

**Fail-Safe 原则**:
- Mode Gateway 失败时，系统继续运行
- 记录警告日志，便于监控和审计
- 使用默认许可 Gateway（批准所有转换）
- 优先系统可用性而非严格执行

### 4.2 其他潜在集成点（未实施）

Phase 1 只实施了 Integration Point #1，以下是其他潜在集成点（供未来参考）：

#### Integration Point #2: Pre-Execution Hook
- **位置**: TaskRunner 执行前
- **用途**: 在任务实际执行前最后验证
- **优势**: 更接近执行时刻，可以检查运行时条件
- **劣势**: 任务已经进入 RUNNING 状态，回滚复杂

#### Integration Point #3: Post-Execution Hook
- **位置**: TaskRunner 执行后
- **用途**: 在任务完成后验证结果
- **优势**: 可以验证输出、副作用
- **劣势**: 事后验证，无法阻止执行

#### Integration Point #4: Disposition Evaluation
- **位置**: 决定任务下一步操作时
- **用途**: 根据 Mode 决定是验证、完成还是重试
- **优势**: 灵活的流程控制
- **劣势**: 复杂度高，与状态机耦合

#### Integration Point #5: Gate Augmentation
- **位置**: 增强现有的状态入口门
- **用途**: Mode 作为额外的门检查
- **优势**: 与现有门系统一致
- **劣势**: Mode 逻辑分散在多个门中

---

*(继续下一部分...)*
