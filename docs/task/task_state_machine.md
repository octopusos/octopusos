# Task State Machine

## 状态图（State Diagram）

```
                                    [DRAFT]
                                      |
                         +------------+------------+
                         |                         |
                    [APPROVED]                [CANCELED]
                         |
                         v
                     [QUEUED] ----------------------+
                         |                          |
                         v                          |
                    [RUNNING] --------------------+ |
                         |                        | |
                         +-------+--------+       | |
                         |       |        |       | |
                         v       v        v       | |
                   [VERIFYING] [FAILED] [CANCELED]| |
                         |       |                | |
                         v       |                | |
                   [VERIFIED]    |                | |
                         |       |                | |
                         v       |                | |
                      [DONE]     +------>[QUEUED] | |
                                         (retry)  | |
                                                  | |
                  [CANCELED] <--------------------+-+
```

## 状态定义

| 状态 | 描述 | 类型 | 备注 |
|------|------|------|------|
| `DRAFT` | 任务草稿 | 初始 | 等待批准 |
| `APPROVED` | 已批准 | 审批 | 准备进入队列 |
| `QUEUED` | 已排队 | 执行 | 等待执行器 |
| `RUNNING` | 执行中 | 执行 | 正在执行 |
| `VERIFYING` | 验证中 | 验证 | 执行后验证 |
| `VERIFIED` | 已验证 | 验证 | 准备标记完成 |
| `DONE` | 已完成 | 终态 | 成功完成 |
| `FAILED` | 失败 | 终态 | 可重试 |
| `CANCELED` | 已取消 | 终态 | 用户/系统取消 |

## 转换规则表（Transition Table）

### 所有允许的转换

| 从状态 | 到状态 | 允许 | 原因 |
|--------|--------|------|------|
| DRAFT | APPROVED | ✅ | 任务被批准执行 |
| DRAFT | CANCELED | ✅ | 草稿阶段取消 |
| APPROVED | QUEUED | ✅ | 任务进入执行队列 |
| APPROVED | CANCELED | ✅ | 批准后取消 |
| QUEUED | RUNNING | ✅ | 开始执行 |
| QUEUED | CANCELED | ✅ | 排队时取消 |
| RUNNING | VERIFYING | ✅ | 执行完成，开始验证 |
| RUNNING | FAILED | ✅ | 执行失败 |
| RUNNING | CANCELED | ✅ | 执行时取消 |
| VERIFYING | VERIFIED | ✅ | 验证通过 |
| VERIFYING | FAILED | ✅ | 验证失败 |
| VERIFYING | CANCELED | ✅ | 验证时取消 |
| VERIFIED | DONE | ✅ | 标记为完成 |
| FAILED | QUEUED | ✅ | 重试（可选） |

### 禁止的转换示例

| 从状态 | 到状态 | 原因 |
|--------|--------|------|
| DRAFT | QUEUED | 必须先经过 APPROVED |
| DRAFT | RUNNING | 必须经过 APPROVED 和 QUEUED |
| APPROVED | RUNNING | 必须先经过 QUEUED |
| DONE | RUNNING | 终态，不能重启 |
| CANCELED | RUNNING | 终态，不能重启 |

## 核心原则

1. **没有 APPROVED 不允许执行** - 任务必须先批准才能进入 QUEUED/RUNNING
2. **所有转换都有审计** - 每次状态变更都记录在 task_audits 表
3. **幂等性** - 转换到相同状态是安全的
4. **原子性** - 状态转换在事务中完成
5. **可追溯** - 完整的转换历史

## API 参考

### TaskStateMachine 类

```python
class TaskStateMachine:
    def __init__(self, db_path: Optional[Path] = None)

    def can_transition(self, frm: str, to: str) -> bool
    def validate_or_raise(self, frm: str, to: str) -> None
    def transition(
        self,
        task_id: str,
        to: str,
        actor: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task

    def get_valid_transitions(self, from_state: str) -> Set[str]
    def get_transition_history(self, task_id: str) -> list
    def is_terminal_state(self, state: str) -> bool
```

## 使用示例

### 基本生命周期

```python
from agentos.core.task.state_machine import TaskStateMachine
from agentos.core.task.manager import TaskManager

# 创建任务
tm = TaskManager()
task = tm.create_task(title="实现功能 X")
print(f"任务创建，状态: {task.status}")  # draft

# 初始化状态机
sm = TaskStateMachine()

# 批准任务
task = sm.transition(
    task_id=task.task_id,
    to="approved",
    actor="product_owner",
    reason="功能已批准用于 Sprint 5"
)

# 进入队列
task = sm.transition(
    task_id=task.task_id,
    to="queued",
    actor="scheduler",
    reason="排队等待执行"
)

# 开始执行
task = sm.transition(
    task_id=task.task_id,
    to="running",
    actor="executor_001",
    reason="开始执行任务"
)

# 完成执行
task = sm.transition(
    task_id=task.task_id,
    to="verifying",
    actor="executor_001",
    reason="执行完成，验证结果"
)

# 验证并完成
task = sm.transition(
    task_id=task.task_id,
    to="verified",
    actor="verifier",
    reason="所有检查通过"
)

task = sm.transition(
    task_id=task.task_id,
    to="done",
    actor="system",
    reason="任务成功完成"
)
```

### 错误处理

```python
from agentos.core.task.errors import InvalidTransitionError, TaskNotFoundError

sm = TaskStateMachine()

try:
    # 尝试无效转换
    task = sm.transition(
        task_id="task_001",
        to="running",  # 不能从 draft 直接到 running
        actor="system",
        reason="快速启动"
    )
except InvalidTransitionError as e:
    print(f"无效转换: {e}")
    # 获取有效转换
    valid = sm.get_valid_transitions("draft")
    print(f"从 draft 可转换到: {valid}")
```

### 重试失败任务

```python
# 任务执行失败
task = sm.transition(
    task_id="task_001",
    to="failed",
    actor="executor",
    reason="执行超时",
    metadata={"error": "NetworkTimeoutError", "retry_attempt": 0}
)

# 重试任务
task = sm.transition(
    task_id="task_001",
    to="queued",
    actor="scheduler",
    reason="重试失败任务",
    metadata={"retry_attempt": 1}
)
```

## 审计追踪

每次状态转换都会在 `task_audits` 表中记录：

```json
{
  "from_state": "draft",
  "to_state": "approved",
  "actor": "user@example.com",
  "reason": "任务审核通过",
  "transition_metadata": {
    "reviewer": "john",
    "review_id": "rev_123"
  }
}
```

## 最佳实践

1. **转换前验证** - 使用 `can_transition()` 或 `validate_or_raise()`
2. **提供有意义的原因** - `reason` 参数帮助调试和审计
3. **使用元数据** - 在 `metadata` 中存储额外上下文
4. **优雅处理错误** - 捕获 `InvalidTransitionError` 和 `TaskNotFoundError`
5. **检查终态** - 使用 `is_terminal_state()` 避免从终态转换
6. **审查审计追踪** - 使用 `get_transition_history()` 理解任务生命周期

## 集成

### 与 TaskManager 集成

```python
from agentos.core.task.manager import TaskManager
from agentos.core.task.state_machine import TaskStateMachine

class TaskManagerWithStateMachine(TaskManager):
    def __init__(self, db_path=None):
        super().__init__(db_path)
        self.state_machine = TaskStateMachine(db_path)

    def approve_task(self, task_id: str, actor: str, reason: str):
        """批准任务 (DRAFT -> APPROVED)"""
        return self.state_machine.transition(
            task_id, "approved", actor, reason
        )

    def queue_task(self, task_id: str):
        """排队任务 (APPROVED -> QUEUED)"""
        return self.state_machine.transition(
            task_id, "queued", "scheduler", "任务排队执行"
        )
```

### 与 Supervisor 集成

```python
from agentos.core.task.state_machine import TaskStateMachine
from agentos.core.supervisor.models import DecisionType

class SupervisorIntegration:
    def __init__(self, db_path=None):
        self.state_machine = TaskStateMachine(db_path)

    def enforce_decision(self, task_id: str, decision):
        if decision.decision_type == DecisionType.BLOCK:
            return self.state_machine.transition(
                task_id,
                "canceled",
                "supervisor",
                f"已阻止: {decision.reason}"
            )
        elif decision.decision_type == DecisionType.ALLOW:
            return self.state_machine.transition(
                task_id,
                "verifying",
                "supervisor",
                f"已允许: {decision.reason}"
            )
```

## 参考

- Task Models: `agentos/core/task/models.py`
- Task Manager: `agentos/core/task/manager.py`
- Supervisor Models: `agentos/core/supervisor/models.py`
- Database Schema: `agentos/store/migrations/v06_task_driven.sql`
