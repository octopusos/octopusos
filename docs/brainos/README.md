# BrainOS Documentation

欢迎来到 BrainOS 文档！

## 快速导航

### 核心文档

1. **[BRAINOS_OVERVIEW.md](./BRAINOS_OVERVIEW.md)** - 开始这里
   - BrainOS 是什么？
   - 核心能力（Why/Impact/Trace/Map）
   - 架构概览
   - 路线图

2. **[SCHEMA.md](./SCHEMA.md)** - 数据模型
   - 实体类型（Repo, File, Symbol, Doc, Commit, Term, Capability）
   - 关系类型（MODIFIES, REFERENCES, MENTIONS, DEPENDS_ON, IMPLEMENTS）
   - 证据链（Evidence/Provenance）
   - 存储结构（SQLite）

3. **[GOLDEN_QUERIES.md](./GOLDEN_QUERIES.md)** - 黄金查询
   - 10 条验收查询（基于 AgentOS 真实场景）
   - 每条查询的输入、输出、验收标准
   - 测试策略

4. **[ACCEPTANCE.md](./ACCEPTANCE.md)** - 验收标准
   - 冻结契约（READONLY/PROVENANCE/IDEMPOTENCE）
   - 功能验收（10 条黄金查询）
   - 质量验收（测试覆盖、幂等性、性能）
   - Definition of Done

## 快速开始

### 理解 BrainOS

BrainOS 是 AgentOS 的**只读推理层**，它不执行代码、不修改文件，只负责理解和推理。

**核心能力：**
- **Why**: 追溯设计决策和实现原因
- **Impact**: 分析变更影响范围
- **Trace**: 追踪概念演进历史
- **Map**: 输出知识子图谱

**核心原则：**
- 只读：不修改原仓库内容
- 可追溯：每条结论带证据链
- 可重复：同一 commit 构建结果一致

### 阅读顺序

**新手推荐：**
1. 阅读 [BRAINOS_OVERVIEW.md](./BRAINOS_OVERVIEW.md) 了解全貌
2. 阅读 [GOLDEN_QUERIES.md](./GOLDEN_QUERIES.md) 看实际案例
3. 阅读 [SCHEMA.md](./SCHEMA.md) 理解数据模型
4. 阅读 [ACCEPTANCE.md](./ACCEPTANCE.md) 了解验收标准

**开发者推荐：**
1. 阅读 [SCHEMA.md](./SCHEMA.md) 了解数据结构
2. 查看 `agentos/core/brain/` 代码（接口定义）
3. 阅读 [GOLDEN_QUERIES.md](./GOLDEN_QUERIES.md) 了解目标
4. 阅读 [ACCEPTANCE.md](./ACCEPTANCE.md) 了解测试要求

## 文档索引

### 按主题分类

#### 概念和设计
- [BrainOS 概述](./BRAINOS_OVERVIEW.md)
- [数据模型和 Schema](./SCHEMA.md)
- [冻结契约](./ACCEPTANCE.md#硬约束frozen-contracts)

#### 功能和用例
- [黄金查询](./GOLDEN_QUERIES.md)
- [Why Query](./GOLDEN_QUERIES.md#golden-query-1-why---task-retry)
- [Impact Query](./GOLDEN_QUERIES.md#golden-query-2-impact---modify-taskmodelspy)
- [Trace Query](./GOLDEN_QUERIES.md#golden-query-3-trace---planning_guard-演进)
- [Map Query](./GOLDEN_QUERIES.md#golden-query-9-map---governance-子图)

#### 质量和验收
- [验收标准](./ACCEPTANCE.md)
- [测试策略](./GOLDEN_QUERIES.md#测试策略)
- [Definition of Done](./ACCEPTANCE.md#definition-of-done-dod)

#### 技术细节
- [实体类型](./SCHEMA.md#实体类型entities-v01)
- [关系类型](./SCHEMA.md#关系类型edges-v01)
- [证据链](./SCHEMA.md#证据链evidenceprovenance)
- [存储结构](./SCHEMA.md#存储表结构sqlite)

## 版本历史

### v0.1 (Current) - 骨架 + 契约冻结
**发布日期**: 2026-01-30

**交付物：**
- ✅ 完整的目录结构（agentos/core/brain/）
- ✅ 数据模型定义（Entities, Edges, Evidence）
- ✅ 抽取器接口（GitExtractor, DocExtractor, etc.）
- ✅ 图构建接口（GraphBuilder, VersionManager）
- ✅ 存储接口（SQLiteStore）
- ✅ 查询服务接口（BrainService: Why/Impact/Trace/Map）
- ✅ 冻结契约（READONLY/PROVENANCE/IDEMPOTENCE）
- ✅ 核心文档（4 个完整文档）
- ✅ 10 条黄金查询定义

**Non-goals:**
- 实现真实的抽取逻辑（v0.2）
- 实现真实的查询逻辑（v0.2）
- UI 集成（v0.3）

### v0.2 (Planned) - 核心实现
**预计日期**: TBD

**目标：**
- 实现 GitExtractor、DocExtractor、CodeExtractor
- 实现 SQLiteStore 真实持久化
- 实现 4 类查询（Why/Impact/Trace/Map）
- 通过 10 条黄金查询测试

### v0.3 (Planned) - 高级特性
**预计日期**: TBD

**目标：**
- 向量搜索（semantic similarity）
- WebUI 集成
- 实时增量索引

## 常见问题（FAQ）

### Q: BrainOS 和 AgentOS 的关系？
A: BrainOS 是 AgentOS 的子系统，专注于只读推理。AgentOS 负责执行，BrainOS 负责理解。

### Q: BrainOS 会修改我的代码吗？
A: **绝对不会**。这是冻结契约（READONLY_PRINCIPLE）。BrainOS 只读取代码和文档，构建知识图谱，不会修改任何文件。

### Q: 什么是"证据链"？
A: 每条关系（Edge）都必须有证据（Evidence），说明这条关系是从哪里来的。例如："File A 依赖 File B" 的证据是 "A.py:10:0 的 import 语句"。

### Q: 为什么要幂等性？
A: 确保同一 commit 的多次构建产生相同的图谱，这样查询结果才可靠、可复现。

### Q: 黄金查询是什么？
A: 10 条基于 AgentOS 真实场景的查询，用于验证 BrainOS 的核心能力。它们是 v0.1 MVP 的验收基准。

### Q: BrainOS 支持哪些语言？
A: v0.1 主要支持 Python 和 JavaScript。后续版本会支持更多语言（Go, Rust, Java）。

### Q: 如何扩展 BrainOS？
A: 可以添加新的实体类型、关系类型、抽取器。详见 [SCHEMA.md](./SCHEMA.md#扩展性考虑)。

## 贡献指南

参见 AgentOS 主仓库的贡献指南。

## 联系方式

- **Issue**: 在 AgentOS 仓库提 Issue，标签 `brainos`
- **讨论**: 参见 AgentOS README.md

## License

与 AgentOS 相同
