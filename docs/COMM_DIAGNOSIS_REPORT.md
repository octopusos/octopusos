# CommunicationOS 未生效诊断报告

## 问题描述
用户期望 Chat 可以使用 CommunicationOS 访问互联网（如生成今日 AI 新闻简报），但实际上收到的是虚构内容。

## 根本原因

### 1. Phase Gate 阻止问题

**位置**: `agentos/core/chat/comm_commands.py:267, 326, 443, 788`

```python
def _check_phase_gate(execution_phase: str) -> None:
    """Check if command is allowed in current execution phase.

    Phase Gate Rule:
    - planning phase: BLOCK all /comm commands
    - execution phase: ALLOW (subject to policy checks)
    """
    if execution_phase != "execution":
        raise BlockedError(
            "comm.* commands are forbidden in planning phase. "
            "External communication is only allowed during execution to prevent "
            "information leakage and ensure controlled access."
        )
```

**问题**: 所有 `/comm` 命令（search, fetch, brief）都会在 planning phase 被阻止。

### 2. Session 默认配置问题

**位置**: `agentos/core/chat/service.py:42-73`

```python
def create_session(
    self,
    title: Optional[str] = None,
    task_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> ChatSession:
    """Create a new chat session"""
    session_id = session_id or _generate_ulid()
    title = title or "New Chat"
    metadata = metadata or {}

    # Set default metadata
    if "model" not in metadata:
        metadata["model"] = "local"
    if "provider" not in metadata:
        metadata["provider"] = "ollama"
    if "context_budget" not in metadata:
        metadata["context_budget"] = 8000
    if "rag_enabled" not in metadata:
        metadata["rag_enabled"] = True

    # ⚠️ 注意：这里没有设置 execution_phase！
```

**问题**: 新创建的 session 不包含 `execution_phase` metadata。

### 3. Context 默认值问题

**位置**: `agentos/core/chat/engine.py:478-487`

```python
# Build command context
context = {
    "session_id": session_id,
    "chat_service": self.chat_service,
    "task_manager": self.task_manager,
    "memory_service": self.memory_service,
    "router": self.slash_command_router,
    "execution_phase": session.metadata.get("execution_phase", "planning"),  # ⚠️ 默认 "planning"
    "task_id": session.task_id
}
```

**问题**: 当 session.metadata 中没有 `execution_phase` 时，默认值是 `"planning"`。

### 4. 因果链

```
1. 用户创建新 session
   ↓
2. session.metadata 中没有 execution_phase
   ↓
3. ChatEngine 构建 context 时使用默认值 "planning"
   ↓
4. 用户尝试使用 /comm 命令（或期望 AI 自动搜索）
   ↓
5. Phase Gate 检查发现 execution_phase != "execution"
   ↓
6. 命令被阻止，抛出 BlockedError
   ↓
7. 用户收不到真实搜索结果
```

## 现有功能确认

✅ **CommunicationAdapter 已实现** (`agentos/core/chat/communication_adapter.py`)
- 封装了 CommunicationService
- 注册了 WebSearchConnector 和 WebFetchConnector
- 提供 `search()` 和 `fetch()` 方法

✅ **Slash 命令已注册** (`agentos/core/chat/comm_commands.py`)
- `/comm search <query>` - 网络搜索
- `/comm fetch <url>` - 抓取 URL 内容
- `/comm brief ai --today` - 生成 AI 主题简报

✅ **ChatEngine 已集成** (`agentos/core/chat/engine.py:94`)
- `register_comm_command()` 已调用
- 命令路由正常工作

## 为什么 AI 没有主动使用 /comm 命令？

### 当前状态
- AI (Claude Code CLI) **不知道**自己有 `/comm` 命令可用
- AI 没有被明确告知可以使用 CommunicationOS 访问互联网
- 即使知道，也会因为 phase gate 被阻止

### 原因分析
1. **工具可用性未告知**
   - System prompt 中没有告诉 AI 可以使用 `/comm` 命令
   - AI 无法自动发现 slash 命令的存在

2. **使用方式不明确**
   - 即使 AI 知道命令存在，也不知道何时使用
   - 没有明确的触发条件或使用场景说明

3. **Phase Gate 阻碍**
   - 即使 AI 尝试使用，也会被 phase gate 阻止
   - 用户需要手动切换到 execution phase

## 解决方案

### 方案 1: 修改 Session 默认配置 ⭐ 推荐

**修改位置**: `agentos/core/chat/service.py:64-72`

```python
# Set default metadata
if "model" not in metadata:
    metadata["model"] = "local"
if "provider" not in metadata:
    metadata["provider"] = "ollama"
if "context_budget" not in metadata:
    metadata["context_budget"] = 8000
if "rag_enabled" not in metadata:
    metadata["rag_enabled"] = True
if "execution_phase" not in metadata:  # ✅ 添加这一行
    metadata["execution_phase"] = "execution"  # 默认允许外部通信
```

**优点**:
- 最小改动
- 对用户透明
- WebUI 和 CLI 都生效
- 符合大多数使用场景

**缺点**:
- 需要更新架构文档
- 可能影响其他依赖 planning phase 的场景

### 方案 2: 添加 Phase 切换命令

**实现**: 添加 `/phase execution` 命令

```python
def handle_phase_command(command: str, args: List[str], context: Dict[str, Any]) -> CommandResult:
    """Switch execution phase"""
    if not args or args[0] not in ["planning", "execution"]:
        return CommandResult.error_result("Usage: /phase [planning|execution]")

    phase = args[0]
    session_id = context["session_id"]
    chat_service = context["chat_service"]

    # Update session metadata
    session = chat_service.get_session(session_id)
    session.metadata["execution_phase"] = phase
    chat_service.update_session(session_id, metadata=session.metadata)

    return CommandResult.success_result(f"✅ Switched to {phase} phase")
```

**优点**:
- 用户可控
- 保留了 phase gate 的安全机制
- 灵活切换

**缺点**:
- 用户体验不够流畅
- 需要用户主动操作
- 不够直观

### 方案 3: AI 工具可用性告知

**修改位置**: System Prompt 或 WebUI API

在 AI 的 system prompt 中添加：

```markdown
## Available Tools

### CommunicationOS Commands
You have access to internet search and web content fetching via:
- `/comm search <query>` - Search the web for information
- `/comm fetch <url>` - Fetch and extract content from URLs
- `/comm brief ai --today` - Generate AI topic news brief

Use these commands when users ask for:
- Current information, news, or updates
- Web search results
- Fetching specific URLs
- Generating briefings on topics

Example:
User: "给我一个今日的AI新闻简报"
AI: [Uses /comm brief ai --today to generate real brief]
```

**优点**:
- AI 知道何时使用工具
- 提升用户体验
- 充分利用已有功能

**缺点**:
- 仍然依赖方案 1 或 2 解决 phase gate 问题
- 需要更新 AI 配置

### 方案 4: 条件性 Phase Gate

**修改位置**: `agentos/core/chat/comm_commands.py:254-273`

```python
@staticmethod
def _check_phase_gate(execution_phase: str, session_id: str) -> None:
    """Check if command is allowed in current execution phase.

    Phase Gate Rule:
    - planning phase + task context: BLOCK
    - planning phase + chat only: ALLOW
    - execution phase: ALLOW
    """
    # For standalone chat sessions (no task_id), allow comm commands
    if execution_phase != "execution":
        # Check if this is a task-based session
        from agentos.core.chat.service import ChatService
        service = ChatService()
        session = service.get_session(session_id)

        if session.task_id:
            # Task-based session in planning phase: BLOCK
            raise BlockedError(
                "comm.* commands are forbidden in planning phase for task sessions."
            )
        else:
            # Standalone chat session: ALLOW
            logger.info(f"Allowing /comm command in standalone chat session {session_id}")
```

**优点**:
- 保留了 task-based planning phase 的安全性
- 允许 standalone chat 使用 comm 命令
- 更灵活的策略

**缺点**:
- 复杂度增加
- 可能引入新的边界情况

## 推荐实施路径

### 短期 (立即修复)
1. ✅ 实施**方案 1**: 修改 session 默认配置，设置 `execution_phase="execution"`
2. ✅ 更新相关测试用例
3. ✅ 验证 `/comm` 命令在新 session 中可用

### 中期 (增强体验)
4. ✅ 实施**方案 3**: 在 AI system prompt 中告知工具可用性
5. ✅ 添加使用场景示例和触发条件
6. ✅ 更新 WebUI 提示文本

### 长期 (架构优化)
7. ✅ 考虑**方案 4**: 基于 session 类型的条件性 phase gate
8. ✅ 完善文档，说明 planning vs execution phase 的使用场景
9. ✅ 添加 phase 切换的监控和审计

## 验证步骤

### 1. 验证修复后的基本功能
```python
# 创建新 session
session = chat_service.create_session(title="Test Comm")

# 检查 execution_phase
assert session.metadata.get("execution_phase") == "execution"

# 执行 /comm search
result = engine.send_message(session.session_id, "/comm search Python tutorial")
assert "Search results" in result["content"]
```

### 2. 验证 phase gate 行为
```python
# 显式设置为 planning phase
session = chat_service.create_session(
    title="Planning Phase Test",
    metadata={"execution_phase": "planning"}
)

# 尝试 /comm search，应该被阻止
result = engine.send_message(session.session_id, "/comm search test")
assert "Command blocked" in result["content"]
```

### 3. 端到端测试
```bash
# 启动 WebUI
python -m agentos.webui.app

# 创建新对话
# 输入: "给我一个今日的AI新闻简报"
# 期望: AI 使用 /comm brief ai --today 生成真实简报
```

## 相关文件清单

**需要修改**:
- `agentos/core/chat/service.py` (session 默认配置)
- System prompt / AI 配置 (工具可用性告知)

**需要测试**:
- `tests/unit/core/chat/test_service.py`
- `tests/integration/test_chat_comm_integration_e2e.py`
- `tests/webui/test_communication_view.py`

**需要更新文档**:
- `docs/chat/COMMUNICATION_ADAPTER.md`
- `docs/architecture/ADR-CHAT-COMM-001-Chat-CommunicationOS-Integration.md`
- `README.md`

## 总结

**问题**: Session 默认 `execution_phase="planning"`，导致 Phase Gate 阻止所有 `/comm` 命令。

**根因**: `create_session()` 未设置 `execution_phase` metadata，ChatEngine 使用默认值 "planning"。

**影响**: 用户无法使用 CommunicationOS 的互联网访问功能（搜索、抓取、简报生成）。

**修复**: 在 `create_session()` 中设置 `metadata["execution_phase"] = "execution"` 作为默认值。

**验证**: 新 session 可以成功执行 `/comm` 命令并获取真实网络内容。

---

**生成时间**: 2026-01-31
**诊断工具**: Claude Code CLI
**版本**: AgentOS v0.3.1
