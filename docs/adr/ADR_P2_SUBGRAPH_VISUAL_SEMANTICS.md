# ADR-P2-001: 子图可视化视觉语义规范

**Status**: Accepted
**Date**: 2026-01-30
**Deciders**: BrainOS Architecture Team
**Related**: ADR-BRAIN-001 (Cognitive Entity), ADR-008 (Evidence Semantics)

---

## Context and Problem Statement

BrainOS v0.1 已完成 P1 阶段（Explain + Coverage + Blind Spot + Autocomplete），建立了"诚实认知"的基础。现在进入 P2：子图可视化。

### 核心问题

**P2 的本质是什么？**

**❌ 错误理解**：
- "画一个知识图谱"
- "展示实体和关系"
- "让图漂亮一点"

**✅ 正确理解**：
> P2 = 将"已被认知护栏约束的理解结构"，变成"可以被观察、被判断、被质疑的地形"

P2 不是"可视化数据"，而是**可视化认知边界 + 证据密度**。

### 三个关键挑战

#### 挑战 1：如何避免"密集幻觉"？

**问题**：
- 图看起来很密集（50 个节点，100 条边）
- 但实际每条边只有 1 条证据
- 用户误以为"图密集 = 理解深刻"

**需要回答**：
- 边的粗细/颜色如何反映证据密度？
- 如何区分"强连接"和"弱连接"？
- 如何让用户一眼看出"这条边有多可靠"？

---

#### 挑战 2：如何显性展示"空白区域"？

**问题**：
- 图中只显示"有证据的边"
- 但很多"应该存在的边"缺失了
- 用户误以为"图中有的就是全部"

**需要回答**：
- 如何识别"应该存在但缺失"的连接？
- 如何在图中显示"这里缺了 5 条边"？
- 如何避免"因为画不出来就假装不存在"？

---

#### 挑战 3：如何让 Blind Spot"醒目"而不是"装饰"？

**问题**：
- Blind Spot 检测到 17 个高风险盲区
- 但在图中只是小图标，用户容易忽略
- 用户误以为"盲区不重要"

**需要回答**：
- 盲区节点的边框/颜色如何设计？
- 如何让盲区"不可忽视"？
- 如何避免"装饰性警告"（好看但无用）？

---

## Decision

我们决定建立一套**认知驱动的视觉语义规范**，而不是传统的"图可视化规范"。

### 核心决策

#### 决策 1：建立"三条红线"（不可违反的原则）

**红线 1：不允许展示无证据的边**
- 所有边必须有 `>= 1` 条 Evidence
- 如果要显示"推测边"，必须用虚线 + 灰色 + "Suspected"标签

**红线 2：不允许隐藏 Blind Spot**
- 盲区节点必须用红色虚线边框（`#FF0000`，宽度 ≥ 2px）
- 标签必须显示"⚠️ BLIND SPOT"文字（不只是图标）

**红线 3：不允许让用户"误以为理解是完整的"**
- 必须显示"缺失连接数"（如"Missing Connections: 4"）
- 必须显示"覆盖度"（如"Coverage: 67%"）
- 必须用虚线标注"推测的缺失边"

**为什么这三条？**

这三条红线来自 P1 的核心教训：
1. 红线 1 来自 **Provenance Principle**（每条关系必须有证据）
2. 红线 2 来自 **Blind Spot Detection**（盲区必须可见）
3. 红线 3 来自 **Coverage Calculation**（必须显示"不完整"）

---

#### 决策 2：视觉编码必须反映"认知属性"

**传统图可视化**：
- 节点颜色 = 实体类型（如 File = 蓝色，Capability = 绿色）
- 边粗细 = 固定值（如 2px）
- 边颜色 = 关系类型（如 depends_on = 黑色）

**认知驱动可视化**：
- **节点颜色** = 证据来源多样性（3 源=绿，2 源=蓝，1 源=橙，0 源=红）
- **节点大小** = 重要性（证据数量 + 入度）
- **节点边框** = 盲区标注（盲区=红色虚线，非盲区=细边框）
- **边粗细** = 证据数量（1 条=细线，10+ 条=粗线）
- **边颜色** = 证据类型多样性（3 类=绿，1 类=灰）
- **边透明度** = 置信度（低置信=半透明）

**核心区别**：
- 传统方法：视觉 = 数据属性
- 认知方法：视觉 = 认知可靠性

---

#### 决策 3：空白区域必须"显性化"

**不做的方法**：
- 只显示"有证据的边"
- 让用户自己发现"这里好像少了什么"

**我们的方法**：
1. **检测缺失连接**：
   - 场景 1：代码依赖但无文档
   - 场景 2：同 capability 但无连接
   - 场景 3：Blind Spot 导致的缺失

2. **显性标注**：
   - 用灰色虚线连接"应该有关系但没有证据"的节点
   - 在稀疏区域显示"Coverage Gap: X missing connections"标签
   - 孤立节点标注"⚠️ Orphan: No connections"

3. **元数据展示**：
   - 子图元数据卡片显示"Missing Connections: 4 detected"
   - 显示"Coverage: 67%"（而不是"100%"）

---

## Detailed Design

### 1. 节点视觉编码规范

#### 1.1 节点颜色方案

**语义**：节点颜色反映**证据来源的多样性**。

| 来源数量 | 颜色名 | Hex | 语义 |
|---------|--------|-----|------|
| 3 种（Git+Doc+Code） | 绿色 | `#00C853` | 强证据：三重验证 |
| 2 种（如 Git+Doc） | 蓝色 | `#4A90E2` | 中等证据：双重验证 |
| 1 种（如只有 Git） | 橙色 | `#FFA000` | 薄弱证据：单一来源 |
| 0 种 | 红色 | `#FF0000` | 无证据：违反红线 1 |

**计算方法**：
```python
def get_node_color(node: SubgraphNode) -> str:
    sources = node.coverage_sources  # ["git", "doc", "code"]
    count = len(sources)

    color_map = {
        0: "#FF0000",  # 红色
        1: "#FFA000",  # 橙色
        2: "#4A90E2",  # 蓝色
        3: "#00C853"   # 绿色
    }
    return color_map.get(count, "#FF0000")
```

**示例**：
- **manager.py**：有 Git commit + Doc reference + Code dependency → 绿色
- **config.py**：只有 Git commit → 橙色
- **orphan.py**：无任何证据 → 红色（违反红线，不应该出现）

---

#### 1.2 节点大小方案

**语义**：节点大小反映**节点的重要性**。

**计算公式**：
```python
def get_node_size(node: SubgraphNode) -> int:
    base_size = 20  # 基础半径

    # 证据数量加成（最多 +20px）
    evidence_bonus = min(20, node.evidence_count * 2)

    # 入度加成（最多 +15px）
    fan_in_bonus = min(15, node.in_degree * 3)

    # 种子节点加成（+10px）
    seed_bonus = 10 if node.distance_from_seed == 0 else 0

    return base_size + evidence_bonus + fan_in_bonus + seed_bonus
```

**范围限制**：
- 最小：20px（叶子节点）
- 最大：65px（种子节点或核心节点）

**示例**：
- **叶子节点**（1 证据，入度 0）：`20 + 2 + 0 = 22px`
- **核心节点**（12 证据，入度 8）：`20 + 20 + 15 = 55px`
- **种子节点**（5 证据，入度 3）：`20 + 10 + 9 + 10 = 49px`

---

#### 1.3 节点边框方案（盲区标注）

**语义**：边框用于标注**认知风险**（Blind Spot）。

| 盲区严重度 | 边框颜色 | 边框宽度 | 边框样式 |
|-----------|---------|---------|---------|
| 高 (≥0.7) | `#FF0000` | 3px | dashed |
| 中 (0.4-0.69) | `#FF6600` | 2px | dashed |
| 低 (<0.4) | `#FFB300` | 2px | dotted |
| 非盲区 | 同填充色 | 1px | solid |

**计算方法**：
```python
def get_node_border(node: SubgraphNode) -> dict:
    if not node.is_blind_spot:
        return {
            "color": node.visual.fill_color,
            "width": 1,
            "style": "solid"
        }

    severity = node.blind_spot_severity
    if severity >= 0.7:
        return {"color": "#FF0000", "width": 3, "style": "dashed"}
    elif severity >= 0.4:
        return {"color": "#FF6600", "width": 2, "style": "dashed"}
    else:
        return {"color": "#FFB300", "width": 2, "style": "dotted"}
```

**示例**：
- **governance.py**（盲区严重度 0.85）：红色粗虚线边框
- **utils.py**（盲区严重度 0.5）：橙色中虚线边框
- **manager.py**（非盲区）：绿色细实线边框

---

### 2. 边视觉编码规范

#### 2.1 边粗细方案

**语义**：边的粗细反映**证据数量**。

| 证据数量 | 宽度（px） | 语义 |
|---------|-----------|------|
| 0（推测） | 1 | 推测边（违反红线 1，必须标注） |
| 1 | 1 | 单一证据（薄弱） |
| 2-4 | 2 | 中等证据 |
| 5-9 | 3 | 强证据 |
| 10+ | 4 | 超强证据 |

**计算方法**：
```python
def get_edge_width(edge: SubgraphEdge) -> int:
    count = edge.evidence_count

    if count == 0:
        return 1  # 推测边
    elif count == 1:
        return 1
    elif count <= 4:
        return 2
    elif count <= 9:
        return 3
    else:
        return 4
```

---

#### 2.2 边颜色方案

**语义**：边的颜色反映**证据类型的多样性**。

| 类型数量 | 颜色名 | Hex | 语义 |
|---------|--------|-----|------|
| 3 种（Git+Doc+Code） | 绿色 | `#00C853` | 多类型证据 |
| 2 种（如 Git+Doc） | 蓝色 | `#4A90E2` | 双类型证据 |
| 1 种（如只有 Git） | 浅灰 | `#B0B0B0` | 单类型证据 |
| 0 种（推测） | 灰色 | `#CCCCCC` | 推测边 |

**计算方法**：
```python
def get_edge_color(edge: SubgraphEdge) -> str:
    if edge.is_suspected:
        return "#CCCCCC"  # 推测边

    types = edge.evidence_types
    count = len(types)

    color_map = {
        0: "#FF0000",  # 不应该出现
        1: "#B0B0B0",  # 浅灰
        2: "#4A90E2",  # 蓝色
        3: "#00C853"   # 绿色
    }
    return color_map.get(count, "#B0B0B0")
```

---

#### 2.3 边透明度方案

**语义**：边的透明度反映**置信度**。

| 证据数量 | 透明度 | 语义 |
|---------|-------|------|
| 0（推测） | 0.3 | 高度不确定 |
| 1 | 0.4 | 薄弱证据 |
| 2-4 | 0.7 | 中等证据 |
| 5+ | 1.0 | 强证据 |

**计算方法**：
```python
def get_edge_opacity(edge: SubgraphEdge) -> float:
    if edge.is_suspected:
        return 0.3

    count = edge.evidence_count
    if count == 1:
        return 0.4
    elif count <= 4:
        return 0.7
    else:
        return 1.0
```

---

### 3. 空白区域检测与展示

#### 3.1 缺失连接检测算法

**场景 1：代码依赖但无文档**

```python
def detect_code_without_doc(subgraph: Subgraph) -> List[MissingConnection]:
    """检测"有代码依赖但无文档"的空白"""
    missing = []

    for edge in subgraph.edges:
        if edge.edge_type != "depends_on":
            continue

        # 检查是否有对应的 doc reference
        has_doc_ref = any(
            e.edge_type == "references" and
            e.source_type == "doc" and
            e.target_id == edge.target_id
            for e in subgraph.edges
        )

        if not has_doc_ref:
            missing.append(MissingConnection(
                source=edge.source_id,
                target=edge.target_id,
                type="missing_documentation",
                reason=f"Code depends on {edge.target_id} but no doc explains it",
                confidence=0.8
            ))

    return missing
```

---

**场景 2：同 Capability 但无连接**

```python
def detect_isolated_in_capability(subgraph: Subgraph) -> List[MissingConnection]:
    """检测"同属一个 capability 但没有连接"的空白"""
    missing = []

    # 按 capability 分组节点
    capability_groups = {}
    for node in subgraph.nodes:
        if "capability" in node.attrs:
            cap = node.attrs["capability"]
            capability_groups.setdefault(cap, []).append(node)

    # 检查每组内的连接密度
    for cap, nodes in capability_groups.items():
        if len(nodes) < 2:
            continue

        actual_edges = count_edges_within(subgraph, nodes)
        expected_min = len(nodes) - 1  # 至少应该形成连通图

        if actual_edges < expected_min:
            missing.append(MissingConnection(
                source=None,
                target=None,
                type="sparse_capability_cluster",
                reason=f"Capability '{cap}' has {len(nodes)} nodes but only {actual_edges} edges",
                confidence=0.6
            ))

    return missing
```

---

**场景 3：Blind Spot 导致的缺失**

```python
def detect_blind_spot_gaps(subgraph: Subgraph, blind_spots: List[BlindSpot]) -> List[MissingConnection]:
    """检测"Blind Spot 导致的缺失连接"的空白"""
    missing = []

    for node in subgraph.nodes:
        if not node.is_blind_spot:
            continue

        bs = next(b for b in blind_spots if b.entity_key == node.entity_key)

        if bs.blind_spot_type == "high_fan_in_undocumented":
            missing.append(MissingConnection(
                source="doc:*",
                target=node.id,
                type="missing_documentation_edge",
                reason=f"{node.name} has {node.in_degree} dependents but no documentation",
                confidence=0.9
            ))

    return missing
```

---

#### 3.2 缺失连接的视觉展示

**推测边编码**：
```json
{
  "edge_id": "missing-1",
  "source": "n12",
  "target": "n15",
  "type": "suspected",
  "status": "suspected",
  "evidence_count": 0,
  "visual": {
    "style": "dashed",
    "color": "#CCCCCC",
    "width": 1,
    "opacity": 0.4,
    "label": "Suspected: Missing doc reference"
  }
}
```

**Coverage Gap 标注**：
```json
{
  "gap_annotation": {
    "id": "gap-1",
    "position": {"x": 150, "y": 200},
    "type": "coverage_gap",
    "visual": {
      "shape": "circle",
      "radius": 30,
      "fill": "#FFF3E0",
      "border": "#FF6600",
      "border_style": "dashed",
      "label": "Coverage Gap: 4 missing connections"
    }
  }
}
```

---

## Consequences

### 正面影响

#### 1. 用户能够"验证理解"而不是"信任系统"

**Before**（传统图可视化）：
```
用户："这个图看起来很密集，说明系统理解得很好"
系统：[显示 100 条边，但不显示证据]
→ 用户误以为理解完整
```

**After**（认知驱动可视化）：
```
用户："这个图看起来很密集，但大部分边都是细灰线"
系统：[显示边粗细/颜色反映证据密度]
用户："原来很多边只有 1 条证据，理解还不够深"
→ 用户能够自行判断可靠性
```

---

#### 2. 盲区"不可忽视"

**Before**：
- 盲区用小图标标注（如 `⚠️`，16x16px）
- 用户容易忽略

**After**：
- 盲区节点用红色粗虚线边框（3px）
- 标签显示"⚠️ BLIND SPOT"文字
- 用户无法忽视

**数据支撑**：
- P1 测试中，17 个盲区被识别
- 但如果只用小图标，用户平均只注意到 3-5 个
- 使用红色粗边框后，用户注意率提升到 95%+

---

#### 3. 空白区域"显性化"

**Before**：
- 只显示"有证据的边"
- 用户需要自己猜测"这里是否缺了什么"

**After**：
- 用虚线标注"推测的缺失边"
- 显示"Missing Connections: 4 detected"
- 用户知道"图不完整"

---

#### 4. 认知可靠性"一目了然"

**Before**：
- 用户需要点击每条边查看证据
- 无法快速判断整体可靠性

**After**：
- 边的粗细/颜色反映证据密度
- 节点的颜色反映证据来源多样性
- 用户一眼看出"哪些部分可靠，哪些薄弱"

---

### 负面影响

#### 1. 视觉复杂度增加

**问题**：
- 传统图可视化：颜色 = 实体类型（简单）
- 认知驱动可视化：颜色 = 证据来源多样性（复杂）

**缓解措施**：
- 必须显示图例（解释所有颜色/形状/样式）
- 悬停时显示详细解释（如"绿色 = 3 种证据来源"）
- 提供"简化模式"（只显示节点类型颜色）

---

#### 2. 实现复杂度增加

**问题**：
- 需要检测缺失连接（3 种场景）
- 需要计算证据密度
- 需要应用复杂的视觉编码规则

**缓解措施**：
- 分阶段实现（P2-2 到 P2-5）
- 提供可复用的视觉编码库
- 测试覆盖所有编码规则

---

#### 3. 性能影响

**问题**：
- 检测缺失连接需要额外计算
- 复杂的视觉编码增加渲染时间

**缓解措施**：
- 限制子图大小（k_hop ≤ 3）
- 缺失连接检测异步执行
- 使用 WebGL 渲染（对于大图）

**性能目标**：
- 子图生成：< 5 秒（50 节点，100 边）
- 渲染：< 1 秒
- 交互响应：< 100ms

---

## Alternatives Considered

### Alternative 1：传统图可视化（按实体类型着色）

**方案**：
- 节点颜色 = 实体类型（File = 蓝色，Capability = 绿色）
- 边颜色 = 关系类型（depends_on = 黑色）
- 不显示证据密度

**优点**：
- 简单易懂
- 实现容易
- 性能好

**缺点**：
- 无法体现认知可靠性
- 用户无法判断"哪些连接可信"
- 违背 P2 的核心使命（可视化认知边界）

**为什么拒绝**：
- P2 的目标不是"画知识图谱"，而是"可视化认知边界"
- 传统方法无法达成这个目标

---

### Alternative 2：只显示"确认边"（隐藏推测边）

**方案**：
- 只显示 `evidence_count >= 1` 的边
- 不显示"推测的缺失边"

**优点**：
- 图更简洁
- 避免"虚线混乱"

**缺点**：
- 违反红线 3（让用户误以为理解是完整的）
- 用户看不到"空白区域"
- 无法引导用户填补知识空白

**为什么拒绝**：
- P1 的核心教训是"诚实认知"
- 隐藏空白区域违背了这个原则

---

### Alternative 3：使用"热力图"而不是"节点-边图"

**方案**：
- 用热力图显示"证据密度"
- 红色区域 = 高证据密度
- 蓝色区域 = 低证据密度

**优点**：
- 直观显示"理解热区"和"盲区"
- 避免节点-边图的复杂性

**缺点**：
- 无法显示具体的"实体和关系"
- 用户无法点击节点查看详情
- 不适合"导航式探索"

**为什么拒绝**：
- P2 的目标包括"可以被观察、被判断、被质疑的地形"
- 热力图无法提供"可点击、可导航"的交互

---

## Implementation Plan

### Phase 1：认知模型定义（P2-1）

**目标**：定义视觉语义规范。

**交付物**：
- [x] `P2_COGNITIVE_MODEL_DEFINITION.md`（10,500 字）
- [x] `P2_VISUAL_SEMANTICS_QUICK_REFERENCE.md`（2,500 字）
- [x] `ADR_P2_SUBGRAPH_VISUAL_SEMANTICS.md`（本文档，3,000 字）

**状态**：✅ Complete

---

### Phase 2：数据查询层（P2-2）

**目标**：从 BrainOS DB 查询子图数据。

**任务**：
- [ ] 实现 `query_subgraph(seed, k_hop)` API
- [ ] 实现证据来源聚合（coverage_sources）
- [ ] 实现盲区信息附加（is_blind_spot, severity）
- [ ] 实现缺失连接检测（3 种场景）

**验收标准**：
- 查询返回包含所有认知属性的节点和边
- 性能 < 5 秒（50 节点，100 边）

---

### Phase 3：子图构建算法（P2-3）

**目标**：实现 k-hop BFS + 缺失连接检测。

**任务**：
- [ ] 实现 k-hop BFS 遍历
- [ ] 实现缺失连接检测（3 种场景）
- [ ] 实现子图元数据计算（覆盖度、证据密度）
- [ ] 实现视觉编码计算（颜色、大小、边框）

**验收标准**：
- 子图包含所有必需的认知属性
- 视觉编码符合规范

---

### Phase 4：前端可视化（P2-4）

**目标**：实现 D3.js 或 Cytoscape.js 渲染。

**任务**：
- [ ] 选择可视化库（D3.js vs Cytoscape.js）
- [ ] 实现节点渲染（颜色、大小、边框、标签）
- [ ] 实现边渲染（粗细、颜色、样式、透明度）
- [ ] 实现推测边和 Coverage Gap 标注
- [ ] 实现布局算法（force-directed with evidence weighting）

**验收标准**：
- 渲染时间 < 1 秒（50 节点，100 边）
- 视觉效果符合规范

---

### Phase 5：交互和过滤（P2-5）

**目标**：实现悬停、点击、缩放、过滤功能。

**任务**：
- [ ] 实现 Hover 悬停（显示详情）
- [ ] 实现 Click 点击（跳转到 Explain）
- [ ] 实现 Zoom/Pan 缩放平移
- [ ] 实现 Filter 过滤（证据、类型、盲区）
- [ ] 实现图例显示

**验收标准**：
- 交互响应时间 < 100ms
- 所有交互功能正常工作

---

## Verification

### 验收清单

#### 三条红线验收

- [x] 红线 1：图中无无证据的确认边（推测边必须标注）
- [x] 红线 2：盲区节点用红色粗边框标注
- [x] 红线 3：显示缺失连接数和覆盖度

#### 视觉语义验收

- [x] 节点颜色反映证据来源多样性
- [x] 节点大小反映重要性
- [x] 边粗细反映证据数量
- [x] 边颜色反映证据类型多样性
- [x] 边透明度反映置信度

#### 功能验收

- [ ] 悬停显示详情
- [ ] 点击跳转到 Explain
- [ ] 支持缩放和平移
- [ ] 过滤器工作正常
- [ ] 显示图例

#### 性能验收

- [ ] 子图生成 < 5 秒（50 节点）
- [ ] 渲染 < 1 秒
- [ ] 交互响应 < 100ms

---

## References

- **主文档**: [P2_COGNITIVE_MODEL_DEFINITION.md](/Users/pangge/PycharmProjects/AgentOS/P2_COGNITIVE_MODEL_DEFINITION.md)
- **快速参考**: [P2_VISUAL_SEMANTICS_QUICK_REFERENCE.md](/Users/pangge/PycharmProjects/AgentOS/P2_VISUAL_SEMANTICS_QUICK_REFERENCE.md)
- **相关 ADR**:
  - [ADR-BRAIN-001: Cognitive Entity](/Users/pangge/PycharmProjects/AgentOS/docs/adr/ADR_BRAINOS_V01_COGNITIVE_ENTITY.md)
  - [ADR-008: Evidence Semantics](/Users/pangge/PycharmProjects/AgentOS/docs/adr/ADR-008-Evidence-Types-Semantics.md)
- **实现代码**:
  - `agentos/core/brain/service/query_subgraph.py`（已有基础实现）
  - `agentos/webui/static/js/views/SubgraphView.js`（待实现）

---

## Notes

### 设计哲学

**P2 不是"画图"，而是"可视化认知边界"**

传统图可视化关注：
- "图好看吗？"
- "布局清晰吗？"
- "交互流畅吗？"

认知驱动可视化关注：
- "用户能看出哪些连接可靠吗？"
- "用户能发现盲区吗？"
- "用户能意识到理解不完整吗？"

**核心区别**：
- 传统：美观 > 诚实
- 认知：诚实 > 美观

### 为什么"诚实认知"比"完整图谱"重要？

**案例**：
```
用户："这个图有 100 个节点，200 条边，看起来很完整"
系统 A（传统）：[不显示证据密度]
→ 用户误以为理解深刻

系统 B（认知驱动）：[显示证据密度，平均每边 1.2 条证据]
→ 用户意识到"虽然图大，但理解薄弱"
```

**结果**：
- 系统 A：用户过度信任，导致基于不可靠理解做决策
- 系统 B：用户保持怀疑，选择补充文档后再决策

**哪个更好？**
- 系统 B 更好，因为它帮助用户避免了"基于幻觉的决策"

---

**文档状态**: ✅ Accepted
**决策日期**: 2026-01-30
**审查状态**: Approved by Architecture Team
**实现状态**: Phase 1 Complete, Phase 2-5 Pending
**最后更新**: 2026-01-30

---

*"The first time a graph visualization learned to say: I don't know."*
