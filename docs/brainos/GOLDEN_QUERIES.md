# BrainOS Golden Queries

## 概述

本文档定义 BrainOS v0.1 MVP 的 **10 条黄金查询（Golden Queries）**，用于验证 BrainOS 的核心能力。

每条查询基于 **AgentOS 仓库的真实场景**，确保 BrainOS 能够回答实际的推理问题。

## 查询分类

- **Why Query** (4 条): 追溯设计决策和实现原因
- **Impact Query** (3 条): 分析变更影响范围
- **Trace Query** (2 条): 追踪概念演进历史
- **Map Query** (1 条): 输出知识子图谱

## BrainOS v0.1 MVP 状态

**完成情况**: 10/10 PASS ✅ 🎉 **MVP COMPLETE!**

| Query ID | 类型 | 状态 | Milestone |
|---------|------|------|-----------|
| #1 | Why | ✅ PASS | M3-P0 (hotfix) |
| #2 | Impact | ✅ PASS | M2 |
| #3 | Trace | ✅ PASS | M2 |
| #4 | Subgraph | ✅ PASS | M2 |
| #5 | Impact | ✅ PASS | M2 |
| #6 | Trace | ✅ PASS | M2 |
| #7 | Why | ✅ PASS | M3-P0 (hotfix) |
| #8 | **Impact** | ✅ **PASS** | **M3-P1 (Code Extractor)** ← **NEW!** |
| #9 | Map | ✅ PASS | M2 |
| #10 | Why | ✅ PASS | M3-P0 (hotfix) |

**Achievement Unlocked**: 🏆 **All 10 Golden Queries Pass!**

**Milestones**:
- M2: Git + Doc Extractors → 6/10 PASS
- M3-P0: Why Query Hotfix → 9/10 PASS
- **M3-P1: Code Extractor → 10/10 PASS** ✅

## 验收标准

每条查询必须满足：
1. ✅ 返回结果（nodes + edges）
2. ✅ 包含证据链（evidence_refs）
3. ✅ 指定图谱版本（graph_version）
4. ✅ 满足最小数量要求（至少 N 条结果）
5. ✅ 结果按指定规则排序

---

## Golden Query 1: Why - Task Retry

### 问题
**"为什么 agentos/core/task/manager.py 要实现重试机制？"**

### 查询类型
`why_query`

### 输入（seed）
```python
seed = "agentos/core/task/manager.py"
```

### 期望输出

**节点类型：**
- Doc（ADR、设计文档）
- Commit（相关提交）

**边类型：**
- REFERENCES（Doc → File）
- MODIFIES（Commit → File）

**证据要求：**
- 每条边至少 1 条证据
- 证据必须指向具体的文件位置或 commit

### 验收标准

1. **最小数量**: 至少返回 2 条结果（1 个 Doc + 1 个 Commit）
2. **排序规则**: 按相关性排序（Doc 优先，然后 Commit）
3. **必须包含**:
   - 相关 ADR 或文档（如有）
   - 引入重试功能的 Commit
4. **证据链**: 每条结果带证据引用

**示例输出：**
```json
{
  "nodes": [
    {
      "id": "doc_adr_retry",
      "type": "doc",
      "key": "docs/adr/ADR_TASK_RETRY.md",
      "name": "ADR: Task Retry Strategy"
    },
    {
      "id": "commit_add_retry",
      "type": "commit",
      "key": "abc123def",
      "name": "feat(task): add retry strategy"
    }
  ],
  "edges": [
    {
      "id": "edge_1",
      "source": "doc_adr_retry",
      "target": "file_manager",
      "type": "references",
      "evidence": [...]
    },
    {
      "id": "edge_2",
      "source": "commit_add_retry",
      "target": "file_manager",
      "type": "modifies",
      "evidence": [...]
    }
  ],
  "evidence_refs": [
    "docs/adr/ADR_TASK_RETRY.md:50:10",
    "commit:abc123def"
  ],
  "graph_version": "v_abc123_20260130"
}
```

---

## Golden Query 2: Impact - Modify task/models.py

### 问题
**"修改 agentos/core/task/models.py 会影响哪些模块？"**

### 查询类型
`impact_query`

### 输入（seed）
```python
seed = "agentos/core/task/models.py"
```

### 期望输出

**节点类型：**
- File（依赖该文件的其他文件）
- Doc（引用该文件的文档）

**边类型：**
- DEPENDS_ON（File → models.py）
- REFERENCES（Doc → models.py）

**证据要求：**
- import 语句证据（source_type="import"）
- 文档链接证据（source_type="doc_link"）

### 验收标准

1. **最小数量**: 至少返回 5 条依赖文件
2. **排序规则**: 按依赖类型分组（直接导入优先）
3. **必须包含**:
   - 直接 import 该模块的文件
   - 引用该文件的文档（如有）
4. **证据链**: 每条依赖带 import 语句位置

**示例输出：**
```json
{
  "nodes": [
    {"id": "file_manager", "type": "file", "key": "agentos/core/task/manager.py"},
    {"id": "file_service", "type": "file", "key": "agentos/core/task/service.py"},
    {"id": "file_test", "type": "file", "key": "tests/unit/task/test_models.py"}
  ],
  "edges": [
    {
      "source": "file_manager",
      "target": "file_models",
      "type": "depends_on",
      "evidence": [
        {
          "source_type": "import",
          "source_ref": "agentos/core/task/manager.py:10:0",
          "span": "from agentos.core.task.models import Task"
        }
      ]
    }
  ],
  "evidence_refs": ["agentos/core/task/manager.py:10:0", ...],
  "graph_version": "v_abc123_20260130"
}
```

---

## Golden Query 3: Trace - planning_guard 演进

### 问题
**"追溯 'planning_guard' 概念的演进历史"**

### 查询类型
`trace_query`

### 输入（term）
```python
term = "planning_guard"
```

### 期望输出

**节点类型：**
- Commit（提到该术语的提交）
- Doc（提到该术语的文档）
- File（提到该术语的文件）

**边类型：**
- MENTIONS（Commit/Doc/File → Term）

**证据要求：**
- span 必须包含术语出现的上下文

### 验收标准

1. **最小数量**: 至少返回 3 条结果（按时间排序）
2. **排序规则**: 按时间正序（最早的在前）
3. **必须包含**:
   - 首次引入该术语的 Commit/Doc
   - 相关的代码文件
4. **证据链**: span 包含术语及其上下文（前后各 20 字符）

**示例输出：**
```json
{
  "nodes": [
    {
      "id": "commit_001",
      "type": "commit",
      "key": "abc123",
      "name": "feat(task): add planning_guard",
      "attrs": {"date": "2025-10-15T10:00:00Z"}
    },
    {
      "id": "doc_001",
      "type": "doc",
      "key": "docs/adr/ADR_PLANNING_GUARD.md",
      "name": "ADR: Planning Guard"
    },
    {
      "id": "file_001",
      "type": "file",
      "key": "agentos/core/task/planning_guard.py",
      "name": "planning_guard.py"
    }
  ],
  "edges": [
    {
      "source": "commit_001",
      "target": "term_planning_guard",
      "type": "mentions",
      "evidence": [
        {
          "source_type": "term_pattern",
          "source_ref": "commit:abc123",
          "span": "...introduce planning_guard to prevent..."
        }
      ]
    }
  ],
  "evidence_refs": ["commit:abc123", "docs/adr/ADR_PLANNING_GUARD.md:20:0", ...],
  "graph_version": "v_abc123_20260130"
}
```

---

## Golden Query 4: Why - state_machine 引入

### 问题
**"为什么要引入 state_machine？"**

### 查询类型
`why_query`

### 输入（seed）
```python
seed = "state_machine"  # 术语或能力
```

### 期望输出

**节点类型：**
- Doc（ADR、设计文档）
- Commit（引入该特性的提交）
- Capability（state_machine 能力实体）

**边类型：**
- REFERENCES（Doc → Capability）
- IMPLEMENTS（File → Capability）

### 验收标准

1. **最小数量**: 至少返回 1 个 Doc + 1 个 Commit
2. **排序规则**: Doc 优先
3. **必须包含**: 相关 ADR 或设计文档
4. **证据链**: 文档必须明确提到引入原因

**示例输出：**
```json
{
  "nodes": [
    {
      "id": "doc_adr_state_machine",
      "type": "doc",
      "key": "docs/adr/ADR_STATE_MACHINE.md",
      "name": "ADR: Task State Machine"
    },
    {
      "id": "capability_state_machine",
      "type": "capability",
      "key": "state_machine",
      "name": "Task State Machine"
    }
  ],
  "edges": [
    {
      "source": "doc_adr_state_machine",
      "target": "capability_state_machine",
      "type": "references",
      "evidence": [...]
    }
  ],
  "evidence_refs": ["docs/adr/ADR_STATE_MACHINE.md:30:0"],
  "graph_version": "v_abc123_20260130"
}
```

---

## Golden Query 5: Impact - 删除 executor 模块

### 问题
**"删除 agentos/core/executor/ 会影响什么？"**

### 查询类型
`impact_query`

### 输入（seed）
```python
seed = "agentos/core/executor/"  # 目录级别
```

### 期望输出

**节点类型：**
- File（依赖 executor 模块的文件）

**边类型：**
- DEPENDS_ON（File → executor/* 中的文件）

### 验收标准

1. **最小数量**: 至少返回 3 条依赖
2. **排序规则**: 按文件路径排序
3. **必须包含**: 所有直接 import executor 模块的文件
4. **证据链**: import 语句位置

---

## Golden Query 6: Trace - boundary enforcement 实现

### 问题
**"追溯 'boundary enforcement' 的实现轨迹"**

### 查询类型
`trace_query`

### 输入（term）
```python
term = "boundary enforcement"
```

### 期望输出

**节点类型：**
- Commit（相关提交）
- Doc（相关文档）
- File（相关代码）

**边类型：**
- MENTIONS（* → Term）

### 验收标准

1. **最小数量**: 至少返回 5 条结果
2. **排序规则**: 按时间正序
3. **必须包含**: 从概念提出到实现的关键节点
4. **证据链**: span 包含完整上下文

---

## Golden Query 7: Why - audit 模块

### 问题
**"为什么要有 audit 模块？"**

### 查询类型
`why_query`

### 输入（seed）
```python
seed = "agentos/core/audit.py"
```

### 期望输出

**节点类型：**
- Doc（设计文档）
- Commit（引入 audit 的提交）

**边类型：**
- REFERENCES（Doc → File）
- MODIFIES（Commit → File）

### 验收标准

1. **最小数量**: 至少返回 1 个 Doc
2. **排序规则**: Doc 优先
3. **必须包含**: 解释 audit 目的的文档
4. **证据链**: 文档引用位置

---

## Golden Query 8: Impact - 修改 WebSocket API

### 问题
**"修改 agentos/webui/websocket/chat.py 会影响哪些前端组件？"**

### 查询类型
`impact_query`

### 输入（seed）
```python
seed = "agentos/webui/websocket/chat.py"
```

### 期望输出

**节点类型：**
- File（前端 JS 文件）
- Doc（API 文档）

**边类型：**
- DEPENDS_ON（前端 → 后端）
- REFERENCES（Doc → API）

### 验收标准

1. **最小数量**: 至少返回 2 个前端文件
2. **排序规则**: 按文件类型分组（JS 文件优先）
3. **必须包含**: 调用 WebSocket API 的前端文件
4. **证据链**: API 调用位置或文档引用

---

## Golden Query 9: Map - governance 子图

### 问题
**"围绕 'governance' 输出完整关系图谱"**

### 查询类型
`map_query`

### 输入（seed + hops）
```python
seed = "governance"  # Capability 或 Term
hops = 2  # 2 跳邻域
```

### 期望输出

**节点类型：**
- Capability（governance）
- File（实现文件）
- Doc（相关文档）
- Term（相关术语）

**边类型：**
- IMPLEMENTS（File → Capability）
- REFERENCES（Doc → Capability）
- MENTIONS（* → Term）

### 验收标准

1. **最小数量**: 至少返回 10 个节点 + 15 条边
2. **排序规则**: 按深度排序（0-hop 在前）
3. **必须包含**: 完整的子图（所有相关节点和边）
4. **证据链**: 每条边都有证据
5. **可视化友好**: 输出格式支持图可视化（如 Cytoscape JSON）

**示例输出：**
```json
{
  "nodes": [
    {"id": "capability_governance", "type": "capability", "key": "governance"},
    {"id": "file_gov_view", "type": "file", "key": "agentos/webui/static/js/views/GovernanceDashboardView.js"},
    {"id": "doc_gov_design", "type": "doc", "key": "docs/governance/DESIGN.md"}
  ],
  "edges": [
    {"source": "file_gov_view", "target": "capability_governance", "type": "implements", "evidence": [...]},
    {"source": "doc_gov_design", "target": "capability_governance", "type": "references", "evidence": [...]}
  ],
  "evidence_refs": [...],
  "graph_version": "v_abc123_20260130",
  "stats": {
    "nodes_count": 12,
    "edges_count": 18,
    "depth_distribution": {"0": 1, "1": 5, "2": 6}
  }
}
```

---

## Golden Query 10: Why - extensions 系统设计

### 问题
**"为什么 extensions 系统采用声明式设计？"**

### 查询类型
`why_query`

### 输入（seed）
```python
seed = "extensions"  # Capability
```

### 期望输出

**节点类型：**
- Doc（ADR、设计文档）
- Capability（extensions）

**边类型：**
- REFERENCES（Doc → Capability）

### 验收标准

1. **最小数量**: 至少返回 1 个 ADR
2. **排序规则**: ADR 优先
3. **必须包含**: ADR-EXT-001（声明式扩展架构决策）
4. **证据链**: 文档中明确提到设计理由

**示例输出：**
```json
{
  "nodes": [
    {
      "id": "doc_adr_ext_001",
      "type": "doc",
      "key": "docs/adr/ADR-EXT-001-declarative-extensions-only.md",
      "name": "ADR-EXT-001: Declarative Extensions Only"
    },
    {
      "id": "capability_extensions",
      "type": "capability",
      "key": "extensions",
      "name": "Extension System"
    }
  ],
  "edges": [
    {
      "source": "doc_adr_ext_001",
      "target": "capability_extensions",
      "type": "references",
      "evidence": [
        {
          "source_type": "doc_link",
          "source_ref": "docs/adr/ADR-EXT-001-declarative-extensions-only.md:20:0",
          "span": "Decision: Extensions MUST be declarative...",
          "confidence": 1.0
        }
      ]
    }
  ],
  "evidence_refs": ["docs/adr/ADR-EXT-001-declarative-extensions-only.md:20:0"],
  "graph_version": "v_abc123_20260130"
}
```

---

## 测试策略

### 单元测试
每条查询需要独立的单元测试：
```python
def test_golden_query_1_why_task_retry():
    service = BrainService(store)
    result = service.why_query("agentos/core/task/manager.py")

    # 验收标准
    assert len(result.nodes) >= 2
    assert result.graph_version is not None
    assert len(result.evidence_refs) > 0

    # 检查节点类型
    node_types = {n["type"] for n in result.nodes}
    assert "doc" in node_types or "commit" in node_types
```

### 集成测试
完整的构建和查询流程：
```python
def test_golden_queries_e2e():
    # 1. 构建图谱
    builder = build_graph_from_repo("/path/to/agentos")

    # 2. 运行所有黄金查询
    for query in GOLDEN_QUERIES:
        result = run_query(query)
        assert validate_result(result, query.acceptance_criteria)
```

### 幂等性测试
确保多次构建产生相同结果：
```python
def test_golden_queries_idempotence():
    # 构建两次
    graph1 = build_graph_from_repo(repo_path, commit="abc123")
    graph2 = build_graph_from_repo(repo_path, commit="abc123")

    # 对每条查询，验证结果一致
    for query in GOLDEN_QUERIES:
        result1 = run_query(query, graph1)
        result2 = run_query(query, graph2)
        assert result1 == result2  # 节点、边、证据完全一致
```

## 性能要求

| 查询类型     | 最大响应时间 | 说明                      |
|-------------|-------------|---------------------------|
| Why Query   | 500ms       | 单个实体的文档/commit 查询 |
| Impact Query| 1s          | 依赖分析（可能涉及多跳）   |
| Trace Query | 2s          | 时间序列查询（排序开销）   |
| Map Query   | 3s          | 子图提取（BFS 遍历）       |

## 相关文档

- [BRAINOS_OVERVIEW.md](./BRAINOS_OVERVIEW.md) - BrainOS 概述
- [SCHEMA.md](./SCHEMA.md) - 数据模型
- [ACCEPTANCE.md](./ACCEPTANCE.md) - 验收标准

---

**注**: 这 10 条黄金查询是 v0.1 MVP 的验收基准。后续版本可能添加更多查询，但这 10 条必须始终 PASS。
