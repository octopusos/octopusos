# Task #12: /help 显示 Extension Commands - 快速参考

## 快速概述

✅ `/help` 命令现在分为两个区域显示：
- **Core Commands** - 内置命令
- **Extension Commands** - 扩展命令（标注来源）

## 使用方法

### 在 Chat 中使用

```bash
# 用户在聊天中输入
/help

# 输出示例
**Core Commands:**

- **/help** - Show this help message
- **/task** - Manage tasks in the current session
- **/export** - Export conversation history

**Extension Commands:**

- **/test** - Run test commands (Test Extension)
- **/postman** - Run API tests (Postman Extension)
```

### 在代码中使用

```python
from agentos.core.chat.engine import ChatEngine

# 创建 ChatEngine
engine = ChatEngine()

# 创建会话
session_id = engine.create_session(title="Test")

# 发送 /help 命令
result = engine.send_message(
    session_id=session_id,
    user_input="/help",
    stream=False
)

# 获取帮助文本
help_text = result.get("content")
print(help_text)
```

## 技术实现

### 1. help_handler.py

```python
# 从 context 获取 router
router = context.get('router')

if router:
    # 获取启用的扩展命令
    extension_commands = router.get_available_commands(enabled_only=True)

    # 格式化输出
    for cmd_info in extension_commands:
        help_text += f"- **{cmd_info.command_name}** - {cmd_info.summary} ({cmd_info.extension_name})\n"
```

### 2. engine.py

```python
# 在 _execute_command 中添加 router
context = {
    "session_id": session_id,
    "chat_service": self.chat_service,
    "task_manager": self.task_manager,
    "memory_service": self.memory_service,
    "router": self.slash_command_router  # 新增
}
```

## 输出格式

### 格式规范

```
**Core Commands:**

- **/{command}** - {description}
...

**Extension Commands:**

- **/{command}** - {description} ({Extension Name})
...

**Usage:**
...
```

### 格式特点

1. **分区清晰**：Core 和 Extension 明确分离
2. **来源标注**：Extension 命令标注来源 `(Extension Name)`
3. **对齐美观**：使用 Markdown 列表格式
4. **只显示启用**：只显示 `enabled=True` 的扩展

## 测试验证

### 运行测试

```bash
# 集成测试
python3 -m pytest tests/integration/test_help_with_extensions.py -v

# 预期结果
============================== 6 passed ==============================
```

### 手动测试

```python
# 测试脚本
python3 << 'EOF'
from agentos.core.chat.engine import ChatEngine

engine = ChatEngine()
session_id = engine.create_session(title="Test")

result = engine.send_message(
    session_id=session_id,
    user_input="/help",
    stream=False
)

print(result.get("content"))
EOF
```

## 常见问题

### Q1: 为什么看不到 Extension Commands？

**A**: 检查以下几点：
1. 是否有安装扩展？
   ```bash
   ls ~/.agentos/extensions/
   ```

2. 扩展是否启用？
   ```python
   from agentos.core.extensions.registry import ExtensionRegistry
   registry = ExtensionRegistry()
   extensions = registry.list_extensions()
   for ext in extensions:
       print(f"{ext.id}: enabled={ext.enabled}")
   ```

3. 扩展是否有 slash_command capability？
   ```bash
   cat ~/.agentos/extensions/{extension_id}/manifest.json
   ```

### Q2: 如何添加新的扩展命令？

**A**: 创建扩展时添加 slash_command capability：

```json
// manifest.json
{
  "capabilities": [
    {
      "type": "slash_command",
      "name": "/mycommand",
      "description": "My custom command"
    }
  ]
}
```

### Q3: Extension Commands 显示顺序是什么？

**A**: 按命令名称字母序排序（`/a` < `/b` < `/c`）

### Q4: 如何刷新扩展命令列表？

**A**:
```python
# 方法 1: 通过 API
POST /api/chat/refresh-commands

# 方法 2: 通过代码
from agentos.core.chat.slash_command_router import SlashCommandRouter
from agentos.core.extensions.registry import ExtensionRegistry

registry = ExtensionRegistry()
router = SlashCommandRouter(registry)
router.refresh_cache()
```

## 相关文件

### 核心实现

- `agentos/core/chat/handlers/help_handler.py` - /help 命令处理
- `agentos/core/chat/engine.py` - Context 传递
- `agentos/core/chat/slash_command_router.py` - 扩展命令路由

### 测试文件

- `tests/integration/test_help_with_extensions.py` - 集成测试

### API 端点

- `agentos/webui/api/chat_commands.py` - WebUI API
  - `GET /api/chat/slash-commands` - 获取所有命令
  - `POST /api/chat/refresh-commands` - 刷新命令缓存

## 验收清单

- [x] /help 输出分为 Core Commands 和 Extension Commands
- [x] Extension Commands 标注来源 (Extension Name)
- [x] 只显示 enabled=True 的扩展
- [x] 格式清晰美观
- [x] 向后兼容（无 router 时不报错）
- [x] 集成测试通过 (6/6)
- [x] 现有测试不受影响 (17/17)

## 下一步优化

### 可选功能

1. **命令分类**
   - 按功能分组显示 Extension Commands
   - API Tools / Development / Testing

2. **命令搜索**
   - `/help <keyword>` 搜索相关命令
   - 支持模糊匹配

3. **命令详情**
   - `/help <command>` 显示特定命令详细信息
   - 包含用法示例和参数说明

4. **统计信息**
   - 显示扩展命令总数
   - 显示已启用/已禁用扩展数量

---

**完成时间**: 2026-01-30
**状态**: ✅ 完成并验证
**任务编号**: Task #12: P1-2 /help 显示 Extension Commands
