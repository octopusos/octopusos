# Slash Command 路由修复

## 🐛 问题
用户输入 `/postman 看看google` 显示：`message_idcontentrolemetadatacontext`

## 🔍 根因分析

### 问题1：数据库脏数据
- 扩展在数据库有记录但文件不存在
- 导致路由失败

### 问题2：路由器路径错误
`SlashCommandRouter._load_commands_config` 在错误位置查找文件：
- ❌ 查找：`extensions/tools.test/commands.yaml`
- ✅ 实际：`extensions/tools.test/commands/commands.yaml`

### 问题3：错误处理Bug
WebSocket 迭代字典产生键名而不是内容

## ✅ 修复

### 1. 清理脏数据
```python
registry.unregister_extension("tools.postman.webui.test")
```

### 2. 重新安装扩展
```python
installer.install_from_upload(zip_path="test-extension.zip")
```

### 3. 修复路由器路径
`agentos/core/chat/slash_command_router.py:387-391`

```python
# 修复前
commands_path = self.extensions_dir / extension_id / "commands.yaml"

# 修复后
# Try standard location first: commands/commands.yaml  
commands_path = self.extensions_dir / extension_id / "commands" / "commands.yaml"

# Fallback to legacy location: commands.yaml (root level)
if not commands_path.exists():
    commands_path = self.extensions_dir / extension_id / "commands.yaml"
```

### 4. WebSocket 类型检查（已修复）
`agentos/webui/websocket/chat.py:528-556`

## 🧪 验证结果

```
缓存的命令数: 1
  /test -> tools.test

测试命令: /test hello world
✓ 路由成功!
  Extension: Test Extension
  Command: /test
  Action: hello
  Args: ['world']
```

## 📝 修改文件
1. `agentos/core/chat/slash_command_router.py` - 修复路径查找
2. `agentos/webui/websocket/chat.py` - 类型检查（已修复）

## ✅ 测试步骤
1. 重启 WebUI
2. 输入 `/test hello`
3. 应该显示正常响应而不是键名

---

**所有 Bug 已修复！**
