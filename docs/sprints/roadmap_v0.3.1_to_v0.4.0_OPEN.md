# AgentOS 补齐路线图：v0.3.1 → v0.4.0

**Status**: 🟡 IN PROGRESS (P1 Sprint)
**Start Date**: 2026-01-27
**Current Sprint**: P1 (WebUI 地基搭建)
**Architecture Status**: v0.3.1 架构已冻结，可安全扩展
**Execution Mode**: 增量迭代，按依赖链分三个 Sprint

⸻

## 🎯 进度跟踪

### P1 Sprint 进度 (1/2 完成)

- [x] **W-P1-01**: WebUI 数据持久化 ✅ **DONE** (2026-01-27)
  - 19 tests, 100% pass
  - SQLiteSessionStore + MemorySessionStore fallback
  - 验收标准 5/5 通过
  - Commits: 8595248, 9f8744f
- [ ] **W-P1-02**: Chat Engine 集成 ⏳ **NEXT**
  - 依赖: W-P1-01 ✅
  - 预计工期: 3-4 天

### 整体进度 (1/8 完成)

| Sprint | Tasks | 完成 | 进度 | 状态 |
|--------|-------|------|------|------|
| P1 (地基) | 2 | 1 | 50% | 🟡 进行中 |
| P2 (控制面) | 3 | 0 | 0% | ⏸️ 未开始 |
| P3 (平台能力) | 3 | 0 | 0% | ⏸️ 未开始 |
| **总计** | **8** | **1** | **12.5%** | 🟡 |

⸻

## 📊 总览

### 剩余待实现功能统计

| 优先级 | 数量 | 占比 | 分布 |
|--------|------|------|------|
| P1 (高) | 1/2 | 50% 完成 | WebUI: ~~数据持久化~~ ✅, Chat Engine 集成 |
| P2 (中) | 0/3 | 0% 完成 | WebUI: 实时事件推送, 身份认证, 任务控制 |
| P3 (低) | 0/3 | 0% 完成 | KB: OpenAI 嵌入, 高级搜索; WebUI: Open Plan 可视化 |
| **总计** | **1/8** | **12.5%** | |

### Sprint 划分策略

**核心原则**: 按依赖链拆分，每个 Sprint 产出可发布的阶段版本

```
P1 Sprint (地基)
  ├─ WebUI 数据持久化 → 会话/消息持久化到 SQLite
  └─ Chat Engine 集成 → 替代 Echo 占位符，接入核心聊天引擎

P2 Sprint (控制面)
  ├─ 实时事件推送 → WebSocket 推送任务状态/日志/事件
  ├─ 身份认证 → Token 认证保护接口
  └─ 任务控制 → 暂停/恢复/取消任务

P3 Sprint (平台能力)
  ├─ OpenAI Embedding → 向量嵌入 provider
  ├─ 高级搜索语法 → 短语搜索 + 布尔运算符
  └─ Open Plan 可视化 → DAG 执行图展示
```

⸻

## 🎯 P1 Sprint: WebUI 地基搭建

**目标**: 让 WebUI 从 demo 变成产品
**依赖**: 无（直接开始）
**完成标准**: WebUI 能持久化数据 + 真实 Chat 响应

### Task W-P1-01: WebUI 会话/消息持久化 ✅ **DONE**

**状态**: ✅ **完成** (2026-01-27)
**实际工期**: 1 天 (按计划)
**优先级**: P1 (最高)
**文件位置**: `agentos/webui/api/sessions.py`, `agentos/webui/store/`, `store/webui_schema.sql`

#### 完成情况

**实现内容**:
- ✅ SessionStore 抽象 (424 行)
- ✅ SQLiteSessionStore 实现 (生产环境)
- ✅ MemorySessionStore 实现 (测试/降级)
- ✅ Session/Message 数据模型 (138 行)
- ✅ webui_schema.sql (100 行)
- ✅ API 层重构 (243 行)
- ✅ app.py 集成 + 降级保护
- ✅ 测试套件 (19 tests, 100% pass)

**验收标准 (5/5)**: ✅ 全部通过
- [x] 重启后会话仍存在 (`test_persistence_across_instances`)
- [x] 重启后消息历史完整
- [x] 支持分页 (`test_list_sessions_pagination`)
- [x] 会话按时间倒序 (`test_sessions_ordered_by_updated_at`)
- [x] 错误场景有明确日志 (降级提示)

**Commits**:
- 8595248: feat(webui): P1 Sprint W-P1-01 完成 - WebUI 数据持久化
- 9f8744f: test(webui): 添加 W-P1-01 持久化测试套件

#### 原计划目标 (参考)
- 将 sessions、messages、events 从内存存储迁移到 SQLite
- 复用现有 `store/registry.sqlite` 或创建新表
- 支持重启后数据不丢失

#### 建议落地方式

1. **抽象存储层**
   ```python
   # agentos/webui/store/session_store.py
   class SessionStore(ABC):
       @abstractmethod
       def create_session(self, session_id, user_id, metadata) -> Session

       @abstractmethod
       def get_session(self, session_id) -> Session | None

       @abstractmethod
       def list_sessions(self, user_id=None, limit=50, offset=0) -> list[Session]

   class MemorySessionStore(SessionStore):
       # 现有实现（保留用于测试）

   class SQLiteSessionStore(SessionStore):
       # 新实现（生产环境）
   ```

2. **数据库 Schema 设计**
   ```sql
   -- store/webui_schema.sql
   CREATE TABLE IF NOT EXISTS webui_sessions (
       session_id TEXT PRIMARY KEY,
       user_id TEXT,
       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
       updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
       metadata TEXT  -- JSON
   );

   CREATE TABLE IF NOT EXISTS webui_messages (
       message_id TEXT PRIMARY KEY,
       session_id TEXT NOT NULL,
       role TEXT NOT NULL,  -- 'user' | 'assistant' | 'system'
       content TEXT NOT NULL,
       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
       metadata TEXT,  -- JSON
       FOREIGN KEY (session_id) REFERENCES webui_sessions(session_id)
   );

   CREATE INDEX idx_messages_session ON webui_messages(session_id, created_at);
   ```

3. **迁移现有 API**
   - 修改 `api/sessions.py` 使用 `SQLiteSessionStore`
   - 添加分页支持（避免一次性全加载）

#### 验收标准

- [ ] 创建会话后重启服务，会话仍存在
- [ ] 发送消息后重启服务，消息历史完整
- [ ] 支持分页拉取历史消息（`limit` + `offset`）
- [ ] 会话列表按时间倒序排列
- [ ] 错误场景有明确日志（DB 连接失败、表不存在等）

#### 测试要点

```bash
# 手动验证
1. 启动 WebUI，创建会话 A，发送 5 条消息
2. 停止服务，重启
3. 验证会话 A 仍在列表中
4. 验证消息历史完整（5 条）

# 自动化测试
pytest tests/webui/test_session_persistence.py -v
```

⸻

### Task W-P1-02: WebUI Chat Engine 集成

**优先级**: P1 (最高)
**预计工期**: 3-4 天
**依赖**: W-P1-01 完成
**文件位置**: `agentos/webui/websocket/chat.py`, `agentos/core/chat/`

#### 目标
- WebSocket chat 不再 echo，接入 `agentos.core.chat` 真实引擎
- 支持流式输出（streaming response）
- 将 UI 的 model 选择传递到 chat engine

#### 建议落地方式

1. **集成 Chat Engine**
   ```python
   # agentos/webui/websocket/chat.py
   from agentos.core.chat.engine import ChatEngine
   from agentos.core.chat.service import ChatService

   @app.websocket("/ws/chat/{session_id}")
   async def websocket_chat(websocket: WebSocket, session_id: str):
       await websocket.accept()

       # 初始化 Chat Engine
       chat_service = ChatService()

       try:
           while True:
               data = await websocket.receive_json()
               message = data.get("message", "")
               model = data.get("model", "default")  # 从 UI 获取

               # 调用真实 Chat Engine
               async for chunk in chat_service.stream_chat(
                   session_id=session_id,
                   message=message,
                   model=model
               ):
                   await websocket.send_json({
                       "type": "chunk",
                       "content": chunk
                   })

               # 发送完成标记
               await websocket.send_json({"type": "done"})
       except WebSocketDisconnect:
           manager.disconnect(session_id)
   ```

2. **适配 Core Chat API**
   - 确认 `agentos.core.chat.service` 提供的接口
   - 如果不支持流式，先做阻塞调用，后续优化

3. **UI Model Selector 传递**
   ```javascript
   // static/js/main.js
   function sendMessage(message) {
       const model = document.getElementById('model-selector').value;
       ws.send(JSON.stringify({
           message: message,
           model: model  // 传递给后端
       }));
   }
   ```

#### 验收标准

- [ ] UI 发送消息，收到真实 Chat Engine 的回复（非 echo）
- [ ] 支持流式输出（逐字显示，不是一次性返回）
- [ ] 切换 model selector，后续消息使用新模型
- [ ] 错误场景有明确提示：
  - LLM API Key 未配置
  - 模型不存在
  - 网络超时
- [ ] 消息正确持久化到数据库（W-P1-01 集成）

#### 测试要点

```bash
# 手动验证
1. 配置 LLM provider (OPENAI_API_KEY 或其他)
2. 启动 WebUI，发送消息 "Hello"
3. 验证收到非 echo 的真实回复
4. 切换模型，验证后续消息使用新模型
5. 断网，验证错误提示友好

# 自动化测试
pytest tests/webui/test_chat_integration.py -v
```

⸻

## 📈 P2 Sprint: WebUI 控制面能力

**目标**: 让 WebUI 成为系统控制面
**依赖**: P1 完成（数据持久化 + Chat 集成）
**完成标准**: 实时状态推送 + 认证保护 + 任务控制

### Task W-P2-01: 实时事件推送

**优先级**: P2
**预计工期**: 3-4 天
**依赖**: W-P1-01 (持久化)
**文件位置**: `agentos/webui/api/events.py`, `agentos/webui/websocket/events.py`

#### 目标
- WebSocket 推送任务状态变化、事件流、日志
- UI 实时更新，无需轮询

#### 建议落地方式

1. **创建事件推送 WebSocket**
   ```python
   # agentos/webui/websocket/events.py
   @app.websocket("/ws/events")
   async def websocket_events(websocket: WebSocket):
       await websocket.accept()

       # 订阅事件总线
       event_bus = EventBus.get_instance()
       queue = asyncio.Queue()
       event_bus.subscribe(queue)

       try:
           while True:
               event = await queue.get()
               await websocket.send_json({
                   "type": event.type,
                   "data": event.data,
                   "timestamp": event.timestamp
               })
       except WebSocketDisconnect:
           event_bus.unsubscribe(queue)
   ```

2. **实现事件总线（简化版）**
   ```python
   # agentos/webui/events/bus.py
   class EventBus:
       _instance = None

       def __init__(self):
           self._subscribers = []

       @classmethod
       def get_instance(cls):
           if cls._instance is None:
               cls._instance = EventBus()
           return cls._instance

       def subscribe(self, queue: asyncio.Queue):
           self._subscribers.append(queue)

       def publish(self, event: Event):
           for queue in self._subscribers:
               queue.put_nowait(event)
   ```

3. **集成到 Task 状态变更**
   - 在 `agentos/core/task/manager.py` 更新状态时发布事件
   - 或在 CLI/pipeline 执行时发布

#### 验收标准

- [ ] 创建新 task → UI 2 秒内显示状态
- [ ] 任务状态变化（pending → running → completed）→ UI 实时更新
- [ ] WebSocket 断线重连后能补偿缺失事件（通过 `since_timestamp`）
- [ ] 多客户端同时连接，各自收到独立事件流

#### 测试要点

```bash
# 手动验证
1. 打开两个浏览器窗口
2. 在终端执行 `agentos task create "test"`
3. 验证两个窗口同时收到新任务通知

# 压力测试
创建 100 个任务，验证 UI 不卡顿
```

⸻

### Task W-P2-02: 身份认证（Token）

**优先级**: P2
**预计工期**: 2 天
**文件位置**: `agentos/webui/auth/`, `agentos/webui/app.py`

#### 目标
- 最小可用认证：token + middleware
- 保护所有写接口和 WebSocket

#### 建议落地方式

1. **Token 生成和校验**
   ```python
   # agentos/webui/auth/token.py
   import secrets
   import hashlib

   class TokenAuth:
       def __init__(self):
           self.valid_tokens = set()
           # 从环境变量加载初始 token
           if token := os.getenv("AGENTOS_WEBUI_TOKEN"):
               self.valid_tokens.add(self._hash_token(token))

       def _hash_token(self, token: str) -> str:
           return hashlib.sha256(token.encode()).hexdigest()

       def validate(self, token: str) -> bool:
           return self._hash_token(token) in self.valid_tokens
   ```

2. **FastAPI Middleware**
   ```python
   # agentos/webui/auth/middleware.py
   from fastapi import Request, HTTPException
   from starlette.middleware.base import BaseHTTPMiddleware

   class AuthMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request: Request, call_next):
           # 豁免路径
           if request.url.path in ["/api/health", "/", "/static/*"]:
               return await call_next(request)

           # 检查 Authorization header
           auth_header = request.headers.get("Authorization")
           if not auth_header or not auth_header.startswith("Bearer "):
               raise HTTPException(status_code=401, detail="Unauthorized")

           token = auth_header[7:]  # 去掉 "Bearer "
           if not TokenAuth().validate(token):
               raise HTTPException(status_code=403, detail="Forbidden")

           return await call_next(request)
   ```

3. **WebSocket 认证**
   ```python
   @app.websocket("/ws/chat/{session_id}")
   async def websocket_chat(websocket: WebSocket, session_id: str, token: str = Query(...)):
       if not TokenAuth().validate(token):
           await websocket.close(code=1008, reason="Unauthorized")
           return

       await websocket.accept()
       # ...
   ```

#### 验收标准

- [ ] 无 token 访问 `/api/tasks` → 401
- [ ] 错误 token → 403
- [ ] 正确 token → 正常访问
- [ ] WebSocket 连接必须校验 token
- [ ] UI 有 token 输入界面（或从 localStorage 读取）

#### 测试要点

```bash
# 手动验证
export AGENTOS_WEBUI_TOKEN=test-secret-token
agentos web

# 无 token
curl http://localhost:8000/api/tasks
# → 401

# 有 token
curl -H "Authorization: Bearer test-secret-token" http://localhost:8000/api/tasks
# → 200
```

⸻

### Task W-P2-03: 任务控制（暂停/恢复/取消）

**优先级**: P2
**预计工期**: 3 天
**依赖**: W-P2-02 (认证)
**文件位置**: `agentos/webui/api/tasks.py`, `agentos/core/runner/`

#### 目标
- WebUI 能对 task 发出 pause/resume/cancel 指令
- 操作可追溯（审计日志）

#### 建议落地方式

1. **新增 Task Control API**
   ```python
   # agentos/webui/api/tasks.py
   @router.post("/tasks/{task_id}/pause")
   async def pause_task(task_id: str):
       """暂停任务"""
       runner = TaskRunner.get_instance()
       result = runner.pause(task_id)
       return {"status": "paused", "task_id": task_id}

   @router.post("/tasks/{task_id}/resume")
   async def resume_task(task_id: str):
       """恢复任务"""
       runner = TaskRunner.get_instance()
       result = runner.resume(task_id)
       return {"status": "running", "task_id": task_id}

   @router.post("/tasks/{task_id}/cancel")
   async def cancel_task(task_id: str):
       """取消任务"""
       runner = TaskRunner.get_instance()
       result = runner.cancel(task_id)
       return {"status": "cancelled", "task_id": task_id}
   ```

2. **集成 Pause Gate**
   - 确认 `agentos/core/gates/pause_gate.py` 提供的接口
   - 映射到 runner 的控制方法

3. **审计日志**
   ```python
   # 在控制操作中记录
   audit_logger.log(
       action="task.pause",
       task_id=task_id,
       user="api",
       timestamp=now()
   )
   ```

#### 验收标准

- [ ] UI 点击"暂停" → 任务进入 `paused` 状态
- [ ] 暂停后任务不再执行，可恢复
- [ ] 点击"取消" → 任务进入 `cancelled` 状态，不可恢复
- [ ] 所有操作写入审计日志 (`task_audits` 表)
- [ ] 非法操作有明确错误提示（如暂停已完成的任务）

#### 测试要点

```bash
# 手动验证
1. 创建长时任务（如"生成 1000 个文件"）
2. 任务运行中，点击"暂停"
3. 验证任务停止执行
4. 点击"恢复"，验证任务继续

# E2E 测试
pytest tests/webui/test_task_control.py -v
```

⸻

## 🚀 P3 Sprint: 平台能力扩展

**目标**: 增强知识库和可视化能力
**依赖**: P2 完成
**完成标准**: OpenAI embedding + 高级搜索 + Plan 可视化

### Task KB-P3-01: OpenAI Embedding Provider

**优先级**: P3
**预计工期**: 2 天
**文件位置**: `agentos/core/project_kb/embedding/openai_provider.py`

#### 目标
- 支持 OpenAI embedding API
- 保持与现有 provider 接口一致

#### 建议落地方式

1. **实现 OpenAI Provider**
   ```python
   # agentos/core/project_kb/embedding/openai_provider.py
   import openai
   from .base import EmbeddingProvider

   class OpenAIEmbeddingProvider(EmbeddingProvider):
       def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
           self.api_key = api_key
           self.model = model
           openai.api_key = api_key

       def embed(self, texts: list[str]) -> list[list[float]]:
           """生成向量嵌入"""
           try:
               response = openai.Embedding.create(
                   input=texts,
                   model=self.model
               )
               return [item["embedding"] for item in response["data"]]
           except openai.error.RateLimitError:
               raise EmbeddingError("Rate limit exceeded")
           except openai.error.AuthenticationError:
               raise EmbeddingError("Invalid API key")
   ```

2. **注册到 Factory**
   ```python
   # agentos/core/project_kb/embedding/factory.py
   def create_provider(config: dict) -> EmbeddingProvider:
       provider_type = config.get("type", "local_tfidf")

       if provider_type == "openai":
           return OpenAIEmbeddingProvider(
               api_key=config["api_key"],
               model=config.get("model", "text-embedding-3-small")
           )
       elif provider_type == "local_tfidf":
           return LocalTFIDFProvider()
       else:
           raise ValueError(f"Unknown provider: {provider_type}")
   ```

3. **配置管理**
   ```yaml
   # config/embedding.yaml
   embedding:
     provider: openai
     api_key: ${OPENAI_API_KEY}
     model: text-embedding-3-small
     cost_limit: 1.0  # USD per day
   ```

#### 验收标准

- [ ] 配置 `provider=openai` 后能正常生成向量
- [ ] 同一文本向量维度一致（1536 for text-embedding-3-small）
- [ ] 错误处理明确：
  - API key 缺失 → 清晰错误提示
  - 429 Rate Limit → 自动重试或明确提示
  - 网络错误 → Timeout 有合理默认值
- [ ] 成本控制：记录 token 使用量

#### 测试要点

```python
# tests/project_kb/test_openai_embedding.py
def test_openai_embedding():
    provider = OpenAIEmbeddingProvider(api_key=os.getenv("OPENAI_API_KEY"))
    vectors = provider.embed(["hello", "world"])

    assert len(vectors) == 2
    assert len(vectors[0]) == 1536  # text-embedding-3-small
    assert isinstance(vectors[0][0], float)
```

⸻

### Task KB-P3-02: 高级搜索语法

**优先级**: P3
**预计工期**: 2-3 天
**文件位置**: `agentos/core/project_kb/searcher.py`

#### 目标
- 支持短语搜索 `"exact phrase"`
- 支持布尔运算符 `AND`, `OR`, `NOT`

#### 建议落地方式

1. **扩展搜索语法**
   ```python
   # agentos/core/project_kb/searcher.py
   def search(self, query: str, limit: int = 10) -> list[SearchResult]:
       """
       支持语法:
       - "exact phrase" → 短语搜索
       - term1 AND term2 → 必须同时出现
       - term1 OR term2 → 至少一个出现
       - term1 NOT term2 → term1 出现但 term2 不出现
       """
       parsed_query = self._parse_query(query)
       fts5_query = self._to_fts5_query(parsed_query)

       # 执行 FTS5 查询
       cursor = self.conn.execute(
           f"SELECT * FROM kb_chunks WHERE kb_chunks MATCH ? LIMIT ?",
           (fts5_query, limit)
       )
       return [SearchResult.from_row(row) for row in cursor]

   def _parse_query(self, query: str) -> ParsedQuery:
       """解析查询语法"""
       # 识别短语 "..."
       phrases = re.findall(r'"([^"]+)"', query)

       # 识别布尔运算符
       tokens = query.split()
       operators = ["AND", "OR", "NOT"]

       return ParsedQuery(phrases=phrases, tokens=tokens, operators=operators)

   def _to_fts5_query(self, parsed: ParsedQuery) -> str:
       """转换为 FTS5 查询语法"""
       # FTS5 语法:
       # - "phrase" → 短语
       # - term1 AND term2 → term1 AND term2
       # - term1 OR term2 → term1 OR term2
       # - NOT term → NOT term

       # 简化实现：直接映射
       return parsed.to_fts5()
   ```

2. **输入验证和转义**
   ```python
   def _sanitize_query(self, query: str) -> str:
       """防止 SQL 注入"""
       # FTS5 支持的特殊字符需要转义
       dangerous_chars = ["(", ")", "*", "^"]
       for char in dangerous_chars:
           query = query.replace(char, f"\\{char}")
       return query
   ```

#### 验收标准

- [ ] `"machine learning"` 只匹配连续短语
- [ ] `python AND django` 匹配同时包含两个词的文档
- [ ] `python OR ruby` 匹配至少包含一个词的文档
- [ ] `python NOT django` 匹配包含 python 但不包含 django 的文档
- [ ] 非法语法返回友好错误（不是 SQL 错误）
- [ ] 性能：复杂查询响应时间 < 500ms

#### 测试要点

```python
# tests/project_kb/test_advanced_search.py
def test_phrase_search():
    searcher = Searcher(db_path)
    results = searcher.search('"open source"')
    for result in results:
        assert "open source" in result.text.lower()

def test_boolean_search():
    results = searcher.search('python AND django')
    for result in results:
        assert "python" in result.text.lower()
        assert "django" in result.text.lower()
```

⸻

### Task UI-P3-01: Open Plan 可视化（DAG）

**优先级**: P3
**预计工期**: 4-5 天
**文件位置**: `agentos/webui/api/plans.py`, `agentos/webui/static/js/plan-viewer.js`

#### 目标
- 在 WebUI 中展示 Open Plan / ExecutionGraph
- 显示节点依赖、风险标记、evidence_refs

#### 建议落地方式

1. **后端 API：输出标准 Graph JSON**
   ```python
   # agentos/webui/api/plans.py
   @router.get("/tasks/{task_id}/plan")
   async def get_task_plan(task_id: str):
       """获取任务的 Open Plan"""
       task = task_manager.get_task(task_id)
       if not task:
           raise HTTPException(404, "Task not found")

       # 从 lineage 找到 open_plan
       open_plan = task_manager.get_lineage_entry(task_id, entry_type="open_plan")

       # 转换为前端友好的格式
       return {
           "nodes": [
               {
                   "id": node.id,
                   "label": node.action_type,
                   "risk": node.risk_level,
                   "evidence_refs": node.evidence_refs,
                   "requires_review": node.requires_review
               }
               for node in open_plan.nodes
           ],
           "edges": [
               {
                   "from": edge.from_id,
                   "to": edge.to_id,
                   "type": edge.type  # "depends_on" | "blocks"
               }
               for edge in open_plan.edges
           ]
       }
   ```

2. **前端：使用轻量图可视化库**
   ```javascript
   // static/js/plan-viewer.js (使用 vis.js 或 cytoscape.js)
   async function renderPlan(taskId) {
       const response = await fetch(`/api/tasks/${taskId}/plan`);
       const plan = await response.json();

       // 使用 vis.js 渲染
       const container = document.getElementById('plan-container');
       const data = {
           nodes: new vis.DataSet(plan.nodes.map(node => ({
               id: node.id,
               label: node.label,
               color: getRiskColor(node.risk),
               title: `Evidence: ${node.evidence_refs.join(', ')}`
           }))),
           edges: new vis.DataSet(plan.edges.map(edge => ({
               from: edge.from,
               to: edge.to,
               arrows: 'to'
           })))
       };

       const options = {
           layout: { hierarchical: { direction: 'UD' } },
           physics: { enabled: false }
       };

       new vis.Network(container, data, options);
   }

   function getRiskColor(risk) {
       const colors = {
           'low': '#28a745',
           'medium': '#ffc107',
           'high': '#dc3545',
           'critical': '#6f42c1'
       };
       return colors[risk] || '#6c757d';
   }
   ```

3. **UI 集成**
   ```html
   <!-- templates/task_detail.html -->
   <div class="task-detail">
       <h2>Task: {{ task.id }}</h2>
       <button onclick="showPlan('{{ task.id }}')">View Plan</button>

       <div id="plan-container" style="width: 100%; height: 600px;"></div>
   </div>
   ```

#### 验收标准

- [ ] 任意 task 能打开 Plan View
- [ ] 节点按风险等级着色（low=绿, high=红）
- [ ] 鼠标悬停节点显示 tooltip（evidence_refs, locks）
- [ ] 点击节点展开详情面板（action, inputs, outputs）
- [ ] 依赖关系用箭头清晰表示
- [ ] 支持缩放和拖拽
- [ ] 无 plan 的任务显示友好提示

#### 测试要点

```bash
# 手动验证
1. 运行任务到 open_plan 阶段
2. 打开 WebUI，点击"View Plan"
3. 验证图形正确渲染
4. 悬停节点，验证 tooltip 信息完整

# 边界测试
- 测试包含 100+ 节点的大型 plan
- 测试循环依赖检测
```

⸻

## 📝 实施建议

### Sprint 执行顺序

```
Phase 1: P1 Sprint (2 周)
  Week 1: W-P1-01 (持久化)
  Week 2: W-P1-02 (Chat 集成)
  → Release: v0.3.2 (WebUI Beta)

Phase 2: P2 Sprint (2 周)
  Week 1: W-P2-01 (事件推送) + W-P2-02 (认证)
  Week 2: W-P2-03 (任务控制)
  → Release: v0.3.3 (WebUI Stable)

Phase 3: P3 Sprint (2-3 周)
  Week 1: KB-P3-01 (OpenAI embedding)
  Week 2: KB-P3-02 (高级搜索) + UI-P3-01 (可视化)
  → Release: v0.4.0 (Platform Capabilities)
```

### 并行策略

**P1 阶段**：W-P1-01 和 W-P1-02 可部分并行（前者做 DB schema，后者做 API 适配）

**P2 阶段**：W-P2-01 和 W-P2-02 可完全并行（不同模块）

**P3 阶段**：KB-P3-01, KB-P3-02 可并行，UI-P3-01 可独立进行

### 质量保证

每个 Task 必须满足：
1. **功能验收**：验收标准 100% 通过
2. **测试覆盖**：至少有手动测试脚本 + 核心路径自动化测试
3. **文档更新**：README / API 文档 / 功能清单同步更新
4. **向后兼容**：不破坏现有功能（除非明确标记为 breaking change）

### 风险控制

| 风险 | 缓解措施 |
|------|---------|
| P1 持久化迁移破坏现有会话 | 先做数据备份，提供降级开关（env: `USE_MEMORY_STORE=true`） |
| Chat Engine 集成性能问题 | 先做同步调用，后续优化为异步流式 |
| OpenAI API 成本超预算 | 设置 cost_limit，超限自动降级到 local_tfidf |
| 可视化渲染大型 Plan 卡顿 | 限制节点数（>100 时分页或简化显示） |

⸻

## 🎯 完成后的系统状态

### v0.4.0 系统能力

**核心系统** (v0.3.1 已完成)
- ✅ 任务管理、执行引擎、协调器、评估器
- ✅ 三层验证架构（Schema / BR / DE RED LINE）
- ✅ Dry Executor、Open Plan、审计日志
- ✅ 分布式锁、内存管理、知识库

**WebUI 系统** (v0.4.0 目标)
- ✅ 数据持久化（会话/消息/事件）
- ✅ 真实 Chat Engine 集成
- ✅ 实时事件推送（WebSocket）
- ✅ 身份认证（Token）
- ✅ 任务控制（暂停/恢复/取消）
- ✅ Open Plan 可视化

**知识库系统** (v0.4.0 目标)
- ✅ OpenAI Embedding Provider
- ✅ 高级搜索语法（短语/布尔）
- ✅ FTS5 全文索引

### 实现完成度预测

| 版本 | 完整实现率 | 待实现率 | 说明 |
|------|-----------|---------|------|
| v0.3.1 (当前) | 95.8% | 4.2% | 架构稳定，8 项增强功能待实现 |
| v0.3.2 (P1) | 96.9% | 3.1% | WebUI 地基完成 |
| v0.3.3 (P2) | 98.4% | 1.6% | WebUI 控制面完成 |
| v0.4.0 (P3) | 100% | 0% | 🎉 **功能完整** |

⸻

## 📚 相关文档

- [v0.3.1 Release Notes](../releases/v0.3.1.md)
- [Architecture Validation Layers](../architecture/VALIDATION_LAYERS.md)
- [功能清单](../功能清单.md)
- [WebUI User Guide](../guides/webui.md)

⸻

**Last Updated**: 2026-01-27
**Status**: 🟢 OPEN - Ready for Execution
**Next Action**: 用户确认路线图后，开始 P1 Sprint (Task W-P1-01)
