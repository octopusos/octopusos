# Channel Adapter 规范 v1（FROZEN）

## 状态
**✅ FROZEN** - 2026-02-01
适用范围：所有 CommunicationOS Channel Adapters

---

## 核心原则（不可违反）

### 1. ❌ Adapter 不解析命令
**规则**：Adapter 只传递原始文本，不解析 `/help`、`/session` 等命令。

**正确做法**：
```python
# ✅ 正确：直接传递
inbound = InboundMessage(
    channel_id=self.channel_id,
    user_key=user_id,
    conversation_key=chat_id,
    message_id=message_id,
    text=raw_text,  # 保持原样，不解析
    ...
)
```

**错误做法**：
```python
# ❌ 错误：在 adapter 里解析命令
if text.startswith('/help'):
    return self.handle_help()  # 这是 Core 的职责！

# ❌ 错误：在 adapter 里修改命令
if text.startswith('/'):
    command = parse_command(text)  # 不要解析！
```

**原因**：命令解析属于业务逻辑，由 CommunicationOS Core 统一处理。Adapter 只负责协议转换。

**参考实现**：
- Slack Adapter: `agentos/communicationos/channels/slack/adapter.py:320-338`
- Telegram Adapter: `agentos/communicationos/channels/telegram/adapter.py:254-276`

---

### 2. ❌ Adapter 不管理 session
**规则**：Adapter 只提供 `user_key` + `conversation_key`，不计算 `session_id`。

**正确做法**：
```python
# ✅ 正确：提供原始 key
inbound = InboundMessage(
    user_key=slack_user_id,  # 原始用户ID
    conversation_key=f"{channel_id}:{thread_ts}",  # 原始对话ID
    ...
)
# SessionRouter 会自动根据 user_key + conversation_key 计算 session_id
```

**错误做法**：
```python
# ❌ 错误：在 adapter 里计算 session
session_id = hashlib.md5(f"{user_key}:{conversation_key}".encode()).hexdigest()
inbound.session_id = session_id  # InboundMessage 没有这个字段！

# ❌ 错误：在 adapter 里管理 session 状态
self.active_sessions[user_key] = {
    "last_message": text,
    "context": ...  # 这是 SessionRouter 的职责！
}
```

**原因**：Session 管理由 SessionRouter 统一，确保隔离策略（user、conversation、user_conversation）一致。Adapter 不知道也不应该知道 session 管理逻辑。

**参考实现**：
- Slack Adapter 的 conversation_key 构造: `agentos/communicationos/channels/slack/adapter.py:289-294`
- Manifest 中的 session_scope 声明: `agentos/communicationos/channels/slack/manifest.json:61-67`

---

### 3. ❌ Adapter 不决定执行权限
**规则**：Adapter 只在 manifest 中设置安全默认值，不在运行时做权限判断。

**正确做法**：
```json
// ✅ 正确：在 manifest.json 声明安全默认值
{
  "security_defaults": {
    "mode": "chat_only",
    "allow_execute": false,
    "allowed_commands": ["/session", "/help"],
    "rate_limit_per_minute": 30,
    "retention_days": 7,
    "require_signature": true
  }
}
```

**错误做法**：
```python
# ❌ 错误：在 adapter 里检查执行权限
if message.text.startswith("/execute"):
    if not self.user_has_permission(user_key):
        raise PermissionError("User not allowed to execute")  # 这是 Guardian 的职责！

# ❌ 错误：在 adapter 里过滤危险命令
dangerous_commands = ["/rm", "/delete", "/drop"]
if any(cmd in text for cmd in dangerous_commands):
    return None  # 不要在这里过滤！
```

**原因**：权限判断由 Guardian/Policy 层统一，Adapter 只负责配置默认值。运行时的权限检查应该由上层组件处理。

**参考实现**：
- Slack Manifest 的 security_defaults: `agentos/communicationos/channels/slack/manifest.json:73-80`

---

### 4. ✅ Adapter 只做 I/O + 映射
**职责范围**：
- ✅ 接收外部协议（Webhook/WebSocket/Email/API）
- ✅ 验证签名/认证（channel 特定的安全机制）
- ✅ 映射为 InboundMessage（协议转换）
- ✅ 发送 OutboundMessage 到外部（协议转换）
- ✅ 处理 channel 特定的幂等/重试/去重

**不在职责范围**：
- ❌ 解析业务命令（`/help`、`/session`）
- ❌ 管理对话状态（session、context）
- ❌ 执行权限判断（allow_execute、rate_limit）
- ❌ 调用 LLM（chat completion、embeddings）
- ❌ 存储消息内容（由 MessageBus/Store 处理）
- ❌ 路由消息（由 MessageBus/Router 处理）

**清晰的边界**：
```
External Platform → Adapter (I/O + 映射) → InboundMessage → MessageBus → SessionRouter → Core
                                                                                          ↓
External Platform ← Adapter (I/O + 映射) ← OutboundMessage ← MessageBus ← Core Response
```

---

## Adapter 接口契约

### 必须实现的方法

#### 1. parse_event() / parse_update() / parse_message()
```python
def parse_event(self, payload: Dict[str, Any]) -> Optional[InboundMessage]:
    """
    将 channel 特定的事件转换为 InboundMessage。

    参数：
        payload: Channel 特定的原始事件数据（Webhook body、API response 等）

    返回：
        InboundMessage: 标准化的入站消息
        None: 跳过此事件（如 bot 自己的消息、不支持的事件类型）

    规则：
        1. 返回 None 表示跳过（如 bot 自己的消息、URL verification）
        2. 只做映射，不做业务逻辑（不解析命令、不管理 session）
        3. 必须填充所有必填字段（channel_id, user_key, conversation_key, message_id, timestamp）
        4. 使用 utc_now() 获取时间戳（如果 payload 没有提供）
        5. 将原始 payload 存储在 raw 字段（用于调试）
        6. 将 channel 特定的元数据存储在 metadata 字段

    异常：
        ValueError: 缺少必填字段或字段格式无效

    实现要点：
        - Bot 回环过滤：检查 bot_id、is_bot 等字段
        - 幂等性：跟踪已处理的事件ID（event_id、update_id）
        - 线程支持：正确构造 conversation_key（如 "{channel}:{thread_ts}"）
        - 时间戳：转换为 timezone-aware datetime (UTC)
    """
```

**参考实现**：
- Slack: `agentos/communicationos/channels/slack/adapter.py:180-354`
- Telegram: `agentos/communicationos/channels/telegram/adapter.py:69-283`

#### 2. send_message()
```python
def send_message(self, outbound: OutboundMessage) -> bool:
    """
    将 OutboundMessage 发送到外部 channel。

    参数：
        outbound: 标准化的出站消息

    返回：
        bool: True 表示发送成功，False 表示失败

    规则：
        1. 处理 channel 特定的格式（Markdown/HTML/Plain）
        2. 处理长度限制（截断/分片/错误）
        3. 处理错误（重试/降级/日志）
        4. 不修改 outbound 内容（只格式化）
        5. 正确处理 conversation_key（提取 channel、thread_ts 等）
        6. 正确处理 reply_to_message_id（如果 channel 支持）

    异常：
        不应该抛出异常，应该捕获并返回 False + 记录日志

    实现要点：
        - API 调用：使用 channel 的 SDK 或 HTTP API
        - 线程支持：从 conversation_key 提取 thread_ts
        - 错误处理：捕获异常、记录日志、返回 False
        - 格式转换：Markdown → HTML/Plain（如果需要）
    """
```

**参考实现**：
- Slack: `agentos/communicationos/channels/slack/adapter.py:356-409`
- Telegram: `agentos/communicationos/channels/telegram/adapter.py:285-340`

#### 3. verify_signature() / verify_webhook()
```python
def verify_signature(self, headers: Dict[str, str], body: bytes) -> bool:
    """
    验证来自 channel 的请求签名。

    参数：
        headers: HTTP 请求头（包含签名相关的 header）
        body: 原始请求体（用于计算签名）

    返回：
        bool: True 表示签名有效，False 表示无效

    规则：
        1. 失败返回 False，由调用方返回 401
        2. 使用 channel 官方推荐的验证算法（HMAC-SHA256、JWT 等）
        3. 常数时间比较（防时序攻击，使用 hmac.compare_digest）
        4. 检查时间戳新鲜度（防重放攻击，通常 5 分钟内）

    安全性：
        这是关键安全控制，必须正确实现！
        错误的签名验证会导致安全漏洞（伪造消息、命令注入等）。

    实现要点：
        - HMAC 计算：使用 signing_secret + timestamp + body
        - 常数时间比较：使用 hmac.compare_digest()
        - 时间戳检查：拒绝超过 5 分钟的请求
    """
```

**参考实现**：
- Slack: `agentos/communicationos/channels/slack/adapter.py:113-143`
  - 使用 HMAC-SHA256
  - 格式：`v0={hash}`
  - 签名基础：`v0:{timestamp}:{body}`
- Telegram: `agentos/communicationos/channels/telegram/adapter.py:342-367`
  - 使用 Secret Token（常数时间比较）
  - Header: `X-Telegram-Bot-Api-Secret-Token`

#### 4. get_channel_id()
```python
def get_channel_id(self) -> str:
    """
    获取此 adapter 处理的 channel 唯一标识符。

    返回：
        str: Channel ID（如 "slack_workspace_001", "telegram_bot_123"）

    规则：
        - 返回实例化时传入的 channel_id
        - 用于区分同一类型的不同 channel 实例
    """
```

**参考实现**：
- Slack: `agentos/communicationos/channels/slack/adapter.py:75-81`
- Telegram: `agentos/communicationos/channels/telegram/adapter.py:61-67`

---

## 设计模式（推荐）

### 1. 幂等保护（Adapter 层）
```python
class SlackAdapter:
    def __init__(self):
        self._processed_events: set[str] = set()

    def parse_event(self, payload: Dict[str, Any]) -> Optional[InboundMessage]:
        # 幂等性检查：跟踪已处理的事件ID
        event_id = payload.get('event_id')
        if event_id and event_id in self._processed_events:
            logger.info(f"Skipping duplicate event: {event_id}")
            return None  # 已处理，跳过

        # 处理事件...
        inbound = InboundMessage(...)

        # 标记为已处理
        if event_id:
            self._processed_events.add(event_id)
            # 限制内存使用（保留最近 10000 个）
            if len(self._processed_events) > 10000:
                self._processed_events = set(list(self._processed_events)[5000:])

        return inbound
```

**为什么需要**：
- 许多 channel（如 Slack、Discord）会重试失败的 webhook
- 防止重复处理同一消息（导致重复回复）

**参考实现**：
- Slack: `agentos/communicationos/channels/slack/adapter.py:239-346`

### 2. Bot 回环过滤
```python
def parse_event(self, payload: Dict[str, Any]) -> Optional[InboundMessage]:
    # ✅ 在 Adapter 层过滤 bot 自己的消息
    event = payload.get('event', {})

    # Slack: 检查 bot_id 和 subtype
    if event.get('bot_id') or event.get('subtype') == 'bot_message':
        logger.debug("Ignoring bot message (loop prevention)")
        return None  # 防止回环

    # Telegram: 检查 from.is_bot
    from_user = payload.get('message', {}).get('from', {})
    if from_user.get('is_bot', False):
        logger.debug("Ignoring message from bot (loop prevention)")
        return None

    # 继续处理...
```

**为什么需要**：
- 防止 bot 回复自己的消息（导致无限循环）
- 这是 Adapter 的职责（因为 bot_id 是 channel 特定的）

**参考实现**：
- Slack: `agentos/communicationos/channels/slack/adapter.py:248-253`
- Telegram: `agentos/communicationos/channels/telegram/adapter.py:110-117`

### 3. 延迟确认（3 秒规则）
```python
from fastapi import BackgroundTasks

@app.post("/api/channels/slack/webhook")
async def slack_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    # 1. 立即验证签名
    if not adapter.verify_signature(headers, body):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    # 2. 立即返回 ACK（< 3 秒）
    background_tasks.add_task(process_message_async, payload)
    return {"status": "ok"}  # 立即返回

async def process_message_async(payload: Dict[str, Any]):
    # 3. 异步处理消息（可以慢）
    inbound = adapter.parse_event(payload)
    if inbound:
        await message_bus.publish(inbound)
```

**为什么需要**：
- Slack/Discord 要求 webhook 在 3 秒内响应
- 否则会重试（导致重复消息）
- LLM 调用可能需要 10-30 秒，必须异步处理

**参考实现**：
- 在 webhook handler 中实现（不在 adapter 中）
- 使用 FastAPI BackgroundTasks 或 asyncio.create_task

### 4. 线程/Thread 支持
```python
def parse_event(self, payload: Dict[str, Any]) -> Optional[InboundMessage]:
    event = payload.get('event', {})
    channel_id = event.get('channel')
    thread_ts = event.get('thread_ts')  # Slack 的线程时间戳

    # ✅ 正确：将 thread 信息编码到 conversation_key
    if thread_ts:
        # 线程消息：{channel}:{thread_ts}
        conversation_key = f"{channel_id}:{thread_ts}"
    else:
        # 普通消息：{channel}
        conversation_key = channel_id

    inbound = InboundMessage(
        conversation_key=conversation_key,
        metadata={
            "channel_id": channel_id,
            "thread_ts": thread_ts,  # 保留原始信息
        },
        ...
    )
    return inbound

def send_message(self, outbound: OutboundMessage) -> bool:
    # ✅ 正确：从 conversation_key 解码 thread 信息
    conversation_key = outbound.conversation_key
    thread_ts = None

    if ":" in conversation_key:
        # 这是线程消息
        channel_id, thread_ts = conversation_key.split(":", 1)
    else:
        # 这是普通消息
        channel_id = conversation_key

    # 发送消息（包含 thread_ts）
    return slack_api.post_message(
        channel=channel_id,
        text=outbound.text,
        thread_ts=thread_ts  # 如果是线程，会在同一线程回复
    )
```

**为什么需要**：
- 支持多线程对话（同一 channel 可以有多个独立对话）
- 确保回复发送到正确的线程
- SessionRouter 会根据 conversation_key 隔离不同线程的 session

**参考实现**：
- Slack: `agentos/communicationos/channels/slack/adapter.py:289-294, 372-382`

### 5. 常数时间签名比较（防时序攻击）
```python
import hmac

def verify_signature(self, headers: Dict[str, str], body: bytes) -> bool:
    expected_signature = headers.get('X-Slack-Signature')
    timestamp = headers.get('X-Slack-Request-Timestamp')

    if not expected_signature or not timestamp:
        return False

    # 计算签名
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed_signature = 'v0=' + hmac.new(
        self.signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    # ✅ 正确：使用常数时间比较（防时序攻击）
    return hmac.compare_digest(computed_signature, expected_signature)

    # ❌ 错误：使用 == 比较（容易遭受时序攻击）
    # return computed_signature == expected_signature
```

**为什么需要**：
- 防止时序攻击（timing attack）
- `hmac.compare_digest()` 保证比较时间与字符串内容无关

---

## 测试要求

每个 Adapter 必须包含以下测试（在 `tests/unit/communicationos/channels/{channel}/` 目录下）：

### 1. 签名验证测试
```python
def test_verify_signature_valid():
    """测试有效签名"""
    adapter = SlackAdapter(...)
    assert adapter.verify_signature(valid_headers, valid_body) is True

def test_verify_signature_invalid():
    """测试无效签名"""
    adapter = SlackAdapter(...)
    assert adapter.verify_signature(invalid_headers, valid_body) is False

def test_verify_signature_missing_headers():
    """测试缺失 header"""
    adapter = SlackAdapter(...)
    assert adapter.verify_signature({}, valid_body) is False

def test_verify_signature_replay_attack():
    """测试重放攻击（旧时间戳）"""
    adapter = SlackAdapter(...)
    old_timestamp = str(int(time.time()) - 400)  # 6 分钟前
    assert adapter.verify_signature(old_headers, valid_body) is False
```

### 2. 事件解析测试
```python
def test_parse_event_text_message():
    """测试解析文本消息"""
    payload = {...}  # 完整的 Slack event
    inbound = adapter.parse_event(payload)
    assert inbound is not None
    assert inbound.type == MessageType.TEXT
    assert inbound.text == "Hello"
    assert inbound.user_key == "U1234567"

def test_parse_event_with_attachments():
    """测试解析带附件的消息"""
    payload = {...}  # 包含图片的消息
    inbound = adapter.parse_event(payload)
    assert len(inbound.attachments) > 0
    assert inbound.attachments[0].type == AttachmentType.IMAGE

def test_parse_event_missing_required_fields():
    """测试缺失必填字段"""
    payload = {"event": {}}  # 缺少 user、channel 等
    with pytest.raises(ValueError):
        adapter.parse_event(payload)
```

### 3. Bot 回环过滤测试
```python
def test_parse_event_ignores_bot_messages():
    """测试过滤 bot 消息（防回环）"""
    payload = {
        "event": {
            "bot_id": "B1234567",  # 这是 bot 发送的
            "text": "I am a bot",
            ...
        }
    }
    inbound = adapter.parse_event(payload)
    assert inbound is None  # 应该被过滤

def test_parse_event_ignores_bot_subtype():
    """测试过滤 bot_message subtype"""
    payload = {
        "event": {
            "subtype": "bot_message",
            "text": "I am a bot",
            ...
        }
    }
    inbound = adapter.parse_event(payload)
    assert inbound is None  # 应该被过滤
```

### 4. 幂等性测试
```python
def test_parse_event_idempotency():
    """测试幂等性（重复事件只处理一次）"""
    payload = {
        "event_id": "Ev1234567",
        "event": {...}
    }

    # 第一次处理：成功
    inbound1 = adapter.parse_event(payload)
    assert inbound1 is not None

    # 第二次处理：应该被跳过
    inbound2 = adapter.parse_event(payload)
    assert inbound2 is None
```

### 5. 消息发送测试
```python
def test_send_message_success(mocker):
    """测试成功发送消息"""
    mock_post = mocker.patch('slack_sdk.WebClient.chat_postMessage')
    mock_post.return_value = {"ok": True}

    outbound = OutboundMessage(
        channel_id="slack_001",
        user_key="U1234567",
        conversation_key="C1234567",
        text="Hello"
    )

    success = adapter.send_message(outbound)
    assert success is True
    mock_post.assert_called_once()

def test_send_message_to_thread(mocker):
    """测试发送到线程"""
    mock_post = mocker.patch('slack_sdk.WebClient.chat_postMessage')
    mock_post.return_value = {"ok": True}

    outbound = OutboundMessage(
        conversation_key="C1234567:1234567890.123456",  # 线程
        ...
    )

    success = adapter.send_message(outbound)
    assert success is True
    # 验证 thread_ts 参数
    assert mock_post.call_args[1]['thread_ts'] == "1234567890.123456"

def test_send_message_api_failure(mocker):
    """测试 API 失败"""
    mock_post = mocker.patch('slack_sdk.WebClient.chat_postMessage')
    mock_post.side_effect = Exception("Network error")

    outbound = OutboundMessage(...)
    success = adapter.send_message(outbound)
    assert success is False  # 应该返回 False 而不是抛异常
```

### 6. 线程隔离测试
```python
def test_thread_isolation():
    """测试线程隔离（不同 conversation_key）"""
    # 同一 channel，不同 thread
    payload1 = {"event": {"channel": "C123", "thread_ts": "111.111", ...}}
    payload2 = {"event": {"channel": "C123", "thread_ts": "222.222", ...}}

    inbound1 = adapter.parse_event(payload1)
    inbound2 = adapter.parse_event(payload2)

    # 应该有不同的 conversation_key
    assert inbound1.conversation_key == "C123:111.111"
    assert inbound2.conversation_key == "C123:222.222"
    assert inbound1.conversation_key != inbound2.conversation_key
```

---

## 反模式（禁止）

### ❌ 反模式 1：在 Adapter 里调用 LLM
```python
# ❌ 错误
def parse_event(self, payload):
    text = payload['text']

    # 不要在这里调用 LLM！
    from openai import OpenAI
    client = OpenAI()
    reply = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": text}]
    )

    return InboundMessage(text=text)
```

**为什么错误**：
- Adapter 只负责 I/O，不负责业务逻辑
- LLM 调用应该在 Core/ChatEngine 中
- Webhook 需要在 3 秒内响应，LLM 调用太慢
- 违反单一职责原则

### ❌ 反模式 2：在 Adapter 里存储状态
```python
# ❌ 错误
class SlackAdapter:
    def __init__(self):
        self.user_history: Dict[str, List[str]] = {}  # 不要存储对话历史！
        self.user_context: Dict[str, Any] = {}  # 不要存储上下文！

    def parse_event(self, payload):
        user_id = payload['user']
        text = payload['text']

        # 不要在这里管理历史！
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        self.user_history[user_id].append(text)

        return InboundMessage(text=text)
```

**为什么错误**：
- Adapter 应该是无状态的（stateless）
- 对话历史由 MemoryOS 管理
- Session 状态由 SessionRouter 管理
- 多实例部署时，内存状态会丢失

### ❌ 反模式 3：在 Adapter 里实现业务逻辑
```python
# ❌ 错误
def parse_event(self, payload):
    text = payload['text']

    # 不要在这里实现命令！
    if text == "/help":
        self.send_help_message()
        return None

    if text == "/status":
        status = self.get_system_status()
        self.send_message(OutboundMessage(text=status))
        return None

    # 不要在这里实现自动回复！
    if "你好" in text:
        self.send_message(OutboundMessage(text="你好！有什么可以帮助你的吗？"))

    return InboundMessage(text=text)
```

**为什么错误**：
- 命令解析是 Core 的职责
- 自动回复是 ChatEngine 的职责
- Adapter 只负责传递原始消息
- 违反关注点分离原则

### ❌ 反模式 4：在 Adapter 里做复杂的内容处理
```python
# ❌ 错误
def parse_event(self, payload):
    text = payload['text']

    # 不要在这里清理内容！
    text = remove_emojis(text)
    text = expand_abbreviations(text)
    text = correct_typos(text)
    text = translate_to_english(text)

    return InboundMessage(text=text)
```

**为什么错误**：
- Adapter 应该传递原始内容
- 内容处理是 Core/Preprocessor 的职责
- 可能破坏原始语义（如 emoji 有特殊含义）
- 违反"最小处理"原则

### ❌ 反模式 5：在 Adapter 里直接访问数据库
```python
# ❌ 错误
def parse_event(self, payload):
    user_id = payload['user']

    # 不要在这里访问数据库！
    conn = sqlite3.connect('agentos.db')
    cursor = conn.execute(
        "SELECT last_message_time FROM users WHERE user_id = ?",
        (user_id,)
    )
    last_time = cursor.fetchone()

    # 不要在这里实现速率限制！
    if last_time and (time.time() - last_time[0]) < 5:
        return None  # Rate limit

    return InboundMessage(...)
```

**为什么错误**：
- Adapter 不应该访问数据库
- 速率限制是 Policy/Guardian 的职责
- 违反分层架构
- 难以测试和维护

---

## Manifest 规范

每个 Channel Adapter 必须包含一个 `manifest.json` 文件，描述 channel 的元数据和配置。

### 必填字段

```json
{
  "id": "slack",  // Channel 类型唯一标识符（小写，无空格）
  "name": "Slack",  // 显示名称
  "version": "1.0.0",  // Adapter 版本（语义化版本）
  "description": "短描述（一句话）",
  "long_description": "详细描述（支持 Markdown）",
  "provider": "Slack",  // 平台提供商
  "docs_url": "https://...",  // 官方文档链接

  "required_config_fields": [  // 配置字段
    {
      "name": "bot_token",  // 字段名
      "label": "Bot Token",  // 显示标签
      "type": "password",  // 类型：text/password/select/url
      "required": true,  // 是否必填
      "secret": true,  // 是否加密存储
      "placeholder": "xoxb-...",  // 占位符
      "help_text": "获取方式说明",  // 帮助文本
      "validation_regex": "^xoxb-.*$",  // 验证正则
      "validation_error": "错误提示"  // 验证失败提示
    }
  ],

  "webhook_paths": [  // Webhook 路径（相对于 base_url）
    "/api/channels/slack/webhook"
  ],

  "session_scope": "user_conversation",  // Session 隔离范围
  // 可选值：
  // - "user": 每个用户一个 session（跨对话）
  // - "conversation": 每个对话一个 session（跨用户，如群聊）
  // - "user_conversation": 每个用户+对话一个 session（最常用）

  "capabilities": [  // 支持的能力
    "inbound_text",  // 接收文本
    "outbound_text",  // 发送文本
    "threads",  // 线程支持
    "attachments",  // 附件支持
    "location",  // 位置分享
    "interactive"  // 交互式组件（按钮、菜单）
  ],

  "security_defaults": {  // 安全默认值
    "mode": "chat_only",  // 默认模式：chat_only / auto_execute / manual_approval
    "allow_execute": false,  // 是否允许执行命令
    "allowed_commands": ["/help", "/session"],  // 允许的命令白名单
    "rate_limit_per_minute": 30,  // 每分钟消息数限制
    "retention_days": 7,  // 消息保留天数
    "require_signature": true  // 是否要求签名验证
  },

  "setup_steps": [  // 设置步骤（向导）
    {
      "title": "步骤标题",
      "description": "步骤描述",
      "instruction": "详细说明",
      "checklist": ["检查项1", "检查项2"],
      "auto_check": false  // 是否自动检查（最后一步可以自动测试）
    }
  ],

  "privacy_badges": [  // 隐私标签
    "No Auto Provisioning",  // 不自动开通
    "Chat-only by Default",  // 默认仅聊天
    "Local Storage",  // 本地存储
    "Secrets Encrypted"  // 密钥加密
  ],

  "metadata": {  // 额外元数据
    "category": "messaging",  // 分类：messaging/email/voice/video
    "official": true,  // 是否官方支持
    "verified": true,  // 是否已验证
    "cost": "free",  // 成本：free/freemium/paid
    "setup_difficulty": "medium"  // 设置难度：easy/medium/hard
  }
}
```

**参考实现**：
- Slack: `agentos/communicationos/channels/slack/manifest.json`
- Telegram: `agentos/communicationos/channels/telegram/manifest.json`

---

## 版本策略

### v1 规范冻结
- 本文档自 2026-02-01 起冻结
- 后续变更需 RFC + 社区评审 + 主要版本号升级
- 所有现有 adapter 必须符合本规范

### 向后兼容
- ✅ 允许：新增可选方法（如 `parse_edited_message()`）
- ✅ 允许：新增可选配置字段（在 manifest 中标记为 `required: false`）
- ✅ 允许：新增可选 capabilities（如 `voice_input`）
- ❌ 禁止：修改必需方法签名（破坏现有代码）
- ❌ 禁止：删除方法（破坏现有代码）
- ❌ 禁止：修改 InboundMessage/OutboundMessage 必填字段（破坏现有代码）

### 规范演进流程
如果需要修改本规范：

1. **提交 RFC**（Request for Comments）
   - 在 GitHub Discussions 创建提案
   - 说明修改原因、影响范围、迁移方案

2. **社区评审**（至少 2 周）
   - 核心团队 review
   - 社区讨论和反馈
   - 修改和完善提案

3. **投票**
   - 核心团队投票
   - 需要 2/3 多数通过

4. **实施**
   - 更新规范文档（新建 v2 文档）
   - 更新 lint 工具
   - 提供迁移指南
   - 更新示例 adapter

5. **废弃策略**
   - v1 标记为 deprecated（保留 6 个月）
   - 提供自动迁移工具（如果可能）
   - 在文档中标注迁移路径

---

## 检查清单（新 Adapter 提交前）

在提交新的 Channel Adapter 前，请确保：

### 代码质量
- [ ] ✅ Adapter 不解析命令（不包含命令解析逻辑）
- [ ] ✅ Adapter 不管理 session（不计算 session_id，不存储 session 状态）
- [ ] ✅ Adapter 不做权限判断（不检查 allow_execute、不实施 rate_limit）
- [ ] ✅ Adapter 只做 I/O + 映射（只有协议转换逻辑）
- [ ] ✅ 实现了所有必需方法（parse_event, send_message, verify_signature, get_channel_id）
- [ ] ✅ 正确实现 bot 回环过滤（过滤自己发送的消息）
- [ ] ✅ 正确实现幂等性（跟踪已处理的事件ID）
- [ ] ✅ 正确实现线程支持（conversation_key 包含线程信息）
- [ ] ✅ 正确使用 utc_now()（不使用 datetime.now() 或 datetime.utcnow()）
- [ ] ✅ 正确处理异常（不让异常传播到调用方）

### 测试覆盖
- [ ] ✅ 包含签名验证测试（有效/无效/缺失/重放攻击）
- [ ] ✅ 包含事件解析测试（各种消息类型）
- [ ] ✅ 包含 bot 回环过滤测试
- [ ] ✅ 包含幂等性测试（重复事件）
- [ ] ✅ 包含缺失字段处理测试
- [ ] ✅ 包含消息发送测试（成功/失败/重试）
- [ ] ✅ 包含线程隔离测试（如果支持线程）
- [ ] ✅ 测试覆盖率 > 80%

### 文档完整性
- [ ] ✅ manifest.json 正确配置（所有必填字段）
- [ ] ✅ 包含详细的 docstrings（所有公开方法）
- [ ] ✅ 包含 setup_steps（设置向导）
- [ ] ✅ 包含 README.md（快速开始指南）
- [ ] ✅ 包含示例配置（examples/ 目录）
- [ ] ✅ 符合安全默认值（chat-only）

### 安全检查
- [ ] ✅ 签名验证正确实现（HMAC-SHA256 或等效算法）
- [ ] ✅ 使用常数时间比较（hmac.compare_digest）
- [ ] ✅ 检查时间戳新鲜度（防重放攻击）
- [ ] ✅ 密钥不出现在代码中（使用环境变量或配置）
- [ ] ✅ 不记录敏感信息（不打印 token、secret）

### Lint 检查
- [ ] ✅ 通过 `python scripts/lint_adapter_spec.py your_adapter.py`
- [ ] ✅ 通过 `ruff check .`
- [ ] ✅ 通过 `ruff format --check .`
- [ ] ✅ 通过 `pytest tests/unit/communicationos/channels/your_channel/`

---

## 参考实现

AgentOS 提供了多个参考实现，可以作为新 Adapter 的模板：

### Slack Adapter（推荐模板）
**路径**：`agentos/communicationos/channels/slack/`

**特点**：
- ✅ 完整的签名验证（HMAC-SHA256）
- ✅ URL verification challenge 处理
- ✅ 幂等性保护（跟踪 event_id）
- ✅ Bot 回环过滤
- ✅ 线程支持（thread_ts）
- ✅ 触发策略（dm_only / mention_or_dm / all_messages）
- ✅ 完整的测试套件

**适合参考**：企业级 messaging 平台（Discord、Teams、Mattermost）

### Telegram Adapter（简单模板）
**路径**：`agentos/communicationos/channels/telegram/`

**特点**：
- ✅ Secret token 验证（常数时间比较）
- ✅ Bot 回环过滤（is_bot）
- ✅ 多媒体支持（photo、audio、video、document、location）
- ✅ Reply 支持（reply_to_message_id）
- ✅ 简单清晰的代码结构

**适合参考**：个人/小团队 messaging 平台（WhatsApp、Signal、Matrix）

### Email Adapter（异步模板）
**路径**：`agentos/communicationos/channels/email/`

**特点**：
- ✅ SMTP/IMAP 支持
- ✅ 邮件解析（multipart、attachments）
- ✅ 线程支持（In-Reply-To、References headers）
- ✅ 异步轮询（不是 webhook）

**适合参考**：异步/轮询类 channels（RSS、Webhook polling）

### Discord Adapter（OAuth 模板）
**路径**：`agentos/communicationos/channels/discord/`

**特点**：
- ✅ OAuth2 认证流程
- ✅ Guild（服务器）+ Channel 支持
- ✅ Slash commands 支持
- ✅ Interactions（buttons、menus）

**适合参考**：需要 OAuth 的平台（GitHub、GitLab、Jira）

---

## 快速开始：创建新 Adapter

### 1. 创建目录结构
```bash
mkdir -p agentos/communicationos/channels/your_channel
cd agentos/communicationos/channels/your_channel

# 创建文件
touch __init__.py
touch adapter.py
touch client.py  # 可选：API 客户端封装
touch manifest.json
touch README.md

# 创建测试目录
mkdir -p tests/unit/communicationos/channels/your_channel
touch tests/unit/communicationos/channels/your_channel/test_adapter.py
```

### 2. 实现 Adapter（adapter.py）
```python
"""Your Channel Adapter.

Brief description of your channel and what this adapter does.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from agentos.communicationos.models import (
    InboundMessage,
    OutboundMessage,
    MessageType,
)
from agentos.core.time import utc_now

logger = logging.getLogger(__name__)


class YourChannelAdapter:
    """Channel adapter for Your Channel."""

    def __init__(
        self,
        channel_id: str,
        api_token: str,
        webhook_secret: str
    ):
        self.channel_id = channel_id
        self.api_token = api_token
        self.webhook_secret = webhook_secret
        self._processed_events: set[str] = set()

    def get_channel_id(self) -> str:
        return self.channel_id

    def verify_signature(
        self,
        headers: Dict[str, str],
        body: bytes
    ) -> bool:
        """验证 webhook 签名"""
        # TODO: 实现签名验证逻辑
        pass

    def parse_event(
        self,
        payload: Dict[str, Any]
    ) -> Optional[InboundMessage]:
        """解析事件为 InboundMessage"""
        # TODO: 实现事件解析逻辑
        pass

    def send_message(
        self,
        message: OutboundMessage
    ) -> bool:
        """发送消息"""
        # TODO: 实现消息发送逻辑
        pass
```

### 3. 创建 Manifest（manifest.json）
```json
{
  "id": "your_channel",
  "name": "Your Channel",
  "version": "1.0.0",
  "description": "Brief description",
  "required_config_fields": [
    {
      "name": "api_token",
      "label": "API Token",
      "type": "password",
      "required": true,
      "secret": true
    }
  ],
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

### 4. 编写测试（test_adapter.py）
```python
import pytest
from agentos.communicationos.channels.your_channel.adapter import YourChannelAdapter


def test_parse_event_text_message():
    adapter = YourChannelAdapter(
        channel_id="test_001",
        api_token="test_token",
        webhook_secret="test_secret"
    )

    payload = {
        # TODO: 添加测试数据
    }

    inbound = adapter.parse_event(payload)
    assert inbound is not None
    assert inbound.type.value == "text"
```

### 5. 运行 Lint 检查
```bash
# 检查 adapter 规范
python scripts/lint_adapter_spec.py agentos/communicationos/channels/your_channel/adapter.py

# 检查代码风格
ruff check agentos/communicationos/channels/your_channel/
ruff format agentos/communicationos/channels/your_channel/

# 运行测试
pytest tests/unit/communicationos/channels/your_channel/
```

### 6. 提交 PR
- 确保通过所有 lint 检查
- 确保测试覆盖率 > 80%
- 填写完整的 PR 描述（参考 CONTRIBUTING.md）

---

## 社区资源

### 文档
- [CommunicationOS 架构](../COMMUNICATIONOS_PROJECT_SUMMARY.md)
- [Session 隔离策略](../COMMUNICATIONOS_CONFIGURATION_EXAMPLES.md)
- [贡献指南](../../CONTRIBUTING.md)

### 示例
- [Slack Adapter](../../agentos/communicationos/channels/slack/)
- [Telegram Adapter](../../agentos/communicationos/channels/telegram/)
- [Email Adapter](../../agentos/communicationos/channels/email/)

### 支持
- GitHub Issues: [提交 bug 或建议](https://github.com/seacow-technology/agentos/issues)
- GitHub Discussions: [讨论设计问题](https://github.com/seacow-technology/agentos/discussions)
- Email: dev@seacow.tech

---

## 附录：常见问题

### Q1: Adapter 应该如何处理速率限制？
**A**: Adapter 不应该实施速率限制，但可以：
1. 在 manifest.json 中声明建议的 rate_limit_per_minute
2. 处理 API 返回的 429 错误（指数退避重试）
3. 记录日志提醒管理员

实际的速率限制由 Policy/Guardian 层实施。

### Q2: 如何处理 channel 特定的消息格式（如 Markdown vs HTML）？
**A**: 在 `send_message()` 中转换：
```python
def send_message(self, message: OutboundMessage) -> bool:
    text = message.text

    # 如果 channel 不支持 Markdown，转换为 Plain Text
    if self.supports_markdown:
        formatted_text = text  # 保持 Markdown
    else:
        formatted_text = markdown_to_plain(text)  # 转换为纯文本

    # 发送...
```

### Q3: 如何处理超长消息（超过 channel 限制）？
**A**: 在 `send_message()` 中处理：
```python
def send_message(self, message: OutboundMessage) -> bool:
    text = message.text
    max_length = 4096  # Telegram 限制

    if len(text) <= max_length:
        # 直接发送
        return self._send_single_message(text)
    else:
        # 分片发送
        chunks = split_text_preserving_formatting(text, max_length)
        for chunk in chunks:
            success = self._send_single_message(chunk)
            if not success:
                return False
        return True
```

### Q4: 如何支持交互式组件（buttons、menus）？
**A**:
1. 在 `parse_event()` 中解析交互事件（button clicks）
2. 将交互数据存储在 `metadata` 字段
3. 在 `send_message()` 中发送交互式消息
4. 在 manifest 中声明 `"interactive"` capability

### Q5: 如何处理编辑/删除的消息？
**A**:
1. 实现可选方法 `parse_edited_message()` 和 `parse_deleted_message()`
2. 返回带有 `metadata.edited = True` 或 `metadata.deleted = True` 的 InboundMessage
3. 由 Core 层决定如何处理（忽略、更新、重新处理等）

### Q6: 是否需要处理 emoji/表情？
**A**: 保持原样传递，不要移除或转换。Emoji 可能有语义（如 "👍" 表示确认）。

### Q7: 如何处理文件下载（attachments）？
**A**:
1. 在 `parse_event()` 中提取文件 URL 或 file_id
2. 存储在 `Attachment.url` 字段（可以是临时 URL 或 file_id）
3. 由 Core 层决定是否下载文件
4. 不要在 Adapter 中下载文件内容（除非必须，如 Telegram file_id 需要先获取 URL）

---

**规范维护者**: AgentOS Core Team
**最后更新**: 2026-02-01
**规范版本**: v1.0.0
**联系方式**: dev@seacow.tech
