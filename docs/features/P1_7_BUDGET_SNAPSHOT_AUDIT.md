# P1-7: Budget Snapshot → Audit/TaskDB

## 目标

让每一次模型调用，都能在事后被"完整复盘"：当时用的预算是什么、为何发生截断（若有）。

## 核心原则

### ✅ Snapshot 必须在调用模型前生成
- 真实生效预算
- 不受 provider 成功/失败影响
- 可用于失败场景审计

### ✅ 只存引用 + 核心摘要
- TaskDB / Audit 只存"引用 + 核心摘要"
- Snapshot 本体由 Context/Budget 系统维护
- 避免数据膨胀 & 合规风险

### ✅ 不可变性保证
- 一旦生成，snapshot_id 不可变
- 不允许执行后再补 snapshot
- 不允许 Task 推断 snapshot

## 实施架构

```
┌─────────────────────────────────────────────────────────┐
│                    Chat Engine                          │
│  1. Build Context (ContextBuilder)                      │
│     └─> Create Snapshot (snapshot_id)                   │
│  2. Invoke Model                                         │
│  3. Save Message with snapshot_id in metadata           │
└─────────────────────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  Database Storage                        │
│                                                          │
│  ┌─────────────────────────────────┐                   │
│  │  context_snapshots              │                   │
│  │  - snapshot_id (PK)             │                   │
│  │  - session_id                   │                   │
│  │  - budget_tokens                │                   │
│  │  - total_tokens_est             │                   │
│  │  - tokens_breakdown (6 fields)  │                   │
│  │  - composition_json             │                   │
│  │  - metadata (watermark, ratio)  │                   │
│  └─────────────────────────────────┘                   │
│                           │                              │
│                           ↓                              │
│  ┌─────────────────────────────────┐                   │
│  │  chat_messages                  │                   │
│  │  - message_id                   │                   │
│  │  - metadata:                    │                   │
│  │    {                            │                   │
│  │      "context_snapshot_id": ... │                   │
│  │    }                            │                   │
│  └─────────────────────────────────┘                   │
│                                                          │
│  ┌─────────────────────────────────┐                   │
│  │  tasks                          │                   │
│  │  - task_id                      │                   │
│  │  - metadata:                    │                   │
│  │    {                            │                   │
│  │      "context_snapshot_id": ... │                   │
│  │    }                            │                   │
│  └─────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  Budget Audit API                        │
│                                                          │
│  get_snapshot_by_id(snapshot_id)                        │
│  get_snapshot_for_message(message_id)                   │
│  get_snapshot_for_task(task_id)                         │
│  get_audit_summary(entity_type, entity_id)              │
└─────────────────────────────────────────────────────────┘
```

## 数据模型

### BudgetSnapshot

```python
@dataclass
class BudgetSnapshot:
    # Identifiers
    snapshot_id: str
    session_id: str
    created_at: int
    reason: str  # "send" | "dry_run" | "audit"

    # Model info
    provider: Optional[str]  # "ollama" | "openai"
    model: Optional[str]      # "qwen2.5:14b" | "gpt-4"

    # Budget totals
    budget_tokens: int        # Context window budget
    total_tokens_est: int     # Estimated total usage

    # Breakdown by source
    tokens_system: int
    tokens_window: int
    tokens_rag: int
    tokens_memory: int
    tokens_summary: int
    tokens_policy: int

    # Composition details
    composition: Dict[str, Any]  # {window_msg_ids: [...], ...}
    assembled_hash: Optional[str]

    # Threshold state
    usage_ratio: float              # 0.0 - 1.0
    watermark: ThresholdState       # SAFE | WARNING | CRITICAL
    truncation_expected: bool       # True if usage_ratio > 0.9
```

### ThresholdState

```python
class ThresholdState(Enum):
    SAFE = "safe"          # < 80%
    WARNING = "warning"    # 80% - 90%
    CRITICAL = "critical"  # > 90%
```

## API 使用示例

### 1. 查询消息的预算快照

```python
from agentos.core.chat.budget_audit import get_budget_for_message

# 查询某条消息使用的预算
audit = get_budget_for_message("msg-abc123")

if audit["status"] == "auditable":
    snapshot = audit["snapshot"]
    print(f"Budget: {snapshot['budget_tokens']} tokens")
    print(f"Usage: {snapshot['total_tokens_est']} tokens ({snapshot['usage_ratio']:.1%})")
    print(f"Watermark: {snapshot['watermark']}")
    print(f"Truncation Expected: {snapshot['truncation_expected']}")

    # 查看预算分解
    breakdown = snapshot['breakdown']
    print(f"System: {breakdown['system']} tokens")
    print(f"Window: {breakdown['window']} tokens")
    print(f"RAG: {breakdown['rag']} tokens")
    print(f"Memory: {breakdown['memory']} tokens")
else:
    print(f"Not auditable: {audit['reason']}")
    # Pre-P1-7 message - no snapshot available
```

### 2. 查询 Task 的预算快照

```python
from agentos.core.chat.budget_audit import get_budget_for_task

audit = get_budget_for_task("task-xyz789")

if audit["status"] == "auditable":
    snapshot = audit["snapshot"]

    # 检查是否接近预算上限
    if snapshot["watermark"] == "critical":
        print("⚠️ Task was executed near budget limit")

    # 检查是否发生截断
    if snapshot["truncation_expected"]:
        print("⚠️ Context may have been truncated")
```

### 3. 使用 BudgetAuditAPI 类

```python
from agentos.core.chat.budget_audit import BudgetAuditAPI

api = BudgetAuditAPI()

# 直接查询 snapshot
snapshot = api.get_snapshot_by_id("snap-123")
if snapshot:
    print(f"Budget: {snapshot.budget_tokens}")
    print(f"Usage Ratio: {snapshot.usage_ratio}")

# 查询消息关联的 snapshot
snapshot = api.get_snapshot_for_message("msg-456")
if snapshot:
    data = snapshot.to_dict()
    # 返回完整的字典，可用于 JSON 序列化

# 获取审计摘要
summary = api.get_audit_summary("message", "msg-789")
```

## 关键改动点

### 1. Chat Engine (`agentos/core/chat/engine.py`)

```python
# Line ~206: Non-streaming response
message_metadata = {
    "model_route": model_route,
    "context_tokens": context_pack.metadata.get("total_tokens"),
    "rag_chunks": len(context_pack.audit.get("rag_chunk_ids", [])),
    "memory_facts": len(context_pack.audit.get("memory_ids", []))
}

# P1-7: Link budget snapshot for audit traceability
if context_pack.snapshot_id:
    message_metadata["context_snapshot_id"] = context_pack.snapshot_id

# Line ~291: Streaming response
message_metadata = {
    "model_route": model_route,
    "context_tokens": context_pack.metadata.get("total_tokens"),
    "streamed": True
}

# P1-7: Link budget snapshot for audit traceability
if context_pack.snapshot_id:
    message_metadata["context_snapshot_id"] = context_pack.snapshot_id
```

### 2. Audit Events (`agentos/core/audit.py`)

新增审计事件类型：

```python
# P1-7: Budget snapshot audit events
BUDGET_SNAPSHOT_CREATED = "BUDGET_SNAPSHOT_CREATED"
BUDGET_SNAPSHOT_LINKED = "BUDGET_SNAPSHOT_LINKED"
```

### 3. Budget Audit API (`agentos/core/chat/budget_audit.py`)

新增模块，提供完整的预算审计 API。

### 4. Database Schema

`context_snapshots` 表（已存在于 schema_v11.sql）：

```sql
CREATE TABLE IF NOT EXISTS context_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    reason TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    budget_tokens INTEGER NOT NULL,
    total_tokens_est INTEGER NOT NULL,
    tokens_system INTEGER NOT NULL DEFAULT 0,
    tokens_window INTEGER NOT NULL DEFAULT 0,
    tokens_rag INTEGER NOT NULL DEFAULT 0,
    tokens_memory INTEGER NOT NULL DEFAULT 0,
    tokens_summary INTEGER NOT NULL DEFAULT 0,
    tokens_policy INTEGER NOT NULL DEFAULT 0,
    composition_json TEXT NOT NULL,
    assembled_hash TEXT,
    metadata TEXT
);
```

## 向后兼容性

### 处理旧消息/任务

P1-7 之前创建的消息/任务没有 `context_snapshot_id`，查询时会返回：

```python
{
    "status": "not_auditable",
    "reason": "no_snapshot_linked",
    "entity_type": "message",
    "entity_id": "msg-old-123",
    "note": "This entity was created before P1-7 implementation"
}
```

这是**预期行为**，不影响系统运行。

### 检查可审计性

```python
audit = get_budget_for_message(message_id)

if audit["status"] == "not_auditable":
    # 旧消息，无快照
    print("This message predates budget tracking")
elif audit["status"] == "auditable":
    # 新消息，有快照
    snapshot = audit["snapshot"]
    # 可以进行完整审计
```

## 验收标准

### ✅ 任意 Task/Message 都能回答：

1. **当时预算是多少？**
   ```python
   snapshot.budget_tokens  # 4000
   ```

2. **是否已接近上限？**
   ```python
   snapshot.watermark  # SAFE | WARNING | CRITICAL
   snapshot.usage_ratio  # 0.85 (85%)
   ```

3. **是否预期会发生截断？**
   ```python
   snapshot.truncation_expected  # True if usage_ratio > 0.9
   ```

4. **预算如何分配的？**
   ```python
   snapshot.tokens_system   # 500
   snapshot.tokens_window   # 1200
   snapshot.tokens_rag      # 800
   snapshot.tokens_memory   # 600
   snapshot.tokens_summary  # 300
   ```

### ✅ Snapshot 丢失 → Task 必须标记为不可完全复盘

```python
audit = get_budget_for_task("old-task-123")
assert audit["status"] == "not_auditable"
assert audit["reason"] == "no_snapshot_linked"
```

### ✅ 不影响现有 Task 结构（向后兼容）

- 旧消息/任务不崩溃
- 新消息/任务自动关联 snapshot
- API 正确处理两种情况

## 测试覆盖

### 集成测试 (`tests/integration/chat/test_budget_snapshot_audit.py`)

- ✅ Snapshot 创建和检索
- ✅ Snapshot 关联到 Message
- ✅ 查询不存在的 Snapshot
- ✅ 查询没有 Snapshot 的旧消息（向后兼容）
- ✅ 审计摘要查询（auditable / not_auditable）
- ✅ 阈值状态检测（safe / warning / critical）
- ✅ 预算分解正确性
- ✅ 便捷函数

### 单元测试 (`tests/unit/chat/test_budget_audit_api.py`)

- ✅ 解析 safe watermark
- ✅ 解析 warning watermark
- ✅ 解析 critical watermark 和截断预期
- ✅ BudgetSnapshot.to_dict() 序列化
- ✅ 查询不存在的 snapshot
- ✅ 查询没有 snapshot_id 的消息
- ✅ 查询有 snapshot_id 的消息
- ✅ 审计摘要（auditable）
- ✅ 审计摘要（not_auditable）
- ✅ 截断预期阈值 (>90%)

## 守门员合规检查

### ✅ Snapshot 必须在调用模型前生成
- `ContextBuilder.build()` 在返回 `ContextPack` 前生成 `snapshot_id`
- Chat Engine 在调用模型后立即关联 `snapshot_id`

### ✅ Snapshot 不可变
- `snapshot_id` 一旦生成，写入数据库后不可修改
- 不允许执行后再补 snapshot

### ✅ Task 不推断 snapshot
- 必须显式通过 `metadata["context_snapshot_id"]` 关联
- 不允许猜测或自动推断

### ✅ 只存引用 + 核心摘要
- Message/Task 只存 `snapshot_id` 引用
- 完整 snapshot 数据存储在 `context_snapshots` 表
- 不复制完整上下文内容

## 下一步工作

### P1-8: Completion 截断 UX 文案
- 利用 `snapshot.truncation_expected` 标志
- 在 WebUI 中展示预算状态
- 提供用户友好的截断提示

### P2-9: Budget 推荐系统
- 基于历史 snapshot 数据
- 智能建议合适的 context window
- 只"建议"，不"决定"

## 总结

P1-7 实现了完整的预算可审计性：

1. **写入时机正确**：Snapshot 在调用模型前生成
2. **存储最小化**：只存引用 + 核心摘要
3. **生命周期清晰**：Message/Task → Snapshot 的单向关联
4. **向后兼容**：旧数据不崩溃，新数据自动关联
5. **完全可审计**：任意调用都能回答"当时预算是什么"

所有验收标准通过 ✅
所有守门员红线遵守 ✅
