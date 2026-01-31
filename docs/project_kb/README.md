# ProjectKB: Project Knowledge Retrieval

**项目知识库 - 可审计的文档检索系统**

## 概述

ProjectKB 是 AgentOS 的**项目知识检索层**，为 AI Agent 提供项目级文档知识的访问能力。与现有系统的关系：

- **Content Registry** (70+ 条结构化内容) → 系统自带能力 (workflows/agents/commands)
- **Memory System** (`agentos/core/memory/`) → Agent 运行时记忆
- **ProjectKB** → 项目仓库文档知识 (docs/\*.md, README.md, ADR, runbooks)

## 核心特性

### 1. 可审计 (Auditability First)

每条检索结果都能解释"为什么命中"：

```json
{
  "chunk_id": "chunk_abc123",
  "score": 8.5,
  "explanation": {
    "matched_terms": ["API", "authentication", "JWT"],
    "term_frequencies": {"API": 3, "authentication": 2},
    "document_boost": 1.5,
    "recency_boost": 1.2,
    "path": "docs/architecture/auth_design.md",
    "lines": "L45-L68"
  }
}
```

### 2. 关键词优先 (Keyword Primary)

- 使用 SQLite FTS5 (BM25 算法) 进行关键词检索
- 保证排序可解释、可追溯
- 避免"黑盒"向量相似度

### 3. 向量可选 (Vector Optional)

- 向量检索仅用于 rerank，不作为唯一召回方式
- 保留关键词评分，记录 rerank 排名变化
- 完整的评分链：`keyword_score` + `vector_score` + `rerank_delta`

### 4. 证据链 (Evidence Trail)

所有结果可追溯到 `file:line:hash`：

```python
evidence_ref = "kb:chunk_abc123:docs/architecture/auth_design.md#L45-L68"
```

## 快速开始

### 安装

ProjectKB 已内置在 AgentOS 中，无需额外安装。

### 初始化索引

```bash
# 首次使用需要刷新索引
agentos kb refresh
```

输出示例：

```
✓ Refresh complete!

Total files       45
Changed files     45
Total chunks      230
New chunks        230
Duration          2.34s
```

### 搜索文档

```bash
# 基本搜索
agentos kb search "JWT authentication"

# 指定路径过滤
agentos kb search "API design" --scope docs/architecture/

# 按文档类型过滤
agentos kb search "deployment" --doc-type runbook

# JSON 输出
agentos kb search "testing" --json
```

### 查看 Chunk 详情

```bash
agentos kb explain chunk_abc123
```

### 查看统计信息

```bash
agentos kb stats
```

## 配置

ProjectKB 支持通过 `.agentos/kb_config.json` 配置：

```json
{
  "scan_paths": [
    "docs/**/*.md",
    "README.md",
    "adr/**/*.md"
  ],
  "exclude_patterns": [
    "node_modules/**",
    ".history/**",
    ".git/**"
  ],
  "chunk_size": {
    "min": 300,
    "max": 800
  },
  "index_weights": {
    "heading": 2.0,
    "first_paragraph": 1.5,
    "code_blocks": 1.2
  },
  "doc_type_weights": {
    "adr": 1.5,
    "runbook": 1.3,
    "spec": 1.4
  }
}
```

### 配置项说明

- `scan_paths`: 扫描路径模式 (支持 glob)
- `exclude_patterns`: 排除路径模式
- `chunk_size`: 切片大小限制 (token 数)
- `index_weights`: 索引权重 (heading/paragraph/code)
- `doc_type_weights`: 文档类型权重 (覆盖默认值)

## 编程接口

### Python API

```python
from agentos.core.project_kb import ProjectKBService

# 初始化
kb = ProjectKBService()

# 刷新索引
report = kb.refresh(changed_only=True)
print(report.summary())

# 搜索
results = kb.search(
    query="JWT authentication",
    scope="docs/architecture/",
    top_k=5
)

for result in results:
    print(f"{result.path} ({result.score:.2f})")
    print(result.content[:200])
    
# 获取 chunk
chunk = kb.get("chunk_abc123")

# 解释结果
explanation = kb.explain(results[0])
print(explanation)
```

### 集成到 Intent Builder

```python
from agentos.core.intent_builder import IntentBuilder
from agentos.core.project_kb import ProjectKBService
from agentos.core.content.registry import ContentRegistry

# 初始化
registry = ContentRegistry()
kb = ProjectKBService()
builder = IntentBuilder(registry, project_kb=kb)

# 构建 Intent (自动查询 KB 如果是知识查询)
nl_request = {
    "input_text": "如何实现 JWT 认证？",
    "project_id": "agentos"
}

output = builder.build_intent(nl_request)

# 检查 KB 结果
kb_selections = output["selection_evidence"].get("kb_selections", [])
for sel in kb_selections:
    print(f"Found: {sel['path']} {sel['lines']}")
```

## 架构设计

### 数据模型

ProjectKB 使用 3 张核心表：

1. **kb_sources** - 文档源
2. **kb_chunks** - 文档片段
3. **kb_chunks_fts** - FTS5 全文索引

### 组件架构

```
ProjectKBService (service.py)
├── DocumentScanner (scanner.py)     - 扫描文档
├── MarkdownChunker (chunker.py)     - 智能切片
├── ProjectKBIndexer (indexer.py)    - 索引构建
├── ProjectKBSearcher (searcher.py)  - BM25 检索
└── ResultExplainer (explainer.py)   - 结果解释
```

### 切片策略

- 按 `# / ## / ###` heading 分割
- 段落窗口: 300-800 tokens
- 保持代码块完整性
- 记录行号范围便于追溯

### 评分机制

```python
final_score = base_score × document_boost × recency_boost

# 文档类型权重
document_boost = {
    "adr": 1.5,      # 架构决策记录优先
    "runbook": 1.3,  # 操作手册次之
    "spec": 1.4,     # 规范文档
    "guide": 1.1,
    "index": 0.3     # INDEX.md 降权
}

# 新鲜度衰减 (30天半衰期)
recency_boost = 1.0 + 0.5 × exp(-days_old / 30)
```

## 使用场景

### 1. 知识查询

当用户问"如何"、"什么是"、"在哪里"等问题时，ProjectKB 自动返回相关文档：

```bash
agentos intent build "如何实现 JWT 认证？"
```

Intent Builder 会查询 ProjectKB，将匹配结果附加到 `evidence_refs`。

### 2. 文档维护

检查哪些文档过期（修改时间较久）：

```python
results = kb.search(
    "authentication",
    filters={"mtime_before": int(time.time()) - 90*86400}  # 90天前
)
```

### 3. 代码审查

查找相关设计文档：

```bash
# 审查 auth 相关代码时
agentos kb search "authentication design" --doc-type adr --scope docs/adr/
```

### 4. 新人入职

生成入门知识图谱：

```python
topics = ["architecture", "deployment", "testing", "security"]
for topic in topics:
    results = kb.search(topic, top_k=3)
    print(f"\n{topic.upper()}:")
    for r in results:
        print(f"  - {r.path} ({r.heading})")
```

## 性能考虑

- **索引大小**: 1000 文档 × 10 chunks = 10K chunks ≈ 5MB
- **检索延迟**: FTS5 查询 <10ms (SQLite 本地)
- **刷新时间**: 增量更新，只处理变更文件

## 故障排查

### 搜索无结果

1. 检查索引是否刷新：
   ```bash
   agentos kb stats
   ```

2. 确认文档在扫描路径内：
   ```bash
   cat .agentos/kb_config.json
   ```

3. 尝试全量刷新：
   ```bash
   agentos kb refresh --full
   ```

### 索引失败

查看错误日志：

```bash
agentos kb refresh --verbose
```

### 检索速度慢

1. 检查 chunk 数量 (>100K 建议优化)
2. 缩小 `scan_paths` 范围
3. 增加 `chunk_size.max` 减少 chunk 数量

## 最佳实践

### 1. 文档类型标注

使用目录结构标识文档类型：

```
docs/
├── adr/           # 架构决策记录
├── runbooks/      # 操作手册
├── specs/         # 规范文档
└── guides/        # 指南
```

### 2. Heading 结构化

使用明确的 heading 层次：

```markdown
# 模块名称

## Overview

## Implementation

### Component A

### Component B

## Security Considerations
```

### 3. 定期刷新

在 CI 中添加索引刷新：

```yaml
- name: Refresh ProjectKB
  run: agentos kb refresh
```

### 4. 监控覆盖率

定期检查文档覆盖：

```bash
agentos kb stats
# 期望: 每 1000 行代码对应 100+ chunks
```

## 扩展开发

### 添加新的文档类型

1. 在配置中添加类型：

```json
{
  "doc_type_weights": {
    "api_spec": 1.6
  }
}
```

2. 确保文档路径匹配模式 (scanner.py):

```python
DOC_TYPE_PATTERNS = {
    "api_spec": [r"api/specs/", r"openapi/"]
}
```

### 自定义评分

继承 `ProjectKBSearcher` 并重写 `_calculate_recency_boost`:

```python
class CustomSearcher(ProjectKBSearcher):
    def _calculate_recency_boost(self, mtime):
        # 自定义衰减曲线
        days_old = (time.time() - mtime) / 86400
        return 1.0 + 0.8 * math.exp(-days_old / 60)  # 60天半衰期
```

## 与其他系统对比

| 维度 | ProjectKB | Content Registry | Memory System |
|------|-----------|------------------|---------------|
| 内容来源 | 项目文档 | 系统内置 | 运行时生成 |
| 数据规模 | 数千 chunks | 70+ 条 | 动态增长 |
| 更新频率 | 手动刷新 | 代码部署 | 实时写入 |
| 检索方式 | BM25 + 向量 | SQL 查询 | 时间/范围 |
| 适用场景 | 知识查询 | 能力选择 | 上下文记忆 |

## 未来演进

### v1.3 (计划中)

- [ ] 跨仓库检索 (多项目联合知识库)
- [ ] 时间旅行 (查询特定 commit 时的文档)
- [ ] 图谱增强 (文档间引用关系)

### v2.0 (探索中)

- [ ] 实时更新 (文件系统监听)
- [ ] 语义缓存 (常见查询缓存)
- [ ] 协同编辑 (检索结果直接建议文档更新)

## 参考资料

- [架构设计](./ARCHITECTURE.md)
- [Explain 格式规范](./EXPLAIN_FORMAT.md)
- [Intent Builder 集成指南](./INTEGRATION_GUIDE.md)
- [SQLite FTS5 文档](https://www.sqlite.org/fts5.html)
- [BM25 算法说明](https://en.wikipedia.org/wiki/Okapi_BM25)

## 贡献

欢迎提交 Issue 和 PR！

- 报告 Bug: https://github.com/yourusername/agentos/issues
- 功能建议: 在 Issue 中添加 `enhancement` 标签
- 提交 PR: 请先阅读 CONTRIBUTING.md

## License

MIT License - 详见 LICENSE 文件
