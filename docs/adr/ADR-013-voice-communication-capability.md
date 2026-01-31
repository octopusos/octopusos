# ADR-013: Voice Communication Capability (CommunicationOS::Voice MVP)

**Status:** ✅ Accepted
**Date:** 2026-02-01
**Authors:** AgentOS Architecture Team
**Related ADRs:** ADR-011 (Time Contract), ADR-012 (Capability Contract)

---

## Context

AgentOS v3 已完成 Memory、Decision、Evidence 等核心 Capability 的实现，但仍缺少**语音交互能力**作为输入通道。用户需要能够通过语音与 AgentOS 对话，而不仅仅依赖文本输入。

### 核心需求

1. **实时语音识别 (STT)**：用户通过麦克风说话 → 转为文本 → 送入 Chat 决策链
2. **本地化优先**：MVP 阶段必须支持完全本地运行（无外部依赖的基础能力）
3. **Provider 可插拔**：未来可扩展 Twilio、Google Cloud Speech、Azure 等云服务
4. **审计与治理**：所有语音会话必须可追踪、可审计、可关停
5. **低心智负担**：前端只需标准 WebAudio API，不强依赖第三方 SDK

### 核心挑战

- **延迟敏感**：语音交互对延迟的容忍度远低于文本（< 500ms）
- **数据量大**：16kHz PCM 音频每秒约 32KB，需要高效传输和处理
- **状态同步**：浏览器麦克风采集 → WebSocket 传输 → 后端 STT → 决策链 → 返回响应，多个异步环节需协调
- **资源消耗**：本地 Whisper 模型（即使是 small）也需要一定 CPU/内存

---

## Decision

### 1. 整体架构决策：CommunicationOS::Voice 作为独立 Capability

Voice 能力按照 AgentOS v3 Capability Contract 实现：

```
agentos/
  core/
    communication/
      voice/
        __init__.py
        models.py              # VoiceSession, VoiceEvent, Enums
        policy.py              # RiskTier + AdminToken gate
        service.py             # 会话管理 + 事件分发
        stt_service.py         # STT 协调层
        providers/             # Voice Provider 抽象
          base.py              # IVoiceProvider
          local.py             # LocalProvider (WebSocket 麦克风)
          twilio.py            # TwilioProvider (MVP stub)
        stt/                   # STT 引擎抽象
          base.py              # ISTTProvider
          whisper_local.py     # faster-whisper adapter
          vad.py               # Voice Activity Detection
        tts/                   # TTS (预留，MVP 可选)
          base.py
          dummy.py
```

### 2. MVP 技术栈决策

#### 2.1 STT 引擎：faster-whisper (本地 Whisper)

**选择理由：**
- ✅ 完全本地化，无外部 API 依赖
- ✅ 基于 CTranslate2 优化，速度比 openai-whisper 快 4x
- ✅ CPU 也能跑（small/base 模型），GPU 可选加速
- ✅ 支持多语言（英文、中文、日语等 90+ 种）
- ⚠️ 缺点：首次下载模型需要网络（约 150MB for small）

**配置：**
```bash
VOICE_STT_MODEL=small          # base/small/medium/large
VOICE_STT_DEVICE=auto          # cpu/cuda/auto
VOICE_STT_LANGUAGE=auto        # auto/en/zh
VOICE_STT_VAD_ENABLED=true     # 启用 VAD 自动分段
```

#### 2.2 VAD (Voice Activity Detection)：webrtcvad

**选择理由：**
- ✅ WebRTC 项目的成熟组件，准确率高
- ✅ 轻量（C 扩展），延迟低（< 10ms）
- ✅ 支持 3 种灵敏度模式（0=保守, 2=激进）

**用途：** 检测静音 → 触发 STT final 事件

#### 2.3 前端音频采集：WebAudio API (ScriptProcessor)

**选择理由：**
- ✅ 浏览器原生 API，无需第三方库
- ✅ AudioWorklet 是最佳选择，但 ScriptProcessor 兼容性更好
- ⚠️ ScriptProcessor 已 deprecated，但 2026 年仍广泛支持

**采集参数：**
```javascript
{
  sampleRate: 16000,       // Whisper 要求 16kHz
  channels: 1,             // 单声道
  codec: "pcm_s16le",      // 16-bit PCM
  chunkDuration: 40ms      // 每 40ms 发一个 chunk (640 bytes)
}
```

#### 2.4 传输协议：WebSocket + JSON Events

**双向事件协议：**

**Client → Server:**
```json
{
  "type": "voice.session.join",
  "session_id": "vs_xxx",
  "client": {"ua": "...", "tz": "..."}
}

{
  "type": "voice.audio.chunk",
  "session_id": "vs_xxx",
  "seq": 12,
  "format": {"codec": "pcm_s16le", "sample_rate": 16000, "channels": 1},
  "payload_b64": "....",
  "t_ms": 12345
}

{
  "type": "voice.audio.end",
  "session_id": "vs_xxx",
  "seq": 99
}
```

**Server → Client:**
```json
{
  "type": "voice.stt.partial",
  "session_id": "vs_xxx",
  "text": "hello wor",
  "t_ms": 12500
}

{
  "type": "voice.stt.final",
  "session_id": "vs_xxx",
  "text": "hello world",
  "t_ms": 13000
}

{
  "type": "voice.assistant.text",
  "session_id": "vs_xxx",
  "text": "Got it!"
}

{
  "type": "voice.error",
  "session_id": "vs_xxx",
  "code": "stt_failed",
  "message": "..."
}
```

### 3. Provider 架构决策

#### 3.1 IVoiceProvider 抽象

所有 Voice Provider 必须实现：

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class IVoiceProvider(ABC):
    @abstractmethod
    async def create_session(self, project_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """创建 Voice 会话，返回 session metadata"""
        pass

    @abstractmethod
    async def stop_session(self, session_id: str) -> None:
        """停止会话"""
        pass

    @abstractmethod
    async def get_status(self, session_id: str) -> Dict[str, Any]:
        """获取会话状态"""
        pass
```

#### 3.2 MVP Providers

**LocalProvider (MVP 核心)**
- 管理 WebSocket 连接
- 协调麦克风音频流 → STT → Chat 决策链

**TwilioProvider (MVP stub)**
- MVP 阶段仅提供配置存储和 token 生成
- 不承载音频流（音频仍走 LocalProvider）
- 为未来 Twilio Media Streams / PSTN 预留接口

**设计理念：** MVP 先把"语音能力"做出来，Provider 只是传输层抽象，随时可切换。

### 4. 审计与治理决策

#### 4.1 Policy Gate

```python
from agentos.core.communication.voice.policy import VoicePolicy

class VoicePolicy:
    @staticmethod
    def evaluate(session: VoiceSession) -> PolicyVerdict:
        """
        Voice 作为输入能力，风险等级：LOW
        - 只接收语音输入 → 不需要 admin_token
        - 执行高危操作（写配置、外呼）→ 沿用现有 Execution Gate
        """
        return PolicyVerdict(
            risk_tier=RiskTier.LOW,
            admin_token_required=False,
            reason="Voice input is read-only capability"
        )
```

#### 4.2 审计事件

所有 Voice 事件写入 `VoiceEvent` 表：

```sql
CREATE TABLE voice_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    project_id TEXT,
    event_type TEXT NOT NULL,  -- 'session_created', 'audio_chunk', 'stt_final', 'assistant_reply'
    provider TEXT,              -- 'local', 'twilio'
    stt_provider TEXT,          -- 'whisper_local'
    data_json TEXT,             -- 事件 payload (不含音频，只有 metadata)
    created_at_epoch_ms INTEGER NOT NULL,
    trace_id TEXT               -- 关联到 audit trace
);
```

**审计内容包括：**
- ✅ 会话创建/停止时间
- ✅ STT 文本结果（partial/final）
- ✅ Assistant 回复内容
- ✅ 延迟指标（麦克风 → STT → 回复）
- ❌ **不存储原始音频** (隐私考虑)

### 5. 实时性优化决策

#### 5.1 分段策略

**问题：** Whisper 必须对"完整句子"才能获得最佳效果，但等待完整句子会增加延迟。

**MVP 方案：**
1. **滑动窗口**：每 500ms 累积音频窗口
2. **VAD 触发**：检测到静音 ≥ 500ms → 触发 `final` 事件
3. **Partial 预览**：每 1s 可选地发送 `partial` 事件（让用户看到"正在识别..."）

**优化点（v1+）：**
- streaming Whisper（需要自定义模型）
- 预测性 VAD（在用户停顿前就开始转写）

#### 5.2 延迟基准（MVP 目标）

| 环节 | 目标延迟 |
|------|---------|
| 麦克风采集 → WS 发送 | < 50ms |
| WS 传输 | < 50ms |
| VAD 检测 | < 10ms |
| Whisper 转写 (small, 3s 音频) | < 500ms (CPU) |
| Chat 决策 (简单问答) | < 1s |
| **总延迟 (用户说完 → 看到文本)** | **< 1.5s** |

---

## REST + WebSocket API 设计

### REST Endpoints

```
POST   /api/voice/sessions             # 创建会话
POST   /api/voice/sessions/{id}/stop   # 停止会话
GET    /api/voice/sessions/{id}        # 获取会话状态
GET    /api/voice/sessions             # 列出所有会话 (admin)
```

### WebSocket Endpoint

```
WS     /api/voice/sessions/{id}/events
```

**连接生命周期：**
1. Client POST `/api/voice/sessions` → 拿到 `session_id`
2. Client 连接 WS `/api/voice/sessions/{id}/events`
3. Client 发送 `voice.session.join`
4. Client 开始发送 `voice.audio.chunk`
5. Server 推送 `voice.stt.partial/final` + `voice.assistant.text`
6. Client 发送 `voice.audio.end` 或断开连接
7. Server 自动清理会话（5 分钟 TTL）

---

## WebUI 集成

### 新增 VoiceView

**文件：** `agentos/webui/static/js/views/VoiceView.js`

**UI 功能：**
- Start/Stop 按钮
- 实时 transcript 显示（partial = 灰色，final = 白色）
- Assistant 回复气泡
- 会话状态指示器（ACTIVE / STOPPED）

**依赖文件：**
- `agentos/webui/static/js/voice/mic_capture.js` (麦克风采集)
- `agentos/webui/static/js/voice/voice_ws.js` (WebSocket 协议)

### 导航集成

已集成到 `main.js`：
```javascript
case 'voice':
    renderVoiceView(container);
```

---

## Dependencies

新增依赖（已添加到 `pyproject.toml`）：

```toml
[project]
dependencies = [
    "faster-whisper>=1.0.0",  # Local Whisper STT
    "webrtcvad>=2.0.10",       # Voice Activity Detection
    # ...existing deps
]
```

**模型下载：** 首次运行时 faster-whisper 会自动下载模型到 `~/.cache/huggingface/`。

---

## Testing Strategy

### 单元测试 (5 files)

```
tests/unit/communication/voice/
  test_voice_models.py           # VoiceSession/Event/Enums
  test_voice_policy.py           # Policy gate 逻辑
  test_voice_ws_protocol.py      # WS 事件 schema 校验
  test_voice_session.py          # 会话状态机
  test_whisper_local_adapter.py  # STT adapter mock 测试
```

### 集成测试 (3 files)

```
tests/integration/voice/
  test_voice_e2e.py              # 完整流程：create → ws → stt → stop
  test_voice_websocket_flow.py  # WS 协议完整性测试
  test_voice_stt_integration.py # 真实 Whisper 模型测试
```

### 手动验收清单

见 `docs/voice/BROWSER_TEST_CHECKLIST.md`

---

## MVP 已知限制

| 限制 | 说明 | 计划版本 |
|------|------|---------|
| **延迟** | MVP 是分段式（VAD 触发），不是 token-level 流式 | v1（streaming Whisper） |
| **浏览器兼容性** | 依赖 WebAudio API (95%+ 浏览器支持) | - |
| **TTS** | MVP 只返回文本，不包含语音合成 | v1 |
| **多人对话** | MVP 仅支持单用户会话 | v2 |
| **Twilio 通话** | MVP 不支持 PSTN 外呼/Media Streams | v1+ |

---

## Configuration

### Environment Variables

```bash
# Voice 功能开关
VOICE_ENABLED=true

# STT 配置
VOICE_STT_PROVIDER=whisper_local    # whisper_local / google / azure
VOICE_STT_MODEL=small               # base / small / medium / large
VOICE_STT_DEVICE=auto               # cpu / cuda / auto
VOICE_STT_LANGUAGE=auto             # auto / en / zh / ja / ...

# VAD 配置
VOICE_STT_VAD_ENABLED=true
VOICE_STT_VAD_MODE=2                # 0=保守, 1=正常, 2=激进

# 会话配置
VOICE_SESSION_TTL_SECONDS=300       # 会话超时时间（默认 5 分钟）
```

---

## Migration Path (MVP → v1 → v2)

### MVP (当前)
- ✅ 本地 Whisper STT
- ✅ WebSocket 麦克风采集
- ✅ Twilio Provider stub
- ✅ 审计与 Policy gate

### v1 (Next)
- ⏳ TTS 支持 (OpenAI TTS / ElevenLabs)
- ⏳ Streaming Whisper (token-level)
- ⏳ Twilio Media Streams (真正的通话)
- ⏳ Barge-in (用户打断 TTS)

### v2 (Future)
- ⏳ 多人语音会议
- ⏳ 实时翻译
- ⏳ PSTN 外呼/接听

---

## Consequences

### Positive
- ✅ Voice 能力完全 capability 化，可独立启用/禁用
- ✅ 本地 Whisper 确保隐私，无外部 API 依赖
- ✅ Provider 架构允许未来平滑切换到 Twilio/Google/Azure
- ✅ WebSocket 协议清晰，易于扩展（TTS/多模态）

### Negative
- ⚠️ 本地 Whisper 对 CPU/内存有一定要求（small 模型约 1GB RAM）
- ⚠️ MVP 延迟比商业语音助手（Siri/豆包）稍高（1.5s vs 500ms）
- ⚠️ ScriptProcessor 已 deprecated（但 2026 年仍可用）

### Neutral
- ℹ️ Twilio MVP 只是 stub，真正的 Media Streams 集成需要 v1
- ℹ️ TTS 预留了接口但 MVP 不实现（优先确保 STT 稳定）

---

## References

- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [WebRTC VAD](https://webrtc.googlesource.com/src/+/refs/heads/main/common_audio/vad/)
- [Twilio Programmable Voice](https://www.twilio.com/docs/voice)
- ADR-011: Time Timestamp Contract
- ADR-012: Capability Contract

---

## Appendix: Why Not Twilio Media Streams for MVP?

**问题：** 为什么 MVP 不直接用 Twilio Media Streams 承载音频？

**回答：**
1. **复杂度**：Media Streams 需要 WebSocket + TwiML 配置，增加调试难度
2. **依赖性**：MVP 希望"完全本地可运行"，不依赖 Twilio 账号
3. **成本**：Twilio 通话按分钟计费，MVP 测试阶段成本高
4. **灵活性**：本地 WebSocket 允许我们先把 STT/Chat 链路跑通，Provider 只是传输层

**迁移路径：** v1 再做 Twilio Media Streams，届时只需：
1. 修改 TwilioProvider 实现
2. 前端切换到 Twilio.Device SDK
3. 音频源从 `LocalProvider` 切到 `TwilioProvider`
4. 其他代码（STT/Policy/Audit）完全不变

---

**Approved by:** AgentOS Architecture Board
**Implementation Status:** ✅ Completed (2026-02-01)
