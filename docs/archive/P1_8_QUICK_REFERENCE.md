# P1-8: Completion 截断 UX 文案 - 快速参考

## 📍 一句话总结

当模型响应因 token 限制被截断时，在聊天界面显示非侵入式提示，而不是让用户误以为系统坏了。

---

## 🎯 核心文案（固定不可改）

**主提示**:
```
Response truncated due to completion token limit
```

**次级说明**:
```
Token limits are configurable in Settings.
```

---

## 🏗️ 实施位置

### 1. Adapter 层 (`adapters.py`)

```python
# Ollama
done_reason = result.get("done_reason")
truncated = done_reason == "length"

# OpenAI
finish_reason = response.choices[0].finish_reason
truncated = finish_reason in ['length', 'max_tokens']

# 返回格式
return content, {
    "truncated": truncated,
    "finish_reason": finish_reason,
    "tokens_used": tokens
}
```

### 2. ChatEngine 层 (`engine.py`)

```python
response, metadata = adapter.generate(...)
message_metadata.update(metadata)  # 合并截断信息
```

### 3. WebSocket 层 (`chat.py`)

```python
if msg_metadata.get("truncated"):
    await manager.send_message(session_id, {
        "type": "completion_info",
        "info": {"truncated": True, ...}
    })
```

### 4. 前端 (`main.js`)

```javascript
if (message.type === 'completion_info') {
    if (message.info.truncated) {
        displayCompletionHint(messagesDiv);
    }
}
```

### 5. CSS (`main.css`)

```css
.completion-hint {
    background: #f8f9fa;  /* 淡灰色 */
    border-left: 3px solid #6c757d;  /* 灰色边框 */
    color: #6c757d;  /* 灰色文字 */
}
```

---

## ✅ 验收检查清单

- [ ] 提示在消息**下方**，不在消息内部
- [ ] 使用固定英文文案（见上方）
- [ ] 淡灰色背景，不是红色/黄色
- [ ] 不弹窗、不阻塞输入
- [ ] 只在 `length`/`max_tokens` 时显示
- [ ] 不在 `content_filter` 时显示
- [ ] 测试通过（单元 + 集成）

---

## 🧪 快速测试

```bash
# 单元测试
python3 -m pytest tests/unit/chat/test_completion_truncation.py -v

# 集成测试
python3 -m pytest tests/integration/test_completion_truncation_e2e.py -v -k "not manual"

# 手动测试
# 1. 设置 max_tokens=50
# 2. 发送 "Write a very long story"
# 3. 验证提示显示
```

---

## ⚠️ 禁止事项

❌ **不允许自动续写** - 不尝试"智能补全"剩余内容
❌ **不允许自动拼接** - 不发起"继续生成"请求
❌ **不允许隐藏截断** - 必须明确告知用户
❌ **不使用禁止词汇** - ERROR, FAILED, overflow, 不支持

---

## 📝 修改的文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `adapters.py` | 修改 | 检测截断 |
| `engine.py` | 修改 | 传递元数据 |
| `chat.py` | 修改 | 发送提示 |
| `main.js` | 新增 | 显示提示 |
| `main.css` | 新增 | 样式 |
| `test_completion_truncation.py` | 新增 | 单元测试 |
| `test_completion_truncation_e2e.py` | 新增 | 集成测试 |

---

## 🔍 调试技巧

### 检查截断是否被检测

```python
# 在 adapters.py 中添加日志
logger.info(f"Truncation detected: {truncated}, finish_reason: {finish_reason}")
```

### 检查元数据是否传递

```python
# 在 engine.py 中添加日志
logger.info(f"Response metadata: {response_metadata}")
```

### 检查 WebSocket 是否发送

```python
# 在 chat.py 中添加日志
logger.info(f"Sending completion_info: {info}")
```

### 检查前端是否接收

```javascript
// 在 main.js 中添加日志
console.log('Completion info:', message.info);
```

---

## 📊 元数据格式

所有 adapter 必须返回一致的格式:

```python
{
    "truncated": bool,        # True = 截断, False = 完成
    "finish_reason": str,     # "length", "stop", "content_filter", etc.
    "tokens_used": int        # 使用的 token 数量
}
```

---

## 🚀 未来扩展

1. **流式响应支持** - 当前只支持非流式
2. **国际化** - 当前只有英文文案
3. **设置页面跳转** - 当前只显示 toast

---

**版本**: v1.0
**日期**: 2026-01-30
**任务**: P1-8
