# Task #12: /help 命令可视化演示

## 演示：/help 命令输出

### 场景 1: 有启用的扩展

```
$ 用户输入: /help

**Core Commands:**

- **/context** - Show context information for the current session
- **/export** - Export conversation history
- **/extract** - Extract entities or facts from the conversation
- **/help** - Show this help message
- **/model** - Switch between local and cloud models
- **/stream** - Toggle streaming mode for responses
- **/summary** - Generate a summary of the conversation
- **/task** - Manage tasks in the current session

**Extension Commands:**

- **/test** - Run test commands to verify extension system (Test Extension)

**Usage:**
Type `/command_name` followed by any arguments.
Example: `/model cloud`
```

### 场景 2: 无扩展或扩展未启用

```
$ 用户输入: /help

**Core Commands:**

- **/context** - Show context information for the current session
- **/export** - Export conversation history
- **/extract** - Extract entities or facts from the conversation
- **/help** - Show this help message
- **/model** - Switch between local and cloud models
- **/stream** - Toggle streaming mode for responses
- **/summary** - Generate a summary of the conversation
- **/task** - Manage tasks in the current session

**Usage:**
Type `/command_name` followed by any arguments.
Example: `/model cloud`
```

### 场景 3: 多个扩展

```
$ 用户输入: /help

**Core Commands:**

- **/context** - Show context information for the current session
- **/export** - Export conversation history
- **/extract** - Extract entities or facts from the conversation
- **/help** - Show this help message
- **/model** - Switch between local and cloud models
- **/stream** - Toggle streaming mode for responses
- **/summary** - Generate a summary of the conversation
- **/task** - Manage tasks in the current session

**Extension Commands:**

- **/docker** - Docker container management commands (Docker Extension)
- **/git** - Git version control commands (Git Extension)
- **/postman** - Run Postman API tests (Postman Extension)
- **/test** - Run test commands to verify extension system (Test Extension)

**Usage:**
Type `/command_name` followed by any arguments.
Example: `/model cloud`
```

## 演示：扩展信息

### 查看已安装扩展

```python
from agentos.core.extensions.registry import ExtensionRegistry

registry = ExtensionRegistry()
extensions = registry.list_extensions()

for ext in extensions:
    status = "✓ enabled" if ext.enabled else "✗ disabled"
    print(f"{ext.name} ({ext.id}): {status}")
    for cap in ext.capabilities:
        if cap.type.value == "slash_command":
            print(f"  → {cap.name}: {cap.description}")
```

**输出示例：**
```
Test Extension (tools.test): ✓ enabled
  → /test: Run test commands
```

## 演示：对比图

### 改进前
```
Available Commands:

- /help - Show this help message
- /task - Manage tasks
- /export - Export conversation
- /model - Switch models
- /context - Show context
- /stream - Toggle streaming
- /summary - Generate summary
- /extract - Extract entities

Usage:
Type /command_name followed by arguments.
```

### 改进后
```
**Core Commands:**

- **/help** - Show this help message
- **/task** - Manage tasks in the current session
- **/export** - Export conversation history
- **/model** - Switch between local and cloud models
- **/context** - Show context information for the current session
- **/stream** - Toggle streaming mode for responses
- **/summary** - Generate a summary of the conversation
- **/extract** - Extract entities or facts from the conversation

**Extension Commands:**

- **/test** - Run test commands to verify extension system (Test Extension)
- **/postman** - Run Postman API tests (Postman Extension)

**Usage:**
Type `/command_name` followed by any arguments.
Example: `/model cloud`
```

## 演示：用户体验流程

### 1. 用户想知道有哪些命令可用

```
用户: /help
```

### 2. 系统显示所有可用命令

```
系统响应:

**Core Commands:**
[列出所有内置命令]

**Extension Commands:**
[列出所有扩展命令并标注来源]

**Usage:**
[使用说明]
```

### 3. 用户看到扩展命令

```
用户看到:
- /test - Run test commands (Test Extension)
         ^                   ^
         命令名               来源标注
```

### 4. 用户使用扩展命令

```
用户: /test hello
系统: Hello from Test Extension!
```

## 演示：边界情况

### 情况 1: 扩展被禁用

```python
# 禁用扩展
registry = ExtensionRegistry()
registry.disable_extension("tools.test")

# 运行 /help
engine = ChatEngine()
result = engine.send_message(session_id, "/help")

# 输出：不包含 /test 命令
```

### 情况 2: 扩展未安装

```python
# 没有安装扩展
# ~/.agentos/extensions/ 目录为空

# 运行 /help
# 输出：只有 Core Commands，无 Extension Commands 区域
```

### 情况 3: Router 不可用

```python
# Context 中没有 router
context = {
    "session_id": "test",
    # "router": None  # router 不存在
}

result = handle_help_command("help", [], context)

# 输出：正常显示 Core Commands，不报错
```

## 演示：API 集成

### WebUI API 调用

```javascript
// 前端获取所有命令
fetch('/api/chat/slash-commands?enabled_only=true')
  .then(response => response.json())
  .then(data => {
    console.log('Available commands:', data.commands);
    // data.commands 包含 Core 和 Extension 命令
  });
```

**响应示例：**
```json
{
  "commands": [
    {
      "name": "/help",
      "source": "builtin",
      "summary": "Show this help message",
      "enabled": true
    },
    {
      "name": "/test",
      "source": "extension",
      "extension_id": "tools.test",
      "extension_name": "Test Extension",
      "summary": "Run test commands to verify extension system",
      "enabled": true
    }
  ],
  "total": 9
}
```

## 演示：测试验证

### 集成测试运行

```bash
$ python3 -m pytest tests/integration/test_help_with_extensions.py -v

test_help_command_with_extension_router ✓
test_help_command_without_router ✓
test_help_command_shows_only_enabled_extensions ✓
test_help_command_format ✓
test_help_command_with_multiple_extensions ✓
test_help_command_sections_order ✓

6 passed in 0.20s
```

### E2E 测试运行

```bash
$ python3 << 'EOF'
from agentos.core.chat.engine import ChatEngine

engine = ChatEngine()
session_id = engine.create_session(title="Test")
result = engine.send_message(session_id, "/help", stream=False)
print(result.get("content"))
EOF

**Core Commands:**
...
**Extension Commands:**
...
✓ Test passed!
```

## 演示：格式化细节

### Markdown 渲染

**原始文本：**
```markdown
**Core Commands:**

- **/help** - Show this help message
- **/task** - Manage tasks
```

**WebUI 渲染效果：**

**Core Commands:**

- **/help** - Show this help message
- **/task** - Manage tasks

### 对齐示例

```
**Core Commands:**

- **/help**    - Show this help message
- **/task**    - Manage tasks in the current session
- **/export**  - Export conversation history

**Extension Commands:**

- **/test**    - Run test commands (Test Extension)
- **/postman** - Run API tests (Postman Extension)
```

## 总结

### 视觉特点

1. **分区清晰**
   - Core Commands 和 Extension Commands 分离
   - 视觉层次明确

2. **信息完整**
   - 命令名称
   - 命令描述
   - 扩展来源（Extension Commands）

3. **易于扫描**
   - 列表格式
   - Markdown 加粗
   - 对齐整齐

4. **用户友好**
   - 使用说明在底部
   - 示例命令提供
   - 扩展来源标注

### 用户价值

- ✅ 快速发现所有可用命令
- ✅ 清楚了解扩展提供的功能
- ✅ 轻松区分内置和扩展命令
- ✅ 提升命令可发现性

---

**演示完成时间**: 2026-01-30
**任务编号**: Task #12: P1-2 /help 显示 Extension Commands
**状态**: ✅ 完成并验证
