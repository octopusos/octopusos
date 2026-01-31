# P2-2: 子图查询引擎快速开始

**Version**: 1.0.0
**Date**: 2026-01-30

---

## 概述

本文档提供 P2-2 子图查询引擎的快速上手指南,包括安装、基本用法、常见场景和常见问题解答。

**预计阅读时间**: 10 分钟

---

## 目录

1. [安装和导入](#1-安装和导入)
2. [基本用法](#2-基本用法)
3. [常见场景](#3-常见场景)
4. [常见问题解答](#4-常见问题解答)

---

## 1. 安装和导入

### 1.1 前置条件

- Python 3.10+
- AgentOS 已安装
- BrainOS 数据库已初始化（运行 `agentos brain index`）

### 1.2 导入模块

```python
from agentos.core.brain.store import SQLiteStore
from agentos.core.brain.service.subgraph import query_subgraph
```

### 1.3 验证安装

```python
# 测试导入
from agentos.core.brain.service.subgraph import (
    query_subgraph,
    SubgraphNode,
    SubgraphEdge,
    SubgraphResult
)

print("✅ P2-2 installed successfully")
```

---

## 2. 基本用法

### 2.1 Hello World 示例

```python
from agentos.core.brain.store import SQLiteStore
from agentos.core.brain.service.subgraph import query_subgraph

# 1. 连接数据库
store = SQLiteStore("./store/brain.db")
store.connect()

# 2. 查询子图
result = query_subgraph(
    store,
    seed="file:manager.py",
    k_hop=2
)

# 3. 检查结果
if result.ok:
    print(f"✅ Success!")
    print(f"  Nodes: {len(result.data['nodes'])}")
    print(f"  Edges: {len(result.data['edges'])}")
    print(f"  Coverage: {result.data['metadata']['coverage_percentage']*100:.1f}%")
else:
    print(f"❌ Error: {result.error}")

# 4. 关闭连接
store.close()
```

**输出**:
```
✅ Success!
  Nodes: 15
  Edges: 23
  Coverage: 78.3%
```

### 2.2 遍历节点

```python
result = query_subgraph(store, "file:manager.py", k_hop=2)

if result.ok:
    for node in result.data['nodes']:
        print(f"📄 {node['entity_name']}")
        print(f"   Evidence: {node['evidence_count']}")
        print(f"   Sources: {', '.join(node['coverage_sources'])}")
        print(f"   Blind spot: {'Yes' if node['is_blind_spot'] else 'No'}")
        print()
```

**输出**:
```
📄 manager.py
   Evidence: 12
   Sources: git, doc, code
   Blind spot: No

📄 models.py
   Evidence: 8
   Sources: git, code
   Blind spot: No

📄 governance.py
   Evidence: 3
   Sources: git
   Blind spot: Yes
```

### 2.3 遍历边

```python
result = query_subgraph(store, "file:manager.py", k_hop=2)

if result.ok:
    for edge in result.data['edges']:
        src = next(n for n in result.data['nodes'] if n['id'] == edge['source_id'])
        dst = next(n for n in result.data['nodes'] if n['id'] == edge['target_id'])

        print(f"🔗 {src['entity_name']} --{edge['edge_type']}--> {dst['entity_name']}")
        print(f"   Evidence: {edge['evidence_count']}")
        print(f"   Confidence: {edge['confidence']:.2f}")
        print()
```

**输出**:
```
🔗 manager.py --depends_on--> models.py
   Evidence: 5
   Confidence: 0.85

🔗 manager.py --depends_on--> config.py
   Evidence: 1
   Confidence: 0.40
```

---

## 3. 常见场景

### 3.1 场景 1: 查找盲区节点

```python
result = query_subgraph(store, "file:manager.py", k_hop=2)

if result.ok:
    blind_spots = [
        n for n in result.data['nodes']
        if n['is_blind_spot']
    ]

    print(f"⚠️  Found {len(blind_spots)} blind spot(s):\n")

    for node in blind_spots:
        print(f"📄 {node['entity_name']}")
        print(f"   Type: {node['blind_spot_type']}")
        print(f"   Severity: {node['blind_spot_severity']:.2f}")
        print(f"   Reason: {node['blind_spot_reason']}")
        print(f"   Suggested action: Add documentation explaining this file's purpose")
        print()
```

**输出**:
```
⚠️  Found 2 blind spot(s):

📄 governance.py
   Type: high_fan_in_undocumented
   Severity: 0.75
   Reason: Critical file with 15 dependents but no documentation
   Suggested action: Add documentation explaining this file's purpose

📄 api_handler.py
   Type: trace_discontinuity
   Severity: 0.50
   Reason: Active file (5 commits) with no documented evolution
   Suggested action: Add documentation explaining this file's purpose
```

### 3.2 场景 2: 检查缺失连接

```python
result = query_subgraph(store, "file:manager.py", k_hop=2)

if result.ok:
    metadata = result.data['metadata']

    print(f"🔍 Missing Connections Analysis:")
    print(f"   Total: {metadata['missing_connections_count']}")
    print()

    if metadata['missing_connections_count'] > 0:
        print("   Coverage gaps detected:")
        for gap in metadata['coverage_gaps']:
            print(f"   - {gap['type']}: {gap['description']}")
```

**输出**:
```
🔍 Missing Connections Analysis:
   Total: 4

   Coverage gaps detected:
   - missing_doc_coverage: Code depends on config.py but no doc explains this relationship
   - missing_documentation_edge: critical.py has 8 dependents but no documentation
   - missing_doc_coverage: Code depends on utils.py but no doc explains this relationship
   - missing_documentation_edge: api.py has 6 dependents but no documentation
```

### 3.3 场景 3: 可视化准备（导出 JSON）

```python
import json

result = query_subgraph(store, "file:manager.py", k_hop=2)

if result.ok:
    # 导出为 JSON（供前端 D3.js 使用）
    with open("subgraph.json", "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    print("✅ Exported to subgraph.json")
    print(f"   Nodes: {len(result.data['nodes'])}")
    print(f"   Edges: {len(result.data['edges'])}")
```

**生成的 JSON 示例**:
```json
{
  "ok": true,
  "data": {
    "nodes": [
      {
        "id": "n123",
        "entity_name": "manager.py",
        "visual": {
          "color": "#00C853",
          "size": 45,
          "label": "manager.py\n✅ 85% | 12 evidence"
        }
      }
    ],
    "edges": [
      {
        "id": "e456",
        "source_id": "n123",
        "target_id": "n124",
        "visual": {
          "width": 3,
          "color": "#4A90E2",
          "style": "solid"
        }
      }
    ]
  }
}
```

### 3.4 场景 4: 过滤弱边

```python
result = query_subgraph(store, "file:manager.py", k_hop=2, min_evidence=3)

if result.ok:
    print("🔍 Filtering edges with min_evidence=3")
    print(f"   Total edges: {len(result.data['edges'])}")

    weak_edges = [e for e in result.data['edges'] if e['is_weak']]
    print(f"   Weak edges: {len(weak_edges)}")

    # 只保留强边
    strong_edges = [e for e in result.data['edges'] if not e['is_weak']]
    print(f"   Strong edges: {len(strong_edges)}")
```

### 3.5 场景 5: 多次查询（比较不同种子）

```python
seeds = ["file:manager.py", "file:api.py", "file:config.py"]

for seed in seeds:
    result = query_subgraph(store, seed, k_hop=1)

    if result.ok:
        meta = result.data['metadata']
        print(f"📊 {seed}:")
        print(f"   Nodes: {meta['total_nodes']}")
        print(f"   Coverage: {meta['coverage_percentage']*100:.0f}%")
        print(f"   Blind spots: {meta['blind_spot_count']}")
        print()
```

**输出**:
```
📊 file:manager.py:
   Nodes: 8
   Coverage: 87%
   Blind spots: 0

📊 file:api.py:
   Nodes: 12
   Coverage: 65%
   Blind spots: 2

📊 file:config.py:
   Nodes: 5
   Coverage: 100%
   Blind spots: 0
```

---

## 4. 常见问题解答

### Q1: 如何知道哪些实体可以作为种子？

**A1**: 使用 `autocomplete` 服务查询:

```python
from agentos.core.brain.service.autocomplete import autocomplete_suggest

# 查询文件实体
suggestions = autocomplete_suggest(store, query="manager", entity_type="file")

for s in suggestions.suggestions:
    print(f"- {s.entity_key} (safety: {s.safety.value})")
```

### Q2: 为什么查询结果是空的？

**A2**: 可能的原因:

1. **种子不存在**: 检查种子格式和键值
   ```python
   if not result.ok and "not found" in result.error:
       print("Seed entity does not exist")
   ```

2. **k-hop 太小**: 增加 k-hop 值
   ```python
   result = query_subgraph(store, seed, k_hop=3)  # 尝试 3 跳
   ```

3. **min_evidence 太高**: 降低最小证据数
   ```python
   result = query_subgraph(store, seed, k_hop=2, min_evidence=1)
   ```

### Q3: 如何提高查询性能？

**A3**: 性能优化建议:

1. **限制 k-hop**: 使用 1-2 跳（而非 3-4 跳）
2. **使用索引**: 确保数据库有正确的索引
3. **增加 min_evidence**: 过滤掉弱边
4. **缓存结果**: 对于相同的种子,缓存查询结果

```python
# 性能优化示例
result = query_subgraph(
    store,
    seed="file:manager.py",
    k_hop=2,           # 限制跳数
    min_evidence=2     # 过滤弱边
)
```

### Q4: 盲区节点是什么意思？

**A4**: 盲区节点是 BrainOS "知道自己不知道"的节点:

- **高扇入无文档**: 很多文件依赖它,但没有文档解释
- **能力无实现**: 声明了能力,但没有实现文件
- **轨迹不连续**: 有 Git 历史,但没有文档记录演变

```python
# 检查盲区类型
for node in blind_spot_nodes:
    if node['blind_spot_type'] == 'high_fan_in_undocumented':
        print(f"⚠️ {node['entity_name']} needs documentation!")
```

### Q5: 如何解读视觉编码？

**A5**: 视觉编码规则:

**节点颜色**:
- 🟢 绿色: 强证据（3 种来源）
- 🔵 蓝色: 中等证据（2 种来源）
- 🟠 橙色: 薄弱证据（1 种来源）
- 🔴 红色: 无证据（违规！）

**节点边框**:
- 实线: 正常节点
- 虚线: 盲区节点（红色/橙色）

**边宽度**:
- 细线 (1px): 单一证据
- 中线 (2px): 2-4 条证据
- 粗线 (3px): 5-9 条证据
- 最粗 (4px): 10+ 条证据

**边颜色**:
- 🟢 绿色: 多类型证据（Git+Doc+Code）
- 🔵 蓝色: 双类型证据
- ⚪ 浅灰: 单类型证据
- ⚫ 灰色: 推测边

### Q6: 如何处理大型子图？

**A6**: 大型子图优化策略:

```python
# 策略 1: 限制跳数
result = query_subgraph(store, seed, k_hop=1)  # 只查询 1 跳

# 策略 2: 提高证据阈值
result = query_subgraph(store, seed, k_hop=2, min_evidence=3)

# 策略 3: 分批查询
result1 = query_subgraph(store, "file:A.py", k_hop=1)
result2 = query_subgraph(store, "file:B.py", k_hop=1)
# 合并结果（自行实现）
```

### Q7: 如何与前端集成？

**A7**: 前端集成示例（D3.js）:

```javascript
// 1. 从后端获取子图
fetch('/api/brain/subgraph?seed=file:manager.py&k_hop=2')
  .then(res => res.json())
  .then(data => {
    const nodes = data.data.nodes;
    const edges = data.data.edges;

    // 2. 使用 D3.js 渲染
    renderSubgraph(nodes, edges);
  });

function renderSubgraph(nodes, edges) {
  // 渲染节点
  svg.selectAll('circle')
    .data(nodes)
    .enter().append('circle')
    .attr('r', d => d.visual.size)
    .attr('fill', d => d.visual.color)
    .attr('stroke', d => d.visual.border_color)
    .attr('stroke-width', d => d.visual.border_width);

  // 渲染边
  svg.selectAll('line')
    .data(edges)
    .enter().append('line')
    .attr('stroke', d => d.visual.color)
    .attr('stroke-width', d => d.visual.width)
    .attr('opacity', d => d.visual.opacity);
}
```

### Q8: 错误"Seed node not found"怎么办？

**A8**: 调试步骤:

```python
# 1. 检查种子格式
seed = "file:manager.py"  # 正确
# seed = "manager.py"     # ❌ 错误（缺少类型前缀）

# 2. 查询实体是否存在
cursor = store.conn.cursor()
cursor.execute("SELECT * FROM entities WHERE key LIKE ?", (f"%{seed}%",))
results = cursor.fetchall()

if not results:
    print(f"Entity not found: {seed}")
    print("Available entities:")
    cursor.execute("SELECT key FROM entities LIMIT 10")
    for row in cursor.fetchall():
        print(f"  - {row[0]}")
```

---

## 总结

P2-2 子图查询引擎提供了强大的认知结构提取功能:

✅ **易于使用**: 3 行代码即可查询子图
✅ **认知完整**: 证据、盲区、缺失连接全覆盖
✅ **视觉友好**: 自动生成视觉编码
✅ **性能优秀**: 2-hop 查询 < 500ms

**下一步**:
- 探索 [API 参考](./P2_TASK2_API_REFERENCE.md) 了解详细参数
- 阅读 [实现报告](./P2_TASK2_IMPLEMENTATION_REPORT.md) 了解内部机制
- 查看 [P2-1 定义](./P2_COGNITIVE_MODEL_DEFINITION.md) 了解认知模型

**文档状态**: ✅ Complete
**字数统计**: ~1,800 字
**最后更新**: 2026-01-30
