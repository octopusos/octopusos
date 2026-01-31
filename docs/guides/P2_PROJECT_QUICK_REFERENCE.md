# P2: 子图可视化 - 快速参考

**Version**: 1.0.0
**Date**: 2026-01-30
**Status**: Ready for Production (after Red Line 3 fix)

---

## 一、核心概念速查

### P2 的本质

P2 **不是**"画知识图谱"，而是**可视化认知边界**。

| 维度 | 传统知识图谱 | P2 子图可视化 |
|------|------------|-------------|
| 节点颜色 | 按类型（文件=蓝，函数=绿） | 按证据来源（3源=绿，1源=橙） |
| 边粗细 | 统一 | 按证据数量（1px~4px） |
| 盲区 | 不显示 | 红色虚线边框 |
| 完整性 | 隐藏 | 透明显示覆盖度 |

**核心价值**：让用户一眼看出"哪里懂、哪里不懂、哪里缺失"

---

## 二、三条红线速查

| 红线 | 定义 | 验收方法 |
|------|------|---------|
| ❌ 无证据边 | 所有边必须有 >= 1 evidence | `assert edge.evidence_count >= 1` |
| ❌ 隐藏盲区 | 盲区必须红色虚线边框 | `assert border_color == "#FF0000"` |
| ❌ 完整幻觉 | 必须显示缺失连接数 | `assert "missing_connections_count" in metadata` |

---

## 三、视觉编码速查表

### 3.1 节点颜色（证据来源多样性）

| 来源数 | 颜色 | Hex | 语义 |
|--------|------|-----|------|
| 3 种 | 绿色 | `#00C853` | 强证据（Git+Doc+Code） |
| 2 种 | 蓝色 | `#4A90E2` | 中等证据 |
| 1 种 | 橙色 | `#FFA000` | 薄弱证据 |
| 0 种 | 红色 | `#FF0000` | 无证据（违反红线） |

### 3.2 节点大小（重要性）

```python
size = 20 + min(20, evidence_count * 2) + min(15, in_degree * 3) + (10 if is_seed else 0)
```

| 类型 | 半径（px） | 示例 |
|------|-----------|------|
| 最小 | 20 | 叶子节点（1 证据，入度 0） |
| 中等 | 40 | 普通节点（5 证据，入度 2） |
| 最大 | 65 | 核心节点或种子节点 |

### 3.3 节点边框（盲区标注）

| 盲区严重度 | 边框颜色 | 边框宽度 | 边框样式 |
|-----------|---------|---------|---------|
| 高 (≥0.7) | `#FF0000` 红色 | 3px | dashed |
| 中 (0.4-0.69) | `#FF6600` 橙色 | 2px | dashed |
| 低 (<0.4) | `#FFB300` 黄色 | 2px | dotted |
| 非盲区 | 同填充色 | 1px | solid |

### 3.4 边粗细（证据数量）

| 证据数量 | 宽度（px） | 语义 |
|---------|-----------|------|
| 0（推测） | 1 | 推测边 |
| 1 | 1 | 单一证据 |
| 2-4 | 2 | 中等证据 |
| 5-9 | 3 | 强证据 |
| 10+ | 4 | 超强证据 |

### 3.5 边颜色（证据类型多样性）

| 类型数 | 颜色 | Hex | 语义 |
|--------|------|-----|------|
| 3 种 | 绿色 | `#00C853` | 多类型（Git+Doc+Code） |
| 2 种 | 蓝色 | `#4A90E2` | 双类型 |
| 1 种 | 浅灰 | `#B0B0B0` | 单类型 |
| 0 种（推测） | 灰色 | `#CCCCCC` | 推测边 |

### 3.6 边样式（关系类型）

| 关系类型 | 样式 | 语义 |
|---------|------|------|
| depends_on | solid | 依赖关系 |
| references | solid | 引用关系 |
| mentions | dotted | 提及关系 |
| suspected | dashed | 推测关系 |

---

## 四、API 端点速查

### 4.1 查询子图

**Endpoint**: `GET /api/brain/subgraph`

**参数**:
```
seed: str           # 种子实体（如 "file:manager.py"）
k_hop: int          # 跳数（1-3，默认 2）
min_evidence: int   # 最小证据数（1-10，默认 1）
include_suspected: bool  # 包含推测边（默认 False）
```

**示例**:
```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2&min_evidence=1"
```

**响应格式**:
```json
{
  "ok": true,
  "data": {
    "nodes": [...],
    "edges": [...],
    "metadata": {
      "seed_entity": "file:manager.py",
      "k_hop": 2,
      "total_nodes": 266,
      "total_edges": 292,
      "coverage_percentage": 0.85,
      "evidence_density": 5.2,
      "blind_spot_count": 2,
      "missing_connections_count": 0
    }
  },
  "error": null,
  "cached": false
}
```

---

## 五、故障排查速查

### 5.1 常见错误

| 错误 | 原因 | 解决方法 |
|------|------|---------|
| `Seed node not found` | 实体未索引 | 运行 `/brain build` 重建索引 |
| `Invalid seed format` | seed 格式错误 | 使用 `type:key` 格式（如 `file:manager.py`） |
| `BrainOS index not found` | 索引不存在 | 运行 `/brain build` |
| `Query timeout` | 图太大 | 减小 k_hop 或增加 min_evidence |

### 5.2 性能问题

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 2-hop 查询 > 1 秒 | 数据库未优化 | 检查索引，运行 `ANALYZE` |
| 前端渲染卡顿 | 节点过多（> 500） | 限制 k_hop <= 2 |
| 缓存命中率低 | TTL 太短 | 增加缓存 TTL（默认 15 分钟） |

### 5.3 视觉问题

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 节点颜色错误 | coverage_sources 字段缺失 | 检查 BFS 查询是否正确 |
| 边太细 | evidence_count 字段错误 | 检查证据计算逻辑 |
| 盲区不醒目 | is_blind_spot 字段缺失 | 检查盲区检测逻辑 |
| 推测边看起来像确认边 | status 字段错误 | 检查 status = "suspected" |

---

## 六、快速开始（3 分钟）

### Step 1: 构建 BrainOS 索引

```bash
python -m agentos.cli.webui
```

在 WebUI 中运行:
```
/brain build
```

等待索引构建完成（约 30 秒 - 2 分钟）

### Step 2: 访问子图视图

打开浏览器:
```
http://localhost:5000/#/subgraph
```

### Step 3: 查询子图

在输入框输入:
```
file:agentos/core/task/manager.py
```

点击"Query"按钮

### Step 4: 查看结果

- 观察节点颜色（绿/蓝/橙）
- 观察边粗细（粗/细）
- 查看盲区节点（红色虚线边框）
- 查看元数据面板（覆盖度、缺失连接数）

---

## 七、代码示例速查

### 7.1 后端：查询子图

```python
from agentos.core.brain.store import SQLiteStore
from agentos.core.brain.service.subgraph import query_subgraph

# 1. 连接数据库
store = SQLiteStore(".brainos/v0.1_mvp.db")
store.connect()

# 2. 查询子图
result = query_subgraph(
    store,
    seed="file:manager.py",
    k_hop=2,
    min_evidence=1
)

# 3. 检查结果
if result.ok:
    nodes = result.data["nodes"]
    edges = result.data["edges"]
    metadata = result.data["metadata"]

    print(f"Nodes: {len(nodes)}")
    print(f"Edges: {len(edges)}")
    print(f"Coverage: {metadata['coverage_percentage']:.1%}")
    print(f"Blind spots: {metadata['blind_spot_count']}")
else:
    print(f"Error: {result.error}")

# 4. 关闭连接
store.close()
```

### 7.2 前端：渲染子图

```javascript
// 1. 加载子图数据
async function loadSubgraph(seed, kHop = 2) {
    const url = `/api/brain/subgraph?seed=${encodeURIComponent(seed)}&k_hop=${kHop}`;
    const response = await fetch(url);
    const result = await response.json();

    if (!result.ok) {
        console.error(result.error);
        return;
    }

    // 2. 转换为 Cytoscape 格式
    const nodes = result.data.nodes.map(node => ({
        data: {
            id: node.id,
            label: node.entity_name,
            color: node.visual.color,
            size: node.visual.size,
            border_color: node.visual.border_color,
            border_width: node.visual.border_width,
            border_style: node.visual.border_style
        }
    }));

    const edges = result.data.edges.map(edge => ({
        data: {
            id: edge.id,
            source: edge.source_id,
            target: edge.target_id,
            width: edge.visual.width,
            color: edge.visual.color,
            style: edge.visual.style,
            opacity: edge.visual.opacity
        }
    }));

    // 3. 渲染
    cy.add([...nodes, ...edges]);
    cy.layout({ name: 'cose' }).run();
}

// 使用
loadSubgraph("file:manager.py", 2);
```

### 7.3 测试：验证三条红线

```python
def test_red_lines(brain_store):
    result = query_subgraph(brain_store, seed="file:manager.py", k_hop=2)

    # Red Line 1: 无证据边
    for edge in result.data["edges"]:
        if edge["status"] == "confirmed":
            assert edge["evidence_count"] >= 1

    # Red Line 2: 盲区可见
    blind_spot_nodes = [n for n in result.data["nodes"] if n["is_blind_spot"]]
    for node in blind_spot_nodes:
        assert node["visual"]["border_color"] in ["#FF0000", "#FF6600"]
        assert node["visual"]["border_width"] >= 2
        assert node["visual"]["border_style"] in ["dashed", "dotted"]

    # Red Line 3: 完整性透明
    metadata = result.data["metadata"]
    assert "coverage_percentage" in metadata
    assert "missing_connections_count" in metadata
```

---

## 八、常用命令速查

### 8.1 开发命令

```bash
# 启动 WebUI
python -m agentos.cli.webui

# 构建 BrainOS 索引
# (在 WebUI 中运行 /brain build)

# 运行单元测试
pytest tests/unit/core/brain/test_subgraph.py -v

# 运行集成测试
python test_p2_e2e_integration.py

# 运行特定测试
pytest tests/unit/core/brain/test_subgraph.py::test_node_visual_encoding -v
```

### 8.2 调试命令

```bash
# 查看 BrainOS 统计
curl "http://localhost:5000/api/brain/stats"

# 查询子图（调试）
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=1" | jq .

# 查看覆盖度
curl "http://localhost:5000/api/brain/coverage" | jq .

# 查看盲区
curl "http://localhost:5000/api/brain/blind-spots" | jq .
```

### 8.3 性能测试命令

```bash
# 测试 API 响应时间
time curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2" > /dev/null

# 压力测试（需要 Apache Bench）
ab -n 100 -c 10 "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2"

# 监控内存
watch -n 1 "ps aux | grep python | grep webui"
```

---

## 九、关键文件位置速查

| 文件 | 路径 | 说明 |
|------|------|------|
| **后端查询引擎** | `agentos/core/brain/service/subgraph.py` | 1,172 行 |
| **API 端点** | `agentos/webui/api/brain.py` | 1,380 行 |
| **前端组件** | `agentos/webui/static/js/views/SubgraphView.js` | 850 行 |
| **单元测试** | `tests/unit/core/brain/test_subgraph.py` | 19 tests |
| **集成测试** | `test_p2_e2e_integration.py` | 7 tests |
| **认知模型定义** | `P2_COGNITIVE_MODEL_DEFINITION.md` | 10,500 字 |
| **快速参考（本文档）** | `P2_PROJECT_QUICK_REFERENCE.md` | 2,000 字 |

---

## 十、联系方式和支持

### 10.1 问题报告

如果遇到问题，请提供以下信息:
1. BrainOS 版本（运行 `/brain stats`）
2. 查询参数（seed, k_hop, min_evidence）
3. 错误消息（完整堆栈跟踪）
4. 浏览器和版本（Chrome/Firefox/Safari）

### 10.2 功能请求

功能请求请包含:
1. 用例描述（"作为用户，我想..."）
2. 当前行为（"现在..."）
3. 期望行为（"我希望..."）
4. 优先级（低/中/高）

### 10.3 贡献指南

参与贡献请参考:
- `P2_TASK4_DEVELOPER_GUIDE.md`（前端开发指南）
- `P2_TASK2_API_REFERENCE.md`（后端 API 参考）

---

**文档状态**: ✅ Complete
**字数统计**: ~2,500 字
**最后更新**: 2026-01-30
**下一步**: 查看 `P2_PROJECT_DEMO_GUIDE.md`
