# Channel Adapter 快速参考卡

**规范版本**: v1.0.0 (FROZEN)
**完整规范**: [CHANNEL_ADAPTER_SPECIFICATION_V1.md](CHANNEL_ADAPTER_SPECIFICATION_V1.md)

---

## 4 条核心原则（不可违反）

### 1. ❌ Adapter 不解析命令
```python
# ❌ 错误
if text.startswith('/help'):
    return self.handle_help()

# ✅ 正确
return InboundMessage(text=text)  # 原样传递
```

### 2. ❌ Adapter 不管理 session
```python
# ❌ 错误
session_id = hash(user_key, conversation_key)

# ✅ 正确
return InboundMessage(
    user_key=user_id,
    conversation_key=chat_id
)  # SessionRouter 会计算 session_id
```

### 3. ❌ Adapter 不决定执行权限
```python
# ❌ 错误
if not user_has_permission():
    raise PermissionError()

# ✅ 正确（在 manifest.json）
{
  "security_defaults": {
    "allow_execute": false
  }
}
```

### 4. ✅ Adapter 只做 I/O + 映射
**做什么**:
- ✅ 接收 webhook/API 事件
- ✅ 验证签名
- ✅ 转换为 InboundMessage
- ✅ 发送 OutboundMessage

**不做什么**:
- ❌ 解析命令
- ❌ 管理 session
- ❌ 检查权限
- ❌ 调用 LLM
- ❌ 访问数据库

---

## 必需方法（4 个）

```python
class YourAdapter:
    def get_channel_id(self) -> str:
        """返回 channel 唯一标识符"""
        return self.channel_id

    def parse_event(self, payload: Dict) -> Optional[InboundMessage]:
        """将外部事件转换为 InboundMessage"""
        # 1. 检查 bot 回环（返回 None）
        # 2. 检查幂等性（返回 None）
        # 3. 提取必填字段
        # 4. 构造 InboundMessage
        return InboundMessage(...)

    def send_message(self, outbound: OutboundMessage) -> bool:
        """发送消息到外部 channel"""
        # 1. 提取 conversation_key
        # 2. 调用 channel API
        # 3. 处理错误
        return success

    def verify_signature(self, headers: Dict, body: bytes) -> bool:
        """验证 webhook 签名"""
        # 1. 提取签名 header
        # 2. 计算期望签名
        # 3. 常数时间比较
        return hmac.compare_digest(expected, actual)
```

---

## 5 个推荐模式

### 1. 幂等保护
```python
def __init__(self):
    self._processed_events: set[str] = set()

def parse_event(self, payload):
    event_id = payload.get('event_id')
    if event_id in self._processed_events:
        return None  # 已处理
    self._processed_events.add(event_id)
    # 继续处理...
```

### 2. Bot 回环过滤
```python
def parse_event(self, payload):
    # Slack
    if payload.get('bot_id'):
        return None

    # Telegram
    if payload['from'].get('is_bot'):
        return None
```

### 3. 延迟确认（Webhook Handler）
```python
@app.post("/webhook")
async def webhook(request, background_tasks):
    # 立即返回 ACK (< 3 秒)
    background_tasks.add_task(process_async, payload)
    return {"status": "ok"}
```

### 4. 线程支持
```python
# parse_event: 编码线程信息
if thread_ts:
    conversation_key = f"{channel}:{thread_ts}"
else:
    conversation_key = channel

# send_message: 解码线程信息
if ":" in conversation_key:
    channel, thread_ts = conversation_key.split(":", 1)
```

### 5. 常数时间签名比较
```python
import hmac

def verify_signature(self, expected, actual):
    # ✅ 正确（防时序攻击）
    return hmac.compare_digest(expected, actual)

    # ❌ 错误（可能遭受时序攻击）
    # return expected == actual
```

---

## 测试清单（6 类）

```python
# 1. 签名验证
def test_verify_signature_valid(): pass
def test_verify_signature_invalid(): pass
def test_verify_signature_replay_attack(): pass

# 2. 事件解析
def test_parse_event_text_message(): pass
def test_parse_event_with_attachments(): pass

# 3. Bot 回环过滤
def test_parse_event_ignores_bot_messages(): pass

# 4. 幂等性
def test_parse_event_idempotency(): pass

# 5. 消息发送
def test_send_message_success(): pass
def test_send_message_to_thread(): pass
def test_send_message_api_failure(): pass

# 6. 线程隔离
def test_thread_isolation(): pass
```

---

## 提交前检查清单

```bash
# 1. 运行 lint
python scripts/lint_adapter_spec.py your_adapter.py

# 2. 运行测试
pytest tests/unit/communicationos/channels/your_channel/ -v

# 3. 检查覆盖率
pytest tests/unit/communicationos/channels/your_channel/ --cov

# 4. 代码格式
ruff check your_channel/
ruff format your_channel/
```

**检查清单**:
- [ ] ✅ Adapter 不解析命令
- [ ] ✅ Adapter 不管理 session
- [ ] ✅ Adapter 不做权限判断
- [ ] ✅ 实现了所有必需方法
- [ ] ✅ 包含完整测试套件（覆盖率 > 80%）
- [ ] ✅ manifest.json 正确配置
- [ ] ✅ 使用 utc_now() 获取时间
- [ ] ✅ 通过 lint 检查

---

## 常见错误速查

| 错误代码 | 描述 | 解决方案 |
|---------|------|---------|
| PARSE_CMD | 在 adapter 里解析命令 | 删除命令解析代码，原样传递文本 |
| MANAGE_SESSION | 在 adapter 里管理 session | 删除 session 管理代码，只提供 user_key + conversation_key |
| CHECK_PERMISSION | 在 adapter 里检查权限 | 删除权限检查代码，在 manifest 设置 security_defaults |
| CALL_LLM | 在 adapter 里调用 LLM | 删除 LLM 调用，这是 Core 的职责 |
| ACCESS_DB | 在 adapter 里访问数据库 | 删除数据库访问，这是 Store 的职责 |
| STORE_HISTORY | 在 adapter 里存储对话历史 | 删除历史存储，这是 MemoryOS 的职责 |
| DATETIME_NOW | 使用 datetime.now() | 改用 `from agentos.core.time import utc_now` |

---

## InboundMessage 必填字段

```python
InboundMessage(
    channel_id=self.channel_id,           # ✅ 必填
    user_key=user_id,                      # ✅ 必填
    conversation_key=chat_id,              # ✅ 必填
    message_id=unique_id,                  # ✅ 必填
    timestamp=utc_now(),                   # ✅ 必填（使用 utc_now()）
    type=MessageType.TEXT,                 # ✅ 必填
    text=raw_text,                         # 可选（TEXT 类型需要）
    attachments=[],                        # 可选
    location=None,                         # 可选
    raw=payload,                           # 推荐（用于调试）
    metadata={}                            # 推荐（channel 特定信息）
)
```

---

## Manifest 必填字段

```json
{
  "id": "your_channel",
  "name": "Your Channel",
  "version": "1.0.0",
  "description": "Short description",
  "provider": "Provider Name",
  "docs_url": "https://...",
  "required_config_fields": [...],
  "webhook_paths": ["/api/channels/your_channel/webhook"],
  "session_scope": "user_conversation",
  "capabilities": ["inbound_text", "outbound_text"],
  "security_defaults": {
    "mode": "chat_only",
    "allow_execute": false,
    "rate_limit_per_minute": 30
  }
}
```

---

## 参考实现

| Adapter | 路径 | 适合参考场景 |
|---------|------|------------|
| Slack | `channels/slack/adapter.py` | 企业级平台（OAuth、线程、触发策略） |
| Telegram | `channels/telegram/adapter.py` | 个人平台（Secret token、多媒体） |
| Email | `channels/email/adapter.py` | 异步轮询（SMTP/IMAP） |
| Discord | `channels/discord/adapter.py` | OAuth + 交互式组件 |

---

## 快速链接

- 📖 完整规范: [CHANNEL_ADAPTER_SPECIFICATION_V1.md](CHANNEL_ADAPTER_SPECIFICATION_V1.md)
- 🛠️ Lint 工具: `scripts/lint_adapter_spec.py`
- 📝 贡献指南: [CONTRIBUTING.md](../CONTRIBUTING.md#developing-channel-adapters)
- 💬 讨论: [GitHub Discussions](https://github.com/seacow-technology/agentos/discussions)
- 🐛 报告问题: [GitHub Issues](https://github.com/seacow-technology/agentos/issues)

---

**最后更新**: 2026-02-01
**规范版本**: v1.0.0 (FROZEN)
