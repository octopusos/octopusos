# P2-2: 子图查询引擎 API 参考

**Version**: 1.0.0
**Date**: 2026-01-30
**Module**: `agentos.core.brain.service.subgraph`

---

## 概述

本文档提供 P2-2 子图查询引擎的完整 API 参考,包括函数签名、参数说明、返回值结构、错误码和使用示例。

---

## 目录

1. [核心函数](#1-核心函数)
2. [数据结构](#2-数据结构)
3. [视觉编码函数](#3-视觉编码函数)
4. [辅助函数](#4-辅助函数)
5. [错误处理](#5-错误处理)
6. [示例请求和响应](#6-示例请求和响应)

---

## 1. 核心函数

### 1.1 `query_subgraph()`

查询以种子实体为中心的 k-hop 子图。

#### 函数签名

```python
def query_subgraph(
    store: SQLiteStore,
    seed: str,
    k_hop: int = 2,
    include_suspected: bool = False,
    min_evidence: int = 1
) -> SubgraphResult
```

#### 参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `store` | `SQLiteStore` | 必需 | 已连接的 SQLiteStore 实例 |
| `seed` | `str` | 必需 | 种子实体键（格式: "type:key"） |
| `k_hop` | `int` | `2` | 跳数（1-3 推荐） |
| `include_suspected` | `bool` | `False` | 是否包含推测边（无证据边） |
| `min_evidence` | `int` | `1` | 最小证据数（Red Line 1） |

#### Seed 格式

种子实体键的格式为 `"type:key"`:

| 类型 | 示例 | 说明 |
|------|------|------|
| `file` | `"file:manager.py"` | 文件路径（相对或绝对） |
| `capability` | `"capability:api"` | 能力名称 |
| `term` | `"term:authentication"` | 术语 |
| `doc` | `"doc:ADR-001"` | 文档名称 |
| `commit` | `"commit:abc123"` | Git commit hash |

#### 返回值

返回 `SubgraphResult` 对象:

```python
@dataclass
class SubgraphResult:
    ok: bool                    # 查询是否成功
    data: Optional[Dict]        # 子图数据（见下文）
    error: Optional[str]        # 错误信息
    graph_version: str          # 图版本
    computed_at: str            # 计算时间（ISO 8601）
```

**成功时**（`ok=True`）:
```python
result.data = {
    "nodes": [...]         # List[Dict] - 节点列表
    "edges": [...]         # List[Dict] - 边列表
    "metadata": {...}      # Dict - 元数据
}
```

**失败时**（`ok=False`）:
```python
result.data = None
result.error = "Seed node not found: file:nonexistent.py"
```

#### 使用示例

```python
from agentos.core.brain.store import SQLiteStore
from agentos.core.brain.service.subgraph import query_subgraph

# 连接数据库
store = SQLiteStore("./brainos.db")
store.connect()

# 查询 2-hop 子图
result = query_subgraph(
    store,
    seed="file:manager.py",
    k_hop=2,
    min_evidence=1
)

if result.ok:
    print(f"Found {len(result.data['nodes'])} nodes")
    print(f"Coverage: {result.data['metadata']['coverage_percentage']*100:.1f}%")
else:
    print(f"Error: {result.error}")

store.close()
```

#### 错误场景

| 错误类型 | `ok` | `error` 内容 |
|---------|------|-------------|
| 种子不存在 | `False` | `"Seed node not found: {seed}"` |
| 数据库错误 | `False` | `"Database error: {details}"` |
| 内部错误 | `False` | `"{exception message}"` |

---

## 2. 数据结构

### 2.1 SubgraphNode

子图节点的完整结构。

#### 字段列表

```python
{
    "id": "n123",                           # str: 节点 ID
    "entity_type": "file",                  # str: 实体类型
    "entity_key": "file:manager.py",        # str: 实体键
    "entity_name": "manager.py",            # str: 显示名称
    "entity_id": 123,                       # int: 内部 DB ID

    # 证据属性
    "evidence_count": 12,                   # int: 总证据数
    "coverage_sources": ["git", "doc"],     # List[str]: 证据来源
    "evidence_density": 0.85,               # float: 证据密度 (0-1)

    # 盲区属性
    "is_blind_spot": False,                 # bool: 是否为盲区
    "blind_spot_severity": None,            # float|None: 严重度 (0-1)
    "blind_spot_type": None,                # str|None: 盲区类型
    "blind_spot_reason": None,              # str|None: 盲区原因

    # 拓扑属性
    "in_degree": 8,                         # int: 入度
    "out_degree": 3,                        # int: 出度
    "distance_from_seed": 1,                # int: 距离种子节点的跳数

    # 视觉编码
    "visual": {
        "color": "#00C853",                 # str: 填充颜色（十六进制）
        "size": 45,                         # int: 半径（像素）
        "border_color": "#00C853",          # str: 边框颜色
        "border_width": 1,                  # int: 边框宽度（像素）
        "border_style": "solid",            # str: 边框样式
        "shape": "circle",                  # str: 形状
        "label": "manager.py\n✅ 85% | 12 evidence",  # str: 标签文本
        "tooltip": "Entity: file:manager.py\n..."    # str: 悬停提示
    }
}
```

#### 字段说明

**基础属性**:
- `id`: 节点唯一标识符（格式: `"nXXX"`）
- `entity_type`: 实体类型（`"file"` / `"capability"` / `"term"` / `"doc"` / `"commit"`）
- `entity_key`: 实体唯一键（格式: `"type:key"`）
- `entity_name`: 显示名称（用户友好的名称）
- `entity_id`: 数据库内部 ID

**证据属性** (核心):
- `evidence_count`: 该节点相关的总证据数（所有连接的边的证据总和）
- `coverage_sources`: 证据来源列表（`["git", "doc", "code"]`的子集）
- `evidence_density`: 证据密度（归一化到 0-1）

**盲区属性** (核心):
- `is_blind_spot`: 是否为认知盲区
- `blind_spot_severity`: 盲区严重度（`0.0` = 低风险, `1.0` = 高风险）
- `blind_spot_type`: 盲区类型（`"high_fan_in_undocumented"` / `"capability_no_implementation"` / `"trace_discontinuity"`）
- `blind_spot_reason`: 盲区原因的人类可读描述

**拓扑属性**:
- `in_degree`: 指向该节点的边数（子图内）
- `out_degree`: 从该节点出发的边数（子图内）
- `distance_from_seed`: 距离种子节点的最短路径长度（跳数）

**视觉编码**:
- `visual`: 视觉属性对象（见 NodeVisual 详解）

### 2.2 SubgraphEdge

子图边的完整结构。

#### 字段列表

```python
{
    "id": "e456",                           # str: 边 ID
    "source_id": "n123",                    # str: 源节点 ID
    "target_id": "n124",                    # str: 目标节点 ID
    "edge_type": "depends_on",              # str: 边类型
    "edge_db_id": 456,                      # int: 内部 DB ID

    # 证据属性
    "evidence_count": 5,                    # int: 证据数量
    "evidence_types": ["git", "code"],      # List[str]: 证据类型
    "evidence_list": [                      # List[Dict]: 完整证据列表
        {
            "id": 789,
            "source_type": "git",
            "source_ref": "commit:abc123",
            "span": {"line": 10},
            "attrs": {}
        },
        ...
    ],
    "confidence": 0.85,                     # float: 置信度 (0-1)

    # 状态属性
    "status": "confirmed",                  # str: 状态
    "is_weak": False,                       # bool: 是否为弱边
    "is_suspected": False,                  # bool: 是否为推测边

    # 视觉编码
    "visual": {
        "width": 3,                         # int: 线宽（像素）
        "color": "#4A90E2",                 # str: 颜色
        "style": "solid",                   # str: 样式
        "opacity": 0.7,                     # float: 不透明度 (0-1)
        "label": "depends_on | 5 (git+code)",  # str: 标签
        "tooltip": "Edge: depends_on\n..."     # str: 悬停提示
    }
}
```

#### 字段说明

**基础属性**:
- `id`: 边唯一标识符（格式: `"eXXX"`）
- `source_id`: 源节点 ID（指向 nodes 列表）
- `target_id`: 目标节点 ID（指向 nodes 列表）
- `edge_type`: 边类型（`"depends_on"` / `"references"` / `"mentions"` / `"implements"` / `"modifies"`）
- `edge_db_id`: 数据库内部 ID

**证据属性** (核心):
- `evidence_count`: 这条边的证据数量
- `evidence_types`: 证据类型列表（`["git", "doc", "code"]`的子集）
- `evidence_list`: 完整的证据记录列表
- `confidence`: 置信度分数（基于证据数量和类型计算）

**状态属性**:
- `status`: 边的状态（`"confirmed"` = 有证据支撑, `"suspected"` = 推测的）
- `is_weak`: 是否为弱边（`evidence_count < 3`）
- `is_suspected`: 是否为推测边（`evidence_count == 0`）

**视觉编码**:
- `visual`: 视觉属性对象（见 EdgeVisual 详解）

### 2.3 SubgraphMetadata

子图元数据和统计信息。

#### 字段列表

```python
{
    "seed_entity": "file:manager.py",       # str: 种子实体键
    "k_hop": 2,                             # int: 跳数
    "total_nodes": 15,                      # int: 节点总数
    "total_edges": 23,                      # int: 边总数
    "confirmed_edges": 21,                  # int: 确认边数量
    "suspected_edges": 2,                   # int: 推测边数量

    # 认知完整性指标
    "coverage_percentage": 0.78,            # float: 覆盖百分比 (0-1)
    "evidence_density": 2.45,               # float: 平均证据密度
    "blind_spot_count": 2,                  # int: 盲区节点数量
    "high_risk_blind_spot_count": 1,        # int: 高风险盲区数量

    # 空白区域
    "missing_connections_count": 4,         # int: 缺失连接数量
    "coverage_gaps": [                      # List[Dict]: 覆盖空白
        {
            "type": "missing_doc_coverage",
            "description": "Code depends on config.py but no doc explains this"
        },
        ...
    ]
}
```

#### 字段说明

**基础统计**:
- `seed_entity`: 种子实体键
- `k_hop`: 查询的跳数
- `total_nodes`: 子图中的节点总数
- `total_edges`: 子图中的边总数
- `confirmed_edges`: 有证据支撑的边数量
- `suspected_edges`: 推测边数量

**认知完整性指标** (核心):
- `coverage_percentage`: 有证据的节点占总节点的比例
- `evidence_density`: 每条边的平均证据数量
- `blind_spot_count`: 盲区节点总数
- `high_risk_blind_spot_count`: 高风险盲区数量（severity >= 0.7）

**空白区域** (核心):
- `missing_connections_count`: 检测到的缺失连接数量
- `coverage_gaps`: 覆盖空白详情列表

---

## 3. 视觉编码函数

### 3.1 `compute_node_visual()`

计算节点的视觉编码。

#### 函数签名

```python
def compute_node_visual(node: SubgraphNode) -> NodeVisual
```

#### 参数

| 参数 | 类型 | 描述 |
|------|------|------|
| `node` | `SubgraphNode` | 包含认知属性的节点对象 |

#### 返回值

返回 `NodeVisual` 对象:

```python
@dataclass
class NodeVisual:
    color: str             # 填充颜色（十六进制）
    size: int              # 半径（像素）
    border_color: str      # 边框颜色
    border_width: int      # 边框宽度（像素）
    border_style: str      # 边框样式
    shape: str             # 形状
    label: str             # 标签文本
    tooltip: str           # 悬停提示
```

#### 编码规则

**颜色规则** (基于 `coverage_sources`):
| 来源数量 | 颜色 | Hex Code |
|---------|------|----------|
| 3 种 | 绿色 | `#00C853` |
| 2 种 | 蓝色 | `#4A90E2` |
| 1 种 | 橙色 | `#FFA000` |
| 0 种 | 红色 | `#FF0000` |

**大小规则** (基于 `evidence_count` 和 `in_degree`):
```python
size = 20 + min(20, evidence_count * 2) + min(15, in_degree * 3) + (10 if is_seed else 0)
```
范围: 20px - 65px

**边框规则** (盲区标注):
| 盲区严重度 | 边框颜色 | 边框宽度 | 边框样式 |
|-----------|---------|---------|---------|
| >= 0.7 | `#FF0000` | 3px | `dashed` |
| 0.4-0.69 | `#FF6600` | 2px | `dashed` |
| < 0.4 | `#FFB300` | 2px | `dotted` |
| 非盲区 | 同填充色 | 1px | `solid` |

### 3.2 `compute_edge_visual()`

计算边的视觉编码。

#### 函数签名

```python
def compute_edge_visual(edge: SubgraphEdge) -> EdgeVisual
```

#### 参数

| 参数 | 类型 | 描述 |
|------|------|------|
| `edge` | `SubgraphEdge` | 包含认知属性的边对象 |

#### 返回值

返回 `EdgeVisual` 对象:

```python
@dataclass
class EdgeVisual:
    width: int             # 线宽（像素）
    color: str             # 颜色（十六进制）
    style: str             # 样式
    opacity: float         # 不透明度 (0-1)
    label: str             # 标签文本
    tooltip: str           # 悬停提示
```

#### 编码规则

**宽度规则** (基于 `evidence_count`):
| 证据数量 | 宽度 |
|---------|------|
| 0-1 | 1px |
| 2-4 | 2px |
| 5-9 | 3px |
| 10+ | 4px |

**颜色规则** (基于 `evidence_types` 多样性):
| 类型数量 | 颜色 | Hex Code |
|---------|------|----------|
| 3 种 | 绿色 | `#00C853` |
| 2 种 | 蓝色 | `#4A90E2` |
| 1 种 | 浅灰 | `#B0B0B0` |
| 0 种（推测） | 灰色 | `#CCCCCC` |

**透明度规则** (基于 `confidence`):
| 证据数量 | 透明度 |
|---------|--------|
| 0（推测） | 0.3 |
| 1 | 0.4 |
| 2-4 | 0.7 |
| 5+ | 1.0 |

---

## 4. 辅助函数

### 4.1 `find_seed_node()`

查找种子节点的内部 ID。

#### 函数签名

```python
def find_seed_node(cursor, seed: str) -> Optional[int]
```

### 4.2 `bfs_k_hop()`

执行 BFS k-hop 遍历。

#### 函数签名

```python
def bfs_k_hop(cursor, seed_id: int, k: int, min_evidence: int) -> Dict
```

### 4.3 `detect_missing_connections()`

检测缺失连接。

#### 函数签名

```python
def detect_missing_connections(cursor, nodes: List[SubgraphNode], edges: List[SubgraphEdge]) -> List[Dict]
```

---

## 5. 错误处理

### 5.1 错误码

| 错误类型 | `result.ok` | `result.error` 格式 |
|---------|------------|-------------------|
| 种子不存在 | `False` | `"Seed node not found: {seed}"` |
| 种子格式错误 | `False` | `"Invalid seed format (expected 'type:key'): {seed}"` |
| 数据库连接错误 | `False` | `"Database connection failed: {details}"` |
| 查询超时 | `False` | `"Query timeout after {seconds}s"` |
| 内部错误 | `False` | `"{exception message}"` |

### 5.2 错误处理示例

```python
result = query_subgraph(store, "invalid_format")

if not result.ok:
    if "not found" in result.error:
        print("Seed entity does not exist in the knowledge graph")
    elif "Invalid seed format" in result.error:
        print("Seed format should be 'type:key'")
    else:
        print(f"Unexpected error: {result.error}")
```

---

## 6. 示例请求和响应

### 6.1 成功查询示例

**请求**:
```python
query_subgraph(
    store,
    seed="file:manager.py",
    k_hop=2,
    min_evidence=1
)
```

**响应**:
```python
SubgraphResult(
    ok=True,
    data={
        "nodes": [
            {
                "id": "n123",
                "entity_type": "file",
                "entity_key": "file:manager.py",
                "entity_name": "manager.py",
                "evidence_count": 12,
                "coverage_sources": ["git", "doc", "code"],
                "is_blind_spot": False,
                "in_degree": 8,
                "out_degree": 3,
                "distance_from_seed": 0,
                "visual": {...}
            },
            ...
        ],
        "edges": [
            {
                "id": "e456",
                "source_id": "n123",
                "target_id": "n124",
                "edge_type": "depends_on",
                "evidence_count": 5,
                "confidence": 0.85,
                "status": "confirmed",
                "visual": {...}
            },
            ...
        ],
        "metadata": {
            "seed_entity": "file:manager.py",
            "k_hop": 2,
            "total_nodes": 15,
            "total_edges": 23,
            "coverage_percentage": 0.78,
            "blind_spot_count": 2,
            "missing_connections_count": 4
        }
    },
    error=None,
    graph_version="2026-01-30T10:30:00Z-abc123",
    computed_at="2026-01-30T10:35:42.123456Z"
)
```

### 6.2 种子不存在示例

**请求**:
```python
query_subgraph(
    store,
    seed="file:nonexistent.py",
    k_hop=2
)
```

**响应**:
```python
SubgraphResult(
    ok=False,
    data=None,
    error="Seed node not found: file:nonexistent.py",
    graph_version="unknown",
    computed_at="2026-01-30T10:35:42.123456Z"
)
```

---

## 总结

P2-2 API 提供了完整的子图查询功能,包括:
- ✅ 认知属性计算（证据、覆盖、盲区）
- ✅ 视觉编码生成（颜色、大小、边框、宽度、透明度）
- ✅ 空白区域检测（缺失连接）
- ✅ 完整的错误处理

**文档状态**: ✅ Complete
**字数统计**: ~2,500 字
**最后更新**: 2026-01-30
