# Task #8 快速参考: Alert Integration

## 快速验证

### 1. 检查代码修改

```bash
# 检查导入
grep -n "alert_mode_violation" agentos/core/executor/executor_engine.py

# 输出应该有 2 行:
# 25:from agentos.core.mode.mode_alerts import alert_mode_violation
# 679:            alert_mode_violation(
```

### 2. 语法检查

```bash
python3 -m py_compile agentos/core/executor/executor_engine.py
# 应该无输出（表示成功）
```

### 3. 运行验证脚本

```bash
python3 verify_task8_alert_integration.py
# 应该看到 6 个 ✅ 和成功总结
```

---

## 修改摘要

| 项目 | 值 |
|------|---|
| 修改文件 | `agentos/core/executor/executor_engine.py` |
| 新增代码行数 | 13 行 |
| 修改位置 1 | 第 25 行（导入） |
| 修改位置 2 | 第 678-688 行（告警调用） |
| 依赖文件 | `agentos/core/mode/mode_alerts.py` (Task #7) |
| 配置文件 | `configs/mode/alert_config.json` (Task #9) |

---

## 关键代码片段

### 导入语句 (Line 25)

```python
from agentos.core.mode.mode_alerts import alert_mode_violation
```

### 告警调用 (Lines 678-688)

```python
# 🔔 Mode 违规告警
alert_mode_violation(
    mode_id=mode_id,
    operation="apply_diff",
    message=f"Mode '{mode_id}' attempted to apply diff (forbidden)",
    context={
        "audit_context": audit_context or "unknown",
        "allows_commit": False,
        "error_category": "config"
    }
)
```

---

## 告警参数说明

| 参数 | 类型 | 值 | 说明 |
|------|------|---|------|
| `mode_id` | str | 当前 mode ID | 触发违规的模式 |
| `operation` | str | "apply_diff" | 违规的操作类型 |
| `message` | str | 动态消息 | 人类可读的违规描述 |
| `context.audit_context` | str | audit_context or "unknown" | 审计上下文（通常是 tool_run_id） |
| `context.allows_commit` | bool | False | Mode 是否允许 commit |
| `context.error_category` | str | "config" | 错误类别 |

---

## 告警输出位置

### 默认输出（控制台）

- **格式**: 彩色文本 + emoji
- **目标**: stderr
- **示例**:
  ```
  [2026-01-30T12:00:00Z] ❌ ERROR [read_only] apply_diff: Mode 'read_only' attempted to apply diff (forbidden)
  ```

### 可选输出（文件）

- **文件**: `outputs/mode_alerts.jsonl`
- **格式**: JSONL（每行一个 JSON 对象）
- **配置**:
  ```python
  from agentos.core.mode.mode_alerts import get_alert_aggregator, FileAlertOutput

  aggregator = get_alert_aggregator()
  aggregator.add_output(FileAlertOutput("outputs/mode_alerts.jsonl"))
  ```

---

## 触发条件

告警在以下情况触发：

1. ✅ 调用 `apply_diff_or_raise()` 方法
2. ✅ mode 不允许 commit (`mode.allows_commit() == False`)
3. ✅ 在 `ModeViolationError` 异常抛出之前

**不触发的情况**:
- ❌ Mode 允许 commit (implementation mode)
- ❌ 在其他方法中
- ❌ 异常抛出之后

---

## 执行流程

```
┌─────────────────────────────────┐
│  apply_diff_or_raise() 被调用   │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  检查 mode.allows_commit()      │
└────────────┬────────────────────┘
             │
             ├─ YES (implementation) ─→ 继续执行 diff 应用
             │
             └─ NO (其他 mode)
                  │
                  ▼
          ┌──────────────────────┐
          │ log_event("mode_diff │  ← 审计日志
          │      _denied")       │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │ alert_mode_violation │  ← 🔔 告警（新增）
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │ raise ModeViolation  │  ← 异常
          │      Error           │
          └──────────────────────┘
```

---

## 测试告警

### 方法 1: 单元测试（Task #10）

```bash
# 待 Task #10 完成后运行
python3 -m pytest tests/unit/mode/test_mode_alerts.py -v
```

### 方法 2: 模拟违规

```python
from agentos.core.mode.mode_alerts import alert_mode_violation

# 手动发送告警测试
alert_mode_violation(
    mode_id="test_mode",
    operation="apply_diff",
    message="Test alert",
    context={"test": True}
)
```

### 方法 3: E2E 测试

创建一个 `read_only` mode 的执行请求，尝试 apply diff：

```python
execution_request = {
    "execution_request_id": "test_001",
    "mode_id": "read_only",  # ← 不允许 commit
    "allowed_operations": [
        {"action": "git_commit", "params": {"message": "test"}}
    ]
}

# 应该触发告警并抛出 ModeViolationError
```

---

## 故障排查

### 问题 1: 告警没有显示

**检查**:
```python
from agentos.core.mode.mode_alerts import get_alert_aggregator

aggregator = get_alert_aggregator()
print(aggregator.get_stats())  # 检查 total_alerts
```

**可能原因**:
- Mode 实际上允许 commit (检查 mode_id)
- 没有调用 apply_diff_or_raise()
- 告警发送失败（检查 stderr 输出）

### 问题 2: 文件输出不工作

**检查**:
```bash
ls -la outputs/mode_alerts.jsonl
```

**可能原因**:
- 没有配置 FileAlertOutput（默认只有 ConsoleOutput）
- outputs 目录没有写权限
- 磁盘空间不足

**解决**:
```python
# 在应用启动时添加
from agentos.core.mode.mode_alerts import get_alert_aggregator, FileAlertOutput

aggregator = get_alert_aggregator()
aggregator.add_output(FileAlertOutput("outputs/mode_alerts.jsonl"))
```

### 问题 3: 告警格式不对

**检查告警内容**:
```python
aggregator = get_alert_aggregator()
recent = aggregator.get_recent_alerts(limit=1)
print(recent[0].to_dict())
```

**正确格式**:
```json
{
  "timestamp": "2026-01-30T12:00:00Z",
  "severity": "error",
  "mode_id": "read_only",
  "operation": "apply_diff",
  "message": "Mode 'read_only' attempted to apply diff (forbidden)",
  "context": {
    "audit_context": "exec_001",
    "allows_commit": false,
    "error_category": "config"
  }
}
```

---

## 相关任务

| 任务 | 状态 | 说明 |
|------|------|------|
| Task #7 | ✅ 完成 | 创建 mode_alerts.py |
| Task #8 | ✅ 完成 | 集成告警到 executor_engine.py (本任务) |
| Task #9 | ✅ 完成 | 创建 alert_config.json |
| Task #10 | 🔄 进行中 | 编写告警系统单元测试 |
| Task #11 | ⏳ 待开始 | Gate GM4 告警集成验证 |

---

## 一键验证命令

```bash
# 完整验证（推荐）
python3 verify_task8_alert_integration.py && \
python3 -m py_compile agentos/core/executor/executor_engine.py && \
echo "✅ Task #8 验证通过"

# 快速检查（仅代码）
grep -q "alert_mode_violation" agentos/core/executor/executor_engine.py && \
echo "✅ 代码修改存在"
```

---

## 文档和证明

- 📄 完整报告: `TASK8_COMPLETION_REPORT.md`
- 🧪 验证脚本: `verify_task8_alert_integration.py`
- 📋 快速参考: `TASK8_QUICK_REFERENCE.md` (本文档)
- 📊 告警输出: `outputs/mode_alerts.jsonl` (运行后生成)

---

**任务完成日期**: 2026-01-30
**验收状态**: ✅ 通过所有验收标准
**下一步**: Task #11 - Gate GM4 告警集成验证
