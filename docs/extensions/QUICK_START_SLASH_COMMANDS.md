# Quick Start: Slash Command Routing

## 5 分钟快速上手

### 1. 了解 Slash Command

Slash Command 是一种特殊的聊天命令，以 `/` 开头，用于调用扩展功能。

```
用户输入: /postman get https://api.example.com
          ↓
系统识别: 这是一个 slash command
          ↓
路由到:   Postman 扩展
          ↓
执行:     发送 GET 请求并返回结果
```

### 2. 用户使用

```bash
# 查看可用命令（前端自动完成功能）
输入 / 即可看到所有可用命令

# 使用扩展命令
/postman get https://httpbin.org/get
/postman test collection.json --env dev
/hello
```

### 3. 扩展开发者

#### 步骤 1: 定义命令（commands.yaml）

```yaml
slash_commands:
  - name: "/hello"
    summary: "Simple hello world command"
    description: "Prints a hello message"
    examples:
      - "/hello"
      - "/hello World"
    maps_to:
      capability: "examples.hello"
      actions:
        - id: "default"
          description: "Say hello"
          runner: "echo.hello"
```

#### 步骤 2: 创建使用文档（docs/USAGE.md）

```markdown
# Hello Extension Usage

## Command

Say hello:
```
/hello [name]
```

Example:
```
/hello World
→ "Hello, World!"
```

#### 步骤 3: 实现 Runner（runners/echo_hello.py）

```python
def execute(args, context):
    name = args[0] if args else "World"
    return f"Hello, {name}!"
```

#### 步骤 4: 声明 Capability（manifest.json）

```json
{
  "capabilities": [
    {
      "type": "slash_command",
      "name": "examples.hello",
      "description": "Hello world command"
    }
  ]
}
```

### 4. 系统集成

#### 在代码中使用

```python
from agentos.core.chat.engine import ChatEngine

# 创建 Chat Engine
engine = ChatEngine()

# 创建会话
session_id = engine.create_session(title="Test")

# 发送命令
response = engine.send_message(
    session_id=session_id,
    user_input="/postman get https://api.example.com"
)

# 检查结果
if 'extension_command' in response['metadata']:
    print(f"✅ Extension: {response['metadata']['extension_id']}")
    print(f"✅ Action: {response['metadata']['action_id']}")
```

#### 刷新命令缓存

```python
from agentos.core.chat.slash_command_router import SlashCommandRouter
from agentos.core.extensions.registry import ExtensionRegistry

registry = ExtensionRegistry()
router = SlashCommandRouter(registry)

# 安装/启用扩展后刷新
router.refresh_cache()
```

### 5. API 使用

#### 获取可用命令

```bash
GET /api/chat/slash-commands?enabled_only=true

Response:
{
  "commands": [
    {
      "name": "/postman",
      "source": "extension",
      "extension_id": "tools.postman",
      "summary": "Run API tests",
      "examples": ["/postman get https://example.com"],
      "enabled": true
    }
  ],
  "total": 1
}
```

#### 刷新命令

```bash
POST /api/chat/refresh-commands

Response:
{
  "success": true,
  "total_commands": 5
}
```

### 6. 测试

```python
# 单元测试
from agentos.core.chat.slash_command_router import CommandParser

def test_parse():
    parser = CommandParser()
    result = parser.parse("/postman get https://api.example.com")

    assert result['command'] == "/postman"
    assert result['action'] == "get"
    assert result['args'] == ["https://api.example.com"]

# 集成测试
def test_route():
    engine = ChatEngine()
    session_id = engine.create_session()

    response = engine.send_message(
        session_id=session_id,
        user_input="/hello"
    )

    assert 'extension_command' in response['metadata']
```

### 7. 常见问题

#### Q: 命令不生效？

```python
# 检查扩展是否启用
registry = ExtensionRegistry()
extension = registry.get_extension("tools.postman")
print(f"Enabled: {extension.enabled}")

# 如果禁用，启用它
registry.enable_extension("tools.postman")

# 刷新命令缓存
router.refresh_cache()
```

#### Q: 如何调试命令解析？

```python
from agentos.core.chat.slash_command_router import CommandParser

parser = CommandParser()
result = parser.parse(user_input)

print(f"Command: {result['command']}")
print(f"Action: {result['action']}")
print(f"Args: {result['args']}")
print(f"Raw: {result['raw_args']}")
```

#### Q: 如何查看已缓存的命令？

```python
router = SlashCommandRouter(registry)
print(f"Cached commands: {list(router.command_cache.keys())}")

# 查看详细信息
for cmd_name, (ext_id, config) in router.command_cache.items():
    print(f"{cmd_name} → {ext_id}")
```

### 8. 完整示例

```python
#!/usr/bin/env python3
"""
Complete example: Using slash commands in a chat application
"""

from agentos.core.chat.engine import ChatEngine
from agentos.core.extensions.registry import ExtensionRegistry
from agentos.core.chat.slash_command_router import SlashCommandRouter

def main():
    # 1. Initialize components
    registry = ExtensionRegistry()
    router = SlashCommandRouter(registry)
    engine = ChatEngine(
        extension_registry=registry,
        slash_command_router=router
    )

    # 2. Create session
    session_id = engine.create_session(title="Demo Session")

    # 3. Get available commands
    commands = router.get_available_commands(enabled_only=True)
    print("Available commands:")
    for cmd in commands:
        print(f"  {cmd.command_name}: {cmd.summary}")

    # 4. Send command
    response = engine.send_message(
        session_id=session_id,
        user_input="/postman get https://httpbin.org/get"
    )

    # 5. Handle response
    if 'extension_command' in response['metadata']:
        print(f"\n✅ Command executed successfully!")
        print(f"Extension: {response['metadata']['extension_id']}")
        print(f"Action: {response['metadata']['action_id']}")
        print(f"\nResponse:\n{response['content']}")
    else:
        print(f"\n❌ Command failed:\n{response['content']}")

if __name__ == "__main__":
    main()
```

运行：
```bash
python3 demo.py

Output:
Available commands:
  /postman: Run API tests via Postman CLI
  /hello: Hello world example

✅ Command executed successfully!
Extension: tools.postman
Action: get

Response:
Extension command '/postman' routed successfully!
...
```

### 9. 下一步

- 📖 阅读完整文档: [SLASH_COMMAND_ROUTING.md](./SLASH_COMMAND_ROUTING.md)
- 🔧 查看示例扩展: PR-F
- 🚀 实现 Capability Runner: PR-E
- 🎨 集成前端 UI: PR-C

### 10. 资源

- **源代码**: `/agentos/core/chat/slash_command_router.py`
- **单元测试**: `/tests/unit/core/chat/test_slash_command_router.py`
- **集成测试**: `/tests/integration/test_slash_command_integration.py`
- **API 端点**: `/agentos/webui/api/chat_commands.py`
- **完整文档**: `/docs/extensions/SLASH_COMMAND_ROUTING.md`

---

**祝你使用愉快！如有问题，请查看完整文档或提交 Issue。**
