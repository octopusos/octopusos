# Gate 4/6/7 失败详细报告

**日期**: 2026-01-25  
**目的**: 提供精确的接口签名和失败栈，用于P0修复施工

---

## Gate 4: 核心不变量强制执行 (2/9 失败)

### ❌ 失败 1: `test_gate_4_2_full_auto_cannot_ask_questions`

**失败原因**: `ExecutionPolicy.question_budget` 可以被外部修改

**失败栈**:
```python
tests/gates/test_gate_4_invariants_enforcement.py:88: in test_gate_4_2_full_auto_cannot_ask_questions
    policy.question_budget = 1  # 应该被拒绝或无效
E   Failed: DID NOT RAISE any of (<class 'ValueError'>, <class 'AssertionError'>)
```

**当前实现** (`agentos/core/policy/execution_policy.py:9-26`):
```python
class ExecutionPolicy:
    def __init__(self, mode: str, config: Optional[dict] = None):
        self.mode = mode
        config = config or {}
        
        # Question budget
        if mode == "full_auto":
            self.question_budget = 0  # ❌ 可变属性
        elif mode == "semi_auto":
            self.question_budget = config.get("question_budget", 3)
        else:  # interactive
            self.question_budget = config.get("question_budget", 999)
```

**问题分析**:
- `question_budget` 是普通实例属性，可以被外部赋值
- `full_auto` 模式的 `question_budget=0` 不变量无法强制执行
- 缺少 setter 拦截或使用 `@property`

**修复要求**:
1. 使用 `@property` + 私有属性 `_question_budget`
2. 在 setter 中检查 `mode == "full_auto"` 时拒绝修改
3. 或使用 `@dataclass(frozen=True)` 使整个对象不可变

---

### ❌ 失败 2: `test_gate_4_2_full_auto_blocks_question_creation`

**失败原因**: 缺少依赖导致无法运行测试（次要问题）

**失败栈**:
```python
tests/gates/test_gate_4_invariants_enforcement.py:96: in test_gate_4_2_full_auto_blocks_question_creation
    from agentos.core.generator.question import Question, QuestionType
agentos/core/llm/openai_client.py:14: in <module>
    def __init__(self, api_key: str | None = None):
E   TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

**问题分析**:
- Python 3.9 不支持 `str | None` 语法（需要 3.10+）
- 项目 `pyproject.toml` 要求 `>=3.13` 但测试环境是 3.9

---

## Gate 6: 锁语义可证明性 (5/6 失败)

### ❌ 失败 1-3, 5: 接口签名不匹配

**失败测试**:
- `test_gate_6_file_lock_prevents_concurrent_modification`
- `test_gate_6_task_enters_waiting_lock_state`
- `test_gate_6_rebase_triggered_after_lock_release`
- `test_gate_6_concurrent_tasks_on_different_files_allowed`

**失败栈** (典型):
```python
tests/gates/test_gate_6_lock_semantics.py:34: in test_gate_6_file_lock_prevents_concurrent_modification
    lock_a = FileLock(db_path, task_id="task-a", run_id=1)
E   TypeError: __init__() got an unexpected keyword argument 'task_id'
```

**测试期望的接口**:
```python
# Gate 测试期望
lock = FileLock(db_path, task_id="task-a", run_id=1)
success = lock.acquire_batch(files, holder="agent-a")
lock.release_batch(files)
```

**当前实现的接口** (`agentos/core/locks/file_lock.py:19-39`):
```python
class FileLock:
    def __init__(self, db_path: Optional[Path] = None):  # ❌ 缺少 task_id, run_id
        if db_path is None:
            db_path = Path.home() / ".agentos" / "store.db"
        self.db_path = db_path
    
    def acquire_batch(
        self,
        repo_root: str,        # ❌ 测试传的是 file_paths
        file_paths: list[str],
        task_id: str,          # ✅ 有这个参数
        run_id: int,           # ✅ 有这个参数
        duration: int = 600,
        metadata: Optional[dict] = None,
    ) -> tuple[bool, list[str]]:  # ❌ 返回 (bool, list) 而不是 bool
```

**TaskLock 同样问题**:
```python
# 测试期望
lock = TaskLock(db_path, task_id="task-a", run_id=1)
acquired = lock.acquire(holder="agent-a", lease_duration=300)

# 当前实现
class TaskLock:
    def __init__(self, db_path: Optional[Path] = None):  # ❌ 缺少 task_id, run_id
        ...
    
    def acquire(self, task_id: str, run_id: int, worker_id: str, duration: int = 300) -> bool:
        # ❌ 参数名不一致: worker_id vs holder, duration vs lease_duration
```

---

### ❌ 失败 4: `test_gate_6_rebase_validates_intent_consistency`

**失败原因**: `RebaseStep.validate_intent_consistency()` 方法缺失

**失败栈**:
```python
tests/gates/test_gate_6_lock_semantics.py:244: in test_gate_6_rebase_validates_intent_consistency
    intent_valid = rebase.validate_intent_consistency(
        original_intent=original_intent,
        current_state=current_file_state
    )
AttributeError: 'RebaseStep' object has no attribute 'validate_intent_consistency'
```

**测试期望**:
```python
from agentos.core.orchestrator.rebase import RebaseStep

rebase = RebaseStep(db_path)
intent_valid = rebase.validate_intent_consistency(
    original_intent: dict,
    current_state: dict
) -> bool
```

**问题分析**:
- `RebaseStep` 类存在但缺少 `validate_intent_consistency()` 方法
- 这是 V0.3 Alert Point #3 的关键检查点
- 需要实现意图一致性验证逻辑

---

## Gate 7: Scheduler 可审计性 (5/7 失败)

### ❌ 失败 1-2, 4-5: 接口签名不匹配

**失败测试**:
- `test_gate_7_sequential_scheduling_is_audited`
- `test_gate_7_parallel_scheduling_respects_locks`
- `test_gate_7_cron_scheduling_is_audited`
- `test_gate_7_mixed_mode_scheduling`

**典型失败栈**:
```python
tests/gates/test_gate_7_scheduler_audit.py:58: in test_gate_7_sequential_scheduling_is_audited
    graph = TaskGraph()
agentos/core/scheduler/task_graph.py:23: in __init__
    raise ImportError("networkx is required...")
E   ImportError: networkx is required for task scheduling.
```

**测试期望的接口**:
```python
from agentos.core.scheduler import Scheduler, TaskGraph

# TaskGraph 接口
graph = TaskGraph()
graph.add_task(task_id="task-a", depends_on=[])
execution_order = graph.get_execution_order()  # → ["task-a", "task-b", "task-c"]
parallelizable = graph.get_parallelizable_tasks()

# Scheduler 接口
scheduler = Scheduler(db_path, mode="sequential"|"parallel"|"cron"|"mixed")
events = scheduler.get_scheduling_events()
```

**当前实现状态**:
- `TaskGraph` 存在但方法签名未验证
- `Scheduler` 存在但调度事件审计接口缺失
- 缺少审计事件的标准化结构

---

### ❌ 失败 3: `test_gate_7_parallel_respects_resource_budget`

**失败栈**:
```python
tests/gates/test_gate_7_scheduler_audit.py:235: in test_gate_7_parallel_respects_resource_budget
    from agentos.core.scheduler.resource_aware import ResourceAwareScheduler
E   ModuleNotFoundError: No module named 'agentos.core.scheduler.resource_aware'
```

**测试期望的接口**:
```python
from agentos.core.scheduler.resource_aware import ResourceAwareScheduler

budget = {
    "token_budget": 10000,
    "cost_budget_usd": 1.0,
    "parallelism_budget": 3
}

scheduler = ResourceAwareScheduler(budget)
can_schedule, reason = scheduler.can_schedule(task)
scheduler.record_usage(tokens, cost)
```

**问题分析**:
- `ResourceAwareScheduler` 类不存在
- 需要实现资源预算跟踪和检查逻辑

---

## 修复优先级总结

### P0-1: ExecutionPolicy 不变量强制 (Gate 4)
**修复文件**: `agentos/core/policy/execution_policy.py`
```python
@property
def question_budget(self) -> int:
    return self._question_budget

@question_budget.setter
def question_budget(self, value: int):
    if self.mode == "full_auto":
        raise ValueError("Cannot modify question_budget in full_auto mode (Invariant #2)")
    self._question_budget = value
```

### P0-2: FileLock 接口对齐 (Gate 6)
**修复文件**: `agentos/core/locks/file_lock.py`

**最小稳定接口**:
```python
class FileLock:
    def __init__(self, db_path: Path, task_id: str, run_id: int):
        self.db_path = db_path
        self.task_id = task_id
        self.run_id = run_id
        self.repo_root = None  # 延迟设置
    
    def acquire_batch(self, file_paths: list[str], holder: str, 
                     repo_root: str = None, duration: int = 600,
                     metadata: dict = None) -> bool:
        """返回 bool，不是 tuple"""
        repo_root = repo_root or self.repo_root or "."
        success, _ = self._internal_acquire(repo_root, file_paths, 
                                            self.task_id, self.run_id, 
                                            duration, metadata)
        return success
    
    def release_batch(self, file_paths: list[str], repo_root: str = None):
        repo_root = repo_root or self.repo_root or "."
        self._internal_release(repo_root, file_paths, self.run_id)
```

### P0-3: TaskLock 接口对齐 (Gate 6)
**修复文件**: `agentos/core/locks/task_lock.py`

**最小稳定接口**:
```python
class TaskLock:
    def __init__(self, db_path: Path, task_id: str, run_id: int):
        self.db_path = db_path
        self.task_id = task_id
        self.run_id = run_id
    
    def acquire(self, holder: str, lease_duration: int = 300) -> bool:
        """统一参数名: holder, lease_duration"""
        return self._internal_acquire(self.task_id, self.run_id, 
                                      holder, lease_duration)
    
    def release(self):
        """简化接口，不需要重复传 task_id, run_id"""
        self._internal_release(self.task_id, self.run_id)
```

### P0-4: RebaseStep 意图验证方法 (Gate 6)
**修复文件**: `agentos/core/orchestrator/rebase.py`

```python
class RebaseStep:
    def validate_intent_consistency(self, 
                                   original_intent: dict,
                                   current_state: dict) -> bool:
        """
        验证原始意图在文件变更后是否仍然成立
        
        返回:
            True: 意图仍然成立，可以继续
            False: 意图冲突，需要 BLOCK 或重新规划
        """
        # 检查 assumptions
        for assumption in original_intent.get("assumptions", []):
            if not self._check_assumption(assumption, current_state):
                return False
        
        # 检查 goal 是否仍然有效
        if not self._check_goal_validity(original_intent["goal"], current_state):
            return False
        
        return True
```

### P0-5: Scheduler 审计事件接口 (Gate 7)
**修复文件**: `agentos/core/scheduler/scheduler.py`

**标准化事件结构**:
```python
class Scheduler:
    def record_scheduling_event(self, event: dict):
        """
        记录调度事件到审计日志
        
        event 必须包含:
        - scheduler_mode: str
        - task_id: str
        - timestamp: str (ISO 8601)
        - trigger_reason: str
        - decision: str
        """
        required_fields = ["scheduler_mode", "task_id", "timestamp", 
                          "trigger_reason", "decision"]
        for field in required_fields:
            if field not in event:
                raise ValueError(f"Missing required field: {field}")
        
        # 写入 scheduler_events 表或 run_tape
        self._write_audit_event(event)
```

---

## 兼容层策略

为了避免大范围改动，建议创建兼容适配器：

**示例: FileLock 兼容层**
```python
# file_lock.py 末尾添加
class FileLockV2(FileLock):
    """兼容 Gate 测试的适配器"""
    def __init__(self, db_path: Path, task_id: str, run_id: int):
        super().__init__(db_path)
        self.task_id = task_id
        self.run_id = run_id
    
    def acquire_batch(self, file_paths: list[str], holder: str, **kwargs) -> bool:
        repo_root = kwargs.get('repo_root', '.')
        success, _ = super().acquire_batch(repo_root, file_paths, 
                                          self.task_id, self.run_id)
        return success
```

**测试更新**:
```python
# 从
from agentos.core.locks import FileLock
lock = FileLock(db_path, task_id="task-a", run_id=1)

# 改为
from agentos.core.locks.file_lock import FileLockV2 as FileLock
lock = FileLock(db_path, task_id="task-a", run_id=1)
```

---

## 验收标准

✅ **Gate 4 通过条件**:
- `policy.question_budget = 1` 在 `full_auto` 时抛出 `ValueError`
- Python 3.10+ 语法兼容性修复

✅ **Gate 6 通过条件**:
- `FileLock(db_path, task_id, run_id)` 初始化成功
- `acquire_batch(files, holder)` 返回 `bool`
- `RebaseStep.validate_intent_consistency()` 方法存在且返回 `bool`

✅ **Gate 7 通过条件**:
- `TaskGraph.get_execution_order()` 返回正确的拓扑排序
- `Scheduler` 每次决策写入审计事件
- 审计事件包含所有必需字段

---

**下一步**: 按照 P0-1 到 P0-5 顺序修复，每修复一项运行对应的 Gate 测试验证。
