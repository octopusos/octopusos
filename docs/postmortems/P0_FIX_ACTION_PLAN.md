# P0修复行动计划（1.5小时 → 95分）

**当前得分**: 89/100（A级）
**目标得分**: 95/100（A+级）
**增分**: +6分
**预计工时**: 1.5小时
**优先级**: 🔥 最高

---

## 🎯 修复目标

将项目从 **A级（89分）** 提升至 **A+级（95分）**，达到正式验收标准。

---

## 📋 修复清单

### ✅ P0.1 - 修复Retry E2E测试环境（+4分）

**问题描述**:
- 13/16 Retry E2E测试失败
- 错误信息：`sqlite3.OperationalError: no such table: tasks`
- 根因：测试fixture未初始化数据库schema

**影响范围**:
- 测试得分：从15分提升至19分
- E2E通过率：从50%提升至90%

**修复步骤**:

#### 步骤1：检查当前fixture结构（5分钟）
```bash
# 查看现有fixture
cat tests/integration/task/test_retry_e2e.py | grep -A10 "@pytest.fixture"
```

#### 步骤2：添加数据库初始化fixture（30分钟）
```python
# 文件: tests/integration/task/test_retry_e2e.py
# 位置: 文件顶部，import之后

import os
import sqlite3
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Initialize test database with full schema

    This fixture:
    1. Creates a temporary database file
    2. Applies the v31 schema migration
    3. Sets AGENTOS_DB_PATH env var to use test DB
    4. Cleans up after test
    """
    # Create test database
    db_path = tmp_path / "test_retry_e2e.db"
    conn = sqlite3.connect(str(db_path))

    # Load and apply schema
    schema_path = Path(__file__).parent.parent.parent.parent / \
                  "agentos/store/migrations/schema_v31_project_aware.sql"

    if not schema_path.exists():
        # Fallback to minimal schema if v31 not found
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS task_audits (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                level TEXT,
                event_type TEXT,
                payload TEXT,
                created_at TEXT
            );
        """)
    else:
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())

    conn.commit()
    conn.close()

    # Point tests to this database
    old_db_path = os.environ.get("AGENTOS_DB_PATH")
    os.environ["AGENTOS_DB_PATH"] = str(db_path)

    yield db_path

    # Cleanup
    if old_db_path:
        os.environ["AGENTOS_DB_PATH"] = old_db_path
    else:
        del os.environ["AGENTOS_DB_PATH"]
```

#### 步骤3：验证修复（15分钟）
```bash
# 运行修复后的测试
pytest tests/integration/task/test_retry_e2e.py -v --tb=short

# 预期结果：15/16 passed（仅少量预期内的失败）
```

#### 步骤4：提交更改（10分钟）
```bash
git add tests/integration/task/test_retry_e2e.py
git commit -m "fix(test): initialize database schema in retry E2E tests

- Add autouse fixture to create test database
- Apply v31 schema migration before tests
- Isolate test environment with temporary DB
- Fixes 13 failed E2E tests

Impact: E2E pass rate 50% -> 90% (+4 score points)

Related: FINAL_100_SCORE_ACCEPTANCE_REPORT.md P0.1"
```

**验证标准**:
- ✅ Retry E2E通过率 ≥ 85%（14+/16测试通过）
- ✅ 无database table错误
- ✅ 测试隔离（不污染主数据库）

**预计时间**: 1小时

---

### ✅ P0.2 - 修复Timeout exit_reason设置（+2分）

**问题描述**:
- `test_task_timeout_after_limit` 失败
- 预期 `exit_reason='timeout'`，实际 `exit_reason='unknown'`
- 根因：runner在超时时未设置metadata['exit_reason']

**影响范围**:
- 测试得分：从19分提升至21分（但目标是20分，所以+1分）
- E2E通过率：从90%提升至95%+

**修复步骤**:

#### 步骤1：定位超时处理代码（5分钟）
```bash
# 查找超时处理位置
grep -rn "check_timeout" agentos/core/runner/
grep -rn "timeout_manager" agentos/core/runner/
```

#### 步骤2：添加exit_reason设置（15分钟）

**位置1**: `agentos/core/runner/task_runner.py`（或类似文件）

```python
# 在超时检测逻辑中添加
from agentos.core.task.timeout_manager import TimeoutManager

def check_and_handle_timeout(task_id: str, timeout_config: TimeoutConfig, timeout_state: TimeoutState):
    """Check timeout and handle if exceeded"""
    manager = TimeoutManager()
    is_timeout, warning, timeout_msg = manager.check_timeout(timeout_config, timeout_state)

    if is_timeout:
        logger.warning(f"Task {task_id} timed out: {timeout_msg}")

        # 🔧 关键修复：设置exit_reason
        task_manager = TaskManager()
        current_task = task_manager.get_task(task_id)

        # Update metadata with exit_reason
        updated_metadata = current_task.metadata.copy()
        updated_metadata["exit_reason"] = "timeout"

        task_manager.update_task_metadata(
            task_id=task_id,
            metadata=updated_metadata
        )

        # Then transition to failed
        state_machine = TaskStateMachine()
        state_machine.transition(
            task_id=task_id,
            to="failed",
            actor="timeout_manager",
            reason=timeout_msg,
            metadata={"exit_reason": "timeout"}  # Also set in transition metadata
        )

        return True

    return False
```

**位置2**: `agentos/core/task/service.py` 的 timeout处理方法

```python
def handle_task_timeout(self, task_id: str, reason: str) -> Task:
    """Handle task timeout

    Args:
        task_id: Task ID
        reason: Timeout reason

    Returns:
        Updated task in failed state
    """
    # Get current task
    task = self.task_manager.get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    # 🔧 关键修复：设置exit_reason
    updated_metadata = task.metadata.copy()
    updated_metadata["exit_reason"] = "timeout"

    self.task_manager.update_task_metadata(
        task_id=task_id,
        metadata=updated_metadata
    )

    # Transition to failed with timeout reason
    return self.state_machine.transition(
        task_id=task_id,
        to="failed",
        actor="timeout_handler",
        reason=reason,
        metadata={"exit_reason": "timeout"}
    )
```

#### 步骤3：验证修复（5分钟）
```bash
# 运行timeout E2E测试
pytest tests/integration/task/test_timeout_e2e.py::TestTimeoutE2E::test_task_timeout_after_limit -v

# 预期：PASSED
```

#### 步骤4：提交更改（5分钟）
```bash
git add agentos/core/runner/task_runner.py agentos/core/task/service.py
git commit -m "fix(timeout): set exit_reason='timeout' when task times out

- Set task.metadata['exit_reason'] = 'timeout' before transition
- Ensure exit_reason propagates to failed state
- Fixes timeout E2E test assertion

Impact: E2E pass rate 90% -> 95% (+2 score points)

Related: FINAL_100_SCORE_ACCEPTANCE_REPORT.md P0.2"
```

**验证标准**:
- ✅ `test_task_timeout_after_limit` 通过
- ✅ task.metadata['exit_reason'] == 'timeout'
- ✅ 审计日志包含exit_reason

**预计时间**: 30分钟

---

## 📊 修复前后对比

### 评分对比
```
维度         修复前   修复后   增分
───────────────────────────────────
核心代码      20       20       0
测试          15       21      +6
  - Unit       8        8       0
  - E2E        4       10      +6
  - Coverage   3        3       0
文档          20       20       0
集成验证      16       16       0
运维/观测     18       18       0
───────────────────────────────────
总分          89       95      +6
评级          A        A+      ↑
```

### E2E通过率对比
```
测试套件         修复前        修复后
─────────────────────────────────────
Retry E2E       3/16 (19%)   15/16 (94%)  ✅
Timeout E2E     4/5  (80%)    5/5 (100%)  ✅
Cancel E2E      7/7 (100%)    7/7 (100%)  ✅
─────────────────────────────────────────
总计           14/28 (50%)  27/28 (96%)  ✅
```

---

## ⏱️ 执行时间表

```
时间段        任务                          状态
────────────────────────────────────────────
0:00-0:05    检查fixture结构               □
0:05-0:35    添加数据库初始化              □
0:35-0:50    验证Retry E2E修复             □
0:50-1:00    提交P0.1更改                  □
────────────────────────────────────────────
1:00-1:05    定位超时处理代码              □
1:05-1:20    添加exit_reason设置           □
1:20-1:25    验证Timeout E2E修复           □
1:25-1:30    提交P0.2更改                  □
────────────────────────────────────────────
总计: 1小时30分钟
```

---

## ✅ 验证清单

### P0.1验证
- [ ] 运行 `pytest tests/integration/task/test_retry_e2e.py -v`
- [ ] 通过率 ≥ 85%（15+/16）
- [ ] 无 "no such table" 错误
- [ ] 测试数据库隔离（tmp_path）

### P0.2验证
- [ ] 运行 `pytest tests/integration/task/test_timeout_e2e.py -v`
- [ ] `test_task_timeout_after_limit` 通过
- [ ] task.metadata['exit_reason'] == 'timeout'
- [ ] 审计日志包含超时事件

### 总体验证
- [ ] 运行所有E2E测试：`pytest tests/integration/task/ -v`
- [ ] 总通过率 ≥ 95%（27+/28）
- [ ] 重新计算测试得分 ≥ 20分
- [ ] 总分 ≥ 95分（A+级）

---

## 🚀 执行命令速查

```bash
# 1. 检查现状
pytest tests/integration/task/test_retry_e2e.py -v --tb=line | grep -E "(PASSED|FAILED)"
pytest tests/integration/task/test_timeout_e2e.py -v --tb=line | grep -E "(PASSED|FAILED)"

# 2. 修复后验证
pytest tests/integration/task/test_retry_e2e.py -v --tb=short
pytest tests/integration/task/test_timeout_e2e.py -v --tb=short

# 3. 全量测试
pytest tests/integration/task/ -v --tb=short | tail -20

# 4. 提交更改
git add tests/integration/task/test_retry_e2e.py \
        agentos/core/runner/task_runner.py \
        agentos/core/task/service.py
git commit -m "fix(test): P0 fixes for 95+ score

- Initialize DB schema in retry E2E tests
- Set exit_reason='timeout' on timeout

Impact: Score 89 -> 95 (A -> A+)"
```

---

## 📞 支持与资源

**参考文档**:
- 完整报告：`FINAL_100_SCORE_ACCEPTANCE_REPORT.md`
- 快速参考：`FINAL_ACCEPTANCE_QUICK_REFERENCE.md`
- 评分仪表盘：`FINAL_SCORE_DASHBOARD.md`

**相关代码**:
- Retry策略：`agentos/core/task/retry_strategy.py`
- Timeout管理：`agentos/core/task/timeout_manager.py`
- 状态机：`agentos/core/task/state_machine.py`

**测试文件**:
- Retry E2E：`tests/integration/task/test_retry_e2e.py`
- Timeout E2E：`tests/integration/task/test_timeout_e2e.py`
- Cancel E2E：`tests/integration/task/test_cancel_running_e2e.py`

---

## 🎯 成功标准

修复完成后，应满足：
1. ✅ E2E通过率 ≥ 95%（27+/28测试通过）
2. ✅ 测试得分 ≥ 20分
3. ✅ 总分 ≥ 95分（A+级）
4. ✅ 所有P0问题已解决
5. ✅ 代码已提交且通过CI

---

**行动计划版本**: v1.0
**创建日期**: 2026-01-30
**预计完成**: 2026-01-30 + 1.5小时
**责任人**: Development Team
