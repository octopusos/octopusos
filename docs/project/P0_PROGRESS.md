# P0 修复进度跟踪

**开始时间**: 2026-01-25  
**目标**: 让 Gate 4/6/7 全部通过，建立真实门禁

---

## ✅ P0-1: 负向测试语义标准化
**状态**: 已完成  
**提交**: 8440026  
- 使用 `pytest.raises` 替代 `pytest.fail()`
- 测试语义清晰：冲突 → raises, 成功 → 不 raises

---

## ✅ P0-2: ExecutionPolicy 不变量强制 (Gate 4)
**状态**: 已完成  
**提交**: 8440026  
**验收**:
- ✅ `test_gate_4_2_full_auto_cannot_ask_questions` 通过
- ✅ `policy.question_budget = 1` 在 frozen dataclass 上抛异常
- ✅ `full_auto` 模式 question_budget 永远返回 0

**实现**:
- `ExecutionPolicy` → `@dataclass(frozen=True)`
- `question_budget` → `@property` (私有 `_question_budget`)
- 添加 `PolicyViolation` 异常
- 添加 `with_question_budget()` 工厂方法

---

## ✅ P0-3: TaskLock 接口对齐 (Gate 6 部分)
**状态**: 已完成  
**提交**: 8440026  

**实现**:
- ✅ `TaskLockManager` (v0.3 新接口)
- ✅ `LockToken` 数据类
- ✅ `LockConflict` 异常
- ✅ `TaskLock` 兼容层（deprecation warning）
- ✅ 参数别名支持

**接口**:
```python
mgr = TaskLockManager(db_path)
token = mgr.acquire(task_id, holder, ttl_seconds) -> LockToken
token = mgr.renew(token, ttl_seconds) -> LockToken
mgr.release(token)
```

---

## 🔄 P0-4: FileLock 接口对齐 + RebaseStep 验证 (Gate 6)
**状态**: 进行中  
**待实现**:
1. FileLockManager 新接口
2. FileLock 兼容层
3. RebaseStep.validate_intent_consistency()

**目标接口**:
```python
# FileLockManager
mgr = FileLockManager(db_path)
token = mgr.acquire_paths(task_id, holder, paths, ttl_seconds)
mgr.release_paths(token)
info = mgr.get_owner(path) -> FileLockInfo | None

# RebaseStep
rebase = RebaseStep(db_path)
result = rebase.validate_intent_consistency(
    original_intent: dict,
    current_state: dict
) -> bool
```

**待修复 Gate 6 测试**:
- [ ] test_gate_6_file_lock_prevents_concurrent_modification
- [ ] test_gate_6_task_enters_waiting_lock_state
- [ ] test_gate_6_rebase_triggered_after_lock_release
- [ ] test_gate_6_rebase_validates_intent_consistency
- [ ] test_gate_6_concurrent_tasks_on_different_files_allowed

---

## 📋 P0-5: Scheduler 审计事件接口 (Gate 7)
**状态**: 待开始  
**待实现**:
1. TaskGraph 接口对齐
2. SchedulerEvent 标准化
3. ResourceAwareScheduler 类

**目标接口**:
```python
# TaskGraph
graph = TaskGraph()
graph.add_task(node: TaskNode)
graph.add_dependency(before, after)
order = graph.toposort() -> list[str]
ready = graph.ready_tasks(completed: set) -> list[str]

# Scheduler
scheduler = Scheduler(db_path, mode="sequential"|"parallel")
events = scheduler.get_scheduling_events()

# ResourceAwareScheduler
scheduler = ResourceAwareScheduler(db_path, budget)
selected = scheduler.tick(graph, trigger) -> list[str]
```

**待修复 Gate 7 测试**:
- [ ] test_gate_7_sequential_scheduling_is_audited
- [ ] test_gate_7_parallel_scheduling_respects_locks
- [ ] test_gate_7_parallel_respects_resource_budget
- [ ] test_gate_7_cron_scheduling_is_audited
- [ ] test_gate_7_mixed_mode_scheduling

---

## 验收标准

### Gate 4 (2/9 关键测试)
- ✅ test_gate_4_2_full_auto_cannot_ask_questions
- ⏸ test_gate_4_2_full_auto_blocks_question_creation (Python 3.10+ 语法问题)

### Gate 6 (0/6 测试)
- [ ] 所有5个锁冲突测试通过
- [ ] RebaseStep.validate_intent_consistency 存在且可证明

### Gate 7 (0/7 测试)
- [ ] 所有调度审计测试通过
- [ ] 审计事件包含必需字段

---

## 下一步
继续 P0-4: FileLockManager + RebaseStep
