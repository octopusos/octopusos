# P4-A 快速参考指南

## 一句话总结

P4-A 将 BrainOS 的认知判断升级为可追责的决策系统，每次 Navigation/Compare/Health 调用都会生成不可篡改的决策记录。

---

## 核心概念

### DecisionRecord（决策记录）

每次 Navigation/Compare/Health 调用生成一个决策记录，包含：
- **输入**: 谁调用、什么参数
- **输出**: 返回了什么结果
- **治理**: 触发了哪些规则、最终裁决是什么
- **完整性**: SHA256 hash，可验证是否被篡改

### GovernanceAction（治理动作）

```
ALLOW           # 允许，无风险
WARN            # 警告，有风险但可继续
REQUIRE_SIGNOFF # 需要人类签字才能继续
BLOCK           # 阻止，不允许继续
```

优先级：BLOCK > REQUIRE_SIGNOFF > WARN > ALLOW

---

## API 速查

### 列出决策记录

```bash
GET /api/brain/governance/decisions?seed=file:test.py&limit=10
```

### 获取单个记录

```bash
GET /api/brain/governance/decisions/{decision_id}
```

### 重放决策（验证完整性）

```bash
GET /api/brain/governance/decisions/{decision_id}/replay
```

### 签字决策

```bash
POST /api/brain/governance/decisions/{decision_id}/signoff
Content-Type: application/json

{
  "signed_by": "admin@example.com",
  "note": "Approved after review"
}
```

### 列出治理规则

```bash
GET /api/brain/governance/rules
```

---

## 治理规则速查

| 规则 | 条件 | 动作 |
|------|------|------|
| NAV-001 | 高风险路径 | BLOCK |
| NAV-002 | 低置信度 (< 0.5) | WARN |
| NAV-003 | 盲区过多 (>= 3) | REQUIRE_SIGNOFF |
| CMP-001 | 健康分数下降 > 20% | BLOCK |
| CMP-002 | 实体删除 >= 10 | WARN |
| HLT-001 | 健康等级 CRITICAL | REQUIRE_SIGNOFF |
| HLT-002 | 认知债务 >= 50 | WARN |

---

## Python API 示例

### 查询决策记录

```python
from agentos.core.brain.store import SQLiteStore
from agentos.core.brain.governance.decision_recorder import list_decision_records, load_decision_record

# 连接数据库
store = SQLiteStore("~/.agentos/brainos/brain.db")
store.connect()

# 列出最近 10 条决策
records = list_decision_records(store, limit=10)

for r in records:
    print(f"{r['decision_id']}: {r['decision_type']} - {r['final_verdict']}")

# 获取单个记录
record = load_decision_record(store, "abc-123")

# 验证完整性
if record.verify_integrity():
    print("✅ Record is valid")
else:
    print("❌ Record has been tampered!")

store.close()
```

### 手动创建决策记录

```python
from agentos.core.brain.governance.decision_record import (
    DecisionRecord, DecisionType, DecisionStatus, GovernanceAction
)
from agentos.core.brain.governance.decision_recorder import save_decision_record
from datetime import datetime, timezone
import uuid

# 创建记录
record = DecisionRecord(
    decision_id=str(uuid.uuid4()),
    decision_type=DecisionType.NAVIGATION,
    seed="file:test.py",
    inputs={"seed": "file:test.py", "max_hops": 3},
    outputs={"paths_count": 2},
    rules_triggered=[],
    final_verdict=GovernanceAction.ALLOW,
    confidence_score=0.9,
    timestamp=datetime.now(timezone.utc).isoformat(),
    status=DecisionStatus.PENDING
)

# 计算 hash
record.record_hash = record.compute_hash()

# 保存
save_decision_record(store, record)
```

---

## 数据库查询示例

### 查找高风险决策

```sql
SELECT decision_id, seed, timestamp, final_verdict
FROM decision_records
WHERE final_verdict = 'BLOCK'
ORDER BY timestamp DESC
LIMIT 10;
```

### 统计决策类型分布

```sql
SELECT decision_type, final_verdict, COUNT(*) as count
FROM decision_records
GROUP BY decision_type, final_verdict
ORDER BY count DESC;
```

### 查找需要签字的决策

```sql
SELECT decision_id, seed, timestamp
FROM decision_records
WHERE final_verdict = 'REQUIRE_SIGNOFF'
  AND status != 'SIGNED'
ORDER BY timestamp DESC;
```

### 验证所有记录完整性（慢）

```python
import sqlite3
import json
import hashlib

conn = sqlite3.connect("~/.agentos/brainos/brain.db")
cursor = conn.cursor()

cursor.execute("SELECT decision_id, inputs, outputs, rules_triggered, timestamp, record_hash FROM decision_records")

for row in cursor.fetchall():
    decision_id, inputs, outputs, rules_triggered, timestamp, stored_hash = row

    # 重新计算 hash
    hash_input = {
        "decision_id": decision_id,
        "inputs": json.loads(inputs),
        "outputs": json.loads(outputs),
        "rules_triggered": json.loads(rules_triggered),
        "timestamp": timestamp
    }

    computed_hash = hashlib.sha256(json.dumps(hash_input, sort_keys=True).encode()).hexdigest()

    if computed_hash != stored_hash:
        print(f"⚠️ Integrity FAILED: {decision_id}")
    else:
        print(f"✅ Valid: {decision_id}")

conn.close()
```

---

## 文件位置

| 类型 | 文件路径 |
|------|---------|
| 数据模型 | `agentos/core/brain/governance/decision_record.py` |
| 记录器 | `agentos/core/brain/governance/decision_recorder.py` |
| 规则引擎 | `agentos/core/brain/governance/rule_engine.py` |
| REST API | `agentos/webui/api/brain_governance.py` |
| Schema | `agentos/core/brain/store/sqlite_schema.py` |
| 单元测试 | `tests/unit/core/brain/governance/` |
| 集成测试 | `tests/integration/brain/governance/` |

---

## 运行测试

```bash
# 所有治理测试
pytest tests/unit/core/brain/governance/ -v
pytest tests/integration/brain/governance/ -v

# 单个测试文件
pytest tests/unit/core/brain/governance/test_decision_record.py -v
pytest tests/unit/core/brain/governance/test_rule_engine.py -v
pytest tests/integration/brain/governance/test_decision_recording_e2e.py -v

# 特定测试
pytest tests/unit/core/brain/governance/test_decision_record.py::test_decision_record_hash -v
```

---

## 常见问题

### Q: 决策记录会影响性能吗？

A: 影响极小（~6ms/决策），对 Navigation/Compare/Health 影响 < 1%

### Q: 如何清理旧的决策记录？

A: P4-A 设计为 append-only，不建议删除。未来可以添加归档功能。

### Q: 如何自定义治理规则？

A: 当前规则硬编码，P4-B 将提供规则配置功能。

### Q: 签字后还能修改决策吗？

A: 不能。签字是 append-only 操作，修改会破坏完整性验证。

### Q: 如何查看哪些规则被触发最多？

```sql
SELECT
    json_extract(value, '$.rule_id') as rule_id,
    json_extract(value, '$.rule_name') as rule_name,
    COUNT(*) as trigger_count
FROM decision_records,
     json_each(rules_triggered)
GROUP BY rule_id
ORDER BY trigger_count DESC;
```

---

## 故障排查

### 问题：API 返回 404 "BrainOS database not found"

**原因**: BrainOS 数据库未初始化

**解决**:
```bash
agentos brain build
```

### 问题：完整性验证失败

**原因**: 记录可能被篡改或 hash 计算错误

**检查**:
```python
record = load_decision_record(store, decision_id)
print(f"Stored hash: {record.record_hash}")
print(f"Computed hash: {record.compute_hash()}")
```

### 问题：Hook 未生成决策记录

**可能原因**:
1. Navigation/Compare/Health 提前失败（实体不存在）
2. Hook 执行失败（检查日志）

**检查日志**:
```bash
grep "Failed to record.*decision" ~/.agentos/logs/*.log
```

---

## 下一步

- ✅ **P4-A**: 决策记录系统（已完成）
- ⏳ **P4-B**: 治理规则系统（规则配置、自定义规则）
- ⏳ **P4-C**: 复盘系统（时间线、历史快照）
- ⏳ **P4-D**: 责任系统（签字检查、审批流程）

---

**更新日期**: 2026-01-31
**版本**: P4-A v1.0
