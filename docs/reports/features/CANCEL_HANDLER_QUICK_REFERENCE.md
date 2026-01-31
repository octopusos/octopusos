# CancelHandler Quick Reference

**Module**: `agentos/core/task/cancel_handler.py`
**Status**: ✅ Production Ready
**Last Updated**: 2026-01-29

---

## 🚀 Quick Start

```python
from agentos.core.task.cancel_handler import CancelHandler

handler = CancelHandler()
```

---

## 📖 API Reference

### should_cancel(task_id, current_status)

检查任务是否应该被取消。

**签名**:
```python
should_cancel(task_id: str, current_status: str) -> tuple[bool, Optional[str]]
```

**参数**:
- `task_id`: 任务ID
- `current_status`: 当前已知的状态

**返回**:
- `(should_cancel, reason)` 元组
  - `should_cancel`: 是否应该取消 (bool)
  - `reason`: 取消原因或None (Optional[str])

**示例**:
```python
should_cancel, reason = handler.should_cancel("task_123", "running")
if should_cancel:
    print(f"Task needs cancellation: {reason}")
```

---

### perform_cleanup(task_id, cleanup_actions)

执行清理操作。

**签名**:
```python
perform_cleanup(
    task_id: str,
    cleanup_actions: Optional[List[str]] = None
) -> Dict[str, Any]
```

**参数**:
- `task_id`: 任务ID
- `cleanup_actions`: 清理操作列表 (默认: `["flush_logs", "release_resources"]`)

**支持的清理操作**:
- `flush_logs` - 刷新日志
- `release_resources` - 释放资源
- `save_partial_results` - 保存部分结果

**返回**:
```python
{
    "task_id": "task_123",
    "cleanup_performed": ["flush_logs", "release_resources"],
    "cleanup_failed": []
}
```

**示例**:
```python
# 默认清理
results = handler.perform_cleanup("task_123")

# 自定义清理
results = handler.perform_cleanup(
    "task_123",
    ["flush_logs", "release_resources", "save_partial_results"]
)

print(f"成功: {results['cleanup_performed']}")
print(f"失败: {results['cleanup_failed']}")
```

---

### record_cancel_event(task_id, actor, reason, cleanup_results)

记录取消事件到审计日志。

**签名**:
```python
record_cancel_event(
    task_id: str,
    actor: str,
    reason: str,
    cleanup_results: Dict[str, Any]
) -> None
```

**参数**:
- `task_id`: 任务ID
- `actor`: 取消任务的执行者
- `reason`: 取消原因
- `cleanup_results`: 清理结果 (来自 `perform_cleanup()`)

**示例**:
```python
cleanup_results = handler.perform_cleanup("task_123")

handler.record_cancel_event(
    task_id="task_123",
    actor="user_456",
    reason="User requested cancellation",
    cleanup_results=cleanup_results
)
```

---

### cancel_task_gracefully(task_id, actor, reason, cleanup_actions)

完整的取消工作流 (一站式方法)。

**签名**:
```python
cancel_task_gracefully(
    task_id: str,
    actor: str,
    reason: str,
    cleanup_actions: Optional[List[str]] = None
) -> Dict[str, Any]
```

**参数**:
- `task_id`: 任务ID
- `actor`: 取消任务的执行者
- `reason`: 取消原因
- `cleanup_actions`: 可选的清理操作列表

**返回**:
```python
{
    "task_id": "task_123",
    "canceled_by": "user_456",
    "reason": "User requested cancellation",
    "cleanup_results": {...},
    "canceled_at": "2026-01-29T13:07:30.172771+00:00"
}
```

**示例**:
```python
summary = handler.cancel_task_gracefully(
    task_id="task_123",
    actor="admin_user",
    reason="System maintenance"
)

print(f"已取消: {summary['canceled_at']}")
print(f"执行者: {summary['canceled_by']}")
```

---

## 🔄 典型工作流

### 1. 在 Runner 循环中检测取消

```python
from agentos.core.task.cancel_handler import CancelHandler

handler = CancelHandler()

while running:
    # 检查取消信号
    should_cancel, reason = handler.should_cancel(task_id, current_status)

    if should_cancel:
        # 执行清理
        cleanup_results = handler.perform_cleanup(
            task_id,
            ["flush_logs", "release_resources", "save_partial_results"]
        )

        # 记录审计
        handler.record_cancel_event(
            task_id=task_id,
            actor=task.metadata.get("cancel_actor", "system"),
            reason=reason,
            cleanup_results=cleanup_results
        )

        # 退出循环
        break

    # 继续执行任务
    # ...
```

### 2. 简化版 (使用 cancel_task_gracefully)

```python
from agentos.core.task.cancel_handler import CancelHandler

handler = CancelHandler()

while running:
    should_cancel, reason = handler.should_cancel(task_id, current_status)

    if should_cancel:
        summary = handler.cancel_task_gracefully(
            task_id=task_id,
            actor="system",
            reason=reason
        )
        print(f"Task canceled: {summary}")
        break
```

---

## 📊 审计日志格式

### Event Type
- `TASK_CANCELED_DURING_EXECUTION`

### Level
- `warn`

### Payload Structure
```json
{
  "actor": "user_123",
  "reason": "User requested cancellation",
  "canceled_at": "2026-01-29T13:07:30.172771+00:00",
  "cleanup_results": {
    "task_id": "task_123",
    "cleanup_performed": ["flush_logs", "release_resources"],
    "cleanup_failed": []
  },
  "cleanup_summary": {
    "total_actions": 2,
    "successful": 2,
    "failed": 0
  }
}
```

---

## 🛡️ 错误处理

### 任务不存在
```python
should_cancel, reason = handler.should_cancel("nonexistent_task", "running")
# Returns: (False, None)
# Logs warning but doesn't raise exception
```

### 未知清理操作
```python
results = handler.perform_cleanup("task_123", ["unknown_action"])
# cleanup_performed: []
# cleanup_failed: [{"action": "unknown_action", "error": "Unknown cleanup action"}]
```

### 清理失败
```python
# 如果某个清理操作失败,其他操作仍会继续执行
results = handler.perform_cleanup("task_123", ["flush_logs", "failing_action"])
# cleanup_performed: ["flush_logs"]  # 成功的操作
# cleanup_failed: [{"action": "failing_action", "error": "..."}]  # 失败的操作
```

---

## 🧪 测试

### 运行单元测试
```bash
python3 -m pytest tests/unit/task/test_cancel_handler.py -v
```

### 运行集成测试
```bash
python3 test_cancel_handler_demo.py
```

---

## 📝 设计原则

1. **容错性**: 清理失败不应阻止其他清理操作
2. **可审计性**: 完整记录所有取消事件
3. **一致性**: 与 retry_strategy 和 timeout_manager 保持一致的API风格
4. **可扩展性**: 支持自定义清理操作

---

## 🔗 相关模块

- **RetryStrategy**: `agentos/core/task/retry_strategy.py`
- **TimeoutManager**: `agentos/core/task/timeout_manager.py`
- **TaskManager**: `agentos/core/task/manager.py`
- **TaskService**: `agentos/core/task/service.py`

---

## 📚 更多文档

- **完整实现报告**: `CANCEL_HANDLER_IMPLEMENTATION_REPORT.md`
- **状态机实现方案**: `状态机100%完成落地方案.md`
- **单元测试**: `tests/unit/task/test_cancel_handler.py`
- **集成测试**: `test_cancel_handler_demo.py`

---

## 💡 最佳实践

### DO ✅
- 总是执行清理操作后再退出
- 记录取消事件到审计日志
- 使用描述性的取消原因
- 处理清理失败的情况

### DON'T ❌
- 不要在清理失败时直接退出
- 不要忽略审计日志
- 不要使用模糊的取消原因
- 不要假设所有清理操作都会成功

---

## 🎯 性能考虑

- **should_cancel()**: 轻量级数据库查询 (~1ms)
- **perform_cleanup()**: 取决于清理操作类型 (通常 <100ms)
- **record_cancel_event()**: 单次数据库写入 (~1ms)

**建议**: 在 runner 循环中,每次迭代检查一次取消信号即可,不需要更高频率。

---

**Last Updated**: 2026-01-29
**Version**: 1.0.0
**Status**: Production Ready
