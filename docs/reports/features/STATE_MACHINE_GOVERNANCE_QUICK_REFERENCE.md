# 状态机治理能力 - 快速参考

**版本**: v1.0 | **更新**: 2026-01-30 | **适用**: AgentOS v0.4+

---

## 🚀 5分钟快速上手

### 1. 理解核心概念

**治理能力 = 规则 + 证据 + 审计 + 回放 + 验收**

- **规则**：State Entry Gates（关键状态进入条件）
- **证据**：exit_reason, cleanup_summary, audit_events
- **审计**：所有状态迁移记录到 task_audits
- **回放**：replay_task_lifecycle.py 工具
- **验收**：validate_task_compliance() 函数

### 2. 关键状态 Gate 检查

| 状态 | Gate 条件 | 行为 |
|-----|----------|------|
| **DONE** | 审计日志 ≥ 2 条 | ⚠️ 警告（不拒绝） |
| **FAILED** | 必须有 exit_reason | ❌ 强制拒绝 |
| **CANCELED** | 建议有 cleanup_summary | ✅ 自动创建 |

### 3. 快速检查任务合规性

```python
# 导入
from scripts.replay_task_lifecycle import replay_task_lifecycle

# 回放生命周期
timeline = replay_task_lifecycle("your_task_id")
print(f"Total events: {len(timeline)}")

# 检查合规性（需要在文档中复制 validate_task_compliance 函数）
result = validate_task_compliance("your_task_id")
if result["compliant"]:
    print("✅ Task is compliant")
else:
    print(f"❌ Issues: {result['issues']}")
```

---

## 📋 常见操作速查

### 操作 1: 查看任务审计日志

```python
import sqlite3
import json

conn = sqlite3.connect("agentos.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT event_type, level, payload, created_at
    FROM task_audits
    WHERE task_id = ?
    ORDER BY created_at DESC
    LIMIT 20
""", ("your_task_id",))

for row in cursor.fetchall():
    print(f"[{row[1]}] {row[0]} at {row[3]}")
```

### 操作 2: 回放任务生命周期

```bash
# 命令行
python scripts/replay_task_lifecycle.py <task_id>

# 带摘要
python scripts/replay_task_lifecycle.py <task_id> --summary

# JSON 格式
python scripts/replay_task_lifecycle.py <task_id> --format json
```

### 操作 3: 设置 exit_reason（避免 FAILED Gate 拒绝）

```python
from agentos.core.task import TaskManager

tm = TaskManager()
task = tm.get_task("your_task_id")

# 设置 exit_reason
task.metadata["exit_reason"] = "timeout"  # 或其他有效原因
tm.update_task(task)

# 然后可以安全地转换到 FAILED 状态
from agentos.core.task.service import TaskService
service = TaskService()
service.fail_task("your_task_id", actor="system", reason="Task timed out")
```

### 操作 4: 为 CANCELED 任务添加 cleanup_summary

```python
from agentos.core.task.service import TaskService

service = TaskService()

cleanup_summary = {
    "cleanup_performed": [
        "stopped runner process",
        "released lease"
    ],
    "cleanup_failed": [],
    "cleanup_skipped": []
}

service.cancel_task(
    task_id="your_task_id",
    actor="user",
    reason="User requested cancellation",
    cleanup_summary=cleanup_summary
)
```

---

## 🔑 有效 exit_reason 列表

```python
VALID_EXIT_REASONS = [
    "timeout",           # 任务超时
    "retry_exhausted",   # 重试次数用尽
    "canceled",          # 用户取消
    "exception",         # 未处理异常
    "gate_failed",       # Gate 检查失败
    "user_stopped",      # 用户主动停止
    "fatal_error",       # 致命错误
    "max_iterations",    # 超过最大迭代次数
    "blocked",           # 执行被阻塞
    "unknown",           # 未知原因（兜底）
]
```

**推荐映射**：

| 场景 | 推荐 exit_reason |
|-----|-----------------|
| 超时 | `"timeout"` |
| 异常崩溃 | `"exception"` |
| 用户取消 | `"canceled"` |
| 重试失败 | `"retry_exhausted"` |
| 系统阻塞 | `"blocked"` |
| 其他 | `"unknown"` |

---

## ⚠️ 常见错误和解决方案

### 错误 1: "cannot fail without exit_reason"

**原因**：任务转换到 FAILED 状态但 metadata 中没有 exit_reason

**解决**：
```python
task.metadata["exit_reason"] = "exception"  # 添加 exit_reason
tm.update_task(task)
```

### 错误 2: "insufficient audit trail"

**原因**：任务的 audit 日志少于 2 条（DONE Gate 警告）

**解决**：这只是警告，不会阻止转换。如果需要补充审计：
```python
service.add_audit(
    task_id="your_task_id",
    event_type="AUDIT_BACKFILL",
    level="info",
    payload={"reason": "Historical audit backfill"}
)
```

### 错误 3: cleanup_summary 格式错误

**原因**：cleanup_summary 缺少必需字段

**解决**：使用标准格式：
```python
cleanup_summary = {
    "cleanup_performed": [],  # 必需
    "cleanup_failed": [],     # 必需
    "cleanup_skipped": []     # 必需
}
```

---

## 📊 治理指标查询

### 查询 1: 审计覆盖率

```sql
SELECT
    (SELECT COUNT(DISTINCT task_id) FROM task_audits) * 1.0 /
    (SELECT COUNT(*) FROM tasks) as audit_coverage_rate;
```

### 查询 2: Exit Reason 覆盖率（FAILED 任务）

```sql
SELECT
    SUM(CASE WHEN json_extract(metadata, '$.exit_reason') IS NOT NULL THEN 1 ELSE 0 END) * 1.0 /
    COUNT(*) as exit_reason_coverage_rate
FROM tasks
WHERE status = 'failed';
```

### 查询 3: Cleanup Summary 覆盖率（CANCELED 任务）

```sql
SELECT
    SUM(CASE WHEN json_extract(metadata, '$.cleanup_summary') IS NOT NULL THEN 1 ELSE 0 END) * 1.0 /
    COUNT(*) as cleanup_coverage_rate
FROM tasks
WHERE status = 'canceled';
```

### 查询 4: 状态转换统计

```sql
SELECT
    event_type,
    COUNT(*) as transition_count
FROM task_audits
WHERE event_type LIKE 'STATE_TRANSITION_%'
GROUP BY event_type
ORDER BY transition_count DESC;
```

---

## 🎯 治理最佳实践

### ✅ DO（推荐）

1. **始终通过 TaskService 操作状态**
   ```python
   # ✅ 好
   from agentos.core.task.service import TaskService
   service = TaskService()
   service.approve_task(task_id, actor="user", reason="...")
   ```

2. **失败任务必须设置 exit_reason**
   ```python
   # ✅ 好
   task.metadata["exit_reason"] = "timeout"
   service.fail_task(task_id, actor="system", reason="...")
   ```

3. **取消任务时提供 cleanup_summary**
   ```python
   # ✅ 好
   cleanup_summary = {...}
   service.cancel_task(task_id, actor="user", reason="...", cleanup_summary=cleanup_summary)
   ```

### ❌ DON'T（避免）

1. **不要直接设置 task.status**
   ```python
   # ❌ 差
   task.status = "approved"
   tm.update_task(task)
   ```

2. **不要使用 TaskManager.update_task_status()**
   ```python
   # ❌ 差（已废弃）
   tm.update_task_status(task_id, "approved")
   ```

3. **不要让 FAILED 任务缺少 exit_reason**
   ```python
   # ❌ 差（会被 Gate 拒绝）
   service.fail_task(task_id, actor="system", reason="...")
   # 缺少 task.metadata["exit_reason"] = "..."
   ```

---

## 📚 完整文档链接

- [完整实施报告](STATE_MACHINE_GOVERNANCE_IMPLEMENTATION_REPORT.md)
- [运维手册（治理章节）](docs/task/STATE_MACHINE_OPERATIONS.md#7-治理与合规)
- [回放工具源码](scripts/replay_task_lifecycle.py)
- [Gate 单元测试](tests/unit/task/test_state_machine_gates.py)

---

## 🔧 故障排查速查表

| 问题 | 诊断 | 解决方案 |
|-----|------|---------|
| Gate 检查失败 | 缺少 exit_reason | 添加 `task.metadata["exit_reason"]` |
| 审计日志缺失 | audit_count < 2 | 这只是警告，可忽略 |
| cleanup_summary 格式错误 | 缺少必需字段 | 使用标准 schema |
| 状态转换被拒绝 | InvalidTransitionError | 检查转换表是否允许此转换 |
| 任务不合规 | validate_task_compliance() 失败 | 参考 issues 列表逐一修复 |

---

**快速参考结束** | 如需详细信息，请查看完整文档
