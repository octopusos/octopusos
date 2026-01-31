# P3-B Compare 快速参考

## 核心概念

**Compare = 理解结构的演化审计**

不是 git diff，而是回答：
- 新增了哪些理解？
- 哪些理解变弱了？
- 哪些理解消失了？

---

## 变化类型

| 类型 | 含义 | 示例 |
|------|------|------|
| 🟢 ADDED | 新增 | 新实体、新边 |
| 🔴 REMOVED | 删除 | 实体删除、边断开 |
| 🟡 WEAKENED | 弱化 | 证据减少、覆盖降低 |
| 🟦 STRENGTHENED | 增强 | 证据增加、覆盖提升 |

---

## API 快速参考

### 1. 创建快照
```bash
POST /api/brain/snapshots
{
  "description": "Before refactoring"
}
```

### 2. 列出快照
```bash
GET /api/brain/snapshots?limit=10
```

### 3. 对比快照
```bash
GET /api/brain/compare?from=snapshot_A&to=snapshot_B
```

---

## Python API

### 创建快照
```python
from agentos.core.brain.compare import capture_snapshot
snapshot_id = capture_snapshot(store, "My snapshot")
```

### 对比快照
```python
from agentos.core.brain.compare import compare_snapshots
result = compare_snapshots(store, snap1_id, snap2_id)

print(f"Added: {result.entities_added}")
print(f"Removed: {result.entities_removed}")
print(f"Weakened: {result.entities_weakened}")
```

---

## Red Line 2 检查清单

P3-B 必须满足：

- ✅ 显示所有 REMOVED 变化
- ✅ 显示所有 WEAKENED 变化
- ✅ 标注覆盖度退化（`is_degradation`）
- ✅ 总体评估反映退化（`overall_assessment`）

**禁止**：隐藏理解退化、只展示"最好看的版本"

---

## 测试状态

- 单元测试：28/28 通过 ✅
- Red Line 2 测试：7/7 通过 ✅
- 性能测试：对比查询 < 1s ✅

---

## 文件位置

| 功能 | 文件路径 |
|------|---------|
| 快照管理 | `agentos/core/brain/compare/snapshot.py` |
| 差异引擎 | `agentos/core/brain/compare/diff_engine.py` |
| API 处理器 | `agentos/core/brain/api/handlers.py` |
| 测试 | `tests/unit/core/brain/compare/` |

---

## 下一步

Phase 4（待实施）：WebUI 集成
- 创建 Compare View
- 实现对比可视化
- 添加时间线视图
