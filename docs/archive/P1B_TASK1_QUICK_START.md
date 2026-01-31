# P1-B Task 1: Autocomplete 建议引擎 - 快速开始

## 5 分钟快速上手

### 1. 基本使用

```python
from agentos.core.brain.store import SQLiteStore
from agentos.core.brain.service import autocomplete_suggest

# 连接数据库
store = SQLiteStore("./brainos.db")
store.connect()

# 获取建议
result = autocomplete_suggest(store, prefix="task", limit=10)

# 显示结果
for suggestion in result.suggestions:
    print(f"✅ {suggestion.display_text}")
    print(f"   {suggestion.hint_text}")

store.close()
```

### 2. 核心概念

**Autocomplete = 认知边界护栏**

只建议满足以下**全部 4 个条件**的实体：
1. ✅ 已被索引
2. ✅ 有证据链（≥1 条 Evidence）
3. ✅ Coverage ≠ 0（至少一种：Git/Doc/Code）
4. ✅ 非高危盲区（severity < 0.7）

### 3. 安全等级

- `SAFE` ✅ - 符合全部标准
- `WARNING` ⚠️ - 中等风险盲区（0.4-0.7）
- `DANGEROUS` 🚨 - 高危盲区（≥0.7，默认过滤）
- `UNVERIFIED` ❌ - 无证据或未索引

### 4. 高级用法

```python
# 按类型过滤
result = autocomplete_suggest(
    store,
    prefix="core",
    entity_types=["file"],
    limit=5
)

# 包含警告
result = autocomplete_suggest(
    store,
    prefix="task",
    include_warnings=True,  # 包含中等风险盲区
    limit=10
)

# 查看过滤统计
print(f"Total: {result.total_matches}")
print(f"Filtered: {result.filtered_out}")
print(f"Reason: {result.filter_reason}")
```

### 5. 运行测试

```bash
# 单元测试
python3 -m pytest tests/unit/core/brain/test_autocomplete.py -v

# 真实数据测试
python3 test_autocomplete_real.py
```

### 6. 文件位置

- **实现**: `agentos/core/brain/service/autocomplete.py`
- **测试**: `tests/unit/core/brain/test_autocomplete.py`
- **完整文档**: `AUTOCOMPLETE_ENGINE_DEMO.md`
- **完成报告**: `P1B_TASK1_AUTOCOMPLETE_COMPLETION_REPORT.md`

---

## 记住

> "没有 Autocomplete 的子图，是'漂亮但不诚实的认知界面'。"

Autocomplete 不是搜索引擎，而是**认知宪法的执行机构**。

它确保用户始终在 BrainOS 的"理解范围"内活动。
