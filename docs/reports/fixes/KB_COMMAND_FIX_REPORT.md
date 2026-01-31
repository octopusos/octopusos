# KB 命令修复报告

## 修复时间
2026-01-26

## 问题描述

1. **`ProjectKBService.stats()` 方法缺失**
   - 错误：`'ProjectKBService' object has no attribute 'stats'`
   - 位置：`agentos/core/command/handlers/kb_handlers.py:75`
   - 影响：`kb:stats` 命令无法执行

2. **`kb:explain` 命令参数说明不清晰**
   - 问题：用户不知道 `kb:explain` 需要什么参数以及如何使用
   - 影响：所有需要参数的 KB 二级命令都没有使用说明

## 修复内容

### 1. 添加 `stats()` 方法到 `ProjectKBService`

**文件：** `agentos/core/project_kb/service.py`

添加了 `stats()` 方法，返回 KB 统计信息：

```python
def stats(self) -> dict:
    """获取 ProjectKB 统计信息
    
    Returns:
        统计信息字典
    """
    stats_dict = {
        "total_chunks": self.indexer.get_chunk_count(),
        "schema_version": self.indexer.get_meta("schema_version"),
        "last_refresh": self.indexer.get_meta("last_refresh"),
    }
    
    # P2: 添加 embedding 统计 (如果启用)
    if self.embedding_manager:
        embed_stats = self.embedding_manager.get_stats()
        stats_dict["embeddings"] = {
            "total": embed_stats["total"],
            "by_model": embed_stats["by_model"],
            "latest_built_at": embed_stats["latest_built_at"],
        }
        
        # 计算覆盖率
        total_chunks = stats_dict["total_chunks"]
        if total_chunks > 0:
            stats_dict["embeddings"]["coverage"] = embed_stats["total"] / total_chunks
    
    return stats_dict
```

### 2. 添加 `help_text` 字段到 `CommandMetadata`

**文件：** `agentos/core/command/types.py`

扩展了 `CommandMetadata` 数据类，添加了 `help_text` 字段：

```python
@dataclass
class CommandMetadata:
    """命令元数据"""
    id: str
    title: str
    hint: str
    category: CommandCategory
    handler: Callable
    needs_arg: bool = False
    requires_context: list[str] = field(default_factory=list)
    dangerous: bool = False
    help_text: Optional[str] = None  # 新增：详细帮助文档
```

### 3. 为所有 KB 命令添加详细的帮助文档

**文件：** `agentos/core/command/handlers/kb_handlers.py`

为每个 KB 命令添加了详细的 `help_text`：

- `kb:search` - 搜索文档，包含用法、选项和示例
- `kb:refresh` - 刷新索引，说明增量和全量模式
- `kb:stats` - 显示统计信息，说明显示内容
- `kb:explain` - 解释结果，说明如何获取 chunk_id
- `kb:repair` - 修复索引，说明各种选项
- `kb:inspect` - 检查 chunk，说明显示的详细信息
- `kb:eval` - 评估搜索质量，说明 JSONL 格式
- `kb:reindex` - 重建索引，警告危险操作

示例（`kb:explain`）：

```python
CommandMetadata(
    id="kb:explain",
    title="Explain KB result",
    hint="Usage: kb:explain <chunk_id>",
    category=CommandCategory.KB,
    handler=kb_explain_handler,
    needs_arg=True,
    help_text="""Show detailed explanation for a specific chunk.

Arguments:
  chunk_id    The ID of the chunk to explain (required)
              Get chunk_id from search results

Example:
  kb:explain chunk_abc123def456
  
Note: Run kb:search first to get chunk IDs from results""",
)
```

### 4. 在命令面板中添加帮助功能

**文件：** `agentos/ui/widgets/command_palette.py`

1. 添加了 `?` 快捷键绑定：
   ```python
   BINDINGS = [
       # ... 其他绑定 ...
       ("question_mark", "show_help", "Help"),
   ]
   ```

2. 实现了 `action_show_help()` 方法：
   - 显示当前选中命令的详细帮助信息
   - 如果没有详细帮助，显示 hint

3. 在命令列表中显示 `(requires arg)` 标记：
   ```python
   text = f"{cmd.key:<12} {cmd.title}"
   if cmd.needs_arg:
       text += " [dim](requires arg)[/dim]"
   ```

### 5. 更新状态栏提示文本

**文件：** `agentos/ui/screens/home.py`

在命令列表模式下显示 "? help" 提示：

```python
elif cp.mode == CommandPaletteMode.COMMANDS:
    # Commands mode
    hint.update("↑↓ navigate · ? help · Enter select · ESC back")
```

### 6. 修复参数路由问题

**文件：** `agentos/ui/screens/home.py`

修复了 `kb:explain` 和 `kb:inspect` 的参数路由：

```python
if argument:
    if command_id == "kb:search":
        kwargs["query"] = argument
    elif command_id == "kb:explain":
        kwargs["chunk_id"] = argument
    elif command_id == "kb:inspect":
        kwargs["chunk_id"] = argument
    elif command_id == "kb:eval":
        kwargs["queries_file"] = argument
    # ... 其他路由
```

## 测试验证

创建了 `test_kb_fixes.py` 验证脚本，测试：

1. ✅ `ProjectKBService.stats()` 方法存在并正常工作
2. ✅ 命令元数据正确注册，包含 `help_text`
3. ✅ `CommandMetadata.help_text` 字段正常工作

所有测试通过：

```
============================================================
测试汇总
============================================================
  ✓ PASS  stats 方法
  ✓ PASS  命令元数据
  ✓ PASS  help_text 字段

总计: 3/3 通过

🎉 所有测试通过！
```

## 使用说明

### 在 TUI 中查看命令帮助

1. 打开命令面板（主屏幕）
2. 选择一个类别（如 KB）
3. 导航到任意命令
4. 按 `?` 键查看详细帮助

### 在 CLI 中使用

所有 KB 命令现在都有清晰的使用说明：

```bash
# 搜索文档
agentos kb search "JWT authentication"

# 显示统计信息（无需参数）
agentos kb stats

# 解释特定 chunk（需要 chunk_id）
agentos kb explain chunk_abc123def456

# 检查 chunk 详情
agentos kb inspect chunk_abc123def456

# 评估搜索质量
agentos kb eval queries.jsonl
```

## 受影响的文件

1. `agentos/core/project_kb/service.py` - 添加 `stats()` 方法
2. `agentos/core/command/types.py` - 添加 `help_text` 字段
3. `agentos/core/command/handlers/kb_handlers.py` - 添加所有命令的帮助文档
4. `agentos/ui/widgets/command_palette.py` - 添加 `?` 帮助功能
5. `agentos/ui/screens/home.py` - 更新提示文本和参数路由
6. `test_kb_fixes.py` - 验证测试脚本（新增）

## 后续建议

1. **扩展到其他命令类别**
   - 为 Memory、Task、History 命令也添加详细的 `help_text`
   
2. **增强帮助显示**
   - 考虑使用对话框显示完整的帮助文本，而不仅仅是通知
   - 支持 Markdown 格式的帮助文档
   
3. **CLI 帮助集成**
   - 在 CLI 中也支持 `--help` 显示详细帮助
   
4. **文档生成**
   - 从 `help_text` 自动生成命令参考文档

## 总结

本次修复解决了两个关键问题：

1. ✅ 修复了 `kb:stats` 命令的运行时错误
2. ✅ 为所有 KB 命令添加了清晰的使用说明

用户现在可以：
- 正常使用 `kb:stats` 命令
- 通过 `?` 键在 TUI 中查看任何命令的详细帮助
- 在命令面板中看到哪些命令需要参数
- 通过示例了解如何正确使用每个命令
