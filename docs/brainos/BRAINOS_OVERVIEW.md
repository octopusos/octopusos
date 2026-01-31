# BrainOS Overview

## 定位

**BrainOS 是 AgentOS 的只读推理层（Read-only Reasoning Layer）**

BrainOS 不执行、不修改、不决策，只负责理解和推理。它通过索引、构图、查询来支持 AgentOS 的高级推理能力。

## 核心能力

BrainOS 提供 4 类推理查询：

### 1. Why Query - 追溯原因
**回答"为什么这样设计/实现？"**

- 输入：代码文件、函数、模块
- 输出：相关的 ADR、文档、设计决策、Commit 历史
- 示例："为什么 task/manager.py 要实现重试机制？" → 返回 ADR_TASK_RETRY.md + 相关 commits + 证据链

### 2. Impact Query - 影响分析
**回答"改这个会影响什么？"**

- 输入：代码文件、模块、API
- 输出：依赖它的所有模块、测试、文档
- 示例："修改 task/models.py 会影响哪些模块？" → 返回依赖图 + 受影响的测试

### 3. Trace Query - 演进追踪
**回答"这个概念是如何演进的？"**

- 输入：术语、概念、能力
- 输出：提到它的所有 Commit/Doc/File，按时间排序
- 示例："追溯 'planning_guard' 概念的演进历史" → 返回时间线 + 关键里程碑

### 4. Map Query - 知识子图
**回答"围绕这个概念有什么相关知识？"**

- 输入：实体（文件/术语/能力）
- 输出：围绕它的子图谱（N-hop neighborhood）
- 示例："围绕 'extensions' 能力输出子图谱" → 返回相关文件、文档、实现、测试的关系图

## 核心原则

BrainOS 遵循 3 个冻结契约（Frozen Contracts）：

### 1. 只读原则（READONLY_PRINCIPLE）
```python
READONLY_PRINCIPLE = "BrainOS MUST NOT modify any repo content"
```

**可做：**
- ✅ 索引仓库内容（代码、文档、Git 历史）
- ✅ 构建知识图谱
- ✅ 查询和推理
- ✅ 追溯和关联
- ✅ 写入 BrainOS 自己的索引库（brain.db）

**不可做：**
- ❌ 修改任何源代码文件
- ❌ 创建/删除文件
- ❌ 触发代码执行
- ❌ 修改 Git 历史
- ❌ 写入业务数据库（除 brain.db）

### 2. 证据链原则（PROVENANCE_PRINCIPLE）
```python
PROVENANCE_PRINCIPLE = "Every conclusion MUST have traceable evidence"
```

**要求：**
- 每条关系边（Edge）必须有至少一条证据（Evidence）
- 证据必须包含：来源类型（source_type）、引用位置（source_ref）、文本片段（span）
- 证据必须可追溯到原始文件的具体位置（file:line:col）

**示例：**
```python
Evidence(
    source_type="import",
    source_ref="agentos/core/task/manager.py:10:0",
    span="from agentos.core.task.models import Task",
    confidence=1.0
)
```

### 3. 幂等性原则（IDEMPOTENCE_PRINCIPLE）
```python
IDEMPOTENCE_PRINCIPLE = "Same commit MUST produce identical graph"
```

**要求：**
- 同一 commit hash 的多次构建必须产生相同的图谱
- 图谱版本号基于 commit hash 生成（确定性）
- 抽取器和构图逻辑必须是确定性的（无随机性）

## 边界约束

### BrainOS 的输入（只读）
- Git 仓库（commits, history, branches）
- 代码文件（Python, JS, YAML, etc.）
- 文档文件（Markdown, RST）
- 配置文件（pyproject.toml, package.json, etc.）

### BrainOS 的输出
- 知识图谱（Entities + Edges + Evidence）
- 查询结果（带证据链）
- 图谱版本元数据

### BrainOS 的持久化
- **唯一可写入**：`brain.db`（SQLite 索引库）
- 存储：实体、关系、证据、版本、FTS 索引
- 位置：项目根目录或 `.agentos/brain.db`

### BrainOS 不碰的东西
- 原仓库的任何文件（只读）
- AgentOS 的业务数据库（store/agentos.db）
- 运行时状态（tasks, sessions, memory）
- 用户数据和配置

## v0.1 MVP 目标

**MVP 目标：回答 10 条黄金查询（Golden Queries）**

v0.1 专注于骨架和契约冻结，具体包括：

1. ✅ 创建完整的目录结构和模块骨架
2. ✅ 定义核心数据模型（Entities, Edges, Evidence）
3. ✅ 定义抽取器接口（GitExtractor, DocExtractor, etc.）
4. ✅ 定义图构建接口（GraphBuilder, VersionManager）
5. ✅ 定义存储接口（SQLiteStore）
6. ✅ 定义查询服务接口（BrainService: Why/Impact/Trace/Map）
7. ✅ 冻结 3 个核心契约（READONLY/PROVENANCE/IDEMPOTENCE）
8. ✅ 定义 10 条黄金查询模板（基于 AgentOS 真实场景）
9. ✅ 编写完整文档（Overview, Schema, Queries, Acceptance）

**v0.1 Non-goals（不做）：**
- ❌ 实现真实的抽取逻辑（v0.2 实现）
- ❌ 实现真实的查询逻辑（v0.2 实现）
- ❌ UI 集成（v0.3）
- ❌ 向量搜索（v0.3）
- ❌ 实时增量索引（v0.3）
- ❌ 多仓库支持（v0.4）

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                      BrainOS v0.1                       │
│              (Read-only Reasoning Layer)                │
└─────────────────────────────────────────────────────────┘
                           │
                           ↓
         ┌─────────────────────────────────────┐
         │         Extractors (只读)            │
         ├─────────────────────────────────────┤
         │ • GitExtractor   (Commit → File)    │
         │ • DocExtractor   (Doc → File/Term)  │
         │ • CodeExtractor  (File → File)      │
         │ • TermExtractor  (* → Term)         │
         └─────────────────────────────────────┘
                           │
                           ↓ ExtractionResult
         ┌─────────────────────────────────────┐
         │        GraphBuilder (构图)           │
         ├─────────────────────────────────────┤
         │ • 合并实体（去重）                   │
         │ • 合并边（证据链）                   │
         │ • 版本管理（基于 commit）            │
         └─────────────────────────────────────┘
                           │
                           ↓ Graph + Version
         ┌─────────────────────────────────────┐
         │       SQLiteStore (持久化)           │
         ├─────────────────────────────────────┤
         │ • entities, edges, evidence         │
         │ • versions (commit hash)            │
         │ • FTS 全文搜索索引                   │
         └─────────────────────────────────────┘
                           │
                           ↓ Query
         ┌─────────────────────────────────────┐
         │       BrainService (查询)            │
         ├─────────────────────────────────────┤
         │ • why_query()    - 追溯原因          │
         │ • impact_query() - 影响分析          │
         │ • trace_query()  - 演进追踪          │
         │ • map_query()    - 子图提取          │
         └─────────────────────────────────────┘
                           │
                           ↓ QueryResult (带证据链)
         ┌─────────────────────────────────────┐
         │            API / CLI                │
         │      (v0.2+ WebUI 集成)             │
         └─────────────────────────────────────┘
```

## 数据流

### 构建流程（Build Phase）
1. **Extraction**: 抽取器从 repo 读取数据 → ExtractionResult
2. **Graph Building**: GraphBuilder 合并结果 → Graph + Version
3. **Storage**: SQLiteStore 持久化 → brain.db

### 查询流程（Query Phase）
1. **Query**: BrainService 接收查询 → SQLiteStore
2. **Retrieval**: 从 brain.db 检索节点和边
3. **Evidence Collection**: 收集相关证据链
4. **Result**: 返回 QueryResult（nodes + edges + evidence_refs + version）

## 版本策略

### 图谱版本
- **版本号格式**：`v_{commit_hash[:8]}_{timestamp}`
- **版本依据**：基于 Git commit hash（保证幂等性）
- **版本存储**：versions 表（commit_hash, stats, metadata）

### 增量构建
- v0.1: 全量构建（每次重建整个图谱）
- v0.2+: 增量构建（仅处理变更的 commits/files）

## 使用场景

### 1. 代码审查（Code Review）
"修改这个文件会影响什么？" → Impact Query

### 2. 架构探索（Architecture Exploration）
"围绕 'task' 模块有哪些相关组件？" → Map Query

### 3. 设计溯源（Design Rationale）
"为什么要引入 state_machine？" → Why Query

### 4. 概念演进（Concept Evolution）
"'boundary enforcement' 是如何演进的？" → Trace Query

### 5. 依赖分析（Dependency Analysis）
"删除这个模块会破坏什么？" → Impact Query

## 技术栈

- **语言**: Python 3.9+
- **存储**: SQLite 3（FTS5 全文搜索）
- **图处理**: 自实现（轻量级，无需 Neo4j）
- **解析**:
  - Git: gitpython 或 subprocess
  - Python AST: ast 标准库
  - Markdown: mistletoe 或 markdown-it-py
- **测试**: pytest（单测 + 集成测试 + 幂等性测试）

## 路线图

### v0.1 (Current) - 骨架 + 契约冻结
- [x] 目录结构和模块骨架
- [x] 数据模型定义
- [x] 接口定义（抽取/构图/存储/查询）
- [x] 冻结契约（READONLY/PROVENANCE/IDEMPOTENCE）
- [x] 核心文档（Overview/Schema/Queries/Acceptance）

### v0.2 - 实现核心抽取和查询
- [ ] 实现 GitExtractor（Commit → File）
- [ ] 实现 DocExtractor（Doc → File/Term）
- [ ] 实现 CodeExtractor（File → File）
- [ ] 实现 SQLiteStore（真实持久化）
- [ ] 实现 4 类查询（Why/Impact/Trace/Map）
- [ ] 通过 10 条黄金查询测试

### v0.3 - 高级特性
- [ ] 向量搜索（semantic similarity）
- [ ] WebUI 集成（可视化子图）
- [ ] 实时增量索引
- [ ] 查询缓存和优化

### v0.4 - 企业级特性
- [ ] 多仓库支持
- [ ] 跨仓库依赖分析
- [ ] 查询 API（REST + GraphQL）
- [ ] 权限和安全

## 相关文档

- [SCHEMA.md](./SCHEMA.md) - 数据模型和存储结构
- [GOLDEN_QUERIES.md](./GOLDEN_QUERIES.md) - 10 条黄金查询模板
- [ACCEPTANCE.md](./ACCEPTANCE.md) - 验收标准和测试要求

## 团队和贡献

BrainOS 是 AgentOS 的子项目，遵循 AgentOS 的贡献指南。

**联系方式**: 参见 AgentOS README.md

**License**: 与 AgentOS 相同
