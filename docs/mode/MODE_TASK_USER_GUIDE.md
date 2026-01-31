# Mode-Task 集成用户指南

**版本**: 1.0
**更新日期**: 2026年1月30日
**目标用户**: AgentOS 用户、任务创建者、系统操作员

---

## 目录

1. [快速开始](#快速开始)
2. [使用场景](#使用场景)
3. [常见任务](#常见任务)
4. [Mode 决策理解](#mode-决策理解)
5. [故障排除](#故障排除)
6. [最佳实践](#最佳实践)
7. [命令行示例](#命令行示例)

---

## 快速开始

### 5 分钟入门

#### 1. 创建一个带 Mode 的任务

```python
from agentos.core.task import TaskService

service = TaskService()

# 创建 implementation mode 任务（标准执行模式）
task = service.create_draft_task(
    metadata={
        "mode_id": "implementation",
        "name": "My first task",
        "description": "This task will execute normally"
    }
)

print(f"Created task: {task.task_id}")
print(f"Status: {task.status}")  # "DRAFT"
print(f"Mode: {task.metadata.get('mode_id')}")  # "implementation"
```

#### 2. 转换任务状态

```python
# 批准任务
task = service.transition_task(
    task_id=task.task_id,
    to_state="APPROVED",
    actor_id="user-001",
    reason="Ready for execution"
)

# 排队执行
task = service.transition_task(
    task_id=task.task_id,
    to_state="QUEUED",
    actor_id="system",
    reason="Queued for execution"
)

# 开始执行（implementation mode 允许）
task = service.transition_task(
    task_id=task.task_id,
    to_state="RUNNING",
    actor_id="runner-001",
    reason="Starting execution"
)

print(f"Task is now: {task.status}")  # "RUNNING"
```

#### 3. 验证 Mode 集成工作

尝试创建一个 design mode 任务并尝试执行：

```python
# 创建 design mode 任务（仅规划，不执行）
design_task = service.create_draft_task(
    metadata={
        "mode_id": "design",
        "name": "Design task",
        "description": "This task is for planning only"
    }
)

# 批准并排队
service.transition_task(design_task.task_id, "APPROVED", "user-001", "Approved")
service.transition_task(design_task.task_id, "QUEUED", "system", "Queued")

# 尝试执行（将被 Mode Gateway 阻止）
try:
    service.transition_task(design_task.task_id, "RUNNING", "runner-001", "Start")
except ModeViolationError as e:
    print(f"Expected error: {e}")
    print("Design mode tasks cannot execute - Mode integration works!")
```

**预期输出**:
```
Expected error: Mode violation for task xxx: Design mode tasks cannot transition to RUNNING
Design mode tasks cannot execute - Mode integration works!
```

---

## 使用场景

### 场景 1: Implementation Mode 任务

**何时使用**:
- 标准的任务执行
- 需要实际运行代码
- 生产环境任务
- 自动化工作流

**行为**:
- ✅ 可以完整执行所有状态转换
- ✅ DRAFT → APPROVED → QUEUED → RUNNING → VERIFYING → VERIFIED → DONE
- ✅ 支持失败重试: RUNNING → FAILED → QUEUED
- ✅ 无特殊限制

**创建示例**:
```python
task = service.create_draft_task(
    metadata={
        "mode_id": "implementation",
        "task_type": "data_processing",
        "priority": "high",
        "timeout": 3600
    }
)
```

**适用任务类型**:
- 数据处理任务
- API 调用任务
- 文件操作任务
- 定时任务
- 批处理任务

---

### 场景 2: Design Mode 任务

**何时使用**:
- 任务规划和设计
- 方案评估
- 架构讨论
- 原型设计
- 需求分析

**限制**:
- ❌ **不能执行**: QUEUED → RUNNING 转换被阻止
- ✅ 可以创建和审批
- ✅ 可以取消
- ✅ 可以查看和编辑

**行为**:
```
DRAFT → APPROVED → QUEUED → ❌ RUNNING (BLOCKED)
                          ↓
                       CANCELED (允许)
```

**创建示例**:
```python
task = service.create_draft_task(
    metadata={
        "mode_id": "design",
        "purpose": "design_review",
        "design_doc": "https://docs.example.com/design-001",
        "reviewers": ["user-001", "user-002"]
    }
)
```

**最佳实践**:
- 使用 design mode 进行规划，完成后切换到 implementation mode 创建新任务执行
- 在 metadata 中记录设计决策
- 使用 design 任务作为 implementation 任务的前置依赖

**错误处理**:
```python
try:
    service.transition_task(design_task_id, "RUNNING", "system", "Execute")
except ModeViolationError as e:
    # 预期的错误，design mode 不能执行
    logger.info(f"Design task cannot execute: {e}")
    # 如果需要执行，创建新的 implementation 任务
    impl_task = service.create_draft_task(
        metadata={
            "mode_id": "implementation",
            "based_on_design": design_task_id,
            "name": f"Implementation of {design_task.name}"
        }
    )
```

---

### 场景 3: Chat Mode 任务

**何时使用**:
- 交互式对话任务
- 需要人工输入
- 问答场景
- 客服机器人
- 实时交互

**限制**:
- ❌ **不能自动执行**: QUEUED → RUNNING 转换被阻止
- ✅ 可以手动转换到 RUNNING（通过特殊权限）
- ✅ 支持交互式会话
- ✅ 可以随时取消

**行为**:
- Chat mode 任务需要人工触发执行
- 不会被自动调度器执行
- 适合需要实时用户交互的场景

**创建示例**:
```python
task = service.create_draft_task(
    metadata={
        "mode_id": "chat",
        "chat_type": "customer_support",
        "user_id": "user-12345",
        "channel": "web",
        "session_id": "session-abc123"
    }
)
```

**适用场景**:
- 客户支持对话
- 交互式调试
- 实时问答
- 人机协作任务

---

### 场景 4: Autonomous Mode 任务

**何时使用**:
- 自主决策任务
- 高风险操作
- 需要审批的任务
- 需要人工监督

**限制**:
- ⚠️ **需要审批**: QUEUED → RUNNING 转换需要批准
- ⚠️ **检查点**: 执行过程中可能需要多次批准
- ✅ 获得批准后可以正常执行

**行为**:
```
DRAFT → APPROVED → QUEUED → ⚠️ BLOCKED (等待批准)
                                  ↓
                              (批准后)
                                  ↓
                               RUNNING
```

**创建示例**:
```python
task = service.create_draft_task(
    metadata={
        "mode_id": "autonomous",
        "autonomy_level": "supervised",
        "risk_level": "high",
        "approval_required": True,
        "approver": "manager-001"
    }
)
```

**批准流程**:
1. 任务创建并排队
2. 尝试转换到 RUNNING 时被 BLOCKED
3. 系统发送审批请求告警
4. 审批人审核并批准
5. 系统解除阻止
6. 重新尝试转换到 RUNNING
7. 成功执行

**审批示例**（伪代码）:
```python
# 任务被阻止时
try:
    service.transition_task(auto_task_id, "RUNNING", "system", "Auto-start")
except ModeViolationError as e:
    if "Blocked" in str(e):
        # 发送审批请求
        send_approval_request(
            task_id=auto_task_id,
            approver="manager-001",
            reason="Autonomous task requires approval"
        )

# 审批人批准后
def on_approval_granted(task_id):
    # 更新任务元数据，标记为已批准
    service.update_task_metadata(
        task_id,
        {"approval_granted": True, "approved_by": "manager-001"}
    )

    # 重新尝试转换（此时应该成功）
    service.transition_task(task_id, "RUNNING", "system", "Approved and starting")
```

---

### 场景 5: 无 Mode 任务（向后兼容）

**何时使用**:
- 现有任务（未指定 Mode）
- 简单任务不需要 Mode 控制
- 向后兼容场景

**行为**:
- ✅ 完全按原逻辑执行
- ✅ 不进行 Mode 验证
- ✅ 与 Phase 1 之前的行为一致

**创建示例**:
```python
# 不指定 mode_id，按原逻辑执行
task = service.create_draft_task(
    metadata={
        "name": "Legacy task",
        "type": "simple_task"
        # 注意：没有 mode_id
    }
)

# 所有转换按原规则进行，无 Mode 限制
task = service.transition_task(task.task_id, "APPROVED", "user", "Approve")
task = service.transition_task(task.task_id, "QUEUED", "system", "Queue")
task = service.transition_task(task.task_id, "RUNNING", "runner", "Execute")
# 成功，无 Mode 检查
```

---

## 常见任务

### 创建带 Mode 的任务

**方式 1: 通过 TaskService**

```python
from agentos.core.task import TaskService

service = TaskService()

task = service.create_draft_task(
    metadata={
        "mode_id": "implementation",  # 必需：指定 Mode
        "name": "Data processing task",
        "description": "Process user data",
        "priority": "high"
    }
)
```

**方式 2: 通过 CLI（如果可用）**

```bash
agentos task create \
  --mode implementation \
  --name "Data processing task" \
  --metadata '{"priority": "high"}'
```

**方式 3: 通过 API**

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "mode_id": "implementation",
      "name": "Data processing task"
    }
  }'
```

### 切换任务 Mode

**注意**: 当前版本不支持运行时切换 Mode。如需更改 Mode，建议：

**方案 1: 创建新任务**（推荐）

```python
# 基于旧任务创建新任务
old_task = service.get_task(old_task_id)
old_metadata = json.loads(old_task.metadata)

new_task = service.create_draft_task(
    metadata={
        **old_metadata,  # 复制旧元数据
        "mode_id": "implementation",  # 新 Mode
        "replaces_task": old_task_id,  # 记录关联
    }
)

# 取消旧任务
service.transition_task(old_task_id, "CANCELED", "user", "Replaced by new task")
```

**方案 2: 更新元数据（仅限 DRAFT 状态）**

```python
# 仅当任务在 DRAFT 状态时可以修改
if task.status == "DRAFT":
    task.metadata = json.dumps({
        **json.loads(task.metadata),
        "mode_id": "implementation"
    })
    service.update_task(task)
else:
    print("Cannot change mode for non-DRAFT tasks")
```

### 查看 Mode 决策历史

Mode 决策记录在审计追踪中：

```python
# 获取任务的转换历史
history = service.get_transition_history(task_id)

for entry in history:
    if "mode_decision" in entry.get("metadata", {}):
        decision = entry["metadata"]["mode_decision"]
        print(f"Transition: {entry['from_state']} -> {entry['to_state']}")
        print(f"Mode decision: {decision['verdict']}")
        print(f"Reason: {decision['reason']}")
        print(f"Timestamp: {decision['timestamp']}")
        print("---")
```

### 处理 Mode 违规

**捕获和处理 ModeViolationError**:

```python
from agentos.core.task.errors import ModeViolationError

try:
    task = service.transition_task(
        task_id,
        "RUNNING",
        "system",
        "Auto-start"
    )
except ModeViolationError as e:
    # 检查违规类型
    if "Blocked" in str(e):
        print(f"Task blocked: {e.reason}")
        print(f"Requires approval: {e.metadata.get('requires_approval')}")
        # 发送审批请求
        request_approval(e.task_id, e.metadata)

    elif "Deferred" in str(e):
        print(f"Task deferred: {e.reason}")
        retry_after = e.metadata.get("retry_after", "60s")
        print(f"Retry after: {retry_after}")
        # 安排重试
        schedule_retry(e.task_id, retry_after)

    else:  # Rejected
        print(f"Task rejected: {e.reason}")
        # 任务不能执行，记录并终止
        log_rejection(e.task_id, e.reason)
```

---

## Mode 决策理解

### 如何解读 Mode 决策

Mode 决策包含以下信息：

```python
{
    "verdict": "BLOCKED",           # 决策类型
    "reason": "Requires approval",  # 人类可读原因
    "metadata": {                   # 额外信息
        "requires_approval": True,
        "approval_type": "human",
        "checkpoint_id": "exec-001"
    },
    "timestamp": "2026-01-30T12:34:56.789Z",
    "gateway_id": "autonomous_approval_gate"
}
```

### APPROVED vs REJECTED

| 方面 | APPROVED | REJECTED |
|------|----------|----------|
| **含义** | 批准，允许转换 | 拒绝，不允许转换 |
| **状态** | 转换成功 | 转换失败，状态不变 |
| **日志** | DEBUG 级别 | ERROR 级别 |
| **告警** | 无 | 无（预期的拒绝） |
| **重试** | 不需要 | 无意义（永久拒绝） |
| **审计** | 记录在审计追踪 | 记录在审计追踪 |

### 如何处理 BLOCKED

**BLOCKED 表示需要外部批准**:

1. **识别阻止原因**:
```python
except ModeViolationError as e:
    if "Blocked" in str(e):
        reason = e.reason
        requires_approval = e.metadata.get("requires_approval", False)
        approval_type = e.metadata.get("approval_type", "unknown")
```

2. **发送审批请求**:
```python
if requires_approval:
    if approval_type == "human":
        # 发送给人工审批
        send_email_to_approver(
            task_id=e.task_id,
            reason=e.reason,
            approval_url=f"https://ui.example.com/approve/{e.task_id}"
        )
    elif approval_type == "system":
        # 调用系统审批服务
        approval_service.request_approval(
            task_id=e.task_id,
            reason=e.reason
        )
```

3. **等待批准**:
```python
# 任务保持当前状态（QUEUED）
# 系统监听审批事件
```

4. **批准后重试**:
```python
def on_approval_granted(task_id, approver_id):
    # 更新任务标记为已批准
    service.update_task_metadata(
        task_id,
        {"approval_granted": True, "approved_by": approver_id}
    )

    # 重新尝试转换
    try:
        service.transition_task(
            task_id,
            "RUNNING",
            approver_id,
            "Approved and starting"
        )
    except ModeViolationError:
        # 仍然被阻止，可能需要其他批准
        pass
```

---

## 故障排除

### Mode 违规

#### 问题: "Design mode tasks cannot transition to RUNNING"

**原因**: Design mode 任务不允许执行

**解决方法**:
1. 确认任务确实应该是 design mode
2. 如果需要执行，创建新的 implementation 任务
3. 或者取消 design 任务

```python
# 方案 A: 创建新任务执行
impl_task = service.create_draft_task(
    metadata={
        "mode_id": "implementation",
        "based_on_design": design_task_id
    }
)

# 方案 B: 取消 design 任务
service.transition_task(
    design_task_id,
    "CANCELED",
    "user",
    "Design complete, execution not needed"
)
```

#### 问题: "Autonomous mode requires approval"

**原因**: Autonomous mode 任务需要批准才能执行

**解决方法**:
1. 发送审批请求给审批人
2. 等待审批
3. 批准后重试转换

```python
# 步骤 1: 捕获阻止
try:
    service.transition_task(task_id, "RUNNING", "system", "Auto-start")
except ModeViolationError as e:
    if e.metadata.get("requires_approval"):
        # 步骤 2: 请求审批
        request_approval(task_id, e.metadata.get("approval_type"))

# 步骤 3: 审批后重试（在审批回调中）
def on_approval(task_id):
    service.transition_task(task_id, "RUNNING", "approver", "Approved")
```

### 任务被阻止

#### 检查清单

1. **检查任务 Mode**:
```python
task = service.get_task(task_id)
mode_id = json.loads(task.metadata).get("mode_id")
print(f"Task mode: {mode_id}")
```

2. **检查当前状态和目标状态**:
```python
print(f"Current state: {task.status}")
print(f"Attempting transition to: RUNNING")
```

3. **检查 Mode Gateway 配置**:
```python
from agentos.core.mode.gateway_registry import get_mode_gateway

gateway = get_mode_gateway(mode_id)
print(f"Gateway: {gateway.__class__.__name__}")
print(f"Gateway ID: {gateway.gateway_id}")
```

4. **手动测试 Mode 决策**:
```python
decision = gateway.validate_transition(
    task_id=task_id,
    mode_id=mode_id,
    from_state=task.status,
    to_state="RUNNING",
    metadata=json.loads(task.metadata)
)

print(f"Decision: {decision.verdict}")
print(f"Reason: {decision.reason}")
print(f"Metadata: {decision.metadata}")
```

#### 解决步骤

1. **确认 Mode 配置正确**
2. **检查是否需要审批**（BLOCKED 决策）
3. **检查是否应该使用不同的 Mode**
4. **联系系统管理员**（如果是配置问题）

---

## 最佳实践

### Mode 选择指南

| 任务类型 | 推荐 Mode | 原因 |
|----------|-----------|------|
| **数据处理** | implementation | 需要实际执行 |
| **API 调用** | implementation | 需要实际执行 |
| **定时任务** | implementation | 需要实际执行 |
| **设计评审** | design | 仅规划，不执行 |
| **方案讨论** | design | 仅规划，不执行 |
| **客服对话** | chat | 交互式，不自动执行 |
| **问答机器人** | chat | 交互式，不自动执行 |
| **高风险操作** | autonomous | 需要审批 |
| **生产部署** | autonomous | 需要审批 |
| **简单任务** | 无 Mode | 向后兼容 |

### 任务设计建议

1. **明确任务目的**
   - 执行操作 → implementation
   - 规划设计 → design
   - 交互对话 → chat
   - 需要审批 → autonomous

2. **使用元数据记录上下文**
```python
metadata = {
    "mode_id": "implementation",
    "purpose": "data_processing",
    "created_by": "user-001",
    "priority": "high",
    "estimated_duration": "10m",
    "requires_resources": ["database", "s3"],
}
```

3. **设计 → 实施工作流**
```python
# 步骤 1: 创建 design 任务
design_task = service.create_draft_task(
    metadata={
        "mode_id": "design",
        "phase": "planning",
        "design_doc": "https://..."
    }
)

# 步骤 2: 审批 design
service.transition_task(design_task.task_id, "APPROVED", "reviewer", "Approved")

# 步骤 3: 基于 design 创建 implementation 任务
impl_task = service.create_draft_task(
    metadata={
        "mode_id": "implementation",
        "based_on_design": design_task.task_id,
        "design_approved": True
    }
)
```

### 错误避免

❌ **不要**: 尝试在运行时切换 Mode
```python
# 错误：不支持
task.metadata["mode_id"] = "implementation"
```

✅ **应该**: 创建新任务
```python
# 正确
new_task = service.create_draft_task(
    metadata={
        "mode_id": "implementation",
        "replaces_task": old_task_id
    }
)
```

❌ **不要**: 忽略 ModeViolationError
```python
# 错误：吞掉错误
try:
    service.transition_task(...)
except ModeViolationError:
    pass  # 危险！
```

✅ **应该**: 正确处理
```python
# 正确
try:
    service.transition_task(...)
except ModeViolationError as e:
    logger.error(f"Mode violation: {e}")
    # 根据错误类型采取适当行动
    handle_mode_violation(e)
```

---

## 命令行示例

### 创建任务

```bash
# Implementation mode
python -c "
from agentos.core.task import TaskService
service = TaskService()
task = service.create_draft_task(metadata={'mode_id': 'implementation'})
print(f'Created task: {task.task_id}')
"

# Design mode
python -c "
from agentos.core.task import TaskService
service = TaskService()
task = service.create_draft_task(metadata={'mode_id': 'design'})
print(f'Created design task: {task.task_id}')
"
```

### 查询状态

```bash
# 查询任务
python -c "
from agentos.core.task import TaskService
service = TaskService()
task = service.get_task('task-001')
import json
metadata = json.loads(task.metadata)
print(f'Task: {task.task_id}')
print(f'Status: {task.status}')
print(f'Mode: {metadata.get(\"mode_id\", \"no mode\")}')
"
```

### 调试命令

```bash
# 测试 Mode 决策
python -c "
from agentos.core.mode.gateway_registry import get_mode_gateway

gateway = get_mode_gateway('design')
decision = gateway.validate_transition(
    task_id='test',
    mode_id='design',
    from_state='QUEUED',
    to_state='RUNNING',
    metadata={}
)

print(f'Verdict: {decision.verdict}')
print(f'Reason: {decision.reason}')
"
```

---

## 总结

### 关键要点

1. **Mode 是可选的** - 现有任务不受影响
2. **Mode 控制转换** - 在状态转换前验证
3. **4 种决策类型** - APPROVED, REJECTED, BLOCKED, DEFERRED
4. **Fail-safe 设计** - Gateway 失败时系统继续运行
5. **完全向后兼容** - 无破坏性变更

### 下一步

- 了解 [技术集成指南](./MODE_TASK_INTEGRATION_GUIDE.md)
- 查看 [Phase 1 实施总结](../../PHASE1_MODE_TASK_INTEGRATION_SUMMARY.md)
- 探索高级用例和自定义 Gateway

---

**文档版本**: 1.0
**最后更新**: 2026年1月30日
**反馈**: 如有问题或建议，请联系技术支持
