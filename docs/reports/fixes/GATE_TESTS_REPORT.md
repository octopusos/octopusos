# AgentOS v0.3 Gate Tests Report

**Generated**: 2026-01-25T14:39:57.514808

## Summary

- **Total Gates**: 4
- **Passed**: 0 ✅
- **Failed**: 4 ❌

⚠️ **Some gates failed. Review required before production.**

## Detailed Results

### Gate 4: 核心不变量强制执行

**Status**: ❌ FAILED
**Test File**: `test_gate_4_invariants_enforcement.py`

**Output**:
```
============================= test session starts ==============================
platform darwin -- Python 3.13.1, pytest-9.0.2, pluggy-1.6.0 -- /Users/pangge/PycharmProjects/AgentOS/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/pangge/PycharmProjects/AgentOS
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 9 items

tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_1_no_memory_pack_blocks_execution PASSED [ 11%]
tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_1_empty_memory_pack_is_allowed PASSED [ 22%]
tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_2_full_auto_cannot_ask_questions FAILED [ 33%]
tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_2_full_auto_blocks_question_creation FAILED [ 44%]
tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_3_healing_actions_whitelist_enforced PASSED [ 55%]
tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_3_full_auto_only_allows_low_risk_healing PASSED [ 66%]
tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_4_learning_must_propose_before_apply PASSED [ 77%]
tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_4_learning_auto_apply_requires_conditions PASSED [ 88%]
tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_4_learning_apply_must_be_reversible PASSED [100%]

=================================== FAILURES ===================================
_________________ test_gate_4_2_full_auto_cannot_ask_questions _________________
tests/gates/test_gate_4_invariants_enforcement.py:87: in test_gate_4_2_full_auto_cannot_ask_questions
    with pytest.raises((ValueError, AssertionError)):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE any of (<class 'ValueError'>, <class 'AssertionError'>)
_______________ test_gate_4_2_full_auto_blocks_question_creation _______________
tests/gates/test_gate_4_invariants_enforcement.py:96: in test_gate_4_2_full_auto_blocks_question_creation
    from agentos.core.generator.question import Question, QuestionType
E   ImportError: cannot import name 'QuestionType' from 'agentos.core.generator.question' (/Users/pangge/PycharmProjects/AgentOS/agentos/core/generator/question.py)
=========================== short test summary info ============================
FAILED tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_2_full_auto_cannot_ask_questions - Failed: DID NOT RAISE any of (<class 'ValueError'>, <class 'AssertionError'>)
FAILED tests/gates/test_gate_4_invariants_enforcement.py::test_gate_4_2_full_auto_blocks_question_creation - ImportError: cannot import name 'QuestionType' from 'agentos.core.generator.question' (/Users/pangge/PycharmProjects/AgentOS/agentos/core/generator/question.py)
========================= 2 failed, 7 passed in 0.34s ==========================

```

### Gate 5: Traceability 三件套

**Status**: ❌ FAILED
**Test File**: `test_gate_5_traceability.py`

**Output**:
```
============================= test session starts ==============================
platform darwin -- Python 3.13.1, pytest-9.0.2, pluggy-1.6.0 -- /Users/pangge/PycharmProjects/AgentOS/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/pangge/PycharmProjects/AgentOS
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 6 items

tests/gates/test_gate_5_traceability.py::test_gate_5_review_pack_required_for_commits FAILED [ 16%]
tests/gates/test_gate_5_traceability.py::test_gate_5_run_tape_required_for_commits FAILED [ 33%]
tests/gates/test_gate_5_traceability.py::test_gate_5_commit_binding_required FAILED [ 50%]
tests/gates/test_gate_5_traceability.py::test_gate_5_complete_traceability_chain PASSED [ 66%]
tests/gates/test_gate_5_traceability.py::test_gate_5_review_pack_file_exists FAILED [ 83%]
tests/gates/test_gate_5_traceability.py::test_gate_5_run_tape_has_required_steps FAILED [100%]

=================================== FAILURES ===================================
_________________ test_gate_5_review_pack_required_for_commits _________________
tests/gates/test_gate_5_traceability.py:80: in test_gate_5_review_pack_required_for_commits
    pytest.fail(
E   Failed: Gate 5 violation: Run 1 (task task-001) has commit abc123def but no patches/review_pack
__________________ test_gate_5_run_tape_required_for_commits ___________________
tests/gates/test_gate_5_traceability.py:139: in test_gate_5_run_tape_required_for_commits
    pytest.fail(
E   Failed: Gate 5 violation: Run 1 (task task-001) has patches but no run_tape
_____________________ test_gate_5_commit_binding_required ______________________
tests/gates/test_gate_5_traceability.py:198: in test_gate_5_commit_binding_required
    pytest.fail(
E   Failed: Gate 5 violation: Run 1 (task task-001) status=PUBLISHED has patches but no commit binding (Invariant #7)
_____________________ test_gate_5_review_pack_file_exists ______________________
tests/gates/test_gate_5_traceability.py:273: in test_gate_5_review_pack_file_exists
    pytest.fail(
E   Failed: Gate 5 violation: Run 1 claims to have review_pack at /var/folders/cm/cw7cby1x0t52gcdk4_9rg35r0000gn/T/tmp3qg0dfve/artifacts/review_pack_run_1.md but file does not exist
___________________ test_gate_5_run_tape_has_required_steps ____________________
tests/gates/test_gate_5_traceability.py:314: in test_gate_5_run_tape_has_required_steps
    pytest.fail(
E   Failed: Gate 5 violation: run_tape for run 2 missing required steps: ['apply', 'verify']
=========================== short test summary info ============================
FAILED tests/gates/test_gate_5_traceability.py::test_gate_5_review_pack_required_for_commits - Failed: Gate 5 violation: Run 1 (task task-001) has commit abc123def but no patches/review_pack
FAILED tests/gates/test_gate_5_traceability.py::test_gate_5_run_tape_required_for_commits - Failed: Gate 5 violation: Run 1 (task task-001) has patches but no run_tape
FAILED tests/gates/test_gate_5_traceability.py::test_gate_5_commit_binding_required - Failed: Gate 5 violation: Run 1 (task task-001) status=PUBLISHED has patches but no commit binding (Invariant #7)
FAILED tests/gates/test_gate_5_traceability.py::test_gate_5_review_pack_file_exists - Failed: Gate 5 violation: Run 1 claims to have review_pack at /var/folders/cm/cw7cby1x0t52gcdk4_9rg35r0000gn/T/tmp3qg0dfve/artifacts/review_pack_run_1.md but file does not exist
FAILED tests/gates/test_gate_5_traceability.py::test_gate_5_run_tape_has_required_steps - Failed: Gate 5 violation: run_tape for run 2 missing required steps: ['apply', 'verify']
========================= 5 failed, 1 passed in 0.04s ==========================

```

### Gate 6: 锁语义可证明

**Status**: ❌ FAILED
**Test File**: `test_gate_6_lock_semantics.py`

**Output**:
```
============================= test session starts ==============================
platform darwin -- Python 3.13.1, pytest-9.0.2, pluggy-1.6.0 -- /Users/pangge/PycharmProjects/AgentOS/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/pangge/PycharmProjects/AgentOS
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 6 items

tests/gates/test_gate_6_lock_semantics.py::test_gate_6_file_lock_prevents_concurrent_modification FAILED [ 16%]
tests/gates/test_gate_6_lock_semantics.py::test_gate_6_task_enters_waiting_lock_state FAILED [ 33%]
tests/gates/test_gate_6_lock_semantics.py::test_gate_6_rebase_triggered_after_lock_release FAILED [ 50%]
tests/gates/test_gate_6_lock_semantics.py::test_gate_6_rebase_validates_intent_consistency FAILED [ 66%]
tests/gates/test_gate_6_lock_semantics.py::test_gate_6_wait_has_audit_record PASSED [ 83%]
tests/gates/test_gate_6_lock_semantics.py::test_gate_6_concurrent_tasks_on_different_files_allowed FAILED [100%]

=================================== FAILURES ===================================
____________ test_gate_6_file_lock_prevents_concurrent_modification ____________
tests/gates/test_gate_6_lock_semantics.py:34: in test_gate_6_file_lock_prevents_concurrent_modification
    lock_a = FileLock(db_path, task_id="task-a", run_id=1)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: FileLock.__init__() got an unexpected keyword argument 'task_id'
__________________ test_gate_6_task_enters_waiting_lock_state __________________
tests/gates/test_gate_6_lock_semantics.py:81: in test_gate_6_task_enters_waiting_lock_state
    lock_a = TaskLock(db_path, task_id="task-a", run_id=1)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: TaskLock.__init__() got an unexpected keyword argument 'task_id'
_______________ test_gate_6_rebase_triggered_after_lock_release ________________
tests/gates/test_gate_6_lock_semantics.py:147: in test_gate_6_rebase_triggered_after_lock_release
    lock_a = FileLock(db_path, task_id="task-a", run_id=1)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: FileLock.__init__() got an unexpected keyword argument 'task_id'
_______________ test_gate_6_rebase_validates_intent_consistency ________________
tests/gates/test_gate_6_lock_semantics.py:244: in test_gate_6_rebase_validates_intent_consistency
    intent_valid = rebase.validate_intent_consistency(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'RebaseStep' object has no attribute 'validate_intent_consistency'
___________ test_gate_6_concurrent_tasks_on_different_files_allowed ____________
tests/gates/test_gate_6_lock_semantics.py:296: in test_gate_6_concurrent_tasks_on_different_files_allowed
    lock_a = FileLock(db_path, task_id="task-a", run_id=1)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: FileLock.__init__() got an unexpected keyword argument 'task_id'
=========================== short test summary info ============================
FAILED tests/gates/test_gate_6_lock_semantics.py::test_gate_6_file_lock_prevents_concurrent_modification - TypeError: FileLock.__init__() got an unexpected keyword argument 'task_id'
FAILED tests/gates/test_gate_6_lock_semantics.py::test_gate_6_task_enters_waiting_lock_state - TypeError: TaskLock.__init__() got an unexpected keyword argument 'task_id'
FAILED tests/gates/test_gate_6_lock_semantics.py::test_gate_6_rebase_triggered_after_lock_release - TypeError: FileLock.__init__() got an unexpected keyword argument 'task_id'
FAILED tests/gates/test_gate_6_lock_semantics.py::test_gate_6_rebase_validates_intent_consistency - AttributeError: 'RebaseStep' object has no attribute 'validate_intent_consistency'
FAILED tests/gates/test_gate_6_lock_semantics.py::test_gate_6_concurrent_tasks_on_different_files_allowed - TypeError: FileLock.__init__() got an unexpected keyword argument 'task_id'
========================= 5 failed, 1 passed in 0.33s ==========================

```

### Gate 7: Scheduler 可审计

**Status**: ❌ FAILED
**Test File**: `test_gate_7_scheduler_audit.py`

**Output**:
```
============================= test session starts ==============================
platform darwin -- Python 3.13.1, pytest-9.0.2, pluggy-1.6.0 -- /Users/pangge/PycharmProjects/AgentOS/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/pangge/PycharmProjects/AgentOS
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 7 items

tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_sequential_scheduling_is_audited FAILED [ 14%]
tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_parallel_scheduling_respects_locks FAILED [ 28%]
tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_parallel_respects_parallelism_group PASSED [ 42%]
tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_parallel_respects_resource_budget PASSED [ 57%]
tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_cron_scheduling_is_audited FAILED [ 71%]
tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_mixed_mode_scheduling FAILED [ 85%]
tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_scheduler_audit_record_completeness PASSED [100%]

=================================== FAILURES ===================================
_________________ test_gate_7_sequential_scheduling_is_audited _________________
tests/gates/test_gate_7_scheduler_audit.py:60: in test_gate_7_sequential_scheduling_is_audited
    graph.add_task(
    ^^^^^^^^^^^^^^
E   AttributeError: 'TaskGraph' object has no attribute 'add_task'
________________ test_gate_7_parallel_scheduling_respects_locks ________________
tests/gates/test_gate_7_scheduler_audit.py:141: in test_gate_7_parallel_scheduling_respects_locks
    graph.add_task(task_id=task["task_id"])
    ^^^^^^^^^^^^^^
E   AttributeError: 'TaskGraph' object has no attribute 'add_task'
____________________ test_gate_7_cron_scheduling_is_audited ____________________
tests/gates/test_gate_7_scheduler_audit.py:298: in test_gate_7_cron_scheduling_is_audited
    scheduler = Scheduler(db_path, mode="cron")
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: Scheduler.__init__() got an unexpected keyword argument 'mode'
______________________ test_gate_7_mixed_mode_scheduling _______________________
tests/gates/test_gate_7_scheduler_audit.py:352: in test_gate_7_mixed_mode_scheduling
    scheduler = Scheduler(db_path, mode="mixed")
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: Scheduler.__init__() got an unexpected keyword argument 'mode'
=========================== short test summary info ============================
FAILED tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_sequential_scheduling_is_audited - AttributeError: 'TaskGraph' object has no attribute 'add_task'
FAILED tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_parallel_scheduling_respects_locks - AttributeError: 'TaskGraph' object has no attribute 'add_task'
FAILED tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_cron_scheduling_is_audited - TypeError: Scheduler.__init__() got an unexpected keyword argument 'mode'
FAILED tests/gates/test_gate_7_scheduler_audit.py::test_gate_7_mixed_mode_scheduling - TypeError: Scheduler.__init__() got an unexpected keyword argument 'mode'
========================= 4 failed, 3 passed in 0.15s ==========================

```

## Gate Details

### Gate 4: 核心不变量强制执行

验证内容：
- 4.1: 无 MemoryPack 不允许执行（系统拒绝 + 审计）
- 4.2: full_auto question_budget = 0（强制执行）
- 4.3: 自愈动作白名单（非白名单拒绝）
- 4.4: Learning 先提案后应用（不能直接修改）

### Gate 5: Traceability 三件套

验证内容：
- 有 commit 必须有 review_pack
- 有 review_pack 必须有 run_tape
- 有 run_tape 必须有 commit 绑定
- run_tape 包含必需步骤（plan/apply/verify）

### Gate 6: 锁语义可证明

验证内容：
- 文件锁阻止并发修改
- 锁冲突时进入 WAITING_LOCK 状态
- 锁释放后触发 REBASE
- REBASE 验证 intent 一致性
- WAIT 有审计记录

### Gate 7: Scheduler 可审计

验证内容：
- sequential 调度有审计
- parallel 遵守锁和预算
- parallelism_group 限制并发
- cron 触发有审计
- mixed 模式支持
