# BrainOS Autocomplete Engine - Cognitive Guardrail Demo

## 核心理念

Autocomplete 不是搜索引擎优化工具，而是**认知宪法的执行机构**。

> **Autocomplete = 认知边界护栏（Cognitive Guardrail）**

### 战略定位

用户的核心判断：
> "没有 Autocomplete 的子图，是'漂亮但不诚实的认知界面'。"

**核心使命**：
- ❌ 不是为了"提高命中率"
- ❌ 不是为了"更快输入"
- ❌ 不是为了"模糊匹配"
- ✅ **只做一件事**：只允许用户沿着"已被 BrainOS 理解并有证据链的结构"移动

## 硬性验收标准（认知宪法）

Autocomplete **只能**提示满足**全部 4 个条件**的实体：

1. ✅ **已被索引**：存在于 entities 表
2. ✅ **有证据链**：≥1 条 Evidence
3. ✅ **Coverage ≠ 0**：至少一种证据类型（Git/Doc/Code）
4. ✅ **非高危盲区**：Blind Spot severity < 0.7（或明确标注 ⚠️）

**否则**：
- ❌ 不提示
- ❌ 不补全
- ❌ 不"猜你想问什么"

## API 使用

### 基本用法

```python
from agentos.core.brain.store import SQLiteStore
from agentos.core.brain.service import autocomplete_suggest

# 连接到 BrainOS 数据库
store = SQLiteStore("./brainos.db")
store.connect()

# 获取 autocomplete 建议
result = autocomplete_suggest(store, prefix="task", limit=10)

# 查看结果
print(f"Total matches: {result.total_matches}")
print(f"Filtered out: {result.filtered_out}")
print(f"Safe suggestions: {len(result.suggestions)}")

for suggestion in result.suggestions:
    print(f"\n{suggestion.display_text}")
    print(f"  Safety: {suggestion.safety_level.value}")
    print(f"  Evidence: {suggestion.evidence_count}")
    print(f"  Coverage: {', '.join(suggestion.coverage_sources)}")
    print(f"  Hint: {suggestion.hint_text}")

store.close()
```

### 高级用法

#### 1. 按实体类型过滤

```python
# 只建议文件
result = autocomplete_suggest(
    store,
    prefix="core",
    entity_types=["file"],
    limit=5
)

# 只建议 capability 和 term
result = autocomplete_suggest(
    store,
    prefix="governance",
    entity_types=["capability", "term"],
    limit=10
)
```

#### 2. 包含中等风险盲区

```python
# 默认：排除所有高危盲区
result = autocomplete_suggest(store, "task", include_warnings=False)

# 包含中等风险盲区（带警告标记）
result = autocomplete_suggest(store, "task", include_warnings=True)

# 查看警告
for suggestion in result.suggestions:
    if suggestion.safety_level.value == "warning":
        print(f"⚠️ {suggestion.display_text}")
        print(f"   {suggestion.hint_text}")
        print(f"   Reason: {suggestion.blind_spot_reason}")
```

#### 3. 检查过滤统计

```python
result = autocomplete_suggest(store, "test", limit=5)

print(f"Filter Report:")
print(f"  Total matches: {result.total_matches}")
print(f"  Passed filters: {len(result.suggestions)}")
print(f"  Filtered out: {result.filtered_out}")
print(f"  Reason: {result.filter_reason}")
```

## 数据结构

### AutocompleteSuggestion

```python
@dataclass
class AutocompleteSuggestion:
    """Autocomplete 建议（带认知安全信息）"""

    # 实体标识
    entity_type: str           # 'file', 'capability', 'term', 'doc'
    entity_key: str            # 唯一键
    entity_name: str           # 显示名称

    # 认知安全信息
    safety_level: EntitySafety # SAFE, WARNING, DANGEROUS, UNVERIFIED
    evidence_count: int        # 证据数量
    coverage_sources: List[str] # ['git', 'doc', 'code']

    # 盲区信息
    is_blind_spot: bool
    blind_spot_severity: Optional[float]  # 0.0-1.0
    blind_spot_reason: Optional[str]

    # 显示信息
    display_text: str          # 用户看到的文本
    hint_text: str             # 提示文本
```

### EntitySafety 枚举

```python
class EntitySafety(Enum):
    SAFE = "safe"              # ✅ 符合全部 4 条标准
    WARNING = "warning"        # ⚠️ 中等风险盲区（0.4-0.7）
    DANGEROUS = "dangerous"    # 🚨 高风险盲区（≥0.7）
    UNVERIFIED = "unverified"  # ❌ 无证据或未索引
```

## 认知过滤逻辑

### 过滤流程

```
1. 前缀匹配
   ├─> SELECT entities WHERE key LIKE 'prefix%' OR name LIKE 'prefix%'
   └─> 原始匹配数：N

2. 证据检查（硬性条件 2）
   ├─> SELECT COUNT(*) FROM evidence WHERE entity_id = ?
   └─> 过滤：evidence_count < 1 → UNVERIFIED

3. Coverage 检查（硬性条件 3）
   ├─> SELECT DISTINCT source_category FROM edges+evidence
   └─> 过滤：coverage_sources 为空 → UNVERIFIED

4. Blind Spot 检查（硬性条件 4）
   ├─> detect_blind_spots()
   ├─> severity >= 0.7 → DANGEROUS（默认过滤）
   ├─> 0.4 <= severity < 0.7 → WARNING（包含但标注）
   └─> severity < 0.4 → SAFE

5. 排序
   ├─> 优先级 1: safety_level (SAFE > WARNING > DANGEROUS)
   ├─> 优先级 2: evidence_count (降序)
   ├─> 优先级 3: coverage_sources 长度 (降序)
   └─> 优先级 4: entity_name (字母顺序)

6. 应用 Limit
   └─> 返回前 N 个建议
```

### 过滤示例

假设有以下实体：

1. `task_manager.py`
   - Evidence: 10 条
   - Coverage: [git, doc, code]
   - Blind Spot: 无
   - **结果**: ✅ SAFE - 包含在建议中

2. `old_legacy.py`
   - Evidence: 0 条
   - Coverage: []
   - Blind Spot: 无
   - **结果**: ❌ UNVERIFIED - 被过滤

3. `critical_module.py`
   - Evidence: 3 条
   - Coverage: [git]
   - Blind Spot: High fan-in (severity=0.8)
   - **结果**: 🚨 DANGEROUS - 默认被过滤（除非 include_warnings=True）

4. `util_helper.py`
   - Evidence: 5 条
   - Coverage: [git, code]
   - Blind Spot: Moderate (severity=0.5)
   - **结果**: ⚠️ WARNING - 包含但带警告标记

## 单元测试

运行测试：

```bash
python3 -m pytest tests/unit/core/brain/test_autocomplete.py -v
```

测试覆盖：
- ✅ 只返回有证据的实体
- ✅ 过滤无证据实体
- ✅ 过滤零覆盖实体
- ✅ 多覆盖源实体优先
- ✅ 按证据数量排序
- ✅ Limit 参数
- ✅ 实体类型过滤
- ✅ 前缀匹配
- ✅ 空前缀（返回所有安全实体）
- ✅ 无匹配
- ✅ 提示文本格式化
- ✅ 错误处理

## 性能考虑

### 优化建议

1. **Blind Spot 缓存**
   ```python
   # 缓存 Blind Spot 检测结果（避免每次查询）
   blind_spots_cache = detect_blind_spots(store, max_results=100)
   # 使用缓存（有效期：5 分钟）
   ```

2. **索引优化**
   ```sql
   -- 已有索引
   CREATE INDEX idx_entities_key ON entities(key);
   CREATE INDEX idx_entities_type ON entities(type);
   CREATE INDEX idx_evidence_edge ON evidence(edge_id);
   ```

3. **Limit 优先**
   ```python
   # 尽早应用 limit，减少处理量
   result = autocomplete_suggest(store, prefix, limit=5)
   ```

### 性能基准

- 单次查询：< 50ms（小型库：< 1000 entities）
- Blind Spot 检测：< 200ms（缓存后：< 10ms）
- 内存占用：< 10MB

## 集成示例

### Web UI 集成

```javascript
// 前端 - 输入框 autocomplete
async function fetchSuggestions(prefix) {
    const response = await fetch('/api/autocomplete', {
        method: 'POST',
        body: JSON.stringify({ prefix, limit: 10 })
    });
    const result = await response.json();

    return result.suggestions.map(s => ({
        text: s.display_text,
        hint: s.hint_text,
        safety: s.safety_level,
        icon: getSafetyIcon(s.safety_level)
    }));
}

function getSafetyIcon(safety) {
    if (safety === 'safe') return '✅';
    if (safety === 'warning') return '⚠️';
    if (safety === 'dangerous') return '🚨';
    return '❓';
}
```

```python
# 后端 - Flask/FastAPI 路由
@app.post('/api/autocomplete')
def api_autocomplete(request: AutocompleteRequest):
    store = get_brain_store()
    result = autocomplete_suggest(
        store,
        prefix=request.prefix,
        limit=request.limit,
        entity_types=request.entity_types
    )
    return result.to_dict()
```

## 相关文件

- 实现：`agentos/core/brain/service/autocomplete.py`
- 测试：`tests/unit/core/brain/test_autocomplete.py`
- 依赖：
  - `agentos/core/brain/service/blind_spot.py` - Blind Spot 检测
  - `agentos/core/brain/store/sqlite_store.py` - 数据库访问

## 设计原则回顾

1. **认知诚实**：只建议 BrainOS 真正理解的实体
2. **安全优先**：宁可少返回，不可返回不安全的
3. **明确标注**：风险必须清晰可见（⚠️、🚨）
4. **可解释性**：每个建议都有证据支撑
5. **性能友好**：< 50ms 响应时间

## 未来扩展

### P1-B Phase 2+

1. **语义相似度**：基于 embedding 的相似实体推荐
2. **上下文感知**：根据当前 conversation 调整建议
3. **学习优化**：根据用户选择优化排序
4. **多模态支持**：支持代码片段、图片等

---

**记住**：Autocomplete 是认知边界护栏，不是搜索引擎。
它的存在是为了确保用户始终在 BrainOS 的"理解范围"内活动。
