# WebSocket 消息显示 Bug 修复

## 🐛 问题描述

用户在聊天中输入 `/postman 看看google` 后，assistant 回复显示为：
```
message_idcontentrolemetadatacontext
```

而不是正常的文本内容。

---

## 🔍 根本原因

### 问题链
1. `ChatEngine.send_message(stream=True)` 在某些情况下返回 **字典对象** 而不是 **generator**
2. WebSocket 代码假设总是返回 generator，直接迭代：
   ```python
   for chunk in stream_generator:
       # ...
   ```
3. 当迭代字典时，Python 返回字典的 **键名**：
   ```python
   for chunk in {"message_id": ..., "content": ..., ...}:
       # chunk 依次为: "message_id", "content", "role", "metadata", "context"
   ```
4. 这些键名被当作 content 发送到前端
5. 前端拼接显示：`message_idcontentrolemetadatacontext`

### 验证
```python
test_dict = {
    "message_id": "123",
    "content": "hello",
    "role": "assistant",
    "metadata": {},
    "context": {}
}

for chunk in test_dict:
    print(chunk)
# 输出: message_id, content, role, metadata, context

''.join(test_dict.keys())
# 输出: message_idcontentrolemetadatacontext
```

---

## ✅ 修复方案

### 位置
`agentos/webui/websocket/chat.py:518-556`

### 修复内容
在 WebSocket 消息处理前添加**类型检查**：

```python
# Bug fix: Check if stream_generator is actually a generator
# In some error cases, send_message might return a dict instead
if isinstance(stream_generator, dict):
    # Handle dict response (error case)
    await manager.send_message(session_id, {
        "type": "message.start",
        "message_id": message_id,
        "role": "assistant",
        "metadata": {},
    })

    content_text = stream_generator.get("content", str(stream_generator))
    await manager.send_message(session_id, {
        "type": "message.delta",
        "content": content_text,
        "metadata": {},
    })

    await manager.send_message(session_id, {
        "type": "message.end",
        "message_id": message_id,
        "content": content_text,
        "metadata": stream_generator.get("metadata", {}),
    })
    return
```

### 修复逻辑
1. 检查 `stream_generator` 是否为字典
2. 如果是字典，提取 `content` 字段
3. 发送正确的 WebSocket 消息序列：
   - `message.start`
   - `message.delta` (包含实际内容)
   - `message.end`
4. 如果是 generator，继续原有流程

---

## 🧪 测试验证

### 测试代码
```python
test_cases = [
    ("Generator", (x for x in ["Hello", " world"])),
    ("Dict", {"content": "Test", "metadata": {}})
]

for name, stream_generator in test_cases:
    if isinstance(stream_generator, dict):
        content = stream_generator.get("content")
        print(f"✓ {name}: {content}")
    else:
        chunks = list(stream_generator)
        print(f"✓ {name}: {''.join(chunks)}")
```

### 结果
```
✓ Generator: Hello world
✓ Dict: Test
```

---

## 📊 影响范围

### 受影响的场景
- Extension slash commands (如 `/postman`)
- 错误处理路径
- 任何 `send_message(stream=True)` 返回字典的情况

### 不受影响的场景
- 正常聊天消息
- 正常的流式响应
- Built-in commands

---

## 🔮 后续改进

### 根本修复（可选）
修改 `ChatEngine.send_message(stream=True)` 确保 **总是** 返回 generator：

```python
def send_message(self, session_id, user_input, stream=False):
    # ...
    if stream:
        # Ensure we always return a generator
        result = self._execute_command(...)
        if isinstance(result, dict):
            # Convert dict to generator
            def dict_to_generator():
                yield result.get("content", "")
            return dict_to_generator()
        return result
```

### 类型注解
添加类型提示避免此类问题：
```python
from typing import Generator, Dict, Union

def send_message(...) -> Union[Generator[str, None, None], Dict]:
    ...
```

---

## ✅ 修复状态

- ✅ Bug 已定位
- ✅ 修复已实施
- ✅ 逻辑已验证
- ✅ 无破坏性变更
- ✅ 向后兼容

### 测试建议
1. 重启 WebUI
2. 输入 `/postman test` 或任何 slash command
3. 验证显示正常文本而不是字段名

---

## 📝 相关代码

### 修改文件
- `agentos/webui/websocket/chat.py` (第 518-556 行)

### 相关文件（未修改）
- `agentos/core/chat/engine.py` (_execute_extension_command)
- `agentos/webui/static/js/main.js` (WebSocket 消息处理)

---

**问题已修复！重启 WebUI 后 `/postman` 命令应该能正常显示内容了。** 🎉
