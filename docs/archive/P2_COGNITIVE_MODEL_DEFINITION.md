# P2: 子图可视化认知模型定义

**Version**: v1.0.0
**Date**: 2026-01-30
**Status**: Foundation Document
**Authors**: BrainOS Architecture Team
**Related**: ADR-BRAIN-001, ADR-008

---

## Executive Summary

本文档定义 P2（子图可视化）的**认知模型**和**视觉语义规范**。P2 的核心使命是：

> **将"已被认知护栏约束的理解结构"，变成"可以被观察、被判断、被质疑的地形"**

这不是"画知识图谱"，而是**可视化认知边界 + 证据密度**。P2 必须让用户一眼看出：
- **哪些连接是强证据支撑的**（可信）
- **哪些连接是薄弱的**（存疑）
- **哪些连接应该存在但缺失**（盲区）

本文档字数：~10,500 字，包含：
1. 核心原则（三条红线）
2. 节点语义定义
3. 边语义定义
4. 空白区域语义定义
5. 视觉编码字典
6. 交互语义
7. 反模式清单（20+ 个）
8. 验收标准

---

## 1. 核心原则

### 1.1 三条红线（验收标准，不可违反）

#### 红线 1：❌ 不允许展示无证据的边

**定义**：
- 图中的每条边必须有 `>= 1` 条 Evidence 支撑
- 如果没有证据，边不能出现在图中（即使理论上"应该存在"）

**验收方法**：
```python
# 验收测试
for edge in subgraph.edges:
    evidence_count = len(edge.evidence_list)
    assert evidence_count >= 1, f"Edge {edge.id} has no evidence"
```

**例外情况**：
- **虚线推测边**：如果要显示"推测的边"（如 Blind Spot 检测到的缺失连接），必须：
  - 用明显的**虚线**样式
  - 标注为"Suspected Missing Connection"
  - 颜色必须是**灰色**（不能是正常的蓝色/绿色）
  - 不计入统计的"edge_count"

**示例**：
```json
{
  "edge_id": "e123",
  "source": "file:manager.py",
  "target": "file:models.py",
  "type": "depends_on",
  "evidence_count": 0,  // ❌ 违反红线 1
  "status": "confirmed"
}
```
❌ **拒绝**：这条边不能出现在图中。

```json
{
  "edge_id": "e124",
  "source": "file:manager.py",
  "target": "file:models.py",
  "type": "depends_on",
  "evidence_count": 0,
  "status": "suspected",  // ✅ 标记为推测
  "display": {
    "style": "dashed",
    "color": "#999999",
    "label": "Missing: No import evidence"
  }
}
```
✅ **接受**：这是显性标注的推测边。

---

#### 红线 2：❌ 不允许隐藏 Blind Spot

**定义**：
- 如果某个节点或边是盲区（Blind Spot），必须在视觉上明确标注
- 不能用"装饰性图标"（小而不显眼），必须是"认知警告"（醒目且不可忽视）

**验收方法**：
```python
# 验收测试
for node in subgraph.nodes:
    if node.is_blind_spot:
        assert node.visual_warning_level in ["high", "critical"]
        assert node.border_color in ["#FF0000", "#FF6600"]  # 红色或橙色
        assert node.blind_spot_label is not None
```

**视觉要求**：
- **盲区节点**：
  - 边框颜色：`#FF0000`（红色）或 `#FF6600`（橙色）
  - 边框样式：`dashed`（虚线）或 `bold`（加粗）
  - 标注：节点旁边显示 `⚠️ Blind Spot: {type}`
  - 大小：不小于正常节点（不能通过缩小来"隐藏"）

- **盲区边**：
  - 颜色：`#FF9999`（浅红色）
  - 样式：`dotted`（点线）
  - 标注：边上显示 `⚠️ Low Evidence`

**示例**：
```json
{
  "node_id": "n45",
  "type": "file",
  "name": "governance.py",
  "is_blind_spot": true,
  "blind_spot_severity": 0.85,
  "blind_spot_type": "high_fan_in_undocumented",
  "visual": {
    "border_color": "#FF0000",
    "border_style": "dashed",
    "border_width": 3,
    "warning_label": "⚠️ Blind Spot: 15 dependents, 0 docs"
  }
}
```

---

#### 红线 3：❌ 不允许让用户"误以为理解是完整的"

**定义**：
- 必须显性展示"空白区域"（应该有但缺失的连接）
- 必须显示"覆盖度不足"（只有部分证据类型的节点）
- 子图的整体"完整度"必须可见（如"覆盖度：67%"）

**验收方法**：
```python
# 验收测试
subgraph_metadata = subgraph.get_metadata()
assert "coverage_percent" in subgraph_metadata
assert "missing_connections_count" in subgraph_metadata
assert "evidence_density" in subgraph_metadata

# 显示要求
assert subgraph_ui.has_coverage_badge()
assert subgraph_ui.has_missing_connections_indicator()
```

**显示要求**：
- **子图元数据卡片**（必须显示）：
  ```
  Subgraph Coverage: 67%
  - Nodes: 12 (3 with Blind Spots)
  - Edges: 18 (5 weak, 2 suspected)
  - Missing Connections: 4 detected
  - Evidence Density: 3.2 avg per edge
  ```

- **空白区域提示**：
  - 如果检测到"A 和 B 应该有连接但没有"，用虚线标注
  - 如果某个节点的"出度"或"入度"异常低，标注"Potential Isolation"

**示例**：
```json
{
  "subgraph_metadata": {
    "seed": "file:manager.py",
    "k_hop": 2,
    "node_count": 12,
    "edge_count": 18,
    "coverage_percent": 0.67,
    "blind_spot_nodes": 3,
    "weak_edges": 5,
    "suspected_edges": 2,
    "missing_connections": [
      {
        "expected_source": "file:manager.py",
        "expected_target": "file:config.py",
        "reason": "manager.py uses Config class but no DEPENDS_ON edge",
        "confidence": 0.75
      }
    ]
  }
}
```

---

### 1.2 必须具备的视觉特征

#### 特征 1：证据厚度感

**定义**：边的**视觉权重**必须反映证据数量和质量。

**编码规则**：
- **边粗细**：
  - `1 条证据`：细线（`width: 1px`）
  - `2-4 条证据`：中等（`width: 2px`）
  - `5-9 条证据`：粗线（`width: 3px`）
  - `10+ 条证据`：最粗（`width: 4px`）

- **边透明度**：
  - `1 条证据`：`opacity: 0.4`（半透明）
  - `2-4 条证据`：`opacity: 0.7`
  - `5+ 条证据`：`opacity: 1.0`（不透明）

- **边颜色**（基于证据类型多样性）：
  - 单一类型（如只有 Git）：`#AAAAAA`（灰色）
  - 两种类型（Git + Doc）：`#4A90E2`（蓝色）
  - 三种类型（Git + Doc + Code）：`#00C853`（绿色）

**示例**：
```json
{
  "edge_id": "e56",
  "evidence_count": 12,
  "evidence_types": ["git", "doc", "code"],
  "visual": {
    "width": 4,
    "opacity": 1.0,
    "color": "#00C853",
    "label": "12 evidence (Git+Doc+Code)"
  }
}
```

---

#### 特征 2：空白区域可见性

**定义**：缺失的连接必须是**明显的**，不是"隐式的"。

**实现方式**：
- **虚线推测边**：用浅灰色虚线连接"应该有关系但没有证据"的节点
- **空洞标注**：在"应该密集但稀疏"的区域显示"Coverage Gap"标签
- **孤立节点警告**：如果节点的度数异常低（如出度 = 0 且不是叶子节点），标注"Potential Orphan"

**示例**：
```json
{
  "missing_connection": {
    "source": "n12",
    "target": "n15",
    "reason": "Both in 'task' capability but no edge",
    "visual": {
      "style": "dashed",
      "color": "#CCCCCC",
      "width": 1,
      "label": "Suspected: Same capability"
    }
  }
}
```

---

#### 特征 3：风险标注

**定义**：Blind Spot 必须在图中**可见且醒目**。

**实现方式**：
- **节点边框**：盲区节点用红色虚线边框
- **节点背景**：可选用浅红色背景（`#FFEBEE`）
- **图标叠加**：在节点上叠加 `⚠️` 图标
- **悬停提示**：鼠标悬停时显示盲区详情（类型、严重度、建议行动）

**示例**：
```json
{
  "node_id": "n45",
  "is_blind_spot": true,
  "blind_spot_severity": 0.85,
  "blind_spot_type": "high_fan_in_undocumented",
  "visual": {
    "border_color": "#FF0000",
    "border_style": "dashed",
    "background_color": "#FFEBEE",
    "icon_overlay": "⚠️",
    "hover_tooltip": {
      "title": "Blind Spot: High Fan-In Undocumented",
      "severity": "High (0.85)",
      "description": "15 files depend on this, but no documentation exists",
      "suggested_action": "Add ADR explaining this file's architecture"
    }
  }
}
```

---

## 2. 节点语义定义

### 2.1 节点的认知属性

每个节点必须包含以下属性：

```python
@dataclass
class SubgraphNode:
    """子图节点的认知属性"""
    # 基础属性（来自 Entity）
    id: str                      # 节点 ID（如 "n12"）
    entity_id: str               # 实体 ID（如 "entity:file:manager.py"）
    entity_type: str             # 实体类型（file/capability/term/doc）
    entity_key: str              # 实体唯一键（如 "file:manager.py"）
    entity_name: str             # 显示名称（如 "manager.py"）

    # 证据属性
    evidence_count: int          # 该节点的证据总数
    coverage_sources: List[str]  # 证据来源（["git", "doc", "code"]）
    evidence_density: float      # 证据密度（evidence_count / max_possible）

    # 盲区属性
    is_blind_spot: bool          # 是否为盲区
    blind_spot_severity: float   # 盲区严重度（0.0-1.0）
    blind_spot_type: Optional[str]  # 盲区类型（见 BlindSpotType）
    blind_spot_reason: Optional[str]  # 盲区原因

    # 拓扑属性
    in_degree: int               # 入度（有多少边指向它）
    out_degree: int              # 出度（有多少边从它出发）
    distance_from_seed: int      # 距离种子节点的跳数

    # 视觉编码属性（运行时计算）
    visual: NodeVisual
```

---

### 2.2 节点视觉编码规则

#### 2.2.1 节点颜色（基于 coverage_sources）

**语义**：节点颜色反映**证据来源的多样性**。

**编码方案**：
```python
def get_node_color(node: SubgraphNode) -> str:
    """计算节点颜色"""
    sources = node.coverage_sources
    count = len(sources)

    if count == 0:
        return "#FF0000"  # 红色：无证据（违反红线 1）
    elif count == 1:
        return "#FFA000"  # 橙色：单一来源（薄弱）
    elif count == 2:
        return "#4A90E2"  # 蓝色：两种来源（中等）
    elif count >= 3:
        return "#00C853"  # 绿色：三种来源（强证据）
```

**示例**：
- **文件 A**：只有 Git commit 修改记录 → 橙色
- **文件 B**：有 Git commit + Doc reference → 蓝色
- **文件 C**：有 Git + Doc + Code dependency → 绿色

**特殊情况**：
- **Blind Spot 节点**：无论 coverage_sources 如何，边框颜色强制为红色（`#FF0000`），背景颜色可以保持编码规则。

---

#### 2.2.2 节点大小（基于 evidence_count 和 in_degree）

**语义**：节点大小反映**节点的重要性**。

**编码方案**：
```python
def get_node_size(node: SubgraphNode) -> int:
    """计算节点大小（半径，单位：px）"""
    # 基础大小
    base_size = 20

    # 根据证据数量调整（最多 +20px）
    evidence_bonus = min(20, node.evidence_count * 2)

    # 根据入度调整（最多 +15px）
    fan_in_bonus = min(15, node.in_degree * 3)

    # 如果是种子节点，额外 +10px
    seed_bonus = 10 if node.distance_from_seed == 0 else 0

    return base_size + evidence_bonus + fan_in_bonus + seed_bonus
```

**范围限制**：
- 最小：`20px`（叶子节点）
- 最大：`65px`（种子节点或高扇入节点）

**示例**：
- **叶子节点**：1 条证据，入度 0 → `20 + 2 + 0 = 22px`
- **核心节点**：12 条证据，入度 8 → `20 + 20 + 15 = 55px`
- **种子节点**：5 条证据，入度 3 → `20 + 10 + 9 + 10 = 49px`

---

#### 2.2.3 节点边框（标注 Blind Spot）

**语义**：边框用于标注**认知风险**。

**编码方案**：
```python
def get_node_border(node: SubgraphNode) -> dict:
    """计算节点边框"""
    if not node.is_blind_spot:
        return {
            "color": node.visual.fill_color,  # 与填充色相同
            "width": 1,
            "style": "solid"
        }
    else:
        severity = node.blind_spot_severity
        if severity >= 0.7:
            return {
                "color": "#FF0000",  # 红色
                "width": 3,
                "style": "dashed"
            }
        elif severity >= 0.4:
            return {
                "color": "#FF6600",  # 橙色
                "width": 2,
                "style": "dashed"
            }
        else:
            return {
                "color": "#FFB300",  # 黄色
                "width": 2,
                "style": "dotted"
            }
```

**示例**：
- **安全节点**：细边框，颜色与填充色相同
- **高风险盲区**：粗红色虚线边框
- **低风险盲区**：细黄色点线边框

---

#### 2.2.4 节点标签（显示信息）

**语义**：标签用于显示**关键认知信息**。

**内容结构**：
```
[Entity Name]
[Coverage Badge] [Evidence Count]
```

**示例**：
```
manager.py
✅ 89% | 12 evidence
```

**编码方案**：
```python
def get_node_label(node: SubgraphNode) -> str:
    """生成节点标签"""
    name = node.entity_name
    coverage = node.evidence_density * 100
    evidence = node.evidence_count

    # Coverage badge
    if coverage >= 80:
        badge = "✅"
    elif coverage >= 50:
        badge = "⚠️"
    else:
        badge = "❌"

    # Blind spot indicator
    if node.is_blind_spot:
        badge = "⚠️ BLIND SPOT"

    return f"{name}\n{badge} {coverage:.0f}% | {evidence} evidence"
```

**字体大小**：
- 主标题（Entity Name）：`14px`
- 副标题（Coverage/Evidence）：`10px`

---

#### 2.2.5 节点形状（区分实体类型）

**语义**：形状用于快速识别**实体类型**。

**编码方案**：
```python
def get_node_shape(node: SubgraphNode) -> str:
    """根据实体类型返回形状"""
    shape_map = {
        "file": "circle",         # 文件：圆形
        "capability": "square",   # 能力：方形
        "term": "diamond",        # 术语：菱形
        "doc": "rectangle",       # 文档：矩形
        "commit": "hexagon",      # 提交：六边形
        "symbol": "ellipse"       # 符号：椭圆
    }
    return shape_map.get(node.entity_type, "circle")
```

**示例**：
- **文件节点**：圆形
- **能力节点**：方形
- **术语节点**：菱形

---

## 3. 边语义定义

### 3.1 边的认知属性

每条边必须包含以下属性：

```python
@dataclass
class SubgraphEdge:
    """子图边的认知属性"""
    # 基础属性
    id: str                      # 边 ID（如 "e56"）
    source_id: str               # 源节点 ID
    target_id: str               # 目标节点 ID
    edge_type: str               # 边类型（depends_on/references/mentions/implements）

    # 证据属性
    evidence_count: int          # 这条边的证据数量
    evidence_types: List[str]    # 证据来源（["git", "doc", "code"]）
    evidence_list: List[Evidence]  # 完整证据列表
    confidence: float            # 置信度（0.0-1.0，基于证据质量）

    # 状态属性
    status: str                  # 状态（"confirmed" / "suspected" / "weak"）
    is_weak: bool                # 是否为弱边（evidence_count < 3）
    is_suspected: bool           # 是否为推测边（evidence_count = 0）

    # 视觉编码属性（运行时计算）
    visual: EdgeVisual
```

---

### 3.2 边视觉编码规则

#### 3.2.1 边粗细（反映 evidence_count）

**语义**：边的粗细反映**证据数量**。

**编码方案**：
```python
def get_edge_width(edge: SubgraphEdge) -> int:
    """计算边粗细（单位：px）"""
    count = edge.evidence_count

    if count == 0:
        return 1  # 推测边：细线
    elif count == 1:
        return 1  # 单一证据：细线
    elif count <= 4:
        return 2  # 中等证据：中线
    elif count <= 9:
        return 3  # 强证据：粗线
    else:
        return 4  # 超强证据：最粗线
```

**范围限制**：
- 最小：`1px`
- 最大：`4px`

---

#### 3.2.2 边颜色（反映 evidence_types 多样性）

**语义**：边的颜色反映**证据来源的多样性**。

**编码方案**：
```python
def get_edge_color(edge: SubgraphEdge) -> str:
    """计算边颜色"""
    types = edge.evidence_types
    count = len(types)

    if edge.is_suspected:
        return "#CCCCCC"  # 灰色：推测边
    elif count == 0:
        return "#FF0000"  # 红色：无证据（不应该出现）
    elif count == 1:
        return "#B0B0B0"  # 浅灰：单一来源
    elif count == 2:
        return "#4A90E2"  # 蓝色：两种来源
    elif count >= 3:
        return "#00C853"  # 绿色：三种来源
```

**示例**：
- **只有 Git 证据**：浅灰色
- **Git + Doc**：蓝色
- **Git + Doc + Code**：绿色

---

#### 3.2.3 边样式（区分 edge_type）

**语义**：边的样式反映**关系类型**。

**编码方案**：
```python
def get_edge_style(edge: SubgraphEdge) -> str:
    """计算边样式"""
    if edge.is_suspected:
        return "dashed"  # 虚线：推测边

    style_map = {
        "depends_on": "solid",      # 依赖：实线
        "references": "solid",      # 引用：实线
        "mentions": "dotted",       # 提及：点线
        "implements": "solid",      # 实现：实线
        "modifies": "solid"         # 修改：实线
    }
    return style_map.get(edge.edge_type, "solid")
```

**示例**：
- **依赖关系**：实线
- **提及关系**：点线
- **推测关系**：虚线

---

#### 3.2.4 边透明度（反映 confidence）

**语义**：边的透明度反映**置信度**。

**编码方案**：
```python
def get_edge_opacity(edge: SubgraphEdge) -> float:
    """计算边透明度"""
    if edge.is_suspected:
        return 0.3  # 推测边：半透明

    # 基于 evidence_count 计算
    count = edge.evidence_count
    if count == 1:
        return 0.4
    elif count <= 4:
        return 0.7
    else:
        return 1.0  # 强证据：不透明
```

---

#### 3.2.5 边标签（显示证据信息）

**语义**：标签用于显示**证据详情**。

**内容结构**：
```
[Edge Type] | [Evidence Count] evidence
```

**示例**：
```
depends_on | 5 evidence (Git+Code)
```

**编码方案**：
```python
def get_edge_label(edge: SubgraphEdge) -> str:
    """生成边标签"""
    if edge.is_suspected:
        return f"Suspected: {edge.edge_type}"

    types_str = "+".join(sorted(edge.evidence_types))
    return f"{edge.edge_type} | {edge.evidence_count} ({types_str})"
```

**显示策略**：
- 默认：不显示标签（避免图过于拥挤）
- 悬停时：显示完整标签
- 弱边（evidence_count < 3）：始终显示标签（警告作用）

---

#### 3.2.6 边箭头（表示方向性）

**语义**：箭头用于表示**关系方向**。

**编码方案**：
```python
def get_edge_arrow(edge: SubgraphEdge) -> dict:
    """计算边箭头"""
    # 大多数边是有向的
    arrow_map = {
        "depends_on": "target",      # A depends on B: A → B
        "references": "target",      # Doc references File: Doc → File
        "mentions": "target",        # Doc mentions Term: Doc → Term
        "implements": "target",      # File implements Capability: File → Capability
        "modifies": "target"         # Commit modifies File: Commit → File
    }

    direction = arrow_map.get(edge.edge_type, "target")

    return {
        "direction": direction,
        "size": 8,
        "shape": "triangle"
    }
```

---

## 4. 空白区域语义定义

### 4.1 空白区域识别逻辑

**定义**：空白区域是**应该存在但缺失的连接**。

#### 场景 1：代码依赖但无文档

**检测逻辑**：
```python
def detect_code_without_doc(subgraph: Subgraph) -> List[MissingConnection]:
    """检测"有代码依赖但无文档"的空白"""
    missing = []

    for edge in subgraph.edges:
        if edge.edge_type == "depends_on":
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

**示例**：
- **A imports B**（代码中）
- 但没有 Doc 提到 "为什么 A 依赖 B"
- 空白：**文档缺失**

---

#### 场景 2：同 Capability 但无连接

**检测逻辑**：
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

        # 计算实际连接数
        actual_edges = count_edges_within(subgraph, nodes)

        # 期望连接数（至少应该有 n-1 条，形成连通图）
        expected_min = len(nodes) - 1

        if actual_edges < expected_min:
            missing.append(MissingConnection(
                source=None,
                target=None,
                type="sparse_capability_cluster",
                reason=f"Capability '{cap}' has {len(nodes)} nodes but only {actual_edges} edges",
                confidence=0.6,
                suggested_edges=suggest_missing_edges(nodes)
            ))

    return missing
```

**示例**：
- **文件 A、B、C** 都属于 "task" capability
- 但 A-B-C 之间没有任何边连接
- 空白：**关系未建立**

---

#### 场景 3：Blind Spot 导致的缺失

**检测逻辑**：
```python
def detect_blind_spot_gaps(subgraph: Subgraph, blind_spots: List[BlindSpot]) -> List[MissingConnection]:
    """检测"Blind Spot 导致的缺失连接"的空白"""
    missing = []

    for node in subgraph.nodes:
        if not node.is_blind_spot:
            continue

        # 获取盲区详情
        bs = next(b for b in blind_spots if b.entity_key == node.entity_key)

        if bs.blind_spot_type == "high_fan_in_undocumented":
            # 高扇入但无文档：期望有 doc → node 的边
            missing.append(MissingConnection(
                source="doc:*",
                target=node.id,
                type="missing_documentation_edge",
                reason=f"{node.name} has {node.in_degree} dependents but no documentation",
                confidence=0.9
            ))

        elif bs.blind_spot_type == "capability_no_implementation":
            # 能力无实现：期望有 file → capability 的边
            missing.append(MissingConnection(
                source="file:*",
                target=node.id,
                type="missing_implementation_edge",
                reason=f"Capability '{node.name}' declared but not implemented",
                confidence=0.85
            ))

    return missing
```

**示例**：
- Blind Spot 检测到 "governance capability has no implementation"
- 期望有 `file:governance.py → capability:governance` 的边
- 但图中没有这条边
- 空白：**盲区导致**

---

### 4.2 空白区域展示规则

#### 展示方式 1：虚线推测边

**视觉编码**：
```json
{
  "missing_connection": {
    "id": "missing-1",
    "source": "n12",
    "target": "n15",
    "type": "suspected",
    "visual": {
      "style": "dashed",
      "color": "#CCCCCC",
      "width": 1,
      "opacity": 0.4,
      "label": "Suspected: Missing doc reference",
      "arrow": "target"
    }
  }
}
```

**规则**：
- 用虚线连接"应该有关系"的节点
- 颜色必须是灰色（`#CCCCCC`）
- 标签显示"Suspected: [reason]"

---

#### 展示方式 2：空洞标注

**视觉编码**：
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
      "label": "Coverage Gap: 4 missing connections",
      "icon": "⚠️"
    }
  }
}
```

**规则**：
- 在"应该密集但稀疏"的区域显示空心圆
- 标注"Coverage Gap: X missing connections"

---

#### 展示方式 3：孤立节点警告

**检测逻辑**：
```python
def detect_orphan_nodes(subgraph: Subgraph) -> List[OrphanWarning]:
    """检测孤立节点"""
    warnings = []

    for node in subgraph.nodes:
        total_degree = node.in_degree + node.out_degree

        # 如果节点的度数 = 0 且不是种子节点
        if total_degree == 0 and node.distance_from_seed > 0:
            warnings.append(OrphanWarning(
                node_id=node.id,
                reason="Node has no connections",
                severity="high"
            ))

        # 如果节点的出度 = 0 但不是叶子节点（入度很高）
        elif node.out_degree == 0 and node.in_degree > 5:
            warnings.append(OrphanWarning(
                node_id=node.id,
                reason="High fan-in but no outgoing edges (potential dead-end)",
                severity="medium"
            ))

    return warnings
```

**视觉编码**：
- 孤立节点边框用橙色虚线
- 标签显示 "⚠️ Orphan: No connections"

---

## 5. 视觉编码字典

### 5.1 颜色语义

#### 节点颜色（基于证据来源多样性）

| 颜色 | Hex Code | 语义 | 证据来源数量 |
|------|----------|------|-------------|
| 绿色 | `#00C853` | 强证据 | 3 种来源 |
| 蓝色 | `#4A90E2` | 中等证据 | 2 种来源 |
| 橙色 | `#FFA000` | 薄弱证据 | 1 种来源 |
| 红色 | `#FF0000` | 无证据 | 0 种来源 |

#### 边颜色（基于证据类型多样性）

| 颜色 | Hex Code | 语义 | 证据类型数量 |
|------|----------|------|-------------|
| 绿色 | `#00C853` | 强证据 | 3 种类型 |
| 蓝色 | `#4A90E2` | 中等证据 | 2 种类型 |
| 浅灰 | `#B0B0B0` | 薄弱证据 | 1 种类型 |
| 灰色 | `#CCCCCC` | 推测边 | 0 种类型 |

#### 盲区颜色（基于严重度）

| 颜色 | Hex Code | 语义 | 严重度范围 |
|------|----------|------|-----------|
| 红色 | `#FF0000` | 高风险 | 0.7 - 1.0 |
| 橙色 | `#FF6600` | 中风险 | 0.4 - 0.69 |
| 黄色 | `#FFB300` | 低风险 | 0.0 - 0.39 |

#### 背景/空白区域颜色

| 颜色 | Hex Code | 语义 |
|------|----------|------|
| 白色 | `#FFFFFF` | 正常区域 |
| 浅橙 | `#FFF3E0` | Coverage Gap |
| 浅红 | `#FFEBEE` | Blind Spot 区域 |

---

### 5.2 形状/样式语义

#### 节点形状（区分实体类型）

| 形状 | 实体类型 | 示例 |
|------|---------|------|
| 圆形 | file | manager.py |
| 方形 | capability | governance |
| 菱形 | term | TaskState |
| 矩形 | doc | ADR-001 |
| 六边形 | commit | 6aa4aaa |
| 椭圆 | symbol | TaskManager.execute() |

#### 边样式（区分关系类型和状态）

| 样式 | 语义 | 适用场景 |
|------|------|---------|
| 实线 | 确认关系 | depends_on, references, implements |
| 点线 | 弱关系 | mentions |
| 虚线 | 推测关系 | suspected edges |

#### 边箭头

| 箭头方向 | 语义 |
|---------|------|
| 单向（→） | 有向关系（如 A depends on B） |
| 无箭头（—） | 无向关系（不常用） |

---

### 5.3 尺寸语义

#### 节点大小范围

| 大小 | 半径（px） | 语义 |
|------|----------|------|
| 最小 | 20 | 叶子节点（1 证据，入度 0） |
| 小 | 30 | 普通节点（2-5 证据） |
| 中 | 40 | 重要节点（6-10 证据） |
| 大 | 50 | 核心节点（11+ 证据） |
| 最大 | 65 | 种子节点或高扇入节点 |

#### 边粗细范围

| 粗细 | 宽度（px） | 语义 |
|------|----------|------|
| 细 | 1 | 单一证据或推测边 |
| 中 | 2 | 2-4 条证据 |
| 粗 | 3 | 5-9 条证据 |
| 最粗 | 4 | 10+ 条证据 |

#### 标签字体大小

| 元素 | 字体大小（px） |
|------|--------------|
| 节点主标题 | 14 |
| 节点副标题 | 10 |
| 边标签 | 9 |
| 图例说明 | 12 |

---

### 5.4 标注语义

#### 节点标签内容

**格式**：
```
[Entity Name]
[Coverage Badge] [Coverage %] | [Evidence Count] evidence
[Blind Spot Warning]  // 仅当 is_blind_spot = true 时显示
```

**示例**：
```
manager.py
✅ 89% | 12 evidence

governance.py
⚠️ BLIND SPOT | 45% | 3 evidence
High fan-in, undocumented
```

#### 边标签内容

**格式**：
```
[Edge Type] | [Evidence Count] ([Evidence Types])
```

**示例**：
```
depends_on | 5 (Git+Code)
references | 1 (Doc)
Suspected: depends_on
```

#### 图例说明（必须有）

**内容**：
```
Legend:
- Node Color: Green = 3 sources, Blue = 2 sources, Orange = 1 source, Red = 0 source
- Node Border: Red dashed = Blind Spot
- Edge Width: Thickness = evidence count
- Edge Color: Green = multi-type evidence, Gray = single-type
- Dashed Edge: Suspected missing connection
```

---

## 6. 交互语义

### 6.1 Hover 悬停

#### 悬停节点时显示

**内容**：
```
Entity: file:manager.py
Type: file
Coverage: 89%
Evidence Count: 12
- Git: 5 commits
- Doc: 3 references
- Code: 4 dependencies

In-Degree: 8 (8 files depend on this)
Out-Degree: 3 (depends on 3 files)

Blind Spot: No
```

**如果是 Blind Spot**：
```
Entity: file:governance.py
Type: file
Coverage: 45%
Evidence Count: 3

⚠️ BLIND SPOT: High Fan-In Undocumented
Severity: High (0.85)
Reason: 15 files depend on this, but no documentation exists
Suggested Action: Add ADR explaining this file's architecture
```

---

#### 悬停边时显示

**内容**：
```
Edge: manager.py → models.py
Type: depends_on
Evidence Count: 5
Confidence: 0.85

Evidence Sources:
1. Git: commit 6aa4aaa modified both files
2. Code: import statement in manager.py:10
3. Code: function call in manager.py:45
4. Doc: ADR-001 mentions this dependency
5. Git: commit 91db273 updated import
```

**如果是推测边**：
```
Edge: manager.py → config.py (Suspected)
Type: depends_on
Status: Suspected missing connection

Reason: manager.py uses Config class but no DEPENDS_ON edge found
Confidence: 0.75
```

---

### 6.2 Click 点击

#### 点击节点时

**操作**：
- **主操作**：跳转到该实体的 Explain 视图（显示完整信息）
- **次操作**：展开子图（以该节点为种子，显示 1-hop 邻域）

**UI 反馈**：
- 点击后节点高亮（边框加粗，颜色变为黄色）
- 其他节点变灰（opacity 降为 0.3）
- 连接到该节点的边高亮

---

#### 点击边时

**操作**：
- **主操作**：显示证据详情（弹出侧边栏）
- **次操作**：高亮路径（如果边是某个推理链的一部分）

**证据详情内容**：
```
Edge: manager.py → models.py
Type: depends_on

Evidence #1:
- Type: code (import)
- Source: manager.py:10
- Span: "from agentos.core.task.models import Task"
- Confidence: 1.0

Evidence #2:
- Type: git (commit)
- Source: commit 6aa4aaa
- Message: "feat: add task manager"
- Files Changed: manager.py, models.py
- Confidence: 0.8

Evidence #3:
- Type: doc (reference)
- Source: ADR-001
- Span: "TaskManager depends on Task model"
- Confidence: 0.9
```

---

### 6.3 Zoom/Pan 缩放平移

#### 缩放

**支持范围**：
- 最小缩放：`0.3x`（30% 原始大小）
- 最大缩放：`3.0x`（300% 原始大小）

**UI 反馈**：
- 缩放时节点大小和字体大小按比例调整
- 边粗细保持不变（避免在小缩放比例下消失）

---

#### 平移

**支持范围**：
- 无限平移（自动扩展画布）

**UI 反馈**：
- 鼠标拖拽时显示抓手图标
- 平移时显示小地图（右下角）

---

### 6.4 Filter 过滤

#### 过滤低证据边

**UI 控件**：
```
Evidence Filter:
[✓] Show all edges
[ ] Only edges with >= 3 evidence
[ ] Only edges with >= 5 evidence
[ ] Only multi-type evidence edges
```

**行为**：
- 勾选后，不符合条件的边会**淡出**（opacity: 0.1）但不消失
- 被过滤的边不参与布局计算

---

#### 过滤特定类型

**UI 控件**：
```
Entity Type Filter:
[✓] Files
[✓] Capabilities
[✓] Terms
[✓] Docs
[ ] Commits
[ ] Symbols
```

**行为**：
- 取消勾选后，该类型的节点会**淡出**（opacity: 0.1）
- 连接到被过滤节点的边也会淡出

---

#### 过滤 Blind Spot

**UI 控件**：
```
Blind Spot Filter:
[ ] Show only Blind Spot nodes
[ ] Hide Blind Spot nodes
[✓] Show all
```

**行为**：
- "Show only"：只显示 Blind Spot 节点及其连接
- "Hide"：隐藏 Blind Spot 节点（用于"看看没有盲区的图是什么样"）

---

## 7. 反模式清单

### 7.1 认知欺骗型反模式（用户误解）

#### 反模式 1：密集幻觉

**问题**：
- 图看起来很密集（很多节点和边），但实际每条边只有 1 条证据
- 用户误以为"图很密集 = 理解很深"

**错误示例**：
```json
// 50 条边，但每条只有 1 条证据
{
  "edges": [
    {"id": "e1", "evidence_count": 1},
    {"id": "e2", "evidence_count": 1},
    // ... 48 more
  ]
}
```

**正确做法**：
- 边的粗细/颜色必须反映证据密度
- 薄弱边应该是浅色/细线
- 显示子图整体的"证据密度"指标（如 "平均每边 1.2 条证据"）

**验收测试**：
```python
# 检查边的视觉权重是否反映证据密度
for edge in subgraph.edges:
    visual_weight = edge.visual.width * edge.visual.opacity
    evidence_weight = edge.evidence_count / 10.0
    assert abs(visual_weight - evidence_weight) < 0.5
```

---

#### 反模式 2：完整幻觉

**问题**：
- 图没有显示空白区域，用户以为"图中有的就是全部"
- 实际上有很多缺失的连接没有展示

**错误示例**：
```json
{
  "nodes": [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}],
  "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
  "missing_connections": []  // ❌ 没有检测缺失连接
}
```

**正确做法**：
- 运行缺失连接检测
- 用虚线显示"推测的边"
- 显示子图元数据："Missing Connections: 4 detected"

**验收测试**：
```python
# 检查是否检测并显示缺失连接
metadata = subgraph.get_metadata()
assert "missing_connections_count" in metadata
assert metadata["missing_connections_count"] >= 0

# 检查是否有虚线推测边
suspected_edges = [e for e in subgraph.edges if e.is_suspected]
assert len(suspected_edges) == metadata["missing_connections_count"]
```

---

#### 反模式 3：装饰性警告

**问题**：
- Blind Spot 用小图标标注，但不够醒目，用户容易忽略
- 盲区节点看起来和普通节点差不多

**错误示例**：
```json
{
  "node_id": "n45",
  "is_blind_spot": true,
  "visual": {
    "border_color": "#000000",  // ❌ 黑色边框，不醒目
    "border_width": 1,
    "icon_overlay": "⚠️",  // ❌ 只有小图标
    "icon_size": 8  // ❌ 太小
  }
}
```

**正确做法**：
- 盲区节点必须用强对比色（红色/橙色）标注
- 边框必须是粗线（width >= 2px）
- 标签显示"⚠️ BLIND SPOT"文字（不只是图标）

**验收测试**：
```python
# 检查盲区节点的视觉醒目度
for node in subgraph.nodes:
    if node.is_blind_spot:
        assert node.visual.border_color in ["#FF0000", "#FF6600"]
        assert node.visual.border_width >= 2
        assert "BLIND SPOT" in node.visual.label
```

---

#### 反模式 4：无证据边

**问题**：
- 展示了"推测的"或"理论上应该有"的边，但没有实际证据
- 没有明确标注为"推测边"

**错误示例**：
```json
{
  "edge_id": "e99",
  "source": "n1",
  "target": "n2",
  "evidence_count": 0,  // ❌ 无证据
  "visual": {
    "style": "solid",  // ❌ 实线（看起来像确认边）
    "color": "#4A90E2"  // ❌ 蓝色（看起来像中等证据）
  }
}
```

**正确做法**：
- 所有边必须有 >= 1 条 Evidence
- 如果要显示推测边，必须：
  - `status: "suspected"`
  - `style: "dashed"`
  - `color: "#CCCCCC"` (灰色)
  - `label: "Suspected: [reason]"`

**验收测试**：
```python
# 检查无证据边的处理
for edge in subgraph.edges:
    if edge.evidence_count == 0:
        assert edge.status == "suspected"
        assert edge.visual.style == "dashed"
        assert edge.visual.color == "#CCCCCC"
        assert "Suspected" in edge.visual.label
```

---

#### 反模式 5：隐式空白

**问题**：
- 空白区域是"隐式的"（用户需要自己发现"这里好像少了什么"）
- 没有显性标注"这里缺失X个连接"

**错误示例**：
```json
{
  "nodes": [
    {"id": "n1", "entity_type": "file"},
    {"id": "n2", "entity_type": "file"},
    {"id": "n3", "entity_type": "file"}
  ],
  "edges": [
    {"id": "e1", "source": "n1", "target": "n2"}
  ]
  // ❌ n1-n3 和 n2-n3 应该有连接但没有显示
}
```

**正确做法**：
- 在稀疏区域显示"Coverage Gap"标注
- 用虚线连接"应该有关系但没有证据"的节点

**验收测试**：
```python
# 检查空白区域是否显性标注
gap_annotations = subgraph.get_gap_annotations()
assert len(gap_annotations) > 0 or subgraph.is_fully_connected()
```

---

#### 反模式 6：单一视角

**问题**：
- 只显示一种证据类型（如只显示 Git commit）
- 用户误以为"这就是全部证据"

**错误示例**：
```json
{
  "edge_id": "e10",
  "evidence_count": 5,
  "evidence_types": ["git"],  // ❌ 只有 Git 证据
  "visual": {
    "color": "#00C853"  // ❌ 绿色（看起来像多类型证据）
  }
}
```

**正确做法**：
- 边颜色必须反映证据类型的**多样性**
- 单一类型 → 浅灰色
- 多类型 → 绿色/蓝色

**验收测试**：
```python
# 检查边颜色是否反映证据类型多样性
for edge in subgraph.edges:
    if len(edge.evidence_types) == 1:
        assert edge.visual.color == "#B0B0B0"  # 浅灰
    elif len(edge.evidence_types) >= 3:
        assert edge.visual.color == "#00C853"  # 绿色
```

---

#### 反模式 7：覆盖度乐观

**问题**：
- 显示"覆盖度：89%"，但实际只是"89% 的节点有至少 1 条证据"
- 没有显示"证据密度"（平均每节点/边有多少条证据）

**错误示例**：
```json
{
  "metadata": {
    "coverage_percent": 0.89  // ❌ 只显示覆盖度
  }
}
```

**正确做法**：
- 同时显示：
  - **覆盖度**：有证据的节点/边的比例
  - **证据密度**：平均每节点/边的证据数量

**验收测试**：
```python
# 检查是否显示证据密度
metadata = subgraph.get_metadata()
assert "coverage_percent" in metadata
assert "evidence_density" in metadata
assert metadata["evidence_density"] > 0
```

---

#### 反模式 8：孤立节点隐藏

**问题**：
- 孤立节点（度数 = 0）被自动隐藏
- 用户看不到"这个节点没有任何连接"

**错误示例**：
```python
# 过滤掉度数为 0 的节点
visible_nodes = [n for n in subgraph.nodes if n.in_degree + n.out_degree > 0]
```

**正确做法**：
- 孤立节点必须显示
- 标注"⚠️ Orphan: No connections"

**验收测试**：
```python
# 检查孤立节点是否显示
orphan_nodes = [n for n in subgraph.nodes if n.in_degree + n.out_degree == 0]
for node in orphan_nodes:
    assert node.visual.visible == True
    assert "Orphan" in node.visual.label
```

---

#### 反模式 9：边界模糊

**问题**：
- 子图的边界不清晰，用户不知道"图外还有什么"
- 没有显示"这个节点在图外还有 5 条边"

**错误示例**：
```json
{
  "node_id": "n1",
  "in_degree": 3,  // ❌ 只显示子图内的度数
  "out_degree": 2
}
```

**正确做法**：
- 显示两个度数：
  - **子图内度数**：在子图中的连接数
  - **全图度数**：在完整知识图谱中的连接数
- 如果 `全图度数 > 子图度数`，显示"..."标注

**验收测试**：
```python
# 检查是否显示全图度数
for node in subgraph.nodes:
    assert hasattr(node, "in_degree_subgraph")
    assert hasattr(node, "in_degree_full_graph")
    if node.in_degree_full_graph > node.in_degree_subgraph:
        assert "..." in node.visual.label
```

---

#### 反模式 10：置信度隐藏

**问题**：
- 边的置信度没有显示，用户不知道"这条边有多可靠"
- 低置信度的边看起来和高置信度的边一样

**错误示例**：
```json
{
  "edge_id": "e20",
  "confidence": 0.3,  // ❌ 低置信度
  "visual": {
    "opacity": 1.0  // ❌ 不透明（看起来很确定）
  }
}
```

**正确做法**：
- 边的透明度必须反映置信度
- `confidence < 0.5` → `opacity: 0.4` (半透明)
- `confidence >= 0.8` → `opacity: 1.0` (不透明)

**验收测试**：
```python
# 检查透明度是否反映置信度
for edge in subgraph.edges:
    if edge.confidence < 0.5:
        assert edge.visual.opacity <= 0.5
    elif edge.confidence >= 0.8:
        assert edge.visual.opacity >= 0.9
```

---

### 7.2 技术实现型反模式（开发错误）

#### 反模式 11：默认布局算法

**问题**：
- 使用 force-directed 布局但不考虑证据密度
- 导致弱边和强边看起来一样（在图中的距离相同）

**错误示例**：
```python
# 使用默认的 force-directed 布局
layout = force_directed_layout(nodes, edges)
# ❌ 所有边的"弹簧强度"相同，不管证据数量
```

**正确做法**：
- 布局算法必须考虑 `evidence_count` 作为边的"弹簧强度"
- 证据多的边 → 弹簧强 → 节点靠得更近

```python
# 基于证据密度的布局
def weighted_force_directed_layout(nodes, edges):
    for edge in edges:
        edge.spring_strength = edge.evidence_count / 10.0  # 归一化
    return force_directed_layout(nodes, edges)
```

---

#### 反模式 12：无限子图

**问题**：
- 从种子节点无限扩展，导致图过大无法理解
- 用户看到 500+ 个节点，根本无法理解

**错误示例**：
```python
# 无限 BFS
subgraph = bfs_expand(seed, k_hop=999)
# ❌ 可能返回整个知识图谱
```

**正确做法**：
- 限制深度（如 2-3 跳）
- 超出范围用"..."标注
- 提供"展开"按钮让用户手动扩展

---

#### 反模式 13：证据链丢失

**问题**：
- 子图只显示节点和边，不保留证据链
- 用户点击边时无法看到证据详情

**错误示例**：
```json
{
  "edge_id": "e30",
  "evidence_count": 5,
  "evidence_list": []  // ❌ 证据链丢失
}
```

**正确做法**：
- 子图必须包含完整的证据链
- 点击边时显示证据详情

---

#### 反模式 14：静态快照

**问题**：
- 子图是静态的（生成后不会更新）
- 用户修改了代码/文档后，子图没有反映变化

**错误示例**：
```python
# 生成子图后存储为 JSON
subgraph_json = generate_subgraph(seed)
save_to_file("subgraph.json", subgraph_json)
# ❌ 用户修改代码后，subgraph.json 不会更新
```

**正确做法**：
- 子图应该是"实时查询"的结果
- 或者显示"生成时间"和"刷新"按钮

---

#### 反模式 15：性能陷阱

**问题**：
- 计算子图时执行全图遍历
- 对于大型知识图谱（100k+ 节点）性能很差

**错误示例**：
```python
# 全图遍历
def get_subgraph(seed, k_hop):
    all_nodes = load_all_nodes()  # ❌ 加载所有节点
    return bfs(all_nodes, seed, k_hop)
```

**正确做法**：
- 使用数据库索引
- 只加载必要的节点和边
- 设置超时限制（如 5 秒）

---

#### 反模式 16：坐标硬编码

**问题**：
- 节点坐标硬编码（如 `x: 100, y: 200`）
- 当子图变化时，布局不一致

**错误示例**：
```json
{
  "node_id": "n1",
  "position": {"x": 100, "y": 200}  // ❌ 硬编码
}
```

**正确做法**：
- 使用布局算法动态计算坐标
- 或者存储"相对位置"而不是绝对坐标

---

#### 反模式 17：颜色硬编码

**问题**：
- 颜色硬编码在代码中（如 `color = "#00C853"`）
- 无法支持暗色主题或无障碍模式

**错误示例**：
```python
def get_node_color(node):
    if node.coverage_sources >= 3:
        return "#00C853"  # ❌ 硬编码
```

**正确做法**：
- 使用颜色主题系统
- 支持浅色/暗色/高对比度模式

---

#### 反模式 18：缺少图例

**问题**：
- 图中没有图例，用户不知道颜色/形状的含义
- 用户必须"猜测"视觉编码规则

**错误示例**：
```html
<div id="subgraph"></div>
<!-- ❌ 没有图例 -->
```

**正确做法**：
- 必须显示图例
- 解释所有颜色/形状/样式的含义

---

#### 反模式 19：无交互反馈

**问题**：
- 用户悬停/点击节点时没有视觉反馈
- 用户不知道"我点击了哪个节点"

**错误示例**：
```javascript
// 点击节点后什么都不做
node.on('click', function(d) {
  console.log(d);  // ❌ 只在控制台输出
});
```

**正确做法**：
- 点击后节点高亮
- 显示详情面板
- 其他节点变灰

---

#### 反模式 20：过度动画

**问题**：
- 布局变化时有长时间的动画（如 3 秒）
- 用户必须等待动画结束才能继续操作

**错误示例**：
```javascript
// 3 秒的动画
layout.transition().duration(3000);
```

**正确做法**：
- 动画时间控制在 300-500ms
- 提供"跳过动画"选项

---

#### 反模式 21：内存泄漏

**问题**：
- 切换子图时不清理旧的 DOM 元素
- 导致内存占用不断增长

**错误示例**：
```javascript
// 生成新子图但不清理旧的
function renderSubgraph(data) {
  d3.select("#subgraph").append("svg");  // ❌ 不断追加
}
```

**正确做法**：
- 切换前清理旧的 DOM
- 使用 `remove()` 或 `selectAll().remove()`

---

#### 反模式 22：无错误处理

**问题**：
- 子图生成失败时没有错误提示
- 用户看到空白屏幕，不知道发生了什么

**错误示例**：
```python
# 生成子图时出错，但不捕获异常
subgraph = generate_subgraph(seed)  # ❌ 可能抛出异常
```

**正确做法**：
- 捕获异常并显示友好的错误信息
- 如"Seed node not found. Please check the entity key."

---

## 8. 验收标准

### 8.1 三条红线的具体验收方法

#### 验收红线 1：无证据边

**测试用例**：
```python
def test_no_evidence_edge():
    """验证：图中不能有无证据的实线边"""
    subgraph = generate_subgraph("file:manager.py", k_hop=2)

    for edge in subgraph.edges:
        if edge.status == "confirmed":
            assert edge.evidence_count >= 1, f"Edge {edge.id} has no evidence"
        elif edge.status == "suspected":
            # 推测边必须有特殊视觉编码
            assert edge.visual.style == "dashed"
            assert edge.visual.color == "#CCCCCC"
```

---

#### 验收红线 2：隐藏盲区

**测试用例**：
```python
def test_blind_spot_visible():
    """验证：盲区节点必须醒目标注"""
    subgraph = generate_subgraph("file:governance.py", k_hop=1)

    blind_spot_nodes = [n for n in subgraph.nodes if n.is_blind_spot]
    assert len(blind_spot_nodes) > 0, "Expected at least one blind spot node"

    for node in blind_spot_nodes:
        # 检查边框颜色
        assert node.visual.border_color in ["#FF0000", "#FF6600"], \
            f"Blind spot node {node.id} has wrong border color"

        # 检查边框宽度
        assert node.visual.border_width >= 2, \
            f"Blind spot node {node.id} border too thin"

        # 检查标签
        assert "BLIND SPOT" in node.visual.label, \
            f"Blind spot node {node.id} missing label"
```

---

#### 验收红线 3：完整幻觉

**测试用例**：
```python
def test_coverage_metadata():
    """验证：子图元数据显示覆盖度和缺失连接"""
    subgraph = generate_subgraph("file:manager.py", k_hop=2)
    metadata = subgraph.get_metadata()

    # 必须有覆盖度信息
    assert "coverage_percent" in metadata
    assert 0.0 <= metadata["coverage_percent"] <= 1.0

    # 必须有证据密度信息
    assert "evidence_density" in metadata
    assert metadata["evidence_density"] >= 0.0

    # 必须有缺失连接检测
    assert "missing_connections_count" in metadata
    assert metadata["missing_connections_count"] >= 0
```

---

### 8.2 视觉语义的验收 Checklist

**节点验收**：
- [ ] 节点颜色反映证据来源多样性（3 源=绿，2 源=蓝，1 源=橙，0 源=红）
- [ ] 节点大小反映重要性（证据数量 + 入度）
- [ ] 盲区节点有红色/橙色虚线边框
- [ ] 节点标签显示覆盖度和证据数量
- [ ] 节点形状区分实体类型（圆=文件，方=能力，菱=术语）

**边验收**：
- [ ] 边粗细反映证据数量（1 条=细，10+ 条=粗）
- [ ] 边颜色反映证据类型多样性（3 类=绿，2 类=蓝，1 类=灰）
- [ ] 边样式区分关系类型（实线=确认，虚线=推测，点线=弱关系）
- [ ] 边透明度反映置信度（低置信=半透明）
- [ ] 边标签显示证据数量和类型

**空白区域验收**：
- [ ] 缺失的连接用虚线标注
- [ ] 稀疏区域显示"Coverage Gap"标签
- [ ] 孤立节点标注"⚠️ Orphan"

**交互验收**：
- [ ] 悬停节点时显示详细信息（覆盖度、证据数量、盲区详情）
- [ ] 悬停边时显示证据列表
- [ ] 点击节点跳转到 Explain 视图
- [ ] 点击边显示证据详情
- [ ] 支持缩放（0.3x - 3.0x）和平移
- [ ] 过滤控件工作正常（证据过滤、类型过滤、盲区过滤）

**元数据验收**：
- [ ] 显示子图元数据卡片（节点数、边数、覆盖度、缺失连接数）
- [ ] 显示图例（解释所有颜色/形状/样式）
- [ ] 显示生成时间和刷新按钮

**性能验收**：
- [ ] 子图生成时间 < 5 秒（对于 50 节点、100 边）
- [ ] 渲染时间 < 1 秒
- [ ] 交互响应时间 < 100ms
- [ ] 内存占用 < 100MB（对于 100 节点、200 边）

---

## 9. 总结

### 9.1 核心要点

P2 子图可视化的本质是：

1. **诚实认知**：不隐藏盲区，不美化薄弱边，不制造"完整幻觉"
2. **证据驱动**：所有视觉编码都基于证据数量和类型
3. **空白可见**：缺失的连接必须显性标注，不能"因为画不出来就假装不存在"

### 9.2 后续任务

本文档定义了**认知模型和视觉语义**，后续任务将基于此规范实现：

- **P2-2**：数据查询层实现（从 BrainOS DB 查询子图数据）
- **P2-3**：子图构建算法（k-hop BFS + 缺失连接检测）
- **P2-4**：前端可视化实现（D3.js 或 Cytoscape.js）
- **P2-5**：交互和过滤功能（悬停、点击、缩放、过滤）

### 9.3 验收标准

交付物必须满足：
1. ✅ 三条红线清晰定义且可验收
2. ✅ 视觉编码完整（节点、边、空白区域）
3. ✅ 反模式充分（22 个，覆盖认知欺骗和技术实现）
4. ✅ 可执行性强（后续任务可直接依据本文档）
5. ✅ 认知优先（所有设计从"诚实认知"出发）

---

**文档状态**: ✅ Complete
**字数统计**: ~10,500 字
**下一步**: 生成快速参考文档和 ADR 文档
**最后更新**: 2026-01-30
