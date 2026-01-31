# Phase 1 快速参考

**Mode-Task 集成快速查询指南**
**版本**: 1.0 | **日期**: 2026年1月30日

---

## 核心概念速查

| 概念 | 说明 | 位置 |
|------|------|------|
| **ModeGatewayProtocol** | Mode 决策接口协议 | `agentos/core/mode/gateway.py` |
| **ModeDecision** | Mode 决策结果数据类 | `agentos/core/mode/gateway.py` |
| **ModeDecisionVerdict** | 决策类型枚举（4 种） | `agentos/core/mode/gateway.py` |
| **ModeViolationError** | Mode 违规异常 | `agentos/core/task/errors.py` |
| **Integration Point** | Mode 集成点（Transition Validation） | `TaskStateMachine.transition()` |
| **Gateway Registry** | Gateway 注册和缓存 | `agentos/core/mode/gateway_registry.py` |
| **DefaultModeGateway** | 默认许可 Gateway | `agentos/core/mode/gateway_registry.py` |
| **RestrictedModeGateway** | 受限 Mode Gateway | `agentos/core/mode/gateway_registry.py` |

---

## 决策类型速查

| 类型 | 含义 | 系统行为 | 使用场景 |
|------|------|----------|----------|
| **APPROVED** | 批准，允许转换 | 继续执行转换 | 转换符合 Mode 约束 |
| **REJECTED** | 拒绝，永久不允许 | 抛出错误，状态不变 | 转换违反 Mode 规则 |
| **BLOCKED** | 阻止，需要外部批准 | 抛出错误 + 触发告警 | 需要人工/系统审批 |
| **DEFERRED** | 延迟，稍后重试 | 抛出错误（重试） | 异步决策，等待外部响应 |

---

## API 速查

### 创建带 Mode 的任务

```python
from agentos.core.task import TaskService

service = TaskService()

# Implementation mode（标准执行）
task = service.create_draft_task(
    metadata={
        "mode_id": "implementation",
        "name": "My task"
    }
)

# Design mode（仅规划）
task = service.create_draft_task(
    metadata={
        "mode_id": "design",
        "name": "Design task"
    }
)

# Autonomous mode（需要审批）
task = service.create_draft_task(
    metadata={
        "mode_id": "autonomous",
        "name": "High-risk task"
    }
)
```

### 状态转换

```python
# 正常转换
try:
    task = service.transition_task(
        task_id="task-001",
        to_state="RUNNING",
        actor_id="system",
        reason="Start execution"
    )
    print(f"Task is now: {task.status}")
except ModeViolationError as e:
    print(f"Mode violation: {e.reason}")
```

### 获取 Mode Gateway

```python
from agentos.core.mode.gateway_registry import get_mode_gateway

# 获取 Gateway
gateway = get_mode_gateway("implementation")

# 手动测试决策
decision = gateway.validate_transition(
    task_id="task-001",
    mode_id="implementation",
    from_state="QUEUED",
    to_state="RUNNING",
    metadata={}
)

print(f"Verdict: {decision.verdict}")
print(f"Reason: {decision.reason}")
```

### 注册自定义 Gateway

```python
from agentos.core.mode.gateway_registry import register_mode_gateway
from agentos.core.mode.gateway import ModeDecision, ModeDecisionVerdict

class MyGateway:
    def validate_transition(self, task_id, mode_id, from_state, to_state, metadata):
        if from_state == "QUEUED" and to_state == "RUNNING":
            # 自定义逻辑
            if metadata.get("priority") == "high":
                return ModeDecision(
                    verdict=ModeDecisionVerdict.APPROVED,
                    reason="High priority approved"
                )
            else:
                return ModeDecision(
                    verdict=ModeDecisionVerdict.BLOCKED,
                    reason="Requires approval",
                    metadata={"requires_approval": True}
                )
        return ModeDecision(verdict=ModeDecisionVerdict.APPROVED, reason="OK")

# 注册
register_mode_gateway("my_mode", MyGateway())
```

### 处理 Mode 违规

```python
from agentos.core.task.errors import ModeViolationError

try:
    service.transition_task(task_id, "RUNNING", "system", "Start")
except ModeViolationError as e:
    # 检查错误类型
    if "Blocked" in str(e):
        print(f"Task blocked: {e.reason}")
        # 发送审批请求
        requires_approval = e.metadata.get("requires_approval", False)
        if requires_approval:
            request_approval(e.task_id)

    elif "Deferred" in str(e):
        print(f"Task deferred: {e.reason}")
        # 安排重试
        retry_after = e.metadata.get("retry_after", "60s")
        schedule_retry(e.task_id, retry_after)

    else:  # Rejected
        print(f"Task rejected: {e.reason}")
        # 永久拒绝，记录并终止
        log_rejection(e.task_id)
```

---

## Mode 类型速查

| Mode | 用途 | 执行 | 限制 | 适用场景 |
|------|------|------|------|----------|
| **implementation** | 标准执行 | ✅ | 无 | 生产任务，数据处理 |
| **design** | 规划设计 | ❌ | 不能执行 | 方案设计，架构讨论 |
| **chat** | 交互对话 | ❌ | 不能自动执行 | 客服，实时问答 |
| **autonomous** | 自主决策 | ⚠️ | 需要审批 | 高风险操作，生产部署 |
| **无 Mode** | 向后兼容 | ✅ | 无 | 简单任务，现有任务 |

---

## 状态转换速查

### Implementation Mode
```
DRAFT → APPROVED → QUEUED → RUNNING → VERIFYING → VERIFIED → DONE ✅
                                ↓
                             FAILED → QUEUED (retry) ✅
```

### Design Mode
```
DRAFT → APPROVED → QUEUED → ❌ RUNNING (BLOCKED)
                          ↓
                       CANCELED ✅
```

### Autonomous Mode
```
DRAFT → APPROVED → QUEUED → ⚠️ RUNNING (need approval)
                                ↓
                            (approved)
                                ↓
                             RUNNING ✅
```

---

## 命令速查

### Python 脚本

```bash
# 创建 implementation 任务
python -c "
from agentos.core.task import TaskService
service = TaskService()
task = service.create_draft_task(metadata={'mode_id': 'implementation', 'name': 'Test'})
print(f'Created: {task.task_id}')
"

# 创建 design 任务
python -c "
from agentos.core.task import TaskService
service = TaskService()
task = service.create_draft_task(metadata={'mode_id': 'design', 'name': 'Design'})
print(f'Created: {task.task_id}')
"

# 测试 Mode 决策
python -c "
from agentos.core.mode.gateway_registry import get_mode_gateway
gateway = get_mode_gateway('design')
decision = gateway.validate_transition('test', 'design', 'QUEUED', 'RUNNING', {})
print(f'Verdict: {decision.verdict}, Reason: {decision.reason}')
"
```

### 测试命令

```bash
# 运行所有 Mode 测试
pytest tests/unit/mode/ \
       tests/integration/test_mode_task_lifecycle.py \
       tests/e2e/test_mode_task_e2e.py \
       -v

# 运行单元测试
pytest tests/unit/mode/test_mode_gateway.py -v

# 运行集成测试
pytest tests/integration/test_mode_task_lifecycle.py -v

# 运行 E2E 测试
pytest tests/e2e/test_mode_task_e2e.py -v

# 运行压力测试
pytest tests/stress/test_mode_stress.py -v

# 运行回归测试
pytest tests/integration/test_mode_regression.py -v

# 测试覆盖率
pytest tests/unit/mode/ \
       --cov=agentos.core.mode \
       --cov=agentos.core.task.state_machine \
       --cov-report=html

# 类型检查
mypy agentos/core/mode/ agentos/core/task/state_machine.py
```

---

## 故障排除速查

### 常见错误

| 错误 | 可能原因 | 解决方案 |
|------|----------|----------|
| `ModeViolationError: Design mode...` | Design mode 不能执行 | 改用 implementation mode 或取消任务 |
| `ModeViolationError: Blocked` | 需要审批 | 发送审批请求，等待批准 |
| `ModeViolationError: Deferred` | 异步决策进行中 | 稍后重试（检查 retry_after） |
| `Gateway not found` | Mode ID 拼写错误 | 检查 mode_id 是否正确 |
| `Gateway timeout` | Gateway 响应慢 | 优化 Gateway 实现，确保 < 10ms |
| `Database is locked` | SQLite 并发限制 | 减少并发数或迁移到 PostgreSQL |

### 调试步骤

1. **检查任务 Mode**:
```python
task = service.get_task(task_id)
mode_id = json.loads(task.metadata).get("mode_id")
print(f"Mode: {mode_id}")
```

2. **检查 Gateway**:
```python
from agentos.core.mode.gateway_registry import get_mode_gateway
gateway = get_mode_gateway(mode_id)
print(f"Gateway: {gateway.__class__.__name__}")
```

3. **手动测试决策**:
```python
decision = gateway.validate_transition(
    task_id=task_id,
    mode_id=mode_id,
    from_state=task.status,
    to_state="RUNNING",
    metadata=json.loads(task.metadata)
)
print(f"Verdict: {decision.verdict}")
print(f"Reason: {decision.reason}")
```

4. **查看审计日志**:
```python
history = service.get_transition_history(task_id)
for entry in history:
    mode_decision = entry.get("metadata", {}).get("mode_decision")
    if mode_decision:
        print(f"Decision: {mode_decision}")
```

---

## 性能基准

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| **Transition validation** | < 10ms | 2.54ms | ✅ 超出 74% |
| **Gateway lookup** | < 1ms | 0.0001ms | ✅ 超出 99.99% |
| **Full lifecycle** | < 1s | ~100ms | ✅ |
| **Throughput** | > 10/sec | ~20/sec | ✅ |
| **Cache hit rate** | > 90% | ~95% | ✅ |
| **Memory (1000 tasks)** | < 100MB | ~80MB | ✅ |

---

## 文件位置

### 核心文件

| 文件 | 说明 | 代码行数 |
|------|------|----------|
| `agentos/core/mode/gateway.py` | Gateway 协议定义 | 169 |
| `agentos/core/mode/gateway_registry.py` | Gateway 注册和缓存 | 323 |
| `agentos/core/task/state_machine.py` | State Machine 集成 | +150 |
| `agentos/core/task/errors.py` | ModeViolationError | +30 |

### 测试文件

| 文件 | 测试数 | 说明 |
|------|--------|------|
| `tests/unit/mode/test_mode_gateway.py` | 27 | Gateway 单元测试 |
| `tests/unit/mode/test_mode_event_listener.py` | 22 | Event Listener 测试 |
| `tests/integration/test_mode_task_lifecycle.py` | 25 | 生命周期集成测试 |
| `tests/integration/test_mode_regression.py` | 21 | 回归测试 |
| `tests/e2e/test_mode_task_e2e.py` | 13 | E2E 测试 |
| `tests/stress/test_mode_stress.py` | 9 | 压力测试 |

### 文档文件

| 文件 | 说明 |
|------|------|
| `PHASE1_MODE_TASK_INTEGRATION_SUMMARY.md` | Phase 1 总结 |
| `docs/mode/MODE_TASK_INTEGRATION_GUIDE.md` | 技术集成指南 |
| `docs/mode/MODE_TASK_USER_GUIDE.md` | 用户指南 |
| `PHASE1_ACCEPTANCE_CHECKLIST.md` | 验收清单 |
| `PHASE1_KNOWN_ISSUES.md` | 已知问题 |
| `PHASE1_QUICK_REFERENCE.md` | 本文档 |

---

## 配置示例

### 基本配置

```python
# 注册默认 Gateway
from agentos.core.mode.gateway_registry import register_default_gateways
register_default_gateways()

# 注册自定义 Gateway
from agentos.core.mode.gateway_registry import register_mode_gateway
register_mode_gateway("my_mode", MyCustomGateway())
```

### Gateway 配置

```python
from agentos.core.mode.gateway_registry import RestrictedModeGateway

# 配置受限 Mode
restricted_gateway = RestrictedModeGateway(
    mode_id="restricted_mode",
    blocked_transitions={
        "QUEUED": {"RUNNING"},  # Block execution
        "VERIFIED": {"DONE"},   # Require approval for completion
    }
)

register_mode_gateway("restricted_mode", restricted_gateway)
```

---

## 监控指标

### 关键指标

```python
# 伪代码：收集监控指标
metrics = {
    # Gateway 性能
    "mode_gateway_latency_p50": 2.0,  # ms
    "mode_gateway_latency_p99": 8.0,  # ms
    "mode_gateway_latency_max": 15.0,  # ms

    # 决策分布
    "mode_decision_approved": 95,  # %
    "mode_decision_rejected": 3,   # %
    "mode_decision_blocked": 1.5,  # %
    "mode_decision_deferred": 0.5, # %

    # 缓存效率
    "mode_gateway_cache_hit_rate": 95,  # %
    "mode_gateway_cache_size": 10,      # entries

    # Fail-safe
    "mode_gateway_failsafe_count": 0,   # count
    "mode_gateway_failsafe_rate": 0.0,  # %
}
```

### 告警阈值

| 指标 | 正常 | 警告 | 严重 |
|------|------|------|------|
| Gateway latency p99 | < 10ms | > 20ms | > 50ms |
| Violation rate | < 5% | > 10% | > 20% |
| Fail-safe rate | < 0.1% | > 1% | > 5% |
| Cache hit rate | > 90% | < 80% | < 70% |

---

## 最佳实践

### ✅ DO（推荐）

- ✅ 为所有新任务指定 mode_id
- ✅ 使用 implementation mode 进行实际执行
- ✅ 使用 design mode 进行规划和评审
- ✅ 在 Gateway 中快速返回（< 10ms）
- ✅ 使用 DEFERRED 处理异步决策
- ✅ 记录详细的 Mode 决策日志
- ✅ 监控 Gateway 性能指标
- ✅ 处理 ModeViolationError
- ✅ 测试自定义 Gateway

### ❌ DON'T（避免）

- ❌ 不要在运行时切换 Mode
- ❌ 不要在 Gateway 中进行慢操作
- ❌ 不要忽略 ModeViolationError
- ❌ 不要假设 Mode 总是存在
- ❌ 不要在 Gateway 中修改任务状态
- ❌ 不要依赖 Gateway 的副作用
- ❌ 不要阻塞 Gateway（同步模型）
- ❌ 不要在 Gateway 中抛出非 ModeViolation 错误

---

## 快速示例

### 完整的任务生命周期（Implementation Mode）

```python
from agentos.core.task import TaskService

service = TaskService()

# 1. 创建任务
task = service.create_draft_task(
    metadata={"mode_id": "implementation", "name": "Data processing"}
)
print(f"Created: {task.task_id}")

# 2. 批准
task = service.transition_task(task.task_id, "APPROVED", "user-001", "Approved")
print(f"Status: {task.status}")  # APPROVED

# 3. 排队
task = service.transition_task(task.task_id, "QUEUED", "system", "Queued")
print(f"Status: {task.status}")  # QUEUED

# 4. 执行
task = service.transition_task(task.task_id, "RUNNING", "runner-001", "Start")
print(f"Status: {task.status}")  # RUNNING

# 5. 验证
task = service.transition_task(task.task_id, "VERIFYING", "system", "Verify")
print(f"Status: {task.status}")  # VERIFYING

# 6. 已验证
task = service.transition_task(task.task_id, "VERIFIED", "system", "Verified")
print(f"Status: {task.status}")  # VERIFIED

# 7. 完成
task = service.transition_task(task.task_id, "DONE", "system", "Done")
print(f"Status: {task.status}")  # DONE
```

### Design Mode 阻止执行

```python
# 1. 创建 design 任务
task = service.create_draft_task(
    metadata={"mode_id": "design", "name": "Design review"}
)

# 2. 批准并排队
service.transition_task(task.task_id, "APPROVED", "user", "Approved")
service.transition_task(task.task_id, "QUEUED", "system", "Queued")

# 3. 尝试执行（将被阻止）
try:
    service.transition_task(task.task_id, "RUNNING", "runner", "Start")
except ModeViolationError as e:
    print(f"Expected: {e}")  # Design mode tasks cannot execute
```

### Autonomous Mode 审批流程

```python
# 1. 创建 autonomous 任务
task = service.create_draft_task(
    metadata={"mode_id": "autonomous", "name": "High-risk operation"}
)

# 2. 批准并排队
service.transition_task(task.task_id, "APPROVED", "user", "Approved")
service.transition_task(task.task_id, "QUEUED", "system", "Queued")

# 3. 尝试执行（将被阻止，需要审批）
try:
    service.transition_task(task.task_id, "RUNNING", "system", "Auto-start")
except ModeViolationError as e:
    print(f"Blocked: {e.reason}")
    # 发送审批请求
    request_approval(task.task_id, e.metadata)

# 4. 审批后重试（由审批系统触发）
def on_approval_granted(task_id):
    # 更新任务标记为已批准
    service.update_task_metadata(task_id, {"approval_granted": True})
    # 重新尝试转换
    service.transition_task(task_id, "RUNNING", "approver", "Approved")
```

---

## 相关链接

- [Phase 1 实施总结](./PHASE1_MODE_TASK_INTEGRATION_SUMMARY.md)
- [技术集成指南](./docs/mode/MODE_TASK_INTEGRATION_GUIDE.md)
- [用户指南](./docs/mode/MODE_TASK_USER_GUIDE.md)
- [验收清单](./PHASE1_ACCEPTANCE_CHECKLIST.md)
- [已知问题](./PHASE1_KNOWN_ISSUES.md)
- [Task 23 测试报告](./TASK23_MODE_TASK_TESTING_REPORT.md)

---

**文档版本**: 1.0
**最后更新**: 2026年1月30日
**维护**: 保持文档与代码同步更新
