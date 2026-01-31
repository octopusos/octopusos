# Voice 模块测试指南

本文档提供 Voice 模块的完整测试指南，包括集成测试、验收测试和浏览器测试。

## 目录

- [测试架构](#测试架构)
- [快速开始](#快速开始)
- [集成测试](#集成测试)
- [验收测试](#验收测试)
- [浏览器测试](#浏览器测试)
- [CI/CD 集成](#cicd-集成)
- [故障排查](#故障排查)

## 测试架构

Voice 模块的测试分为三个层次:

```
┌─────────────────────────────────────────┐
│         浏览器端手动测试                  │
│  (UI, 麦克风, 实际录音)                   │
└─────────────────────────────────────────┘
                  ↑
┌─────────────────────────────────────────┐
│         手动验收测试脚本                  │
│  (Python 脚本模拟客户端)                 │
└─────────────────────────────────────────┘
                  ↑
┌─────────────────────────────────────────┐
│         自动化集成测试                    │
│  (pytest, E2E, WebSocket, STT)          │
└─────────────────────────────────────────┘
```

### 测试文件结构

```
AgentOS/
├── tests/integration/voice/
│   ├── __init__.py
│   ├── test_voice_e2e.py              # 端到端集成测试
│   ├── test_voice_websocket_flow.py  # WebSocket 流程测试
│   ├── test_voice_stt_integration.py # STT 集成测试
│   └── README.md                       # 测试文档
│
├── scripts/
│   ├── voice_acceptance_test.py      # 手动验收脚本
│   └── run_voice_tests.sh            # 测试运行脚本
│
├── docs/voice/
│   ├── BROWSER_TEST_CHECKLIST.md     # 浏览器测试清单
│   └── VOICE_TESTING_GUIDE.md        # 本文档
│
└── .github/workflows/
    └── voice-tests.yml                # CI 配置
```

## 快速开始

### 1. 安装依赖

```bash
# 安装 AgentOS 及依赖
pip install -e .

# 安装测试依赖
pip install pytest pytest-asyncio pytest-timeout httpx websockets numpy
```

### 2. 启动服务

```bash
# 启动 AgentOS WebUI
uvicorn agentos.webui.app:app --host 127.0.0.1 --port 8000
```

### 3. 运行测试

```bash
# 运行所有 Voice 集成测试
pytest tests/integration/voice/ -v -m integration

# 或使用测试运行脚本
./scripts/run_voice_tests.sh
```

### 4. 手动验收测试

```bash
# 运行验收测试脚本
python scripts/voice_acceptance_test.py
```

### 5. 浏览器测试

打开 http://localhost:8000，参考 [docs/voice/BROWSER_TEST_CHECKLIST.md](BROWSER_TEST_CHECKLIST.md) 进行手动测试。

## 集成测试

### 测试覆盖范围

#### 1. test_voice_e2e.py - 端到端测试

| 测试用例 | 测试内容 | 预期时长 |
|---------|---------|---------|
| `test_complete_voice_session_flow` | 完整会话流程 | ~10s |
| `test_multiple_concurrent_sessions` | 并发会话 | ~15s |
| `test_session_timeout_handling` | 超时处理 | ~5s |
| `test_error_recovery` | 错误恢复 | ~10s |
| `test_session_list_filtering` | 会话列表过滤 | ~5s |
| `test_websocket_close_on_session_stop` | WebSocket 关闭 | ~5s |
| `test_empty_audio_handling` | 空音频处理 | ~5s |

#### 2. test_voice_websocket_flow.py - WebSocket 测试

| 测试用例 | 测试内容 | 预期时长 |
|---------|---------|---------|
| `test_websocket_connection_lifecycle` | 连接生命周期 | ~5s |
| `test_websocket_audio_streaming` | 音频流式传输 | ~10s |
| `test_websocket_reconnection` | 重连机制 | ~10s |
| `test_websocket_error_handling` | 错误处理 | ~10s |
| `test_websocket_multiple_audio_end_events` | 多次结束事件 | ~10s |
| `test_websocket_large_audio_payload` | 大音频负载 | ~20s |

#### 3. test_voice_stt_integration.py - STT 测试

| 测试用例 | 测试内容 | 预期时长 |
|---------|---------|---------|
| `test_whisper_local_real_transcription` | Whisper 转写 | ~30s |
| `test_vad_silence_detection` | VAD 检测 | ~10s |
| `test_audio_format_pipeline` | 格式转换 | ~5s |
| `test_different_sample_rates` | 不同采样率 | ~20s |
| `test_stereo_to_mono_conversion` | 立体声转换 | ~5s |
| `test_audio_duration_calculation` | 时长计算 | ~10s |

### 运行集成测试

#### 运行所有测试

```bash
pytest tests/integration/voice/ -v -m integration
```

#### 运行特定测试文件

```bash
# E2E 测试
pytest tests/integration/voice/test_voice_e2e.py -v -m integration

# WebSocket 测试
pytest tests/integration/voice/test_voice_websocket_flow.py -v -m integration

# STT 测试
pytest tests/integration/voice/test_voice_stt_integration.py -v -m integration
```

#### 运行特定测试用例

```bash
pytest tests/integration/voice/test_voice_e2e.py::test_complete_voice_session_flow -v
```

#### 查看详细日志

```bash
pytest tests/integration/voice/ -v -m integration -s --log-cli-level=INFO
```

#### 生成覆盖率报告

```bash
pytest tests/integration/voice/ -v -m integration \
  --cov=agentos.webui.api.voice \
  --cov-report=html
```

## 验收测试

### 运行验收测试脚本

验收测试脚本是一个自动化 Python 脚本，模拟客户端完整流程:

```bash
python scripts/voice_acceptance_test.py
```

### 验收测试流程

脚本会依次执行以下测试:

1. ✅ **Test 1/5**: 创建 Voice Session
   - POST `/api/voice/sessions`
   - 验证返回的 session_id、ws_url

2. ✅ **Test 2/5**: 连接 WebSocket
   - 连接 `ws://localhost:8000/api/voice/sessions/{session_id}/events`
   - 接收 `voice.session.ready` 事件

3. ✅ **Test 3/5**: 发送测试音频
   - 生成 2 秒测试音频（440 Hz 正弦波）
   - 分块发送（模拟流式传输）
   - 发送 `voice.audio.chunk` 事件

4. ✅ **Test 4/5**: 接收 STT 结果
   - 发送 `voice.audio.end` 事件
   - 接收 `voice.stt.final` 事件
   - 接收 `voice.assistant.text` 事件

5. ✅ **Test 5/5**: 停止 Session
   - POST `/api/voice/sessions/{session_id}/stop`
   - 验证 session state 变为 `STOPPED`

### 验收测试输出示例

```
============================================================
Voice MVP 验收测试
============================================================
ℹ️  Base URL: http://localhost:8000
ℹ️  WebSocket URL: ws://localhost:8000

[Test 1/5] 创建 Voice Session
✅ Session 创建成功: voice-a1b2c3d4e5f6
ℹ️  Project ID: voice-acceptance-test
ℹ️  Provider: local
ℹ️  STT Provider: mock
ℹ️  WebSocket URL: /api/voice/sessions/voice-a1b2c3d4e5f6/events

[Test 2/5] 连接 WebSocket
✅ WebSocket 连接成功
✅ 收到 voice.session.ready 事件
ℹ️  Session ID: voice-a1b2c3d4e5f6
ℹ️  Timestamp: 2026-02-01T12:34:56.789012Z

[Test 3/5] 发送测试音频
ℹ️  生成测试音频: 64000 bytes (2.0s @ 16kHz)
ℹ️  发送 8 个音频块...
  ✓ 发送音频块 #0 (8000 bytes)
  ✓ 发送音频块 #1 (8000 bytes)
  ...
✅ 音频发送完成

[Test 4/5] 等待 STT 结果
ℹ️  已发送 audio.end 信号
ℹ️  等待 STT 转写结果...
✅ 收到 STT 转写结果
ℹ️  Transcription: [Mock transcription of 2.0s audio]
ℹ️  Timestamp: 2026-02-01T12:35:00.123456Z
ℹ️  等待 Assistant 响应...
✅ 收到 Assistant 响应
ℹ️  Response: [MVP Echo] You said: [Mock transcription of 2.0s audio]

[Test 5/5] 停止 Session
✅ Session 停止成功
ℹ️  State: STOPPED
ℹ️  Stopped at: 2026-02-01T12:35:05.789012Z

============================================================
✅ 所有验收测试通过！Voice MVP 可以投入使用。
============================================================

验收测试总结:
  ✅ Session 创建
  ✅ WebSocket 连接
  ✅ 音频流式传输
  ✅ STT 转写
  ✅ Assistant 响应
  ✅ Session 停止

下一步:
  1. 打开浏览器测试: http://localhost:8000
  2. 导航到 Voice 面板
  3. 完成浏览器端手动测试 (参考 docs/voice/BROWSER_TEST_CHECKLIST.md)
```

## 浏览器测试

浏览器测试用于验证前端 UI 和真实麦克风输入。

### 测试前准备

1. 启动 AgentOS WebUI:
   ```bash
   uvicorn agentos.webui.app:app
   ```

2. 打开浏览器: http://localhost:8000

3. 准备测试环境:
   - 确保麦克风可用
   - 确保浏览器支持 WebRTC
   - 准备测试语句（英文或中文）

### 测试步骤

详细测试步骤参见: [docs/voice/BROWSER_TEST_CHECKLIST.md](BROWSER_TEST_CHECKLIST.md)

**核心检查项**:

- [ ] UI 渲染正常
- [ ] 麦克风权限请求
- [ ] 录音状态指示
- [ ] 实时 Transcript 显示
- [ ] Assistant 回复显示
- [ ] 错误处理友好
- [ ] 性能流畅

### 浏览器兼容性

| 浏览器 | 最低版本 | 测试状态 |
|--------|---------|---------|
| Chrome | 90+ | ✅ 推荐 |
| Edge   | 90+ | ✅ 支持 |
| Firefox| 88+ | ✅ 支持 |
| Safari | 14+ | ⚠️ 部分支持 |

## CI/CD 集成

### GitHub Actions 配置

Voice 测试已集成到 GitHub Actions: `.github/workflows/voice-tests.yml`

### 触发条件

- **Push**: 推送到 master/main/develop 分支
- **Pull Request**: 创建或更新 PR
- **路径过滤**: 只在修改 Voice 相关文件时触发

### CI 测试流程

1. **环境准备**
   - Python 3.11, 3.12, 3.13
   - 安装依赖

2. **单元测试** (如果存在)
   - `pytest tests/unit/communication/voice/`

3. **启动测试服务器**
   - `uvicorn agentos.webui.app:app --host 127.0.0.1 --port 8000`

4. **集成测试**
   - E2E 测试
   - WebSocket 流程测试
   - STT 集成测试

5. **验收测试**
   - `python scripts/voice_acceptance_test.py`

6. **清理**
   - 停止测试服务器
   - 上传测试日志（如果失败）

### 查看 CI 结果

- GitHub Actions 页面: `https://github.com/{owner}/{repo}/actions`
- PR 页面会显示测试状态
- 失败时会自动评论 PR

## 故障排查

### 问题 1: 服务器连接失败

**症状**:
```
❌ 无法连接到服务器
httpx.ConnectError: [Errno 111] Connection refused
```

**解决方法**:
1. 确认服务器正在运行:
   ```bash
   curl http://localhost:8000/api/health
   ```

2. 检查端口占用:
   ```bash
   lsof -i :8000
   ```

3. 查看服务器日志:
   ```bash
   # 如果使用 uvicorn --reload
   # 日志会输出到终端
   ```

### 问题 2: WebSocket 连接失败

**症状**:
```
websockets.exceptions.InvalidStatusCode: server rejected WebSocket connection: HTTP 404
```

**解决方法**:
1. 确认 Session ID 有效
2. 检查 WebSocket URL 格式:
   ```
   ws://localhost:8000/api/voice/sessions/{session_id}/events
   ```
3. 查看服务器日志中的 WebSocket 错误

### 问题 3: 测试超时

**症状**:
```
asyncio.TimeoutError
```

**解决方法**:
1. 增加超时时间:
   ```bash
   pytest --timeout=120
   ```

2. 检查网络延迟:
   ```bash
   ping localhost
   ```

3. 检查服务器性能:
   ```bash
   top  # 查看 CPU/内存占用
   ```

### 问题 4: STT 转写失败

**症状**:
```
AssertionError: STT result not received
```

**解决方法**:
1. 确认 STT provider 配置（MVP 使用 mock）
2. 检查音频格式:
   - Codec: pcm_s16le
   - Sample rate: 16000 Hz
   - Channels: 1 (mono)
3. 查看服务器日志中的 STT 处理日志

### 问题 5: 浏览器麦克风权限被拒绝

**症状**:
- 浏览器提示麦克风权限被拒绝
- 无法录音

**解决方法**:
1. Chrome: 地址栏左侧 🔒 → 站点设置 → 麦克风 → 允许
2. Firefox: 地址栏左侧 🔒 → 权限 → 使用麦克风 → 允许
3. Safari: 设置 → 网站 → 麦克风 → 允许

### 问题 6: 性能问题（卡顿）

**症状**:
- UI 卡顿
- 高 CPU 占用
- 内存持续增长

**解决方法**:
1. 检查音频采样率（推荐 16kHz）
2. 减小 WebSocket 消息大小（每块 < 50KB）
3. 清空浏览器缓存
4. 禁用浏览器扩展
5. 检查内存泄漏（浏览器任务管理器）

## 测试最佳实践

### 1. 测试隔离

- 每个测试用例独立运行
- 清理测试数据（Session）
- 避免测试之间相互依赖

### 2. 错误处理

- 使用 `try...finally` 确保资源清理
- 捕获异常并提供清晰的错误信息
- 设置合理的超时时间

### 3. 测试数据

- 使用确定性的测试数据（正弦波）
- 避免依赖外部资源
- Mock 不可用的服务（如 Whisper）

### 4. 性能监控

- 记录测试执行时间
- 监控资源占用
- 设置性能基准

### 5. 文档维护

- 更新测试文档
- 记录已知问题
- 提供故障排查指南

## 测试覆盖率目标

| 模块 | 目标覆盖率 | 当前覆盖率 |
|-----|----------|----------|
| voice.py (REST API) | 90% | TBD |
| voice.py (WebSocket) | 85% | TBD |
| STT Service | 80% | TBD |

生成覆盖率报告:
```bash
pytest tests/integration/voice/ -v -m integration \
  --cov=agentos.webui.api.voice \
  --cov-report=html \
  --cov-report=term

# 查看报告
open htmlcov/index.html
```

## 未来改进

### 短期（MVP 后）

- [ ] 添加 Whisper 本地集成测试
- [ ] 添加 VAD 测试
- [ ] 添加音频质量检测
- [ ] 完善错误场景测试

### 中期

- [ ] 添加 Selenium/Playwright 浏览器自动化测试
- [ ] 添加性能基准测试
- [ ] 添加负载测试（多用户并发）
- [ ] 集成 TTS 测试

### 长期

- [ ] 多语言支持测试
- [ ] 跨平台兼容性测试
- [ ] 实时质量监控
- [ ] A/B 测试框架

## 参考资料

- **Voice API 文档**: `agentos/webui/api/voice.py`
- **集成测试 README**: `tests/integration/voice/README.md`
- **浏览器测试清单**: `docs/voice/BROWSER_TEST_CHECKLIST.md`
- **示例代码**: `examples/voice_websocket_demo.py`
- **CI 配置**: `.github/workflows/voice-tests.yml`

## 联系方式

如有问题或建议，请:

1. 查看本文档和相关文档
2. 提交 GitHub Issue
3. 联系 AgentOS Voice Team

---

**最后更新**: 2026-02-01
**维护者**: AgentOS Voice Team
**版本**: Voice MVP v1.0
