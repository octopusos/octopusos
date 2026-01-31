# BrainOS Schema

## 概述

BrainOS 使用 **知识图谱（Knowledge Graph）** 模型来表示代码库的结构和关系。

核心组件：
1. **Entities（实体）**: 节点，表示代码库中的各种对象
2. **Edges（关系）**: 边，表示实体之间的关系
3. **Evidence（证据）**: 每条边的溯源信息

## 实体类型（Entities v0.1）

所有实体遵循统一结构：

```python
@dataclass
class Entity:
    id: str              # 全局唯一标识符
    type: EntityType     # 实体类型
    key: str             # 业务唯一键
    name: str            # 显示名称
    attrs: Dict[str, Any]  # 扩展属性（JSON）
```

### 1. Repo（仓库）

表示 Git 仓库。

**字段：**
- `id`: 仓库 UUID
- `type`: "repo"
- `key`: 仓库 URL 或本地路径
- `name`: 仓库名称
- `attrs`:
  - `remote_url`: 远程仓库 URL
  - `local_path`: 本地路径
  - `default_branch`: 默认分支（如 "master"）

**示例：**
```json
{
  "id": "repo_001",
  "type": "repo",
  "key": "https://github.com/yourorg/agentos",
  "name": "AgentOS",
  "attrs": {
    "remote_url": "https://github.com/yourorg/agentos",
    "local_path": "/path/to/agentos",
    "default_branch": "master"
  }
}
```

### 2. File（文件）

表示代码文件或配置文件。

**字段：**
- `id`: 文件 UUID
- `type`: "file"
- `key`: 相对于仓库根的路径（如 "agentos/core/task/manager.py"）
- `name`: 文件名（如 "manager.py"）
- `attrs`:
  - `path`: 完整相对路径
  - `extension`: 文件扩展名（如 ".py"）
  - `size`: 文件大小（字节）
  - `last_modified`: 最后修改时间（ISO 8601）

**示例：**
```json
{
  "id": "file_001",
  "type": "file",
  "key": "agentos/core/task/manager.py",
  "name": "manager.py",
  "attrs": {
    "path": "agentos/core/task/manager.py",
    "extension": ".py",
    "size": 15420,
    "last_modified": "2026-01-20T10:30:00Z"
  }
}
```

### 3. Symbol（代码符号）

表示代码中的类、函数、变量等。

**字段：**
- `id`: 符号 UUID
- `type`: "symbol"
- `key`: 符号全限定名（如 "agentos.core.task.manager.TaskManager"）
- `name`: 符号名称（如 "TaskManager"）
- `attrs`:
  - `symbol_type`: 符号类型（"class" / "function" / "variable"）
  - `file_path`: 所在文件路径
  - `line_number`: 行号
  - `signature`: 函数/方法签名（可选）

**示例：**
```json
{
  "id": "symbol_001",
  "type": "symbol",
  "key": "agentos.core.task.manager.TaskManager",
  "name": "TaskManager",
  "attrs": {
    "symbol_type": "class",
    "file_path": "agentos/core/task/manager.py",
    "line_number": 42,
    "signature": "class TaskManager:"
  }
}
```

### 4. Doc（文档）

表示文档文件（Markdown、RST 等）。

**字段：**
- `id`: 文档 UUID
- `type`: "doc"
- `key`: 文档路径（如 "docs/architecture/ADR_V04.md"）
- `name`: 文档标题
- `attrs`:
  - `doc_type`: 文档类型（"adr" / "readme" / "guide" / "api"）
  - `format`: 格式（"markdown" / "rst" / "txt"）
  - `path`: 文档路径
  - `section`: 章节标题（可选）

**示例：**
```json
{
  "id": "doc_001",
  "type": "doc",
  "key": "docs/architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md",
  "name": "ADR V04: Project-Aware Task OS",
  "attrs": {
    "doc_type": "adr",
    "format": "markdown",
    "path": "docs/architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md",
    "section": "Decision"
  }
}
```

### 5. Commit（Git 提交）

表示 Git 提交记录。

**字段：**
- `id`: 提交 UUID
- `type`: "commit"
- `key`: commit hash (SHA-1)
- `name`: 提交消息首行
- `attrs`:
  - `hash`: 完整 commit hash
  - `author`: 作者
  - `date`: 提交日期（ISO 8601）
  - `message`: 完整提交消息
  - `files_changed`: 变更文件数

**示例：**
```json
{
  "id": "commit_001",
  "type": "commit",
  "key": "6aa4aaa1234567890abcdef",
  "name": "fix(websocket): filter out technical errors",
  "attrs": {
    "hash": "6aa4aaa1234567890abcdef",
    "author": "John Doe",
    "date": "2026-01-20T09:15:00Z",
    "message": "fix(websocket): filter out technical errors from user interface\n\nDetails...",
    "files_changed": 3
  }
}
```

### 6. Term（领域术语）

表示领域术语或技术名词。

**字段：**
- `id`: 术语 UUID
- `type`: "term"
- `key`: 术语文本（标准化，如小写）
- `name`: 术语显示名称
- `attrs`:
  - `term`: 原始术语文本
  - `category`: 分类（"technical" / "business" / "domain"）
  - `definition`: 定义（可选）
  - `aliases`: 别名列表

**示例：**
```json
{
  "id": "term_001",
  "type": "term",
  "key": "planning_guard",
  "name": "Planning Guard",
  "attrs": {
    "term": "planning_guard",
    "category": "domain",
    "definition": "A mechanism to prevent unauthorized planning modifications",
    "aliases": ["PlanningGuard", "planning guard"]
  }
}
```

### 7. Capability（能力/特性）

表示系统能力或特性。

**字段：**
- `id`: 能力 UUID
- `type`: "capability"
- `key`: 能力唯一标识（如 "extensions"）
- `name`: 能力名称
- `attrs`:
  - `capability_type`: 能力类型（"feature" / "api" / "integration"）
  - `status`: 状态（"planned" / "implemented" / "deprecated"）
  - `version`: 引入版本
  - `description`: 描述

**示例：**
```json
{
  "id": "capability_001",
  "type": "capability",
  "key": "extensions",
  "name": "Extension System",
  "attrs": {
    "capability_type": "feature",
    "status": "implemented",
    "version": "0.6.0",
    "description": "Declarative extension system for AgentOS"
  }
}
```

## 关系类型（Edges v0.1）

关系边结构：

```python
@dataclass
class Edge:
    id: str                  # 边的唯一标识符
    source: str              # 源节点 ID
    target: str              # 目标节点 ID
    type: EdgeType           # 关系类型
    evidence: List[Evidence] # 证据链（至少一条）
    attrs: Dict[str, Any]    # 扩展属性
```

### 1. MODIFIES（修改）

**Commit → File**

表示一个提交修改了某个文件。

**约束：**
- source: Commit 实体
- target: File 实体

**证据来源：**
- `source_type`: "git_log"
- `source_ref`: "commit:{hash}"
- `span`: diff 片段（可选）

**示例：**
```json
{
  "id": "edge_001",
  "source": "commit_001",
  "target": "file_001",
  "type": "modifies",
  "evidence": [
    {
      "source_type": "git_log",
      "source_ref": "commit:6aa4aaa",
      "span": "M agentos/webui/websocket/chat.py",
      "confidence": 1.0
    }
  ],
  "attrs": {}
}
```

### 2. REFERENCES（引用）

**Doc → File / Term / Capability**

表示文档引用了某个文件、术语或能力。

**约束：**
- source: Doc 实体
- target: File / Term / Capability 实体

**证据来源：**
- `source_type`: "doc_link" / "doc_mention"
- `source_ref`: "doc_path:line:col"
- `span`: 引用文本片段

**示例：**
```json
{
  "id": "edge_002",
  "source": "doc_001",
  "target": "file_001",
  "type": "references",
  "evidence": [
    {
      "source_type": "doc_link",
      "source_ref": "docs/architecture/ADR_V04.md:42:10",
      "span": "See `agentos/core/task/manager.py` for implementation",
      "confidence": 1.0
    }
  ],
  "attrs": {}
}
```

### 3. MENTIONS（提及）

**File / Doc / Commit → Term**

表示某个文件、文档或提交提到了某个术语。

**约束：**
- source: File / Doc / Commit 实体
- target: Term 实体

**证据来源：**
- `source_type`: "term_pattern" / "term_definition"
- `source_ref`: "path:line:col" or "commit:hash"
- `span`: 包含术语的句子

**示例：**
```json
{
  "id": "edge_003",
  "source": "file_001",
  "target": "term_001",
  "type": "mentions",
  "evidence": [
    {
      "source_type": "term_pattern",
      "source_ref": "agentos/core/task/manager.py:120:15",
      "span": "# Apply planning_guard to prevent unauthorized changes",
      "confidence": 0.95
    }
  ],
  "attrs": {}
}
```

### 4. DEPENDS_ON（依赖）

**File → File** (M3-P1 实现)

表示一个文件依赖另一个文件（通过 import/require 语句）。

**语义**:
- 文件级代码依赖关系
- 由 CodeExtractor 通过静态分析提取
- 置信度 = 1.0（静态导入是确定性的）

**约束：**
- source: File 实体（导入方）
- target: File 实体（被导入方）
- 仅限 repo 内文件（不包含第三方依赖）

**支持的导入类型**:

**Python**:
- 绝对导入: `import module.submodule`
- From 导入: `from module import name`
- 相对导入: `from . import sibling`, `from .. import parent`

**JavaScript/TypeScript**:
- ES6 import: `import foo from './module'`
- Named import: `import { named } from './module'`
- CommonJS: `const x = require('./module')`

**证据来源：**
- `source_type`: "code"
- `source_ref`: "source_file_path"
- `span`: import 语句原文
- `metadata.line`: 行号
- `metadata.import_type`: "python_import" | "js_import"

**创建条件**:
- 成功解析 import 语句
- 目标文件存在于 repo 内
- 非第三方依赖

**用途**:
- Impact 分析（谁依赖我？反向遍历）
- 依赖图可视化
- 变更影响评估
- 重构风险分析

**示例 (Python)**:
```json
{
  "id": "depends_on|src:file:agentos/core/task/manager.py|dst:file:agentos/core/task/models.py",
  "source": "file:agentos/core/task/manager.py",
  "target": "file:agentos/core/task/models.py",
  "type": "depends_on",
  "evidence": [
    {
      "source_type": "code",
      "source_ref": "agentos/core/task/manager.py",
      "span": "from agentos.core.task.models import Task",
      "confidence": 1.0,
      "metadata": {
        "line": 10,
        "import_type": "python_import"
      }
    }
  ],
  "attrs": {
    "import_type": "python_import",
    "import_statement": "from agentos.core.task.models import Task",
    "line": 10
  }
}
```

**示例 (JavaScript)**:
```json
{
  "id": "depends_on|src:file:frontend/App.js|dst:file:frontend/utils.js",
  "source": "file:frontend/App.js",
  "target": "file:frontend/utils.js",
  "type": "depends_on",
  "evidence": [
    {
      "source_type": "code",
      "source_ref": "frontend/App.js",
      "span": "import utils from './utils'",
      "confidence": 1.0,
      "metadata": {
        "line": 5,
        "import_type": "js_import"
      }
    }
  ],
  "attrs": {
    "import_type": "js_import",
    "import_statement": "import utils from './utils'",
    "line": 5
  }
}
```

### 5. IMPLEMENTS（实现）

**File / Symbol → Capability**

表示某个文件或符号实现了某个能力。

**约束：**
- source: File / Symbol 实体
- target: Capability 实体

**证据来源：**
- `source_type`: "code" / "doc_declaration"
- `source_ref`: "path:line:col"
- `span`: 相关代码片段

**示例：**
```json
{
  "id": "edge_005",
  "source": "file_003",
  "target": "capability_001",
  "type": "implements",
  "evidence": [
    {
      "source_type": "code",
      "source_ref": "agentos/core/extensions/loader.py:50:0",
      "span": "def load_extension(manifest: dict) -> Extension:",
      "confidence": 1.0
    }
  ],
  "attrs": {}
}
```

## 证据链（Evidence/Provenance）

每条边必须有至少一条证据，用于回答"这条关系是从哪里来的"。

**证据结构：**

```python
@dataclass
class Evidence:
    source_type: str           # 证据来源类型
    source_ref: str            # 具体引用位置
    span: Optional[str]        # 文本片段（可选）
    confidence: float          # 置信度 (0.0-1.0)
    metadata: Dict[str, Any]   # 其他元数据
```

### 证据来源类型（source_type）

| source_type       | 含义                   | 示例 source_ref                     |
|-------------------|------------------------|-------------------------------------|
| `git_log`         | Git 提交历史           | `commit:6aa4aaa`                    |
| `import`          | Python import 语句     | `file.py:10:0`                      |
| `require`         | JS require/import      | `file.js:5:0`                       |
| `doc_link`        | 文档链接               | `docs/adr.md:42:10`                 |
| `doc_mention`     | 文档提及               | `docs/readme.md:100:0`              |
| `term_pattern`    | 术语模式匹配           | `file.py:120:15`                    |
| `term_definition` | 术语定义               | `docs/glossary.md:20:0`             |
| `code`            | 代码定义/实现          | `file.py:50:0`                      |
| `ast`             | AST 分析结果           | `file.py:function:validate`         |

### 引用位置格式（source_ref）

**文件位置：**
```
path/to/file.py:line:col
```

**提交引用：**
```
commit:hash
```

**符号引用：**
```
path/to/file.py:class:ClassName
path/to/file.py:function:function_name
```

### 置信度（confidence）

- `1.0`: 确定性证据（如 import 语句、commit 记录）
- `0.9-0.99`: 高置信度（如 AST 分析、明确的文档链接）
- `0.7-0.89`: 中等置信度（如模式匹配、启发式规则）
- `0.5-0.69`: 低置信度（如模糊匹配、统计推断）
- `< 0.5`: 不建议使用（太不可靠）

## 存储表结构（SQLite）

### 1. entities 表

```sql
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    attrs_json TEXT,
    version_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_entities_type (type),
    INDEX idx_entities_key (key),
    INDEX idx_entities_version (version_id)
);
```

### 2. edges 表

```sql
CREATE TABLE edges (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    type TEXT NOT NULL,
    attrs_json TEXT,
    version_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source) REFERENCES entities(id),
    FOREIGN KEY (target) REFERENCES entities(id),
    INDEX idx_edges_source (source),
    INDEX idx_edges_target (target),
    INDEX idx_edges_type (type),
    INDEX idx_edges_version (version_id),
    UNIQUE (source, target, type, version_id)
);
```

### 3. evidence 表

```sql
CREATE TABLE evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    span TEXT,
    confidence REAL DEFAULT 1.0,
    metadata_json TEXT,
    FOREIGN KEY (edge_id) REFERENCES edges(id),
    INDEX idx_evidence_edge (edge_id)
);
```

### 4. versions 表

```sql
CREATE TABLE versions (
    version_id TEXT PRIMARY KEY,
    commit_hash TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    stats_json TEXT,
    extractor_versions_json TEXT,
    metadata_json TEXT
);
```

### 5. FTS5 全文搜索表

```sql
-- 实体全文搜索
CREATE VIRTUAL TABLE fts_entities USING fts5(
    entity_id UNINDEXED,
    name,
    attrs,
    content='entities',
    content_rowid='rowid'
);

-- 证据全文搜索
CREATE VIRTUAL TABLE fts_evidence USING fts5(
    evidence_id UNINDEXED,
    span,
    content='evidence',
    content_rowid='id'
);
```

## 数据示例

### 完整示例：一个 Commit 修改 File，Doc 引用 File

**实体：**
```json
[
  {
    "id": "commit_abc123",
    "type": "commit",
    "key": "abc123def456",
    "name": "Add retry mechanism",
    "attrs": {
      "hash": "abc123def456",
      "author": "John Doe",
      "date": "2026-01-15T10:00:00Z",
      "message": "Add retry mechanism to task manager"
    }
  },
  {
    "id": "file_manager",
    "type": "file",
    "key": "agentos/core/task/manager.py",
    "name": "manager.py",
    "attrs": {
      "path": "agentos/core/task/manager.py",
      "extension": ".py"
    }
  },
  {
    "id": "doc_adr_retry",
    "type": "doc",
    "key": "docs/adr/ADR_TASK_RETRY.md",
    "name": "ADR: Task Retry Strategy",
    "attrs": {
      "doc_type": "adr",
      "format": "markdown"
    }
  }
]
```

**关系边：**
```json
[
  {
    "id": "edge_commit_modifies_file",
    "source": "commit_abc123",
    "target": "file_manager",
    "type": "modifies",
    "evidence": [
      {
        "source_type": "git_log",
        "source_ref": "commit:abc123def456",
        "span": "M agentos/core/task/manager.py",
        "confidence": 1.0
      }
    ]
  },
  {
    "id": "edge_doc_references_file",
    "source": "doc_adr_retry",
    "target": "file_manager",
    "type": "references",
    "evidence": [
      {
        "source_type": "doc_link",
        "source_ref": "docs/adr/ADR_TASK_RETRY.md:50:10",
        "span": "Implementation: `agentos/core/task/manager.py`",
        "confidence": 1.0
      }
    ]
  }
]
```

## 查询模式

### 1. Why Query 模式

```sql
-- 找到引用某个文件的所有文档
SELECT d.*, e.evidence
FROM entities AS d
JOIN edges AS e ON e.source = d.id
WHERE e.target = 'file_manager'
  AND e.type = 'references'
  AND d.type = 'doc';
```

### 2. Impact Query 模式

```sql
-- 找到依赖某个文件的所有文件
SELECT f.*, e.evidence
FROM entities AS f
JOIN edges AS e ON e.source = f.id
WHERE e.target = 'file_manager'
  AND e.type = 'depends_on'
  AND f.type = 'file';
```

### 3. Trace Query 模式

```sql
-- 找到提到某个术语的所有提交（按时间排序）
SELECT c.*, e.evidence
FROM entities AS c
JOIN edges AS e ON e.source = c.id
WHERE e.target = 'term_planning_guard'
  AND e.type = 'mentions'
  AND c.type = 'commit'
ORDER BY json_extract(c.attrs_json, '$.date') DESC;
```

### 4. Map Query 模式

```sql
-- 2-hop 子图（BFS）
WITH RECURSIVE subgraph(entity_id, depth) AS (
  VALUES('file_manager', 0)
  UNION
  SELECT e.target, sg.depth + 1
  FROM subgraph AS sg
  JOIN edges AS e ON e.source = sg.entity_id
  WHERE sg.depth < 2
)
SELECT entities.*, subgraph.depth
FROM subgraph
JOIN entities ON entities.id = subgraph.entity_id;
```

## 扩展性考虑

### v0.2+ 扩展实体类型
- **Module**: Python 模块/包
- **Test**: 测试用例
- **Issue/PR**: GitHub Issue/Pull Request
- **Release**: 发布版本

### v0.2+ 扩展关系类型
- **INHERITS**: 类继承（Symbol → Symbol）
- **CALLS**: 函数调用（Symbol → Symbol）
- **TESTS**: 测试覆盖（Test → File/Symbol）
- **BELONGS_TO**: 归属关系（Symbol → File, File → Module）

---

## 查询输出 Schema (M2)

从 M2 开始，所有查询返回统一的 `QueryResult` 结构。

### QueryResult 数据类

```python
@dataclass
class QueryResult:
    """统一的查询结果结构"""
    graph_version: str                # 图版本号 (timestamp + commit)
    seed: Dict[str, Any]             # 查询种子
    result: Dict[str, Any]           # 查询特定的结果
    evidence: List[Dict[str, Any]]   # 证据列表
    stats: Dict[str, Any]            # 统计信息
```

### 1. Why Query 输出

```python
{
  "graph_version": "20260130-163235-6aa4aaa",
  "seed": {
    "type": "file",
    "key": "file:agentos/core/task/manager.py",
    "name": "manager.py"
  },
  "result": {
    "paths": [
      {
        "nodes": [
          {"type": "file", "key": "file:...", "name": "...", "created_at": 1700000000},
          {"type": "commit", "key": "commit:abc123", "name": "feat: add retry", "created_at": 1700000000}
        ],
        "edges": [
          {"type": "MODIFIES", "confidence": 1.0}
        ]
      }
    ]
  },
  "evidence": [
    {
      "id": 1,
      "edge_id": 1,
      "source_type": "git",
      "source_ref": "commit:abc123",
      "span": {},
      "attrs": {},
      "created_at": 1700000000
    }
  ],
  "stats": {
    "path_count": 1,
    "evidence_count": 1
  }
}
```

**字段说明**:
- `result.paths`: 从 seed 到起源的路径列表
- 路径按 confidence ↓, recency ↓ 排序

---

### 2. Impact Query 输出

```python
{
  "graph_version": "20260130-163235-6aa4aaa",
  "seed": {
    "type": "file",
    "key": "file:agentos/core/task/models.py",
    "name": "models.py"
  },
  "result": {
    "affected_nodes": [
      {"type": "file", "key": "file:agentos/core/task/manager.py", "name": "manager.py", "distance": 1},
      {"type": "file", "key": "file:agentos/core/task/service.py", "name": "service.py", "distance": 1}
    ],
    "risk_hints": [
      "Medium fan-out: 5 downstream files",
      "Recently modified: 2 commits in downstream files"
    ]
  },
  "evidence": [
    {
      "id": 1,
      "edge_id": 1,
      "source_type": "import",
      "source_ref": "file:agentos/core/task/manager.py:10:0",
      "span": {"start_line": 10, "end_line": 10},
      "attrs": {},
      "created_at": 1700000000
    }
  ],
  "stats": {
    "affected_count": 5,
    "max_depth": 1
  }
}
```

**字段说明**:
- `result.affected_nodes`: 受影响的下游节点（DEPENDS_ON 反向遍历）
- `result.risk_hints`: 风险评估提示（fan-out, recent changes）
- `distance`: 距离 seed 的跳数

---

### 3. Trace Query 输出

```python
{
  "graph_version": "20260130-163235-6aa4aaa",
  "seed": {
    "type": "term",
    "key": "term:websocket",
    "name": "websocket"
  },
  "result": {
    "timeline": [
      {
        "timestamp": 1700000000,
        "node": {"type": "commit", "key": "commit:abc123", "name": "feat: add websocket"},
        "relation": "MENTIONS",
        "evidence": {"source_type": "term_pattern", "source_ref": "commit:abc123"}
      },
      {
        "timestamp": 1700100000,
        "node": {"type": "doc", "key": "doc:websocket.md", "name": "WebSocket Guide"},
        "relation": "MENTIONS",
        "evidence": {"source_type": "doc", "source_ref": "doc:websocket.md:5:0"}
      }
    ],
    "nodes": [
      {"type": "term", "key": "term:websocket", "name": "websocket"},
      {"type": "commit", "key": "commit:abc123", "name": "feat: add websocket"},
      {"type": "doc", "key": "doc:websocket.md", "name": "WebSocket Guide"}
    ]
  },
  "evidence": [...],
  "stats": {
    "mention_count": 5,
    "time_span_days": 30
  }
}
```

**字段说明**:
- `result.timeline`: 按时间排序的 MENTIONS 事件列表（从最早到最近）
- `result.nodes`: 所有涉及的节点
- `time_span_days`: 最早到最近的时间跨度（天）

---

### 4. Subgraph Query 输出

```python
{
  "graph_version": "20260130-163235-6aa4aaa",
  "seed": {
    "type": "file",
    "key": "file:agentos/core/brain/__init__.py",
    "name": "__init__.py"
  },
  "result": {
    "nodes": [
      {"id": 1, "type": "file", "key": "file:...", "name": "...", "distance": 0},
      {"id": 2, "type": "commit", "key": "commit:...", "name": "...", "distance": 1},
      {"id": 3, "type": "file", "key": "file:...", "name": "...", "distance": 1}
    ],
    "edges": [
      {"id": 1, "src_id": 2, "dst_id": 1, "type": "MODIFIES", "confidence": 1.0},
      {"id": 2, "src_id": 3, "dst_id": 1, "type": "DEPENDS_ON", "confidence": 1.0}
    ],
    "top_evidence": [
      {"edge_id": 1, "source_type": "git", "source_ref": "commit:abc123"},
      {"edge_id": 2, "source_type": "import", "source_ref": "file:...:10:0"}
    ]
  },
  "evidence": [...],
  "stats": {
    "node_count": 5,
    "edge_count": 4,
    "k_hop": 1
  }
}
```

**字段说明**:
- `result.nodes`: K-hop 邻域内的所有节点（按 distance 排序）
- `result.edges`: 节点之间的所有边
- `result.top_evidence`: 前 N 条边的证据样本（避免大负载）
- `distance`: 距离 seed 的跳数（seed 为 0）

---

### Evidence 结构

所有查询的 `evidence` 字段包含完整证据列表：

```python
{
  "id": 1,                              # Evidence ID
  "edge_id": 1,                        # 对应的边 ID
  "source_type": "git",                # 证据类型：git/doc/code/import/term_pattern
  "source_ref": "commit:abc123",       # 源引用（commit hash / 文件路径:行:列）
  "span": {"start_line": 10, "end_line": 12},  # 可选：行号范围
  "attrs": {},                         # 可选：额外属性
  "created_at": 1700000000             # 创建时间戳
}
```

**硬规则**:
- ✅ `source_ref` 不可为空
- ✅ 每条边至少有一条 evidence
- ✅ Evidence 可追溯到具体位置

---

## 相关文档

- [BRAINOS_OVERVIEW.md](./BRAINOS_OVERVIEW.md) - BrainOS 概述
- [GOLDEN_QUERIES.md](./GOLDEN_QUERIES.md) - 黄金查询模板
- [ACCEPTANCE.md](./ACCEPTANCE.md) - 验收标准
- [DELIVERY_REPORT_M2.md](./DELIVERY_REPORT_M2.md) - M2 交付报告
