# Conversation Mode 实施计划

## 执行模式：全自动化子 agent 实施

**协调者**: Claude Code (主 agent)
**执行者**: 9 个子 agent
**验收者**: 子 agent #9 (端到端验收)
**人工干预**: 无

---

## 架构概览

### 三层模型设计

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Conversation Mode (对话语义层)                  │
│ ─────────────────────────────────────────────────────── │
│ • chat        - 日常对话/问答                             │
│ • discussion  - 发散讨论/观点对撞                         │
│ • plan        - 规划/设计 (严格无副作用)                  │
│ • development - 开发协作 (允许读 repo)                    │
│ • task        - 明确交付物 (触发任务系统)                 │
│                                                           │
│ 作用: 决定 AI 输出风格和用户体验                          │
│ 不负责: 安全门禁和权限控制                                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Execution Phase (权限门禁层)                    │
│ ─────────────────────────────────────────────────────── │
│ • planning   - 禁止 comm.* / 禁止外部副作用               │
│ • execution  - 允许 comm.* (仍受 policy/audit)           │
│                                                           │
│ 作用: Phase Gate 的安全核心，决定能不能碰真实世界          │
│ 规则: 必须显式切换，不受 mode 影响                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Task Lifecycle (任务状态机层)                   │
│ ─────────────────────────────────────────────────────── │
│ planning → executing → verifying → done/failed/blocked    │
│                                                           │
│ 作用: 任务执行器的状态流转                                │
│ 范围: 仅限 Task 实例，不影响 Chat Session                 │
└─────────────────────────────────────────────────────────┘
```

### 核心原则

1. **语义隔离**: mode ≠ phase ≠ task_status
2. **权限隔离**: mode 不能自动越权切换 phase
3. **显式操作**: phase=execution 必须用户确认
4. **可审计**: 所有 phase 切换记录 audit log
5. **向后兼容**: 不破坏现有 Phase Gate 逻辑

---

## 实施波次

### 🚀 Wave 1: 基础架构定义（并行）

**状态**: ✅ 已启动

| Task ID | 任务 | Agent ID | 状态 |
|---------|------|----------|------|
| #1 | 定义三层架构 ADR | a1669c1 | 🔄 In Progress |
| #2 | 扩展 Session metadata | afdb2a1 | 🔄 In Progress |
| #5 | 更新 Phase Gate 文档 | a6cfeaf | 🔄 In Progress |

**依赖**: 无
**预计完成**: 10-15 分钟

---

### 🚀 Wave 2: 前后端实现（并行，依赖 Wave 1）

**状态**: ⏳ 等待 Wave 1 完成

| Task ID | 任务 | 依赖 | 预计启动时间 |
|---------|------|------|-------------|
| #3 | 实现 WebUI Mode Selector | Task #2 | Wave 1 完成后 |
| #4 | 实现 Session API 端点 | Task #2 | Wave 1 完成后 |
| #6 | 实现 Mode-aware 输出模板 | Task #1, #2 | Wave 1 完成后 |

**预计完成**: 15-20 分钟

---

### 🚀 Wave 3: 测试和文档（并行，依赖 Wave 2）

**状态**: ⏳ 等待 Wave 2 完成

| Task ID | 任务 | 依赖 | 预计启动时间 |
|---------|------|------|-------------|
| #7 | 编写 Gate Tests | Task #3, #4, #6 | Wave 2 完成后 |
| #8 | 更新使用文档 | Task #1 | Wave 2 完成后 |

**预计完成**: 10-15 分钟

---

### 🚀 Wave 4: 端到端验收（串行，依赖 Wave 3）

**状态**: ⏳ 等待 Wave 3 完成

| Task ID | 任务 | 依赖 | 预计启动时间 |
|---------|------|------|-------------|
| #9 | 端到端验收测试 | 所有前序任务 | Wave 3 完成后 |

**预计完成**: 15-20 分钟

---

## 技术实施细节

### Session Metadata Schema

```python
# Before
metadata: {
    "model": "local",
    "provider": "ollama",
    "context_budget": 8000,
    "rag_enabled": true,
    # execution_phase 默认不存在 → 隐式 "planning"
}

# After
metadata: {
    "model": "local",
    "provider": "ollama",
    "context_budget": 8000,
    "rag_enabled": true,
    "conversation_mode": "chat",        # 新增：默认 chat
    "execution_phase": "planning"       # 显式设置：默认 planning（安全优先）
}
```

### WebUI 控件设计

```
┌────────────────────────────────────────────────────────┐
│ Chat Session: "今日 AI 新闻"                            │
│                                                         │
│  [Mode: chat ▼] [Phase: planning ▼] [Settings ⚙️]     │
│  └─────┬─────┘   └───────┬────────┘                    │
│        │                  │                             │
│        │                  └─ Phase Selector             │
│        │                     (2 选项，需确认)            │
│        │                                                 │
│        └─ Mode Selector                                 │
│           ├─ chat (日常对话)                             │
│           ├─ discussion (观点对撞)                       │
│           ├─ plan (规划文档) ← 禁用 execution           │
│           ├─ development (开发协作)                      │
│           └─ task (交付物导向)                           │
└────────────────────────────────────────────────────────┘
```

### API 端点设计

```http
# 切换 Conversation Mode (不需要确认)
PATCH /api/sessions/{session_id}/mode
{
  "mode": "development"
}
Response: 200 OK
{
  "ok": true,
  "session": {
    "conversation_mode": "development",
    "execution_phase": "planning"  # 不变！
  }
}

# 切换 Execution Phase (需要确认 + audit)
PATCH /api/sessions/{session_id}/phase
{
  "phase": "execution",
  "confirmed": true
}
Response: 200 OK
{
  "ok": true,
  "session": {
    "conversation_mode": "development",
    "execution_phase": "execution"
  },
  "audit_id": "evt_01xyz..."  # 审计记录
}

# 尝试从 plan mode 切换到 execution
PATCH /api/sessions/{session_id}/phase
{
  "phase": "execution"
}
Response: 403 Forbidden
{
  "ok": false,
  "error": "Cannot switch to execution phase in plan mode",
  "hint": "Plan mode enforces planning phase for deterministic behavior"
}
```

### Phase Gate 逻辑（不变）

```python
# agentos/core/chat/guards/phase_gate.py
def check(operation: str, execution_phase: str):
    """
    Phase Gate 只检查 execution_phase，不看 conversation_mode。

    conversation_mode 是用户体验层，不影响权限判断。
    """
    if operation.startswith("comm."):
        if execution_phase != "execution":  # ← 只看这个字段
            raise PhaseGateError(
                f"Operation '{operation}' is forbidden in {execution_phase} phase."
            )
```

---

## 验收标准（6 个测试场景）

### Scenario 1: 默认安全状态
```
创建新 session
→ mode=chat, phase=planning
→ /comm search → BLOCK ✅
→ 错误提示："External communication is only allowed in execution phase"
```

### Scenario 2: mode 切换不越权
```
切换 mode=plan
→ phase 仍为 planning ✅
→ /comm search → BLOCK ✅
→ AI 输出风格变为"规划文档结构"
```

### Scenario 3: 显式切换到 execution
```
切换 mode=development
→ 点击 Phase Selector → execution
→ 弹出确认对话框："Switch to execution phase? This allows external communication."
→ 用户点击 [Confirm]
→ phase=execution ✅
→ /comm fetch https://example.com → SUCCESS ✅
→ audit log 记录 phase 切换 ✅
```

### Scenario 4: plan mode 禁止 execution
```
切换 mode=plan
→ Phase Selector 显示 "planning (locked)" ✅
→ 尝试切换到 execution → 被拒绝 ✅
→ 错误提示："Plan mode enforces planning phase"
```

### Scenario 5: task mode 允许但不强制 execution
```
切换 mode=task
→ phase 仍为 planning ✅
→ 可以生成任务清单（本地操作）
→ Phase Selector 可用（需确认才能切到 execution）✅
```

### Scenario 6: 审计完整性
```
所有 phase 切换操作 → audit_log 表有记录 ✅
包含：
- session_id
- old_phase
- new_phase
- confirmed_by_user
- timestamp
```

---

## 交付物清单

### 📄 代码文件

**新增**:
- `docs/adr/ADR-CHAT-MODE-001-Conversation-Mode-Architecture.md`
- `agentos/core/chat/models.py` (ConversationMode 枚举)
- `agentos/webui/static/js/components/ModeSelector.js`
- `agentos/webui/static/js/components/PhaseSelector.js`
- `agentos/webui/static/css/mode-selector.css`
- `agentos/core/chat/prompts.py` (mode-specific prompts)
- `tests/unit/core/chat/test_conversation_mode.py`
- `tests/integration/test_mode_phase_isolation.py`
- `tests/integration/test_mode_phase_gate_e2e.py`
- `docs/chat/CONVERSATION_MODE_GUIDE.md`
- `docs/chat/MODE_VS_PHASE.md`

**修改**:
- `agentos/core/chat/service.py` (create_session 默认值)
- `agentos/core/chat/guards/phase_gate.py` (文档注释)
- `agentos/core/chat/comm_commands.py` (文档注释)
- `agentos/core/chat/engine.py` (context 构建)
- `agentos/webui/api/sessions.py` (新增 mode/phase 端点)
- `agentos/webui/static/js/views/ChatView.js` (集成控件)
- `README.md` (快速开始部分)
- `docs/chat/COMMUNICATION_ADAPTER.md`
- `docs/architecture/ADR-CHAT-COMM-001-Chat-CommunicationOS-Integration.md`

### 📊 测试报告

- `CONVERSATION_MODE_ACCEPTANCE_REPORT.md` (子 agent #9 生成)
- 所有 Gate Tests 通过报告

---

## 风险控制

### 已识别风险

1. **语义混淆风险** → 通过 ADR 和文档明确三层边界
2. **权限越权风险** → 通过显式确认和审计日志防范
3. **向后兼容风险** → Phase Gate 逻辑不变，只加文档
4. **UI 交互复杂度** → 通过禁用/锁定状态简化操作

### 回滚策略

如果验收失败：
1. 保留 ADR 文档（架构决策仍然有效）
2. 回滚所有代码更改（通过 git revert）
3. 保持 execution_phase 默认值为 "planning"（安全优先）
4. 重新评估实施方案

---

## 进度监控

**实时状态查询**:
```bash
# 查看所有任务状态
TaskList

# 查看特定任务详情
TaskGet --task-id <ID>

# 查看子 agent 输出（实时）
tail -f /private/tmp/claude-501/-Users-pangge-PycharmProjects-AgentOS/tasks/<agent_id>.output
```

**预计总耗时**: 50-70 分钟
**当前进度**: Wave 1 / 4 (0%)
**下次更新**: Wave 1 完成时

---

## 备注

- 本计划由 Claude Code (主 agent) 协调
- 所有实施由子 agent 自动完成
- 验收测试由子 agent #9 负责
- 人工只需查看最终验收报告

---

**生成时间**: 2026-01-31 00:50 UTC
**协调者**: Claude Code CLI
**版本**: v1.0 (初始计划)
