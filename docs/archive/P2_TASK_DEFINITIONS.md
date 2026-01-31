# P2 任务定义：详细实施指南

**项目**: AgentOS P2 - 100分路径实施
**版本**: v1.0
**日期**: 2026-01-30

---

## 任务总览

本文档定义P2阶段的4个并行任务，每个任务包含详细的实施步骤、验收标准和预期输出。

| 任务ID | 任务名称 | 优先级 | 工时 | 得分提升 | ROI | 可并行 |
|--------|----------|--------|------|----------|-----|--------|
| **P2-A** | E2E测试环境修复 | P0 | 1.5h | +6分 | 4.0 | - |
| **P2-B** | 覆盖率提升至85% | P1 | 3.0h | +2分 | 0.67 | 与P2-C |
| **P2-C** | 运维回放工具 | P1 | 1.0h | +2分 | 2.0 | 与P2-B |
| **P2-D** | 完整性冲刺100分 | P2 | 2.0h | +1分 | 0.5 | - |

---

## P2-A: E2E测试环境修复

### 任务元信息

- **任务ID**: P2-A
- **优先级**: P0（最高）
- **前置依赖**: 无
- **预估工时**: 1.5小时
- **得分提升**: +6分（89 → 95）
- **目标**: 修复E2E测试环境，使所有E2E测试可正常运行

### 子任务清单

#### 子任务 A1: 修复Retry E2E数据库初始化

**问题描述**:
- 测试文件: `tests/integration/task/test_retry_e2e.py`
- 症状: 13/16测试失败，错误`sqlite3.OperationalError: no such table: tasks`
- 根因: 测试fixture未正确初始化数据库schema

**实施步骤**:

1. **编辑测试文件** (15分钟)
   ```bash
   # 编辑文件
   vim tests/integration/task/test_retry_e2e.py
   ```

2. **添加数据库初始化fixture** (30分钟)
   ```python
   import sqlite3
   import os
   from pathlib import Path

   @pytest.fixture(autouse=True)
   def setup_retry_test_db(tmp_path):
       """Initialize test database with complete schema for retry tests"""
       db_path = tmp_path / "retry_test.db"
       conn = sqlite3.connect(str(db_path))
       conn.row_factory = sqlite3.Row

       # 加载完整schema
       schema_path = Path(__file__).parent.parent.parent.parent / \
                     "agentos/store/migrations/schema_v31_project_aware.sql"

       with open(schema_path) as f:
           schema_sql = f.read()
           # 过滤示例SQL block（参考test_event_service.py的做法）
           lines = []
           in_example = False
           for line in schema_sql.split('\n'):
               if '-- Example:' in line:
                   in_example = True
               elif in_example and line.strip().startswith('--'):
                   in_example = False
               elif not in_example:
                   lines.append(line)

           conn.executescript('\n'.join(lines))

       conn.close()

       # 设置环境变量指向测试数据库
       os.environ["AGENTOS_DB_PATH"] = str(db_path)
       yield db_path

       # 清理
       if "AGENTOS_DB_PATH" in os.environ:
           del os.environ["AGENTOS_DB_PATH"]
   ```

3. **验证修复** (15分钟)
   ```bash
   # 运行Retry E2E测试
   pytest tests/integration/task/test_retry_e2e.py -v --tb=short

   # 预期结果: 16/16 passed (100%)
   ```

**预期输出**:
- 修改文件: `tests/integration/task/test_retry_e2e.py`
- 测试通过: 16/16 (100%)
- 得分提升: +4分

---

#### 子任务 A2: 修复Timeout exit_reason

**问题描述**:
- 测试文件: `tests/integration/task/test_timeout_e2e.py`
- 测试用例: `test_task_timeout_after_limit`
- 症状: exit_reason='unknown'而非'timeout'
- 根因: runner未在超时时正确设置exit_reason

**实施步骤**:

1. **定位超时处理代码** (10分钟)
   ```bash
   # 查找超时处理逻辑
   grep -rn "is_timeout" agentos/core/runner/
   grep -rn "timeout_manager" agentos/core/runner/
   ```

2. **修改task_runner.py** (15分钟)
   ```python
   # 文件: agentos/core/runner/task_runner.py
   # 定位到超时检查逻辑（大约第200-250行）

   # 在超时检测后添加metadata设置
   if is_timeout:
       # 1. 首先更新任务metadata
       task_manager.update_task_metadata(
           task_id=task.task_id,
           metadata={"exit_reason": "timeout"}
       )

       # 2. 然后执行状态转换
       state_machine.transition(
           task_id=task.task_id,
           to="failed",
           actor="timeout_manager",
           reason=timeout_message,
           metadata={"exit_reason": "timeout"}  # 确保metadata传递
       )

       # 3. 记录审计日志
       audit_service.record_event(
           task_id=task.task_id,
           event_type="TASK_TIMEOUT",
           level="ERROR",
           payload={
               "timeout_seconds": timeout_config.get("timeout_seconds"),
               "elapsed_seconds": elapsed_seconds,
               "exit_reason": "timeout"
           }
       )
   ```

3. **验证修复** (5分钟)
   ```bash
   # 运行单个测试
   pytest tests/integration/task/test_timeout_e2e.py::test_task_timeout_after_limit -v

   # 预期结果: PASSED

   # 运行完整Timeout E2E套件
   pytest tests/integration/task/test_timeout_e2e.py -v

   # 预期结果: 5/5 passed (100%)
   ```

**预期输出**:
- 修改文件: `agentos/core/runner/task_runner.py`
- 测试通过: 5/5 (100%)
- 得分提升: +1分

---

#### 子任务 A3: 验证完整E2E套件

**实施步骤**:

1. **运行完整E2E测试套件** (10分钟)
   ```bash
   # 运行所有E2E测试
   pytest tests/integration/task/ -v --tb=short

   # 预期结果:
   # - test_retry_e2e.py: 16/16 passed ✅
   # - test_timeout_e2e.py: 5/5 passed ✅
   # - test_cancel_running_e2e.py: 7/7 passed ✅
   # - 总计: 28/28 passed (100%) ✅
   ```

2. **重新计算E2E通过率** (5分钟)
   ```bash
   # 统计测试结果
   pytest tests/integration/task/ -v --tb=short | grep -E "passed|failed"

   # 计算:
   # E2E通过率: 28/28 = 100% ✅
   # 得分: 8/8 (满分) ✅
   ```

3. **更新评分** (5分钟)
   - 测试维度E2E: 4/8 → 8/8 (+4分)
   - 集成验证E2E环境: 6/8 → 7/8 (+1分)
   - 集成验证关键路径: 6/8 → 8/8 (+2分，因为关键路径全通过）
   - 总分: 89 → 95分 ✅

**验收标准**:
- ✅ 所有E2E测试通过（28/28 = 100%）
- ✅ 总分达到95分（A+级）
- ✅ 无新增失败测试
- ✅ 退出码 = 0

---

## P2-B: 覆盖率提升至85%

### 任务元信息

- **任务ID**: P2-B
- **优先级**: P1
- **前置依赖**: P2-A完成（推荐）
- **预估工时**: 3.0小时
- **得分提升**: +2分（95 → 97）
- **目标**: 将Scope Coverage从62.8%提升至85%
- **可并行**: 与P2-C并行执行

### 子任务清单

#### 子任务 B1: 补充state_machine.py覆盖率

**当前状态**:
- 当前覆盖率: 87.0%（来自P1_2_COMPLETION_REPORT.md）
- 目标覆盖率: 95%+
- 缺失行数: 约18行

**实施步骤**:

1. **分析未覆盖区域** (15分钟)
   ```bash
   # 查看HTML覆盖率报告
   open htmlcov-scope/index.html
   # 找到state_machine.py，查看红色未覆盖行

   # 或者使用命令行
   grep "state_machine.py" coverage-scope.xml -A 50 | grep "line-rate"
   ```

2. **创建错误处理测试文件** (45分钟)
   ```bash
   # 创建新测试文件
   touch tests/unit/task/test_state_machine_errors.py
   ```

   ```python
   # tests/unit/task/test_state_machine_errors.py
   """
   State Machine Error Handling Tests
   Coverage target: Lines 122-126, 151-156, 337-348, 385-395
   """
   import pytest
   from unittest.mock import patch, MagicMock
   from agentos.core.task.state_machine import TaskStateMachine, InvalidTransitionError, TaskStateError


   class TestInvalidTransitions:
       """测试无效状态转换"""

       def test_can_transition_with_invalid_from_state(self):
           """Cover lines 122-126: 无效from_state检测"""
           sm = TaskStateMachine()
           assert sm.can_transition("INVALID_STATE", "APPROVED") is False

       def test_can_transition_with_invalid_to_state(self):
           """Cover lines 122-126: 无效to_state检测"""
           sm = TaskStateMachine()
           assert sm.can_transition("OPEN", "INVALID_STATE") is False

       def test_validate_or_raise_invalid_from_state(self):
           """Cover lines 151-156: validate_or_raise错误路径"""
           sm = TaskStateMachine()
           with pytest.raises(InvalidTransitionError) as exc_info:
               sm.validate_or_raise("INVALID", "APPROVED")
           assert "INVALID" in str(exc_info.value)

       def test_validate_or_raise_invalid_to_state(self):
           """Cover lines 151-156: validate_or_raise错误路径"""
           sm = TaskStateMachine()
           with pytest.raises(InvalidTransitionError) as exc_info:
               sm.validate_or_raise("OPEN", "INVALID")
           assert "INVALID" in str(exc_info.value)

       def test_validate_or_raise_invalid_transition(self):
           """Cover lines 168-173: 转换规则不存在"""
           sm = TaskStateMachine()
           with pytest.raises(InvalidTransitionError) as exc_info:
               sm.validate_or_raise("DONE", "OPEN")  # Done不能回到Open
           assert "not allowed" in str(exc_info.value).lower()


   class TestTimeoutHandling:
       """测试超时处理"""

       def test_transition_timeout_error(self, temp_db):
           """Cover lines 337-342: Writer提交超时"""
           sm = TaskStateMachine()

           # 先创建任务
           from agentos.core.task.service import TaskService
           ts = TaskService()
           task_id = ts.create_task(
               title="Test timeout",
               objective="Test",
               mode="SEMIAUTONOMOUS",
               status="OPEN"
           )

           # Mock writer.submit抛出TimeoutError
           with patch('agentos.core.task.state_machine.get_writer') as mock_writer:
               mock_instance = MagicMock()
               mock_instance.submit.side_effect = TimeoutError("Writer timeout")
               mock_writer.return_value = mock_instance

               with pytest.raises(TaskStateError) as exc_info:
                   sm.transition(task_id=task_id, to="APPROVED", actor="test")
               assert "timeout" in str(exc_info.value).lower()

       def test_transition_database_error(self, temp_db):
           """Cover lines 343-348: 数据库异常处理"""
           sm = TaskStateMachine()

           # 创建任务
           from agentos.core.task.service import TaskService
           ts = TaskService()
           task_id = ts.create_task(
               title="Test DB error",
               objective="Test",
               mode="SEMIAUTONOMOUS",
               status="OPEN"
           )

           # Mock writer.submit抛出数据库异常
           with patch('agentos.core.task.state_machine.get_writer') as mock_writer:
               mock_instance = MagicMock()
               mock_instance.submit.side_effect = Exception("Database error")
               mock_writer.return_value = mock_instance

               with pytest.raises(TaskStateError):
                   sm.transition(task_id=task_id, to="APPROVED", actor="test")


   class TestHistoryQueries:
       """测试历史查询功能"""

       def test_get_transition_history_empty(self, temp_db):
           """Cover lines 385-390: 空历史查询"""
           sm = TaskStateMachine()
           history = sm.get_transition_history("nonexistent-task-id")
           assert history == []

       def test_get_transition_history_with_data(self, temp_db):
           """Cover lines 385-395: 正常历史查询"""
           from agentos.core.task.service import TaskService
           ts = TaskService()
           sm = TaskStateMachine()

           # 创建任务并进行状态转换
           task_id = ts.create_task(
               title="Test history",
               objective="Test",
               mode="SEMIAUTONOMOUS",
               status="OPEN"
           )

           # 执行转换
           sm.transition(task_id=task_id, to="APPROVED", actor="test", reason="Test")

           # 查询历史
           history = sm.get_transition_history(task_id)
           assert len(history) >= 1
           assert history[0]['from_state'] == 'OPEN'
           assert history[0]['to_state'] == 'APPROVED'

       def test_get_valid_transitions_invalid_state(self):
           """Cover lines 400-405: 无效状态查询有效转换"""
           sm = TaskStateMachine()
           transitions = sm.get_valid_transitions("INVALID_STATE")
           assert transitions == []
   ```

3. **运行测试并验证覆盖率** (10分钟)
   ```bash
   # 运行新测试
   pytest tests/unit/task/test_state_machine_errors.py -v

   # 重新生成覆盖率
   ./scripts/coverage_scope_task.sh

   # 检查state_machine.py覆盖率
   # 预期: 87% → 95%+
   ```

**预期输出**:
- 新增文件: `tests/unit/task/test_state_machine_errors.py`
- 新增测试: 约12个
- state_machine.py覆盖率: 87% → 95%+

---

#### 子任务 B2: 补充work_items.py覆盖率

**当前状态**:
- 当前覆盖率: 47.7%
- 目标覆盖率: 75%+
- 缺失行数: 68行（潜在提升1.89%）

**实施步骤**:

1. **分析work_items.py结构** (15分钟)
   ```bash
   # 查看文件结构
   cat agentos/core/task/work_items.py | head -50

   # 查看未覆盖区域
   open htmlcov-scope/agentos_core_task_work_items_py.html
   ```

2. **创建work_items测试文件** (30分钟)
   ```bash
   touch tests/unit/task/test_work_items_coverage.py
   ```

   ```python
   # tests/unit/task/test_work_items_coverage.py
   """
   Work Items Coverage Tests
   Target: 47.7% → 75%+
   """
   import pytest
   from agentos.core.task.work_items import WorkItemManager, WorkItem


   class TestWorkItemCreation:
       """测试WorkItem创建"""

       def test_create_work_item(self, temp_db):
           """基本WorkItem创建"""
           manager = WorkItemManager()

           item = manager.create_work_item(
               task_id="test-task",
               title="Test work item",
               order=1
           )

           assert item is not None
           assert item.title == "Test work item"
           assert item.order == 1

       def test_create_work_item_with_dependencies(self, temp_db):
           """带依赖的WorkItem创建"""
           manager = WorkItemManager()

           # 创建两个work item
           item1 = manager.create_work_item(
               task_id="test-task",
               title="Item 1",
               order=1
           )

           item2 = manager.create_work_item(
               task_id="test-task",
               title="Item 2",
               order=2,
               depends_on=[item1.id]
           )

           assert item2.depends_on == [item1.id]


   class TestWorkItemExecution:
       """测试WorkItem执行"""

       def test_start_work_item(self, temp_db):
           """启动WorkItem"""
           manager = WorkItemManager()

           item = manager.create_work_item(
               task_id="test-task",
               title="Test",
               order=1
           )

           manager.start_work_item(item.id)

           updated = manager.get_work_item(item.id)
           assert updated.status == "IN_PROGRESS"

       def test_complete_work_item(self, temp_db):
           """完成WorkItem"""
           manager = WorkItemManager()

           item = manager.create_work_item(
               task_id="test-task",
               title="Test",
               order=1
           )

           manager.start_work_item(item.id)
           manager.complete_work_item(item.id, result="success")

           updated = manager.get_work_item(item.id)
           assert updated.status == "DONE"
           assert updated.result == "success"

       def test_fail_work_item(self, temp_db):
           """失败WorkItem"""
           manager = WorkItemManager()

           item = manager.create_work_item(
               task_id="test-task",
               title="Test",
               order=1
           )

           manager.start_work_item(item.id)
           manager.fail_work_item(item.id, error="Test error")

           updated = manager.get_work_item(item.id)
           assert updated.status == "FAILED"
           assert "Test error" in updated.error


   class TestWorkItemQueries:
       """测试WorkItem查询"""

       def test_list_work_items(self, temp_db):
           """列出task的所有work items"""
           manager = WorkItemManager()

           # 创建多个work items
           for i in range(3):
               manager.create_work_item(
                   task_id="test-task",
                   title=f"Item {i}",
                   order=i
               )

           items = manager.list_work_items("test-task")
           assert len(items) == 3

       def test_get_pending_work_items(self, temp_db):
           """获取待执行的work items"""
           manager = WorkItemManager()

           # 创建work items
           item1 = manager.create_work_item(
               task_id="test-task",
               title="Item 1",
               order=1
           )

           item2 = manager.create_work_item(
               task_id="test-task",
               title="Item 2",
               order=2
           )

           # 启动item1
           manager.start_work_item(item1.id)

           # 查询pending items
           pending = manager.get_pending_work_items("test-task")
           assert len(pending) == 1
           assert pending[0].id == item2.id
   ```

3. **运行测试** (15分钟)
   ```bash
   pytest tests/unit/task/test_work_items_coverage.py -v

   # 重新生成覆盖率
   ./scripts/coverage_scope_task.sh

   # 检查work_items.py覆盖率
   # 预期: 47.7% → 75%+
   ```

**预期输出**:
- 新增文件: `tests/unit/task/test_work_items_coverage.py`
- 新增测试: 约11个
- work_items.py覆盖率: 47.7% → 75%+
- Scope整体提升: +1.89%

---

#### 子任务 B3: 补充event_service.py覆盖率

**当前状态**:
- 当前覆盖率: 62.8%
- 目标覆盖率: 80%+
- 缺失行数: 55行（潜在提升1.53%）

**实施步骤**:

1. **扩展现有测试** (30分钟)
   ```bash
   # 编辑现有测试文件
   vim tests/unit/task/test_event_service.py
   ```

   ```python
   # 在test_event_service.py末尾添加新测试类

   class TestEventServiceErrorHandling:
       """测试事件服务错误处理"""

       def test_record_event_invalid_task_id(self, temp_db):
           """记录事件时task_id不存在"""
           service = TaskEventService()

           # 应该不抛出异常，静默处理
           event_id = service.record_event(
               task_id="nonexistent",
               event_type="TEST",
               level="INFO",
               payload={}
           )

           assert event_id is not None

       def test_get_events_empty(self, temp_db):
           """查询不存在任务的事件"""
           service = TaskEventService()
           events = service.get_task_events("nonexistent")
           assert events == []

       def test_get_events_by_level(self, temp_db, task_id):
           """按级别过滤事件"""
           service = TaskEventService()

           # 记录不同级别的事件
           service.record_event(task_id, "EVENT1", "INFO", {})
           service.record_event(task_id, "EVENT2", "ERROR", {})
           service.record_event(task_id, "EVENT3", "WARN", {})

           # 只查询ERROR级别
           errors = service.get_events_by_level(task_id, "ERROR")
           assert len(errors) == 1
           assert errors[0]['event_type'] == "EVENT2"

       def test_get_events_by_time_range(self, temp_db, task_id):
           """按时间范围查询事件"""
           from datetime import datetime, timedelta
           service = TaskEventService()

           # 记录事件
           service.record_event(task_id, "EVENT", "INFO", {})

           # 查询最近1小时的事件
           now = datetime.now()
           start = now - timedelta(hours=1)
           end = now + timedelta(minutes=1)

           events = service.get_events_by_time_range(task_id, start, end)
           assert len(events) >= 1

       def test_delete_old_events(self, temp_db, task_id):
           """删除旧事件"""
           from datetime import datetime, timedelta
           service = TaskEventService()

           # 记录一些事件
           for i in range(5):
               service.record_event(task_id, f"EVENT{i}", "INFO", {})

           # 删除30天前的事件
           cutoff = datetime.now() - timedelta(days=30)
           deleted = service.delete_events_before(cutoff)

           # 应该没有删除（因为事件刚创建）
           assert deleted == 0
   ```

2. **运行测试** (10分钟)
   ```bash
   pytest tests/unit/task/test_event_service.py -v

   # 重新生成覆盖率
   ./scripts/coverage_scope_task.sh

   # 检查event_service.py覆盖率
   # 预期: 62.8% → 80%+
   ```

**预期输出**:
- 修改文件: `tests/unit/task/test_event_service.py`
- 新增测试: 约5个
- event_service.py覆盖率: 62.8% → 80%+
- Scope整体提升: +1.53%

---

#### 子任务 B4: 最终验证

**实施步骤**:

1. **运行完整测试套件** (10分钟)
   ```bash
   pytest tests/unit/task -v
   # 预期: 390+ passed, 0 failed
   ```

2. **生成最终覆盖率报告** (5分钟)
   ```bash
   ./scripts/coverage_scope_task.sh

   # 检查输出
   # 预期: Scope Coverage ≥ 85%
   ```

3. **验证关键模块覆盖率** (5分钟)
   ```bash
   # 查看HTML报告
   open htmlcov-scope/index.html

   # 确认关键模块覆盖率:
   # - state_machine.py: ≥ 95%
   # - work_items.py: ≥ 75%
   # - event_service.py: ≥ 80%
   # - 整体Scope: ≥ 85%
   ```

**验收标准**:
- ✅ Scope Coverage行覆盖率 ≥ 85%
- ✅ Scope Coverage分支覆盖率 ≥ 70%
- ✅ 所有新增测试通过
- ✅ 无测试回归
- ✅ 得分提升至97分

---

## P2-C: 运维回放工具

### 任务元信息

- **任务ID**: P2-C
- **优先级**: P1
- **前置依赖**: 无（可与P2-B并行）
- **预估工时**: 1.0小时
- **得分提升**: +2分（95 → 97，或97 → 99取决于P2-B完成情况）
- **目标**: 添加独立的任务生命周期回放工具
- **可并行**: 与P2-B并行执行

### 子任务清单

#### 子任务 C1: 创建回放脚本

**实施步骤**:

1. **创建脚本文件** (30分钟)
   ```bash
   touch scripts/replay_task_lifecycle.py
   chmod +x scripts/replay_task_lifecycle.py
   ```

   ```python
   #!/usr/bin/env python3
   """
   Task Lifecycle Replay Tool

   Usage:
       python3 scripts/replay_task_lifecycle.py <task_id>
       python3 scripts/replay_task_lifecycle.py <task_id> --detailed

   Output:
       - State transition history
       - Audit events
       - Timeline visualization
   """

   import sys
   import argparse
   from datetime import datetime
   from typing import List, Dict
   from pathlib import Path

   # 添加项目根目录到路径
   project_root = Path(__file__).parent.parent
   sys.path.insert(0, str(project_root))

   from agentos.core.task.state_machine import TaskStateMachine
   from agentos.core.task.audit_service import TaskAuditService
   from agentos.core.task.service import TaskService


   def format_timestamp(ts_str: str) -> str:
       """格式化时间戳"""
       try:
           dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
           return dt.strftime("%Y-%m-%d %H:%M:%S")
       except:
           return ts_str


   def print_header(title: str):
       """打印标题"""
       print(f"\n{'='*70}")
       print(f"  {title}")
       print(f"{'='*70}\n")


   def replay_transitions(task_id: str):
       """回放状态转换历史"""
       sm = TaskStateMachine()
       history = sm.get_transition_history(task_id)

       if not history:
           print("⚠️  No transition history found.")
           return

       print(f"📊 Found {len(history)} state transitions:\n")

       for idx, entry in enumerate(history, 1):
           timestamp = format_timestamp(entry.get('created_at', ''))
           from_state = entry.get('from_state', 'UNKNOWN')
           to_state = entry.get('to_state', 'UNKNOWN')
           actor = entry.get('actor', 'system')
           reason = entry.get('reason', 'N/A')

           print(f"  {idx}. [{timestamp}]")
           print(f"     {from_state} → {to_state}")
           print(f"     Actor: {actor}")
           print(f"     Reason: {reason}")

           if entry.get('metadata'):
               print(f"     Metadata: {entry['metadata']}")

           print()


   def replay_audit_events(task_id: str, detailed: bool = False):
       """回放审计事件"""
       audit = TaskAuditService()
       events = audit.get_task_audits(task_id)

       if not events:
           print("⚠️  No audit events found.")
           return

       print(f"📋 Found {len(events)} audit events:\n")

       # 按event_type分组
       event_types = {}
       for event in events:
           et = event.get('event_type', 'UNKNOWN')
           event_types[et] = event_types.get(et, 0) + 1

       # 显示统计
       print("Event Type Summary:")
       for et, count in sorted(event_types.items()):
           print(f"  - {et}: {count}")
       print()

       if detailed:
           print("\nDetailed Events:\n")
           for idx, event in enumerate(events, 1):
               timestamp = format_timestamp(event.get('created_at', ''))
               event_type = event.get('event_type', 'UNKNOWN')
               level = event.get('level', 'INFO')
               payload = event.get('payload', {})

               print(f"  {idx}. [{timestamp}] {event_type}")
               print(f"     Level: {level}")
               if payload:
                   print(f"     Payload: {payload}")
               print()


   def get_task_info(task_id: str) -> Dict:
       """获取任务基本信息"""
       ts = TaskService()
       task = ts.get_task(task_id)

       if not task:
           return None

       return {
           'title': task.get('title', 'N/A'),
           'objective': task.get('objective', 'N/A'),
           'mode': task.get('mode', 'N/A'),
           'status': task.get('status', 'N/A'),
           'created_at': task.get('created_at', 'N/A'),
           'updated_at': task.get('updated_at', 'N/A'),
       }


   def replay_task_lifecycle(task_id: str, detailed: bool = False):
       """完整回放任务生命周期"""
       print_header(f"Task Lifecycle Replay: {task_id}")

       # 1. 任务基本信息
       task_info = get_task_info(task_id)
       if not task_info:
           print(f"❌ Task {task_id} not found.")
           return

       print("📝 Task Information:")
       print(f"  Title: {task_info['title']}")
       print(f"  Objective: {task_info['objective']}")
       print(f"  Mode: {task_info['mode']}")
       print(f"  Status: {task_info['status']}")
       print(f"  Created: {format_timestamp(task_info['created_at'])}")
       print(f"  Updated: {format_timestamp(task_info['updated_at'])}")
       print()

       # 2. 状态转换历史
       print_header("State Transition History")
       replay_transitions(task_id)

       # 3. 审计事件
       print_header("Audit Events")
       replay_audit_events(task_id, detailed)

       print(f"\n{'='*70}")
       print("✅ Replay completed.")
       print(f"{'='*70}\n")


   def main():
       parser = argparse.ArgumentParser(
           description="Replay task lifecycle with state transitions and audit events"
       )
       parser.add_argument("task_id", help="Task ID to replay")
       parser.add_argument(
           "--detailed",
           action="store_true",
           help="Show detailed audit event payloads"
       )

       args = parser.parse_args()

       try:
           replay_task_lifecycle(args.task_id, args.detailed)
       except Exception as e:
           print(f"\n❌ Error during replay: {e}")
           import traceback
           traceback.print_exc()
           sys.exit(1)


   if __name__ == "__main__":
       main()
   ```

2. **测试脚本** (10分钟)
   ```bash
   # 测试基本用法
   python3 scripts/replay_task_lifecycle.py <test_task_id>

   # 测试详细模式
   python3 scripts/replay_task_lifecycle.py <test_task_id> --detailed

   # 测试错误处理
   python3 scripts/replay_task_lifecycle.py nonexistent-task
   ```

**预期输出**:
- 新增文件: `scripts/replay_task_lifecycle.py`
- 可执行: `python3 scripts/replay_task_lifecycle.py <task_id>`
- 输出包含: 任务信息、状态转换历史、审计事件

---

#### 子任务 C2: 添加回放工具单元测试

**实施步骤**:

1. **创建测试文件** (20分钟)
   ```bash
   touch tests/unit/test_replay_tool.py
   ```

   ```python
   # tests/unit/test_replay_tool.py
   """
   Replay Tool Tests
   验证回放脚本的正确性
   """
   import pytest
   from unittest.mock import patch, MagicMock
   import sys
   from pathlib import Path

   # 导入回放脚本模块
   sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
   import replay_task_lifecycle


   class TestReplayFunctions:
       """测试回放功能"""

       def test_format_timestamp(self):
           """测试时间戳格式化"""
           ts = "2026-01-30T10:30:00Z"
           formatted = replay_task_lifecycle.format_timestamp(ts)
           assert "2026-01-30" in formatted
           assert "10:30:00" in formatted

       def test_format_timestamp_invalid(self):
           """测试无效时间戳"""
           ts = "invalid"
           formatted = replay_task_lifecycle.format_timestamp(ts)
           assert formatted == "invalid"  # 应返回原字符串

       def test_get_task_info_not_found(self, temp_db):
           """测试任务不存在"""
           info = replay_task_lifecycle.get_task_info("nonexistent")
           assert info is None

       def test_get_task_info_success(self, temp_db):
           """测试获取任务信息"""
           from agentos.core.task.service import TaskService
           ts = TaskService()

           task_id = ts.create_task(
               title="Test Task",
               objective="Test replay",
               mode="SEMIAUTONOMOUS",
               status="OPEN"
           )

           info = replay_task_lifecycle.get_task_info(task_id)
           assert info is not None
           assert info['title'] == "Test Task"
           assert info['mode'] == "SEMIAUTONOMOUS"


   class TestReplayOutput:
       """测试回放输出"""

       def test_replay_transitions_empty(self, temp_db, capsys):
           """测试空转换历史"""
           replay_task_lifecycle.replay_transitions("nonexistent")
           captured = capsys.readouterr()
           assert "No transition history" in captured.out

       def test_replay_transitions_with_data(self, temp_db, capsys):
           """测试有数据的转换历史"""
           from agentos.core.task.service import TaskService
           from agentos.core.task.state_machine import TaskStateMachine

           ts = TaskService()
           sm = TaskStateMachine()

           task_id = ts.create_task(
               title="Test",
               objective="Test",
               mode="SEMIAUTONOMOUS",
               status="OPEN"
           )

           # 执行转换
           sm.transition(task_id, to="APPROVED", actor="test", reason="Test transition")

           # 回放
           replay_task_lifecycle.replay_transitions(task_id)
           captured = capsys.readouterr()

           assert "state transitions" in captured.out
           assert "OPEN → APPROVED" in captured.out
           assert "test" in captured.out

       def test_replay_audit_events(self, temp_db, capsys):
           """测试审计事件回放"""
           from agentos.core.task.service import TaskService
           from agentos.core.task.audit_service import TaskAuditService

           ts = TaskService()
           audit = TaskAuditService()

           task_id = ts.create_task(
               title="Test",
               objective="Test",
               mode="SEMIAUTONOMOUS",
               status="OPEN"
           )

           # 记录审计事件
           audit.record_event(task_id, "TEST_EVENT", "INFO", {"key": "value"})

           # 回放
           replay_task_lifecycle.replay_audit_events(task_id)
           captured = capsys.readouterr()

           assert "audit events" in captured.out
           assert "TEST_EVENT" in captured.out
   ```

2. **运行测试** (10分钟)
   ```bash
   pytest tests/unit/test_replay_tool.py -v

   # 预期: 所有测试通过
   ```

**预期输出**:
- 新增文件: `tests/unit/test_replay_tool.py`
- 新增测试: 约7个
- 所有测试通过

---

#### 子任务 C3: 文档和验收

**实施步骤**:

1. **更新README或用户指南** (10分钟)
   ```markdown
   # 在适当位置添加回放工具说明

   ## 任务生命周期回放

   使用回放工具查看任务的完整生命周期：

   \`\`\`bash
   # 基本用法
   python3 scripts/replay_task_lifecycle.py <task_id>

   # 详细模式（包含审计事件payload）
   python3 scripts/replay_task_lifecycle.py <task_id> --detailed
   \`\`\`

   输出包括：
   - 任务基本信息（标题、目标、状态等）
   - 状态转换历史（时间线、actor、原因）
   - 审计事件摘要和详情
   ```

2. **手动验证** (10分钟)
   ```bash
   # 创建一个测试任务
   # 然后使用CLI或API进行状态转换
   # 最后使用回放工具验证

   python3 scripts/replay_task_lifecycle.py <task_id> --detailed

   # 检查输出:
   # - 任务信息正确
   # - 状态转换按时间顺序排列
   # - 审计事件完整
   ```

**验收标准**:
- ✅ 回放脚本可执行
- ✅ 输出格式清晰易读
- ✅ 单元测试全部通过
- ✅ 文档更新
- ✅ 得分提升至99分（或97分，取决于P2-B）

---

## P2-D: 完整性冲刺100分

### 任务元信息

- **任务ID**: P2-D
- **优先级**: P2
- **前置依赖**: P2-A, P2-B, P2-C完成
- **预估工时**: 2.0小时
- **得分提升**: +1分（99 → 100）
- **目标**: 补充剩余缺口，达成100分满分

### 子任务清单

#### 子任务 D1: E2E测试100%通过率

**实施步骤**:

1. **审查所有E2E测试** (20分钟)
   ```bash
   # 运行完整E2E套件
   pytest tests/integration/task/ -v --tb=short

   # 检查是否有任何失败或跳过的测试
   ```

2. **修复剩余边缘case**（如果有）(40分钟)
   - 根据具体失败情况修复

3. **验证100%通过** (10分钟)
   ```bash
   pytest tests/integration/task/ -v
   # 预期: 28/28 passed (100%), 0 skipped
   ```

**验收标准**:
- ✅ E2E测试通过率 = 100%
- ✅ 无跳过测试
- ✅ 无flaky测试

---

#### 子任务 D2: Scope覆盖率冲刺至90%+

**实施步骤**:

1. **识别剩余未覆盖区域** (15分钟)
   ```bash
   open htmlcov-scope/index.html
   # 查找覆盖率<90%的模块
   ```

2. **补充高价值分支测试** (30分钟)
   - 优先覆盖错误处理分支
   - 补充边界条件测试

3. **验证覆盖率** (5分钟)
   ```bash
   ./scripts/coverage_scope_task.sh
   # 预期: ≥ 90%
   ```

**验收标准**:
- ✅ Scope Coverage行覆盖率 ≥ 90%
- ✅ Scope Coverage分支覆盖率 ≥ 75%

---

#### 子任务 D3: 性能基准测试

**实施步骤**:

1. **创建性能基准测试文件** (20分钟)
   ```bash
   mkdir -p tests/performance
   touch tests/performance/test_state_machine_benchmark.py
   ```

   ```python
   # tests/performance/test_state_machine_benchmark.py
   """
   State Machine Performance Benchmarks
   """
   import pytest
   import time
   from agentos.core.task.state_machine import TaskStateMachine
   from agentos.core.task.service import TaskService


   @pytest.mark.benchmark
   class TestStateMachinePerformance:
       """状态机性能基准"""

       def test_transition_performance(self, temp_db, benchmark):
           """测试状态转换性能"""
           ts = TaskService()
           sm = TaskStateMachine()

           task_id = ts.create_task(
               title="Benchmark",
               objective="Test",
               mode="SEMIAUTONOMOUS",
               status="OPEN"
           )

           # Benchmark状态转换
           result = benchmark(
               sm.transition,
               task_id=task_id,
               to="APPROVED",
               actor="benchmark",
               reason="Test"
           )

           # 基准: 应在50ms内完成
           assert result is not None

       def test_batch_transitions(self, temp_db):
           """测试批量状态转换"""
           ts = TaskService()
           sm = TaskStateMachine()

           # 创建100个任务并进行转换
           start = time.time()

           for i in range(100):
               task_id = ts.create_task(
                   title=f"Batch {i}",
                   objective="Test",
                   mode="SEMIAUTONOMOUS",
                   status="OPEN"
               )
               sm.transition(task_id, to="APPROVED", actor="test", reason="Batch")

           elapsed = time.time() - start

           # 基准: 100个转换应在5秒内完成
           assert elapsed < 5.0
           print(f"\nBatch transitions: {elapsed:.2f}s ({100/elapsed:.1f} ops/s)")
   ```

2. **运行基准测试** (10分钟)
   ```bash
   pytest tests/performance/test_state_machine_benchmark.py -v

   # 如果安装了pytest-benchmark
   pytest tests/performance/test_state_machine_benchmark.py --benchmark-only
   ```

**验收标准**:
- ✅ 性能基准测试创建
- ✅ 基准测试通过
- ✅ 性能指标documented

---

#### 子任务 D4: 最终验收

**实施步骤**:

1. **运行完整测试套件** (15分钟)
   ```bash
   # Unit测试
   pytest tests/unit/task -v

   # E2E测试
   pytest tests/integration/task -v

   # 性能测试
   pytest tests/performance/ -v
   ```

2. **生成最终覆盖率报告** (5分钟)
   ```bash
   ./scripts/coverage_scope_task.sh

   # 检查输出
   # 预期: Scope Coverage ≥ 90%
   ```

3. **重新计算最终得分** (10分钟)
   ```bash
   # 参考FINAL_100_SCORE_ACCEPTANCE_REPORT.md的评分公式

   # 维度1: 核心代码 20/20 ✅
   # 维度2: 测试覆盖 20/20 ✅
   #   - Unit: 4/4 ✅
   #   - E2E: 8/8 ✅
   #   - Scope: 4/4 ✅ (≥90%)
   #   - Project: 4/4 ✅
   # 维度3: 文档完整性 20/20 ✅
   # 维度4: 集成验证 20/20 ✅
   #   - E2E环境: 8/8 ✅
   #   - 关键路径: 8/8 ✅
   #   - 向后兼容: 4/4 ✅
   # 维度5: 运维/观测 20/20 ✅
   #   - 指标齐全: 6/6 ✅
   #   - 告警配置: 4/4 ✅
   #   - 审计完整: 6/6 ✅
   #   - 可回放: 4/4 ✅

   # 总分: 100/100 ✅✅✅
   ```

**验收标准**:
- ✅ 所有测试通过（Unit + E2E + Performance）
- ✅ Scope Coverage ≥ 90%
- ✅ E2E通过率 = 100%
- ✅ 性能基准建立
- ✅ 最终得分 = 100分

---

## 附录A: 验证命令清单

### A.1 P2-A验证

```bash
# 验证Retry E2E
pytest tests/integration/task/test_retry_e2e.py -v
# 预期: 16/16 passed

# 验证Timeout E2E
pytest tests/integration/task/test_timeout_e2e.py -v
# 预期: 5/5 passed

# 验证完整E2E套件
pytest tests/integration/task/ -v
# 预期: 28/28 passed (100%)

# 验证得分
# 预期: 95分
```

### A.2 P2-B验证

```bash
# 运行新增测试
pytest tests/unit/task/test_state_machine_errors.py -v
pytest tests/unit/task/test_work_items_coverage.py -v
pytest tests/unit/task/test_event_service.py -v

# 生成覆盖率
./scripts/coverage_scope_task.sh

# 查看HTML报告
open htmlcov-scope/index.html

# 验证覆盖率
# 预期: Scope Coverage ≥ 85%

# 验证得分
# 预期: 97分
```

### A.3 P2-C验证

```bash
# 测试回放脚本
python3 scripts/replay_task_lifecycle.py <task_id>
python3 scripts/replay_task_lifecycle.py <task_id> --detailed

# 运行单元测试
pytest tests/unit/test_replay_tool.py -v

# 验证得分
# 预期: 99分
```

### A.4 P2-D验证

```bash
# 完整测试套件
pytest tests/unit/task -v
pytest tests/integration/task -v
pytest tests/performance/ -v

# 最终覆盖率
./scripts/coverage_scope_task.sh

# 验证得分
# 预期: 100分
```

---

## 附录B: 问题排查指南

### B.1 E2E测试失败

**症状**: `sqlite3.OperationalError: no such table: tasks`

**排查步骤**:
1. 检查fixture是否正确初始化数据库
2. 检查schema SQL文件路径是否正确
3. 检查是否有standalone BEGIN/COMMIT语句需要过滤
4. 参考test_event_service.py的成功案例

### B.2 覆盖率未提升

**症状**: 添加测试后覆盖率没有明显变化

**排查步骤**:
1. 确认测试实际执行了（不是被skip）
2. 检查测试是否真正覆盖了目标代码行
3. 使用`--cov-report=html`查看详细覆盖情况
4. 确认mock没有阻止代码执行

### B.3 回放脚本错误

**症状**: 回放脚本抛出异常

**排查步骤**:
1. 检查task_id是否存在
2. 检查数据库路径是否正确
3. 检查API是否有breaking changes
4. 使用`--help`查看用法

---

## 附录C: 时间分配建议

### C.1 最小可行路径（95分）

**总工时**: 1.5小时
- P2-A: 1.5h → 95分

### C.2 推荐路径（99分）

**总工时**: 5.5小时
- 第1天: P2-A (1.5h) → 95分
- 第2天: P2-B (3.0h) || P2-C (1.0h) → 99分

### C.3 完整路径（100分）

**总工时**: 7.5小时
- 第1天: P2-A (1.5h) → 95分
- 第2天: P2-B (3.0h) || P2-C (1.0h) → 99分
- 第3天: P2-D (2.0h) → 100分

---

## 结论

本文档提供了P2阶段从89分到100分的详细实施指南，包括：

- 4个并行任务的详细步骤
- 每个子任务的代码示例
- 完整的验收标准
- 问题排查指南
- 时间分配建议

**推荐执行顺序**:
1. 立即启动P2-A（E2E环境修复）→ 快速达成95分
2. 并行执行P2-B和P2-C → 达成99分
3. 冲刺P2-D → 达成100分满分

**所有任务均可独立执行，无外部依赖，风险可控。**

---

**文档生成时间**: 2026-01-30
**文档版本**: v1.0
**下一步**: 开始执行P2-A任务
