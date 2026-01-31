# P1-7: Budget Snapshot → Audit/TaskDB - 快速参考

## 一句话总结

让每次模型调用都能完整复盘：当时用的预算是什么、为何发生截断（若有）。

---

## 快速使用

### 查询消息预算

```python
from agentos.core.chat.budget_audit import get_budget_for_message

audit = get_budget_for_message("msg-abc123")

if audit["status"] == "auditable":
    s = audit["snapshot"]
    print(f"预算: {s['budget_tokens']} tokens")
    print(f"使用: {s['total_tokens_est']} tokens ({s['usage_ratio']:.1%})")
    print(f"状态: {s['watermark']}")  # safe/warning/critical
    print(f"预期截断: {s['truncation_expected']}")  # True/False
```

### 查询 Task 预算

```python
from agentos.core.chat.budget_audit import get_budget_for_task

audit = get_budget_for_task("task-xyz789")
# 用法同上
```

### 使用 API 类

```python
from agentos.core.chat.budget_audit import BudgetAuditAPI

api = BudgetAuditAPI()

# 直接查 snapshot
snapshot = api.get_snapshot_by_id("snap-123")
if snapshot:
    print(f"Budget: {snapshot.budget_tokens}")
    print(f"System: {snapshot.tokens_system}")
    print(f"Window: {snapshot.tokens_window}")
    print(f"RAG: {snapshot.tokens_rag}")
    print(f"Memory: {snapshot.tokens_memory}")

# 查消息的 snapshot
snapshot = api.get_snapshot_for_message("msg-456")

# 获取审计摘要
summary = api.get_audit_summary("message", "msg-789")
```

---

## 核心概念

### BudgetSnapshot

```python
{
    "snapshot_id": "snap-123",
    "session_id": "session-456",
    "budget_tokens": 4000,        # 预算总量
    "total_tokens_est": 3200,     # 实际使用
    "usage_ratio": 0.8,           # 使用比例 (80%)
    "watermark": "safe",          # safe | warning | critical
    "truncation_expected": False, # True if > 90%
    "breakdown": {
        "system": 500,
        "window": 1200,
        "rag": 800,
        "memory": 600,
        "summary": 100,
        "policy": 0
    }
}
```

### ThresholdState

- **safe**: < 80% 使用率
- **warning**: 80% - 90% 使用率
- **critical**: > 90% 使用率

### Truncation Expected

- `usage_ratio > 0.9` → `truncation_expected = True`
- 表示上下文可能被截断

---

## 实施位置

### 1. Chat Engine 关联

**文件**: `agentos/core/chat/engine.py`

```python
# Line 208-210: 非流式
if context_pack.snapshot_id:
    message_metadata["context_snapshot_id"] = context_pack.snapshot_id

# Line 293-296: 流式
if context_pack.snapshot_id:
    message_metadata["context_snapshot_id"] = context_pack.snapshot_id
```

### 2. Audit 事件

**文件**: `agentos/core/audit.py`

```python
BUDGET_SNAPSHOT_CREATED = "BUDGET_SNAPSHOT_CREATED"
BUDGET_SNAPSHOT_LINKED = "BUDGET_SNAPSHOT_LINKED"
```

### 3. Budget Audit API

**文件**: `agentos/core/chat/budget_audit.py` (新建)

- `BudgetAuditAPI` 类
- `BudgetSnapshot` 数据类
- 便捷函数

---

## 测试覆盖

### 集成测试

**文件**: `tests/integration/chat/test_budget_snapshot_audit.py`

- ✅ 8 个测试全部通过
- 覆盖端到端场景

### 单元测试

**文件**: `tests/unit/chat/test_budget_audit_api.py`

- ✅ 10 个测试全部通过
- 覆盖 API 隔离测试

**总计**: 18/18 PASSED ✅

---

## 向后兼容性

### 旧消息（无 snapshot）

```python
audit = get_budget_for_message("old-msg-123")
# {
#   "status": "not_auditable",
#   "reason": "no_snapshot_linked",
#   "note": "This entity was created before P1-7 implementation"
# }
```

### 新消息（有 snapshot）

```python
audit = get_budget_for_message("new-msg-456")
# {
#   "status": "auditable",
#   "entity_type": "message",
#   "entity_id": "new-msg-456",
#   "snapshot": { ... }
# }
```

---

## 守门员红线

✅ **Snapshot 必须在调用模型前生成**
- Context 构建完成后立即生成
- 不受模型成功/失败影响

✅ **Snapshot 不可变**
- `snapshot_id` 是 PRIMARY KEY
- 不允许覆盖或修改

✅ **不推断 snapshot**
- 必须显式通过 `metadata["context_snapshot_id"]` 关联
- 找不到就返回 `not_auditable`

---

## 常见问题

### Q1: 旧消息查不到 snapshot 怎么办？

**A**: 正常现象。P1-7 之前的消息没有 snapshot，查询会返回 `not_auditable`。这是预期行为，不影响系统运行。

### Q2: 如何判断是否会发生截断？

**A**: 检查 `snapshot.truncation_expected`，如果为 `True` 表示使用率超过 90%，可能发生截断。

### Q3: 预算分解的 6 个字段是什么？

**A**:
- `system`: System prompt
- `window`: 对话窗口消息
- `rag`: RAG 检索结果
- `memory`: 记忆系统
- `summary`: 摘要 artifacts
- `policy`: 策略/规则

### Q4: 如何在 WebUI 中展示？

**A**: P1-8（Completion 截断 UX 文案）会添加 WebUI 集成。

---

## 下一步

### P1-8: Completion 截断 UX 文案

- 在 WebUI 展示 `truncation_expected` 状态
- 提供用户友好的提示

### P2-9: Budget 推荐系统

- 基于历史 snapshot 数据
- 智能推荐 context window

---

## 文档

- **完整文档**: `docs/features/P1_7_BUDGET_SNAPSHOT_AUDIT.md`
- **验收报告**: `P1_7_ACCEPTANCE_REPORT.md`
- **快速参考**: `P1_7_QUICK_REFERENCE.md` (本文件)

---

**状态**: ✅ COMPLETED
**测试**: 18/18 PASSED
**可部署**: YES
