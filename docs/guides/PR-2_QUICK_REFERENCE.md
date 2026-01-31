# PR-2 快速参考：统一的 Session API

## 概述

从 PR-2 开始，所有 session 管理已统一到 `ChatService`。
- 数据存储：`chat_sessions` 表（不再使用 `webui_sessions`）
- 默认值：`conversation_mode="chat"`, `execution_phase="planning"`

## 开发者指南

### 后端：使用 ChatService

#### 创建 Session

```python
from agentos.core.chat.service import ChatService

chat_service = ChatService()

# 创建 session（自动设置默认值）
session = chat_service.create_session(
    title="My Session",
    metadata={"tags": ["test"], "custom_field": "value"}
)

# session.metadata 自动包含：
# - conversation_mode: "chat"
# - execution_phase: "planning"
```

#### 获取 Session

```python
# 获取单个 session
try:
    session = chat_service.get_session(session_id)
    print(f"Mode: {session.metadata['conversation_mode']}")
    print(f"Phase: {session.metadata['execution_phase']}")
except ValueError:
    print("Session not found")

# 列出所有 sessions
sessions = chat_service.list_sessions(limit=50, offset=0)
```

#### 更新 Mode/Phase

```python
# 更新 conversation mode
chat_service.update_conversation_mode(session_id, "development")

# 更新 execution phase（带审计）
chat_service.update_execution_phase(
    session_id,
    "execution",
    actor="user_123",
    reason="Manual approval"
)
```

#### 消息管理

```python
# 添加消息
message = chat_service.add_message(
    session_id=session_id,
    role="user",
    content="Hello!",
    metadata={"source": "webui"}
)

# 获取消息
messages = chat_service.get_messages(session_id, limit=100, offset=0)

# 获取最近 N 条消息（用于上下文）
recent = chat_service.get_recent_messages(session_id, count=10)

# 统计消息数量
count = chat_service.count_messages(session_id)
```

### 前端：REST API

#### 创建 Session

```javascript
// POST /api/sessions
const response = await fetch('/api/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'My Session',
    tags: ['test', 'pr-2'],
    metadata: { custom: 'value' }
  })
});

const data = await response.json();
console.log(data.conversation_mode);  // "chat"
console.log(data.execution_phase);    // "planning"
```

#### 获取 Session

```javascript
// GET /api/sessions/{id}
const response = await fetch(`/api/sessions/${sessionId}`);
const session = await response.json();

console.log(session.id);
console.log(session.conversation_mode);  // 始终有值
console.log(session.execution_phase);    // 始终有值
```

#### 更新 Mode

```javascript
// PATCH /api/sessions/{id}/mode
const response = await fetch(`/api/sessions/${sessionId}/mode`, {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ mode: 'development' })
});

const data = await response.json();
if (data.ok) {
  console.log('Mode updated:', data.session.conversation_mode);
}
```

#### 更新 Phase

```javascript
// PATCH /api/sessions/{id}/phase
const response = await fetch(`/api/sessions/${sessionId}/phase`, {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    phase: 'execution',
    confirmed: true,  // Required for execution phase
    actor: 'user',
    reason: 'User approved'
  })
});

const data = await response.json();
if (data.ok) {
  console.log('Phase updated:', data.session.execution_phase);
  console.log('Audit ID:', data.audit_id);
}
```

#### 列出 Sessions

```javascript
// GET /api/sessions?limit=50&offset=0
const response = await fetch('/api/sessions?limit=50&offset=0');
const sessions = await response.json();

sessions.forEach(session => {
  console.log(`${session.id}: ${session.title}`);
  console.log(`  Mode: ${session.conversation_mode}`);
  console.log(`  Phase: ${session.execution_phase}`);
});
```

#### 添加消息

```javascript
// POST /api/sessions/{id}/messages
const response = await fetch(`/api/sessions/${sessionId}/messages`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    role: 'user',
    content: 'Hello!',
    metadata: { source: 'webui' }
  })
});

const message = await response.json();
console.log('Message ID:', message.id);
```

#### 获取消息

```javascript
// GET /api/sessions/{id}/messages?limit=100&offset=0
const response = await fetch(
  `/api/sessions/${sessionId}/messages?limit=100&offset=0`
);
const messages = await response.json();

messages.forEach(msg => {
  console.log(`[${msg.role}]: ${msg.content}`);
});
```

## 默认值说明

### conversation_mode（对话模式）

默认值: `"chat"`

可选值:
- `chat`: 普通对话模式
- `discussion`: 讨论模式
- `plan`: 规划模式
- `development`: 开发模式
- `task`: 任务模式

用途: UI/UX 上下文，不影响安全控制

### execution_phase（执行阶段）

默认值: `"planning"`（安全默认值）

可选值:
- `planning`: 规划阶段（只读，安全）
- `execution`: 执行阶段（可写，需确认）

用途: 安全上下文，控制外部操作权限

## 迁移指南

### 从 SessionStore 迁移到 ChatService

**旧代码**:
```python
from agentos.webui.api.sessions import get_session_store

store = get_session_store()
session = store.create_session(user_id="default", metadata={...})
```

**新代码**:
```python
from agentos.core.chat.service import ChatService

chat_service = ChatService()
session = chat_service.create_session(title="My Session", metadata={...})
```

### API 路径变化

无变化！所有 API 路径保持不变：
- `POST /api/sessions`
- `GET /api/sessions`
- `GET /api/sessions/{id}`
- `PATCH /api/sessions/{id}/mode`
- `PATCH /api/sessions/{id}/phase`
- ... 等等

## 错误处理

### Session 不存在

**旧行为**: 返回 `None` 或空结果
**新行为**: 抛出 `ValueError`

```python
try:
    session = chat_service.get_session(session_id)
except ValueError:
    # Session not found
    return {"error": "Session not found"}, 404
```

### Phase 更新失败（404 错误）

**问题**: PR-2 之前，如果 session 在 `webui_sessions` 而不在 `chat_sessions`，会返回 404

**解决**: PR-2 之后，所有 session 都在 `chat_sessions`，不再有此问题

```python
# 现在始终成功（只要 session 存在）
chat_service.update_execution_phase(session_id, "execution")
```

## 测试示例

### 单元测试

```python
import pytest
from agentos.core.chat.service import ChatService

def test_create_session_with_defaults():
    """Test that sessions have default mode/phase"""
    chat_service = ChatService()

    session = chat_service.create_session(title="Test")

    assert session.metadata["conversation_mode"] == "chat"
    assert session.metadata["execution_phase"] == "planning"

def test_update_mode():
    """Test mode update"""
    chat_service = ChatService()

    session = chat_service.create_session(title="Test")
    chat_service.update_conversation_mode(session.session_id, "development")

    updated = chat_service.get_session(session.session_id)
    assert updated.metadata["conversation_mode"] == "development"
```

### E2E 测试

```python
import requests

def test_session_lifecycle():
    """Test full session lifecycle via API"""
    base_url = "http://localhost:8000"

    # Create session
    resp = requests.post(f"{base_url}/api/sessions", json={
        "title": "E2E Test"
    })
    assert resp.status_code == 200
    session = resp.json()
    session_id = session["id"]

    # Verify defaults
    assert session["conversation_mode"] == "chat"
    assert session["execution_phase"] == "planning"

    # Update mode
    resp = requests.patch(
        f"{base_url}/api/sessions/{session_id}/mode",
        json={"mode": "development"}
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] == True

    # Update phase (should not 404)
    resp = requests.patch(
        f"{base_url}/api/sessions/{session_id}/phase",
        json={"phase": "execution", "confirmed": True}
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] == True

    # Cleanup
    requests.delete(f"{base_url}/api/sessions/{session_id}")
```

## FAQ

### Q: 为什么要统一到 ChatService？

**A**:
1. 消除数据重复（webui_sessions vs chat_sessions）
2. 解决 404 错误（mode/phase API 找不到 session）
3. 简化代码维护（单一数据源）
4. 提高一致性（所有 session 都有 mode/phase）

### Q: 旧的 webui_sessions 数据怎么办？

**A**: PR-3 将提供迁移脚本，将旧数据迁移到 chat_sessions 表。

### Q: 前端代码需要改吗？

**A**: 不需要。API 接口保持完全向后兼容。

### Q: 如何验证 session 在正确的表中？

**A**: 使用测试脚本：
```bash
python3 test_pr2_sessions_api.py
```

或直接查询数据库：
```bash
sqlite3 store/registry.sqlite "SELECT session_id, title FROM chat_sessions;"
```

### Q: 如果我需要自定义 mode/phase 默认值？

**A**: 在创建 session 时显式指定：
```python
session = chat_service.create_session(
    title="My Session",
    metadata={
        "conversation_mode": "development",
        "execution_phase": "execution"
    }
)
```

## 相关文档

- [PR-2 实施报告](PR-2_IMPLEMENTATION_REPORT.md)
- [ChatService API 文档](agentos/core/chat/service.py)
- [Session API 文档](agentos/webui/api/sessions.py)
- [测试脚本](test_pr2_sessions_api.py)

## 支持

如有问题，请参考：
1. 实施报告中的"验证结果"部分
2. 运行测试脚本进行验证
3. 查看 ChatService 源码中的文档字符串
