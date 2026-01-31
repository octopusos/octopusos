# KB 命令使用指南

## 快速开始

### 在 TUI 中使用

1. **打开命令面板**（主屏幕）
2. **选择 KB 类别**
3. **选择命令**
4. **按 `?` 查看帮助**（任何时候）

### 常用命令

#### 1. 搜索文档
```bash
# TUI: 在命令面板选择 "kb:search" → 输入查询
# CLI:
agentos kb search "JWT authentication"
agentos kb search "API design" --scope docs/architecture/
```

#### 2. 查看统计
```bash
# TUI: 选择 "kb:stats" → 直接执行（无需参数）
# CLI:
agentos kb stats
```

#### 3. 刷新索引
```bash
# TUI: 选择 "kb:refresh"
# CLI:
agentos kb refresh              # 增量刷新
agentos kb refresh --full       # 全量刷新
```

#### 4. 解释搜索结果
```bash
# TUI: 选择 "kb:explain" → 输入 chunk_id
# CLI:
# 先搜索获取 chunk_id
agentos kb search "authentication"
# 然后解释特定结果
agentos kb explain chunk_abc123def456
```

#### 5. 检查 chunk 详情
```bash
# TUI: 选择 "kb:inspect" → 输入 chunk_id
# CLI:
agentos kb inspect chunk_abc123def456
```

## TUI 快捷键

### 命令面板
- `↑↓` - 导航
- `Enter` - 选择/执行
- `ESC` - 返回/取消
- `?` - 显示帮助（在命令列表时）
- `Type` - 搜索命令

### 提示标记
- `(requires arg)` - 命令需要参数，会提示输入

## 命令参考

### kb:search
搜索文档和代码

**参数：**
- `query` - 搜索关键词（必需）

**选项：**
- `--scope` - 路径前缀过滤
- `--doc-type` - 文档类型过滤
- `--top-k` - 返回结果数量
- `--rerank` - 使用向量重排

### kb:refresh
刷新知识库索引

**选项：**
- `--full` - 全量刷新（默认增量）

### kb:stats
显示统计信息

**无参数**

显示：
- 总 chunks 数
- Schema 版本
- 最后刷新时间
- Embedding 统计（如启用）

### kb:explain
解释搜索结果

**参数：**
- `chunk_id` - Chunk ID（必需）

**注意：** 从 `kb:search` 结果获取 chunk_id

### kb:inspect
检查 chunk 详细信息

**参数：**
- `chunk_id` - Chunk ID（必需）

显示：
- Chunk 内容
- 源文件路径
- 行号范围
- 文档类型
- Token 数量
- 元数据

### kb:repair
修复和优化索引

**选项：**
- `--rebuild-fts` - 重建全文搜索索引
- `--cleanup-orphans` - 清理孤儿 chunks

### kb:eval
评估搜索质量

**参数：**
- `queries_file` - JSONL 测试文件（必需）

**选项：**
- `--k-values` - Recall@K 的 K 值列表
- `--rerank` - 使用向量重排

**JSONL 格式：**
```json
{"query": "JWT auth", "expected_chunk_ids": ["chunk_abc", "chunk_def"]}
```

### kb:reindex
完全重建索引（危险）

**选项：**
- `--confirm` - 确认执行（必需）

**⚠️ 警告：** 此操作会删除所有 chunks 和 embeddings！

## 工作流示例

### 1. 初次使用
```bash
# 刷新索引
agentos kb refresh --full

# 查看统计
agentos kb stats
```

### 2. 日常使用
```bash
# 搜索相关文档
agentos kb search "authentication flow"

# 查看详细内容（从搜索结果获取 chunk_id）
agentos kb inspect chunk_abc123

# 增量刷新（文档有更新时）
agentos kb refresh
```

### 3. 调试问题
```bash
# 检查统计
agentos kb stats

# 修复索引
agentos kb repair --rebuild-fts

# 如果需要，完全重建
agentos kb reindex --confirm
```

## 获取帮助

### TUI 中
1. 选择任何 KB 命令
2. 按 `?` 查看详细帮助

### CLI 中
```bash
# 查看命令列表
agentos kb --help

# 查看特定命令帮助
agentos kb search --help
```

## 提示和技巧

1. **搜索技巧**
   - 使用具体的关键词
   - 结合 `--scope` 限制搜索范围
   - 使用 `--rerank` 提高相关性

2. **性能优化**
   - 定期运行 `kb:refresh` 保持索引最新
   - 使用 `kb:repair` 优化索引
   - 启用向量重排获得更好的搜索结果

3. **问题排查**
   - 首先检查 `kb:stats` 确认索引状态
   - 使用 `kb:repair` 修复常见问题
   - 查看 `kb:inspect` 了解具体 chunk 内容
