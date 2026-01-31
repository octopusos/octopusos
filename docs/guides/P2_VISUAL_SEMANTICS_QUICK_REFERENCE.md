# P2: 子图可视化 - 视觉语义速查表

**Version**: v1.0.0
**Date**: 2026-01-30
**Related**: P2_COGNITIVE_MODEL_DEFINITION.md

---

## 1. 三条红线速查

| 红线 | 定义 | 验收方法 |
|------|------|---------|
| ❌ 无证据边 | 每条边必须有 ≥1 条 Evidence | `assert edge.evidence_count >= 1` |
| ❌ 隐藏盲区 | 盲区必须用红色虚线边框标注 | `assert blind_spot.border_color == "#FF0000"` |
| ❌ 完整幻觉 | 必须显示缺失连接数和覆盖度 | `assert metadata.has("missing_connections_count")` |

---

## 2. 节点视觉编码速查表

### 2.1 节点颜色（证据来源多样性）

| 来源数量 | 颜色 | Hex | 语义 |
|---------|------|-----|------|
| 3 种 | 绿色 | `#00C853` | 强证据（Git+Doc+Code） |
| 2 种 | 蓝色 | `#4A90E2` | 中等证据 |
| 1 种 | 橙色 | `#FFA000` | 薄弱证据 |
| 0 种 | 红色 | `#FF0000` | 无证据（违反红线） |

### 2.2 节点大小（重要性）

| 类型 | 半径（px） | 计算公式 |
|------|-----------|---------|
| 最小 | 20 | 基础大小 |
| 小 | 30 | 基础 + evidence_bonus |
| 中 | 40 | 基础 + evidence_bonus + fan_in_bonus |
| 大 | 50 | 中等 + 更多证据 |
| 最大 | 65 | 种子节点或核心节点 |

**公式**：
```python
size = 20 + min(20, evidence_count * 2) + min(15, in_degree * 3) + (10 if is_seed else 0)
```

### 2.3 节点边框（盲区标注）

| 盲区严重度 | 边框颜色 | 边框宽度 | 边框样式 |
|-----------|---------|---------|---------|
| 高 (≥0.7) | `#FF0000` | 3px | dashed |
| 中 (0.4-0.69) | `#FF6600` | 2px | dashed |
| 低 (<0.4) | `#FFB300` | 2px | dotted |
| 非盲区 | 同填充色 | 1px | solid |

### 2.4 节点形状（实体类型）

| 实体类型 | 形状 | 示例 |
|---------|------|------|
| file | 圆形 | manager.py |
| capability | 方形 | governance |
| term | 菱形 | TaskState |
| doc | 矩形 | ADR-001 |
| commit | 六边形 | 6aa4aaa |
| symbol | 椭圆 | execute() |

### 2.5 节点标签格式

```
[Entity Name]
[Badge] [Coverage %] | [Evidence Count] evidence
[Blind Spot Warning]  // 仅盲区时显示
```

**示例**：
```
manager.py
✅ 89% | 12 evidence

governance.py
⚠️ BLIND SPOT | 45% | 3 evidence
```

---

## 3. 边视觉编码速查表

### 3.1 边粗细（证据数量）

| 证据数量 | 宽度（px） | 语义 |
|---------|-----------|------|
| 0 | 1 | 推测边 |
| 1 | 1 | 单一证据 |
| 2-4 | 2 | 中等证据 |
| 5-9 | 3 | 强证据 |
| 10+ | 4 | 超强证据 |

### 3.2 边颜色（证据类型多样性）

| 类型数量 | 颜色 | Hex | 语义 |
|---------|------|-----|------|
| 3 种 | 绿色 | `#00C853` | 多类型（Git+Doc+Code） |
| 2 种 | 蓝色 | `#4A90E2` | 双类型 |
| 1 种 | 浅灰 | `#B0B0B0` | 单类型 |
| 0 种（推测） | 灰色 | `#CCCCCC` | 推测边 |

### 3.3 边样式（关系类型）

| 关系类型 | 样式 | 语义 |
|---------|------|------|
| depends_on | solid | 依赖关系 |
| references | solid | 引用关系 |
| mentions | dotted | 提及关系 |
| implements | solid | 实现关系 |
| modifies | solid | 修改关系 |
| suspected | dashed | 推测关系 |

### 3.4 边透明度（置信度）

| 证据数量 | 透明度 | 语义 |
|---------|-------|------|
| 0（推测） | 0.3 | 半透明 |
| 1 | 0.4 | 薄弱 |
| 2-4 | 0.7 | 中等 |
| 5+ | 1.0 | 强证据 |

### 3.5 边标签格式

```
[Edge Type] | [Evidence Count] ([Evidence Types])
```

**示例**：
```
depends_on | 5 (Git+Code)
references | 1 (Doc)
Suspected: depends_on
```

---

## 4. 空白区域标注速查表

### 4.1 缺失连接类型

| 类型 | 检测场景 | 视觉编码 |
|------|---------|---------|
| 文档缺失 | 代码依赖但无 Doc | 灰色虚线 + "Missing doc" |
| 关系未建立 | 同 capability 但无边 | 灰色虚线 + "Sparse cluster" |
| 盲区导致 | Blind Spot 检测到 | 橙色虚线 + "Blind spot gap" |

### 4.2 推测边视觉编码

```json
{
  "style": "dashed",
  "color": "#CCCCCC",
  "width": 1,
  "opacity": 0.4,
  "label": "Suspected: [reason]"
}
```

### 4.3 Coverage Gap 标注

```json
{
  "shape": "circle",
  "fill": "#FFF3E0",
  "border": "#FF6600",
  "border_style": "dashed",
  "label": "Coverage Gap: X missing connections"
}
```

---

## 5. 交互行为速查表

### 5.1 Hover 悬停

| 元素 | 显示内容 |
|------|---------|
| 节点 | Entity type, Coverage %, Evidence count, In/Out degree, Blind spot info |
| 边 | Edge type, Evidence count, Confidence, Evidence list |

### 5.2 Click 点击

| 元素 | 主操作 | 次操作 |
|------|--------|--------|
| 节点 | 跳转到 Explain 视图 | 展开子图 |
| 边 | 显示证据详情 | 高亮路径 |

### 5.3 Zoom/Pan 缩放平移

| 操作 | 范围 | UI 反馈 |
|------|------|--------|
| 缩放 | 0.3x - 3.0x | 节点/字体按比例调整 |
| 平移 | 无限 | 显示小地图 |

### 5.4 Filter 过滤

| 过滤器 | 选项 | 行为 |
|--------|------|------|
| 证据过滤 | >= 3 evidence, >= 5 evidence | 淡出不符合的边 |
| 类型过滤 | File, Capability, Term, Doc | 淡出不符合的节点 |
| 盲区过滤 | Show only, Hide, Show all | 过滤盲区节点 |

---

## 6. 反模式速查表

### 6.1 认知欺骗型（Top 5）

| 反模式 | 问题 | 正确做法 |
|--------|------|---------|
| 密集幻觉 | 图很密集但证据薄弱 | 边粗细/颜色反映证据密度 |
| 完整幻觉 | 没有显示缺失连接 | 用虚线标注推测边 |
| 装饰性警告 | 盲区标注不醒目 | 红色粗边框 + "BLIND SPOT"标签 |
| 无证据边 | 展示无证据的边 | 所有边必须有 ≥1 evidence |
| 隐式空白 | 空白区域不可见 | 显性标注"Coverage Gap" |

### 6.2 技术实现型（Top 5）

| 反模式 | 问题 | 正确做法 |
|--------|------|---------|
| 默认布局 | 不考虑证据密度 | 边的弹簧强度 = evidence_count |
| 无限子图 | 图过大无法理解 | 限制深度 2-3 跳 |
| 证据链丢失 | 无法查看证据详情 | 保留完整 evidence_list |
| 缺少图例 | 用户不懂颜色含义 | 必须显示图例 |
| 无错误处理 | 失败时空白屏幕 | 友好的错误提示 |

---

## 7. 实现关键注意事项

### 7.1 数据层

**必需属性**：
```python
@dataclass
class SubgraphNode:
    id: str
    entity_type: str
    evidence_count: int
    coverage_sources: List[str]
    is_blind_spot: bool
    blind_spot_severity: float
    in_degree: int
    out_degree: int

@dataclass
class SubgraphEdge:
    id: str
    source_id: str
    target_id: str
    edge_type: str
    evidence_count: int
    evidence_types: List[str]
    evidence_list: List[Evidence]
    confidence: float
    status: str  # "confirmed" / "suspected"
```

---

### 7.2 视觉编码层

**关键函数**：
```python
def get_node_color(node: SubgraphNode) -> str:
    sources = len(node.coverage_sources)
    return ["#FF0000", "#FFA000", "#4A90E2", "#00C853"][sources]

def get_edge_width(edge: SubgraphEdge) -> int:
    count = edge.evidence_count
    if count <= 1: return 1
    elif count <= 4: return 2
    elif count <= 9: return 3
    else: return 4

def get_edge_color(edge: SubgraphEdge) -> str:
    if edge.is_suspected: return "#CCCCCC"
    types = len(edge.evidence_types)
    return ["#B0B0B0", "#B0B0B0", "#4A90E2", "#00C853"][types]
```

---

### 7.3 布局层

**推荐算法**：
```python
def weighted_force_directed_layout(nodes, edges):
    """基于证据密度的 force-directed 布局"""
    for edge in edges:
        # 弹簧强度 = 证据数量（归一化）
        edge.spring_strength = min(1.0, edge.evidence_count / 10.0)

    # 使用 D3.js force simulation
    simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(edges).strength(lambda e: e.spring_strength))
        .force("charge", d3.forceManyBody().strength(-100))
        .force("center", d3.forceCenter(width / 2, height / 2))

    return simulation
```

---

### 7.4 交互层

**必需交互**：
- [x] Hover 悬停显示详情
- [x] Click 点击跳转/展开
- [x] Zoom 缩放（0.3x - 3.0x）
- [x] Pan 平移（无限画布）
- [x] Filter 过滤（证据/类型/盲区）

---

## 8. 验收清单（简化版）

### 8.1 视觉验收

- [ ] 节点颜色反映证据来源（3=绿，2=蓝，1=橙，0=红）
- [ ] 节点大小反映重要性
- [ ] 盲区节点有红色虚线边框
- [ ] 边粗细反映证据数量
- [ ] 边颜色反映证据类型多样性
- [ ] 推测边用灰色虚线

### 8.2 功能验收

- [ ] 悬停显示详情
- [ ] 点击跳转到 Explain
- [ ] 支持缩放和平移
- [ ] 过滤器工作正常
- [ ] 显示图例
- [ ] 显示子图元数据（覆盖度、缺失连接数）

### 8.3 性能验收

- [ ] 生成子图 < 5 秒（50 节点）
- [ ] 渲染 < 1 秒
- [ ] 交互响应 < 100ms
- [ ] 内存占用 < 100MB（100 节点）

---

## 9. 常用代码片段

### 9.1 节点视觉编码

```python
def encode_node_visual(node: SubgraphNode) -> NodeVisual:
    return NodeVisual(
        fill_color=get_node_color(node),
        size=get_node_size(node),
        border_color=get_node_border_color(node),
        border_width=get_node_border_width(node),
        border_style=get_node_border_style(node),
        shape=get_node_shape(node),
        label=get_node_label(node)
    )
```

### 9.2 边视觉编码

```python
def encode_edge_visual(edge: SubgraphEdge) -> EdgeVisual:
    return EdgeVisual(
        width=get_edge_width(edge),
        color=get_edge_color(edge),
        style=get_edge_style(edge),
        opacity=get_edge_opacity(edge),
        label=get_edge_label(edge),
        arrow=get_edge_arrow(edge)
    )
```

### 9.3 检测缺失连接

```python
def detect_missing_connections(subgraph: Subgraph) -> List[MissingConnection]:
    missing = []

    # 场景 1: 代码依赖但无文档
    missing.extend(detect_code_without_doc(subgraph))

    # 场景 2: 同 capability 但无连接
    missing.extend(detect_isolated_in_capability(subgraph))

    # 场景 3: Blind Spot 导致
    missing.extend(detect_blind_spot_gaps(subgraph))

    return missing
```

---

## 10. 调试清单

### 10.1 视觉问题

| 问题 | 检查项 | 解决方法 |
|------|--------|---------|
| 节点颜色错误 | `coverage_sources` 字段 | 检查是否正确加载证据来源 |
| 边太细 | `evidence_count` 字段 | 检查是否正确计算证据数量 |
| 盲区不醒目 | `is_blind_spot` 字段 | 检查是否正确标记盲区 |
| 推测边看起来像确认边 | `status` 字段 | 检查是否设置为 "suspected" |

### 10.2 性能问题

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 生成慢 | 全图遍历 | 使用索引查询 |
| 渲染慢 | 节点过多 | 限制 k_hop 深度 |
| 交互卡顿 | 未防抖 | 添加 debounce |
| 内存泄漏 | DOM 未清理 | 切换前 remove() |

### 10.3 数据问题

| 问题 | 检查项 | 解决方法 |
|------|--------|---------|
| 证据链丢失 | `edge.evidence_list` | 查询时 JOIN evidence 表 |
| 覆盖度计算错误 | `coverage_sources` | 检查 SQL 聚合逻辑 |
| 缺失连接未检测 | `detect_missing_connections()` | 运行检测算法 |

---

## 11. 快速上手示例

### 11.1 生成子图

```python
from agentos.core.brain.service import query_subgraph

# 生成 2-hop 子图
result = query_subgraph(
    db_path="./brainos.db",
    seed="file:agentos/core/task/manager.py",
    k_hop=2
)

subgraph = result.result
print(f"Nodes: {len(subgraph['nodes'])}")
print(f"Edges: {len(subgraph['edges'])}")
```

### 11.2 编码视觉

```python
from agentos.core.brain.visualization import encode_subgraph_visual

# 应用视觉编码
visual_subgraph = encode_subgraph_visual(subgraph)

# 输出为 JSON（供前端渲染）
import json
with open("subgraph.json", "w") as f:
    json.dump(visual_subgraph, f, indent=2)
```

### 11.3 渲染子图（前端）

```javascript
// 使用 D3.js 渲染
import * as d3 from 'd3';

fetch('/api/brain/subgraph?seed=file:manager.py&k_hop=2')
  .then(res => res.json())
  .then(data => {
    renderSubgraph('#subgraph', data);
  });

function renderSubgraph(selector, data) {
  const svg = d3.select(selector).append('svg');

  // 渲染节点
  svg.selectAll('circle')
    .data(data.nodes)
    .enter().append('circle')
    .attr('r', d => d.visual.size)
    .attr('fill', d => d.visual.fill_color)
    .attr('stroke', d => d.visual.border_color)
    .attr('stroke-width', d => d.visual.border_width);

  // 渲染边
  svg.selectAll('line')
    .data(data.edges)
    .enter().append('line')
    .attr('stroke', d => d.visual.color)
    .attr('stroke-width', d => d.visual.width)
    .attr('opacity', d => d.visual.opacity);
}
```

---

## 12. 参考资料

- **完整文档**: [P2_COGNITIVE_MODEL_DEFINITION.md](/Users/pangge/PycharmProjects/AgentOS/P2_COGNITIVE_MODEL_DEFINITION.md)
- **ADR 文档**: [ADR_P2_SUBGRAPH_VISUAL_SEMANTICS.md](/Users/pangge/PycharmProjects/AgentOS/docs/adr/ADR_P2_SUBGRAPH_VISUAL_SEMANTICS.md)
- **实现代码**: `agentos/core/brain/service/query_subgraph.py`
- **前端组件**: `agentos/webui/static/js/views/SubgraphView.js`（待实现）

---

**文档状态**: ✅ Complete
**字数统计**: ~2,500 字
**用途**: 实现时的快速参考
**最后更新**: 2026-01-30
