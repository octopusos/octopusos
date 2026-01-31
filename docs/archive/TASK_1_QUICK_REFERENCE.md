# Task #1 快速参考：Chat → Execution 硬闸门

## 核心规则

```
chat → ❌ 直接执行 (FORBIDDEN)
chat → ✅ 创建 Task (DRAFT only)
task runner → ✅ 执行 (ONLY allowed)
```

---

## 代码示例

### ✅ 正确：Chat 创建 DRAFT 任务

```python
from agentos.core.task.service import TaskService

task_service = TaskService()

# Chat 只能创建 DRAFT 任务
task = task_service.create_draft_task(
    title="Task from chat",
    created_by="chat_mode",
    metadata={"source": "chat"}
)

# 结果：task.status == "draft"
```

### ✅ 正确：通过 TaskService 执行

```python
from agentos.core.task.service import TaskService

task_service = TaskService()

# 使用 TaskService 的组合方法
task = task_service.create_approve_queue_and_start(
    title="Immediate execution",
    created_by="system",
    actor="system"
)

# 内部自动完成：DRAFT → APPROVED → QUEUED → 启动 runner
```

### ✅ 正确：Task Runner 执行

```python
from agentos.core.executor.executor_engine import ExecutorEngine

executor = ExecutorEngine(repo_path=..., output_dir=...)

result = executor.execute(
    execution_request=exec_req,
    sandbox_policy={},
    caller_source="task_runner"  # ✅ 允许
)
```

### ❌ 错误：Chat 直接调用 Executor

```python
from agentos.core.executor.executor_engine import ExecutorEngine
from agentos.core.task.errors import ChatExecutionForbiddenError

executor = ExecutorEngine(repo_path=..., output_dir=...)

# ❌ 这会抛出异常
try:
    result = executor.execute(
        execution_request=exec_req,
        sandbox_policy={},
        caller_source="chat"  # ❌ 禁止！
    )
except ChatExecutionForbiddenError as e:
    print(f"Error: {e}")
    # Error: Chat system is forbidden from directly executing tasks...
```

---

## API 参考

### ChatExecutionForbiddenError

```python
class ChatExecutionForbiddenError(TaskStateError):
    """Chat 尝试直接执行时抛出的异常"""

    def __init__(
        self,
        caller_context: str,      # 调用上下文，如 "ExecutorEngine.execute"
        attempted_operation: str,  # 尝试的操作，如 "execute_task"
        task_id: str = None,      # 可选的任务 ID
        metadata: dict = None     # 可选的额外上下文
    )
```

### ExecutorEngine.execute()

```python
def execute(
    self,
    execution_request: Dict[str, Any],
    sandbox_policy: Dict[str, Any],
    policy_path: Optional[Path] = None,
    caller_source: str = "unknown"  # ← 新增参数
) -> Dict[str, Any]:
    """
    caller_source 取值：
    - "task_runner" → 允许执行
    - "chat" → 抛出 ChatExecutionForbiddenError
    - "unknown" → 记录警告但允许（向后兼容）
    """
```

---

## 工作流

### 标准工作流（推荐）

```
1. Chat 创建 DRAFT 任务
   ↓
2. 用户/系统批准 (DRAFT → APPROVED)
   ↓
3. 系统排队 (APPROVED → QUEUED)
   ↓
4. Task Runner 拾取并执行 (QUEUED → RUNNING)
```

### 快速执行工作流

```python
# 一步完成所有状态转换
task = task_service.create_approve_queue_and_start(
    title="Quick task",
    actor="system"
)
# 内部自动：DRAFT → APPROVED → QUEUED → 启动 runner
```

---

## 测试

### 运行测试

```bash
# 运行所有测试
python3 -m pytest tests/integration/task/test_chat_execution_gate_simple.py -v

# 运行特定测试
python3 -m pytest tests/integration/task/test_chat_execution_gate_simple.py::TestChatExecutionGateSimple::test_chat_can_create_draft_task -v
```

### 测试覆盖

- ✅ Chat 可以创建 DRAFT 任务
- ✅ Chat 不能直接执行
- ✅ Task runner 可以执行
- ✅ 完整工作流测试
- ✅ 错误继承测试

---

## 故障排查

### 如果看到 ChatExecutionForbiddenError

**原因**: 代码尝试以 "chat" 身份调用 executor

**解决方案**:
1. 检查调用栈，找到调用 `executor.execute()` 的地方
2. 确认是否应该由 chat 创建任务而不是直接执行
3. 如果确实需要执行，使用 `TaskService.create_approve_queue_and_start()`

### 如果看到 "unknown caller_source" 警告

**原因**: 代码未传递 `caller_source` 参数

**解决方案**:
1. 更新代码明确传递 `caller_source="task_runner"`
2. 或通过 `ModePipelineRunner` 调用（自动传递）

---

## 迁移指南

### 从旧代码迁移

**旧代码**:
```python
# 直接调用 executor（可能来自 chat）
executor.execute(execution_request=req, sandbox_policy={})
```

**新代码**:
```python
# Option 1: 通过 TaskService
task_service.create_approve_queue_and_start(
    title="Task title",
    actor="system"
)

# Option 2: 明确传递 caller_source
executor.execute(
    execution_request=req,
    sandbox_policy={},
    caller_source="task_runner"  # 明确标识
)
```

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `agentos/core/task/errors.py` | ChatExecutionForbiddenError 定义 |
| `agentos/core/executor/executor_engine.py` | 硬闸门实施位置 |
| `agentos/core/mode/pipeline_runner.py` | Task runner 集成 |
| `tests/integration/task/test_chat_execution_gate_simple.py` | 测试套件 |
| `TASK_1_ACCEPTANCE_REPORT.md` | 完整验收报告 |

---

**最后更新**: 2026-01-30
