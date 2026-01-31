# Supervisor Policies 文档

## 概述

Supervisor Policies 是 Supervisor 的决策引擎，负责根据不同的事件类型执行相应的治理策略。本文档详细说明三个核心 Policy 的工作原理、扩展指南和最佳实践。

## Policy 架构

### 设计原则

1. **单一职责** - 每个 Policy 只处理一种事件类型
2. **可组合** - Policy 通过 PolicyRouter 组合使用
3. **可扩展** - 通过继承 BasePolicy 轻松添加新 Policy
4. **幂等性** - 同一事件多次处理产生相同结果
5. **容错性** - Policy 失败不影响其他 Policy

### 调用流程

```
SupervisorProcessor
        │
        ▼
PolicyRouter.route(event, cursor)
        │
        ├─── event_type = "TASK_CREATED" → OnTaskCreatedPolicy
        ├─── event_type = "TASK_STEP_COMPLETED" → OnStepCompletedPolicy
        ├─── event_type = "TASK_FAILED" → OnTaskFailedPolicy
        └─── event_type = "OTHER" → None (未注册)
        │
        ▼
Policy.evaluate(event, cursor) → Decision
        │
        ├─── 生成 Findings (发现的问题)
        ├─── 确定 DecisionType (ALLOW/PAUSE/BLOCK/RETRY)
        ├─── 创建 Actions (要执行的动作)
        └─── 返回 Decision
        │
        ▼
BasePolicy.__call__() 自动写入审计
```

### BasePolicy

所有 Policy 的基类，提供通用功能。

```python
class BasePolicy(ABC):
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.gate_adapter = GateAdapter(db_path)
        self.evaluator_adapter = EvaluatorAdapter()
        self.audit_adapter = AuditAdapter(db_path)

    @abstractmethod
    def evaluate(self, event: SupervisorEvent, cursor: sqlite3.Cursor) -> Optional[Decision]:
        """评估事件并做出决策（子类实现）"""
        pass

    def __call__(self, event: SupervisorEvent, cursor: sqlite3.Cursor) -> Optional[Decision]:
        """
        使 Policy 可调用，自动处理审计和错误
        """
        try:
            decision = self.evaluate(event, cursor)
            if decision:
                self.audit_adapter.write_decision(event.task_id, decision, cursor)
            return decision
        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}", exc_info=True)
            self.audit_adapter.write_error(event.task_id, str(e), {...}, cursor)
            raise
```

**提供的工具方法：**

| 方法 | 说明 |
|------|------|
| `get_task_metadata(task_id, cursor)` | 获取任务元数据 |
| `get_task_status(task_id, cursor)` | 获取任务状态 |
| `update_task_status(task_id, new_status, cursor)` | 更新任务状态 |

## 核心 Policies

### OnTaskCreatedPolicy

任务创建时的预检 Policy。

#### 职责

1. **红线预检** - 检查 agent/command/rule 是否违反红线
2. **意图评估** - 评估 intent set 的完整性和一致性
3. **冲突检测** - 检测意图之间的冲突
4. **风险评估** - 评估任务的初始风险等级

#### 决策逻辑

```python
def evaluate(self, event: SupervisorEvent, cursor: sqlite3.Cursor) -> Decision:
    findings = []

    # 1. 红线检查
    if agent_spec:
        is_violation, errors = gate_adapter.check_redline_violation("agent", agent_spec)
        if is_violation:
            findings.append(Finding(category="redline", severity="high", ...))

    # 2. Intent Set 评估
    if intent_set_path:
        eval_result = evaluator_adapter.evaluate_intent_set(intent_set_path)

        # 2.1 冲突检测
        conflicts = eval_result["evaluation"]["conflicts"]
        if has_critical_conflicts(conflicts):
            findings.append(Finding(category="conflict", severity="high", ...))

        # 2.2 风险评估
        risk_matrix = eval_result["evaluation"]["risk_comparison"]
        highest_risk = get_highest_risk(risk_matrix)
        if highest_risk in ["high", "critical"]:
            findings.append(Finding(category="risk", severity=highest_risk, ...))

    # 3. 决策
    if has_high_severity_findings(findings):
        return Decision(
            decision_type=DecisionType.BLOCK,
            reason="Critical issues detected",
            findings=findings,
            actions=[Action(action_type=ActionType.MARK_BLOCKED, ...)]
        )
    elif findings:
        return Decision(
            decision_type=DecisionType.PAUSE,
            reason="Issues require review",
            findings=findings,
            actions=[Action(action_type=ActionType.PAUSE_GATE, ...)]
        )
    else:
        return Decision(
            decision_type=DecisionType.ALLOW,
            reason="No issues detected",
            findings=[],
            actions=[Action(action_type=ActionType.MARK_VERIFYING, ...)]
        )
```

#### 输入 (Payload)

```python
{
    "agent_spec": {...},        # Agent 规范（可选）
    "command_spec": {...},      # Command 规范（可选）
    "rule_spec": {...},         # Rule 规范（可选）
    "intent_set_path": str,     # Intent Set 路径（可选）
    "metadata": {...}           # 其他元数据
}
```

#### 输出 (Decision)

| Decision Type | Findings | Actions | 说明 |
|--------------|----------|---------|------|
| `BLOCK` | high/critical | `MARK_BLOCKED` | 发现严重问题（如红线违规），阻塞任务 |
| `PAUSE` | medium | `PAUSE_GATE` | 发现中等问题，暂停等待审批 |
| `ALLOW` | none | `MARK_VERIFYING` | 没有问题，允许继续 |

#### 使用示例

```python
policy = OnTaskCreatedPolicy(db_path)
decision = policy(event, cursor)

if decision.decision_type == DecisionType.BLOCK:
    print(f"Task blocked: {decision.reason}")
    for finding in decision.findings:
        print(f"  - {finding.severity}: {finding.description}")
```

### OnStepCompletedPolicy

步骤完成后的风险再评估 Policy。

#### 职责

1. **风险指标检查** - 检查 error_rate, resource_usage, security_score 等指标
2. **Runtime Gates 检查** - 执行运行时约束验证
3. **异常输出检查** - 检查步骤是否产生警告或错误
4. **风险趋势分析** - 检测风险是否上升

#### 决策逻辑

```python
def evaluate(self, event: SupervisorEvent, cursor: sqlite3.Cursor) -> Decision:
    findings = []

    # 1. 风险指标检查
    risk_indicators = event.payload.get("risk_indicators", {})
    if risk_indicators:
        error_rate = risk_indicators.get("error_rate", 0)
        if error_rate > 0.3:  # 错误率超过 30%
            findings.append(Finding(
                category="risk",
                severity="medium",
                description=f"High error rate: {error_rate:.1%}",
                ...
            ))

        resource_usage = risk_indicators.get("resource_usage", 0)
        if resource_usage > 0.8:  # 资源使用率超过 80%
            findings.append(Finding(
                category="risk",
                severity="medium",
                description=f"High resource usage: {resource_usage:.1%}",
                ...
            ))

    # 2. Runtime Gates 检查
    run_id = event.payload.get("run_id")
    if run_id:
        passed, violation_reason = gate_adapter.enforce_runtime_gates(
            run_id=run_id,
            execution_mode=metadata.get("run_mode", "assisted"),
            cursor=cursor
        )
        if not passed:
            findings.append(Finding(
                category="constraint",
                severity="high",
                description=f"Runtime gate violation: {violation_reason}",
                ...
            ))

    # 3. 决策
    if has_high_severity_findings(findings):
        return Decision(
            decision_type=DecisionType.PAUSE,
            reason="High severity issues require review",
            findings=findings,
            actions=[Action(action_type=ActionType.PAUSE_GATE, ...)]
        )
    else:
        return Decision(
            decision_type=DecisionType.ALLOW,
            reason="Step completed successfully",
            findings=findings,
            actions=[]
        )
```

#### 输入 (Payload)

```python
{
    "step_id": str,
    "step_name": str,           # 可选
    "result": {
        "status": str,
        "output": Any,
        "warnings": List[str],
        "errors": List[str]
    },
    "risk_indicators": {        # 可选
        "error_rate": float,
        "resource_usage": float,
        "security_score": float
    },
    "run_id": str,              # 用于 runtime enforcer
    "metadata": {...}
}
```

#### 输出 (Decision)

| Decision Type | Findings | Actions | 说明 |
|--------------|----------|---------|------|
| `PAUSE` | high | `PAUSE_GATE` | 检测到高风险或 runtime gate 违规，暂停 |
| `ALLOW` | low/medium | none | 风险可控或只有警告，允许继续 |

#### 风险阈值配置

可以通过环境变量或配置文件调整风险阈值：

```python
class OnStepCompletedPolicy(BasePolicy):
    def __init__(self, db_path: Path, config: Optional[Dict] = None):
        super().__init__(db_path)
        self.config = config or {}

        # 可配置的阈值
        self.error_rate_threshold = self.config.get("error_rate_threshold", 0.3)
        self.resource_usage_threshold = self.config.get("resource_usage_threshold", 0.8)
        self.security_score_threshold = self.config.get("security_score_threshold", 50)
```

### OnTaskFailedPolicy

任务失败时的归因和重试决策 Policy。

#### 职责

1. **失败归因** - 分析失败原因和错误类型
2. **可重试性判断** - 判断错误是否可重试
3. **重试次数检查** - 检查是否超过最大重试次数
4. **决策生成** - 决定是建议重试还是阻塞任务

#### 决策逻辑

```python
def evaluate(self, event: SupervisorEvent, cursor: sqlite3.Cursor) -> Decision:
    findings = []

    # 1. 失败归因
    error_message = event.payload.get("error", "Unknown error")
    error_type = event.payload.get("error_type")

    findings.append(Finding(
        category="failure",
        severity="high",
        description=f"Task failed: {error_message}",
        evidence=[error_message, error_type or "no_type"],
        source="on_task_failed_policy"
    ))

    # 2. 判断是否可重试
    can_retry = self._can_retry(error_type, error_message)

    # 3. 检查重试次数
    metadata = get_task_metadata(event.task_id, cursor)
    retry_count = metadata.get("retry_count", 0)
    max_retries = metadata.get("max_retries", 3)

    # 4. 决策
    if can_retry and retry_count < max_retries:
        return Decision(
            decision_type=DecisionType.RETRY,
            reason=f"Retryable error (attempt {retry_count + 1}/{max_retries})",
            findings=findings,
            actions=[Action(
                action_type=ActionType.WRITE_AUDIT,
                target=event.task_id,
                params={"retry_count": retry_count + 1, ...}
            )]
        )
    else:
        return Decision(
            decision_type=DecisionType.BLOCK,
            reason="Non-retryable error or max retries exceeded",
            findings=findings,
            actions=[Action(action_type=ActionType.MARK_BLOCKED, ...)]
        )

def _can_retry(self, error_type: str, error_message: str) -> bool:
    """判断错误是否可重试"""
    # 不可重试的错误类型
    if error_type in ["redline_violation", "permission_denied", "invalid_config"]:
        return False

    # 可重试的错误类型
    if error_type in ["network_timeout", "rate_limited", "service_unavailable"]:
        return True

    # 基于错误信息的启发式判断
    non_retryable_keywords = ["permission denied", "invalid", "forbidden"]
    for keyword in non_retryable_keywords:
        if keyword in error_message.lower():
            return False

    # 默认不可重试（保守策略）
    return False
```

#### 输入 (Payload)

```python
{
    "error": str,               # 错误信息
    "error_code": str,          # 错误代码（可选）
    "error_type": str,          # 错误类型（可选）
    "stack_trace": str,         # 堆栈跟踪（可选）
    "failed_step_id": str,      # 失败的步骤（可选）
    "retry_count": int,         # 当前重试次数（可选）
    "metadata": {...}
}
```

#### 输出 (Decision)

| Decision Type | Findings | Actions | 说明 |
|--------------|----------|---------|------|
| `RETRY` | failure | `WRITE_AUDIT` | 可重试的错误且未超过最大重试次数 |
| `BLOCK` | failure + constraint | `MARK_BLOCKED` | 不可重试或已超过最大重试次数 |

#### 错误分类

**不可重试错误类型：**
- `redline_violation` - 红线违规
- `permission_denied` - 权限拒绝
- `invalid_config` - 配置无效
- `quota_exceeded` - 配额超限
- `auth_failed` - 认证失败

**可重试错误类型：**
- `network_timeout` - 网络超时
- `connection_refused` - 连接拒绝
- `rate_limited` - 限流
- `service_unavailable` - 服务不可用
- `temporary_failure` - 临时失败

#### 重试策略配置

```python
class OnTaskFailedPolicy(BasePolicy):
    def __init__(self, db_path: Path, config: Optional[Dict] = None):
        super().__init__(db_path)
        self.config = config or {}

        # 可配置的重试策略
        self.max_retries = self.config.get("max_retries", 3)
        self.non_retryable_errors = self.config.get(
            "non_retryable_errors",
            ["redline_violation", "permission_denied", "invalid_config"]
        )
        self.retryable_errors = self.config.get(
            "retryable_errors",
            ["network_timeout", "rate_limited", "service_unavailable"]
        )
```

## Policy 注册和路由

### PolicyRouter

PolicyRouter 负责将事件路由到对应的 Policy。

```python
class PolicyRouter:
    def __init__(self):
        self.policies: Dict[str, Callable] = {}

    def register(self, event_type: str, policy: Callable) -> None:
        """注册 Policy"""
        self.policies[event_type] = policy

    def route(self, event: SupervisorEvent, cursor: sqlite3.Cursor) -> Optional[Decision]:
        """路由事件到对应的 Policy"""
        policy = self.policies.get(event.event_type)
        if policy is None:
            return None
        return policy(event, cursor)
```

### 注册示例

```python
from pathlib import Path
from agentos.core.supervisor.supervisor import PolicyRouter
from agentos.core.supervisor.policies.on_task_created import OnTaskCreatedPolicy
from agentos.core.supervisor.policies.on_step_completed import OnStepCompletedPolicy
from agentos.core.supervisor.policies.on_task_failed import OnTaskFailedPolicy

db_path = Path("/path/to/agentos.db")

# 创建 PolicyRouter
router = PolicyRouter()

# 注册核心 Policies
router.register("TASK_CREATED", OnTaskCreatedPolicy(db_path))
router.register("TASK_STEP_COMPLETED", OnStepCompletedPolicy(db_path))
router.register("TASK_FAILED", OnTaskFailedPolicy(db_path))

# 使用 router
decision = router.route(event, cursor)
```

## 扩展指南

### 添加新的 Policy

**步骤 1：创建 Policy 类**

```python
# agentos/core/supervisor/policies/on_task_canceled.py

from pathlib import Path
import sqlite3
from typing import Optional

from ..models import SupervisorEvent, Decision, DecisionType, Finding, Action, ActionType
from .base import BasePolicy


class OnTaskCanceledPolicy(BasePolicy):
    """
    任务取消时的 Policy

    职责：
    1. 记录取消原因
    2. 清理相关资源
    3. 写入审计日志
    """

    def evaluate(self, event: SupervisorEvent, cursor: sqlite3.Cursor) -> Optional[Decision]:
        # 获取取消原因
        reason = event.payload.get("reason", "User canceled")

        # 创建 Finding
        findings = [
            Finding(
                category="lifecycle",
                severity="info",
                description=f"Task canceled: {reason}",
                evidence=[reason],
                source="on_task_canceled_policy"
            )
        ]

        # 创建决策
        decision = Decision(
            decision_type=DecisionType.ALLOW,  # 取消是正常操作，允许
            reason=f"Task canceled: {reason}",
            findings=findings,
            actions=[
                Action(
                    action_type=ActionType.WRITE_AUDIT,
                    target=event.task_id,
                    params={"event_type": "SUPERVISOR_TASK_CANCELED", "reason": reason}
                )
            ]
        )

        # 更新任务状态
        self.update_task_status(event.task_id, "canceled", cursor)

        return decision
```

**步骤 2：注册 Policy**

```python
from agentos.core.supervisor.policies.on_task_canceled import OnTaskCanceledPolicy

# 在 PolicyRouter 中注册
router.register("TASK_CANCELED", OnTaskCanceledPolicy(db_path))
```

**步骤 3：确保事件被发送**

```python
# 在任务取消时发送事件
from agentos.core.events.bus import get_event_bus
from agentos.core.events.models import Event, EventType

event_bus = get_event_bus()
event_bus.publish(Event(
    type=EventType.TASK_CANCELED,
    entity=task,
    ts=datetime.now(timezone.utc).isoformat(),
    payload={"reason": "User requested cancellation"}
))
```

### 自定义 Decision Type

如果需要新的决策类型：

**步骤 1：扩展 DecisionType 枚举**

```python
# models.py

class DecisionType(str, Enum):
    ALLOW = "allow"
    PAUSE = "pause"
    BLOCK = "block"
    RETRY = "retry"
    REQUIRE_REVIEW = "require_review"
    ESCALATE = "escalate"  # 新增：上报给管理员
```

**步骤 2：在 AuditAdapter 中添加映射**

```python
# adapters/audit_adapter.py

event_type_map = {
    "allow": SUPERVISOR_ALLOWED,
    "pause": SUPERVISOR_PAUSED,
    "block": SUPERVISOR_BLOCKED,
    "retry": SUPERVISOR_RETRY_RECOMMENDED,
    "require_review": SUPERVISOR_DECISION,
    "escalate": "SUPERVISOR_ESCALATED"  # 新增
}
```

**步骤 3：在 Policy 中使用**

```python
if critical_security_issue:
    return Decision(
        decision_type=DecisionType.ESCALATE,
        reason="Critical security issue requires immediate attention",
        findings=[...],
        actions=[
            Action(
                action_type=ActionType.WRITE_AUDIT,
                target=event.task_id,
                params={
                    "event_type": "SUPERVISOR_ESCALATED",
                    "escalation_level": "critical"
                }
            )
        ]
    )
```

### 自定义 Action Type

如果需要新的动作类型：

**步骤 1：扩展 ActionType 枚举**

```python
# models.py

class ActionType(str, Enum):
    PAUSE_GATE = "pause_gate"
    RUNTIME_ENFORCE = "runtime_enforce"
    REDLINE_VIOLATION = "redline_violation"
    MARK_BLOCKED = "mark_blocked"
    MARK_VERIFYING = "mark_verifying"
    WRITE_AUDIT = "write_audit"
    NOOP = "noop"
    SEND_NOTIFICATION = "send_notification"  # 新增：发送通知
```

**步骤 2：实现动作执行逻辑**

```python
# 在相关 Adapter 或 Policy 中实现
def execute_action(action: Action):
    if action.action_type == ActionType.SEND_NOTIFICATION:
        recipient = action.params.get("recipient")
        message = action.params.get("message")
        send_email(recipient, message)
```

**步骤 3：在 Policy 中使用**

```python
actions = [
    Action(
        action_type=ActionType.SEND_NOTIFICATION,
        target="admin@example.com",
        params={
            "recipient": "admin@example.com",
            "subject": "High risk task detected",
            "message": f"Task {event.task_id} has high risk..."
        }
    )
]
```

## 最佳实践

### 1. Policy 设计

**保持 Policy 简洁：**
- 一个 Policy 只处理一种事件类型
- 避免在 Policy 中实现复杂业务逻辑
- 将复杂逻辑抽取到 Adapter 或独立模块

**使用清晰的命名：**
- Policy 类名：`On{EventType}Policy`
- Policy 文件名：`on_{event_type}.py`
- 方法名：`evaluate()` 用于决策生成

**提供完整的上下文：**
- 在 Finding 中记录详细的证据
- 在 Decision 的 reason 中说明决策依据
- 在 Action 的 params 中提供足够的信息

### 2. 错误处理

**优雅的降级：**
```python
def evaluate(self, event: SupervisorEvent, cursor: sqlite3.Cursor) -> Optional[Decision]:
    findings = []

    # 尝试评估 intent set，失败时记录 Finding 而不是抛出异常
    try:
        eval_result = self.evaluator_adapter.evaluate_intent_set(intent_set_path)
        # ... 处理结果
    except Exception as e:
        logger.error(f"Intent set evaluation failed: {e}", exc_info=True)
        findings.append(Finding(
            category="risk",
            severity="medium",
            description=f"Failed to evaluate intent set: {str(e)}",
            evidence=[str(e)],
            source="evaluator_adapter"
        ))

    # 继续其他检查...
```

**避免阻塞 Policy 执行：**
```python
# 不要在 Policy 中执行耗时操作
# 不好的做法：
large_file_content = read_large_file()  # 可能耗时很久

# 好的做法：
file_path = event.payload.get("file_path")
# 只记录路径，实际处理异步进行
```

### 3. 性能优化

**批量查询：**
```python
# 不好的做法：在循环中查询
for spec in specs:
    result = gate_adapter.check_redline_violation("agent", spec)

# 好的做法：批量查询
results = gate_adapter.batch_check_redline_violations("agent", specs)
```

**使用缓存：**
```python
class OnStepCompletedPolicy(BasePolicy):
    def __init__(self, db_path: Path):
        super().__init__(db_path)
        self._metadata_cache = {}

    def get_task_metadata(self, task_id: str, cursor: sqlite3.Cursor) -> dict:
        if task_id in self._metadata_cache:
            return self._metadata_cache[task_id]

        metadata = super().get_task_metadata(task_id, cursor)
        self._metadata_cache[task_id] = metadata
        return metadata
```

**避免重复工作：**
```python
# 在 Policy 初始化时加载配置，而不是每次 evaluate 时加载
class OnTaskCreatedPolicy(BasePolicy):
    def __init__(self, db_path: Path):
        super().__init__(db_path)
        self.redline_config = load_redline_config()  # 只加载一次
```

### 4. 测试

**单元测试：**
```python
import unittest
from agentos.core.supervisor.policies.on_task_created import OnTaskCreatedPolicy

class TestOnTaskCreatedPolicy(unittest.TestCase):
    def setUp(self):
        self.db_path = Path(":memory:")
        self.policy = OnTaskCreatedPolicy(self.db_path)

    def test_allow_decision_when_no_issues(self):
        event = SupervisorEvent(
            event_id="test_123",
            source=EventSource.EVENTBUS,
            task_id="task_abc",
            event_type="TASK_CREATED",
            ts="2025-01-28T10:00:00Z",
            payload={}
        )

        decision = self.policy.evaluate(event, mock_cursor)

        self.assertEqual(decision.decision_type, DecisionType.ALLOW)
        self.assertEqual(len(decision.findings), 0)

    def test_block_decision_on_redline_violation(self):
        event = SupervisorEvent(
            event_id="test_456",
            source=EventSource.EVENTBUS,
            task_id="task_xyz",
            event_type="TASK_CREATED",
            ts="2025-01-28T10:00:00Z",
            payload={
                "agent_spec": {"name": ""; "dangerous_commands": ["rm -rf /"]}
            }
        )

        decision = self.policy.evaluate(event, mock_cursor)

        self.assertEqual(decision.decision_type, DecisionType.BLOCK)
        self.assertGreater(len(decision.findings), 0)
```

**集成测试：**
```python
def test_policy_integration():
    # 设置完整的 Supervisor 环境
    supervisor = setup_supervisor(db_path)

    # 发送事件
    event = create_test_event()
    inbox_manager.insert_event(event)

    # 处理事件
    supervisor.processor.process_pending_events()

    # 验证结果
    audit_events = audit_adapter.get_audit_trail(event.task_id)
    assert len(audit_events) > 0
    assert audit_events[0]["event_type"].startswith("SUPERVISOR_")
```

### 5. 监控和调试

**添加详细日志：**
```python
def evaluate(self, event: SupervisorEvent, cursor: sqlite3.Cursor) -> Decision:
    logger.info(f"Evaluating TASK_CREATED for task {event.task_id}")

    # 记录关键步骤
    logger.debug(f"Checking redlines for agent_spec: {event.payload.get('agent_spec')}")

    # 记录决策依据
    logger.info(f"Decision: {decision_type.value} (findings={len(findings)})")

    return decision
```

**提供可观测性：**
```python
# 在 Policy 中记录性能指标
import time

start_time = time.time()
decision = self.evaluate(event, cursor)
elapsed = time.time() - start_time

logger.info(f"Policy evaluation took {elapsed:.3f}s")

# 如果有 metrics 系统，记录到 metrics
metrics.histogram("policy.evaluation_time", elapsed, tags={"policy": self.__class__.__name__})
```

## 常见问题

### Q1: Policy 抛出异常会怎样？

A: BasePolicy 的 `__call__` 方法会捕获异常，写入错误审计，然后重新抛出。SupervisorProcessor 会捕获异常，标记事件为 failed，并继续处理下一个事件。

### Q2: 如何在 Policy 之间共享数据？

A: 不建议在 Policy 之间共享状态。如果需要，可以通过：
1. 任务的 metadata 字段
2. 独立的缓存系统
3. 审计日志

### Q3: Policy 的执行顺序如何保证？

A: Supervisor 按照事件的时间顺序（`received_at`）处理。同一任务的事件会按顺序处理。

### Q4: 如何禁用某个 Policy？

A: 在注册时跳过该 Policy：

```python
# 不注册 OnStepCompletedPolicy
router.register("TASK_CREATED", OnTaskCreatedPolicy(db_path))
# router.register("TASK_STEP_COMPLETED", OnStepCompletedPolicy(db_path))  # 注释掉
router.register("TASK_FAILED", OnTaskFailedPolicy(db_path))
```

### Q5: 如何动态修改 Policy 行为？

A: 通过配置参数：

```python
config = {
    "error_rate_threshold": 0.5,  # 调整阈值
    "enable_runtime_check": False  # 禁用某个检查
}
policy = OnStepCompletedPolicy(db_path, config=config)
```

## 相关文档

- [Supervisor 主文档](./supervisor.md)
- [Supervisor Events](./supervisor_events.md)
- [Supervisor Runbook](./supervisor_runbook.md)
- [Validation Layers](./VALIDATION_LAYERS.md)
