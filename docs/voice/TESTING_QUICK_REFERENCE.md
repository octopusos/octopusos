# Voice 测试快速参考

快速参考指南，用于查找和运行 Voice 模块测试。

## 📁 测试文件位置

```
AgentOS/
├── tests/integration/voice/
│   ├── test_voice_e2e.py              # E2E 集成测试 (7 tests)
│   ├── test_voice_websocket_flow.py  # WebSocket 流程测试 (6 tests)
│   └── test_voice_stt_integration.py # STT 集成测试 (6 tests)
│
├── scripts/
│   ├── voice_acceptance_test.py      # 手动验收脚本
│   └── run_voice_tests.sh            # 测试运行脚本
│
└── docs/voice/
    ├── BROWSER_TEST_CHECKLIST.md     # 浏览器测试清单
    ├── VOICE_TESTING_GUIDE.md        # 详细测试指南
    ├── VOICE_TESTING_ACCEPTANCE_CRITERIA.md  # 验收标准
    └── TESTING_QUICK_REFERENCE.md    # 本文档
```

## 🚀 快速开始

### 1️⃣ 启动服务器

```bash
uvicorn agentos.webui.app:app --host 127.0.0.1 --port 8000
```

### 2️⃣ 运行所有测试

```bash
# 使用测试运行脚本（推荐）
./scripts/run_voice_tests.sh

# 或手动运行
pytest tests/integration/voice/ -v -m integration
```

### 3️⃣ 运行验收测试

```bash
python scripts/voice_acceptance_test.py
```

### 4️⃣ 浏览器测试

打开 http://localhost:8000，参考 `docs/voice/BROWSER_TEST_CHECKLIST.md`

## 📊 测试统计

| 测试类型 | 测试数量 | 预期时长 | 通过标准 |
|---------|---------|---------|---------|
| E2E 集成测试 | 7 | ~60s | ≥ 6/7 |
| WebSocket 测试 | 6 | ~60s | ≥ 5/6 |
| STT 集成测试 | 6 | ~90s | ≥ 4/6 |
| 验收测试脚本 | 5 steps | ~15s | 5/5 |
| 浏览器测试 | 30+ checks | ~20min | 核心 7/7 + UX ≥4/5 |
| **总计** | **19 + 5 + 30** | **~25min** | **见验收标准** |

## 🧪 常用测试命令

### 运行特定测试文件

```bash
# E2E 测试
pytest tests/integration/voice/test_voice_e2e.py -v -m integration

# WebSocket 测试
pytest tests/integration/voice/test_voice_websocket_flow.py -v -m integration

# STT 测试
pytest tests/integration/voice/test_voice_stt_integration.py -v -m integration
```

### 运行特定测试用例

```bash
# 完整会话流程
pytest tests/integration/voice/test_voice_e2e.py::test_complete_voice_session_flow -v

# WebSocket 连接生命周期
pytest tests/integration/voice/test_voice_websocket_flow.py::test_websocket_connection_lifecycle -v

# 音频格式管道
pytest tests/integration/voice/test_voice_stt_integration.py::test_audio_format_pipeline -v
```

### 查看详细日志

```bash
pytest tests/integration/voice/ -v -m integration -s --log-cli-level=INFO
```

### 生成覆盖率报告

```bash
pytest tests/integration/voice/ -v -m integration \
  --cov=agentos.webui.api.voice \
  --cov-report=html \
  --cov-report=term
```

### 使用测试运行脚本

```bash
# 运行所有测试
./scripts/run_voice_tests.sh

# 跳过启动服务器（假设服务器已运行）
./scripts/run_voice_tests.sh --skip-server

# 显示详细输出
./scripts/run_voice_tests.sh --verbose

# 生成覆盖率报告
./scripts/run_voice_tests.sh --coverage
```

## 📋 测试清单

### ✅ Level 1: 自动化集成测试

**E2E 测试** (test_voice_e2e.py):
- [ ] `test_complete_voice_session_flow` - 完整会话流程
- [ ] `test_multiple_concurrent_sessions` - 并发会话
- [ ] `test_session_timeout_handling` - 超时处理
- [ ] `test_error_recovery` - 错误恢复
- [ ] `test_session_list_filtering` - 会话列表过滤
- [ ] `test_websocket_close_on_session_stop` - WebSocket 关闭
- [ ] `test_empty_audio_handling` - 空音频处理

**WebSocket 测试** (test_voice_websocket_flow.py):
- [ ] `test_websocket_connection_lifecycle` - 连接生命周期
- [ ] `test_websocket_audio_streaming` - 音频流式传输
- [ ] `test_websocket_reconnection` - 重连机制
- [ ] `test_websocket_error_handling` - 错误处理
- [ ] `test_websocket_multiple_audio_end_events` - 多次结束事件
- [ ] `test_websocket_large_audio_payload` - 大音频负载

**STT 测试** (test_voice_stt_integration.py):
- [ ] `test_whisper_local_real_transcription` - Whisper 转写 (允许跳过)
- [ ] `test_vad_silence_detection` - VAD 检测
- [ ] `test_audio_format_pipeline` - 格式管道
- [ ] `test_different_sample_rates` - 不同采样率
- [ ] `test_stereo_to_mono_conversion` - 立体声转换
- [ ] `test_audio_duration_calculation` - 时长计算

### ✅ Level 2: 手动验收测试脚本

- [ ] Test 1/5: 创建 Voice Session
- [ ] Test 2/5: 连接 WebSocket
- [ ] Test 3/5: 发送测试音频
- [ ] Test 4/5: 接收 STT 结果
- [ ] Test 5/5: 停止 Session

### ✅ Level 3: 浏览器端手动测试

**核心功能** (必须全部通过):
- [ ] 创建 Session
- [ ] 连接 WebSocket
- [ ] 录音并发送音频
- [ ] 接收 STT 转写
- [ ] 接收 Assistant 回复
- [ ] 停止 Session
- [ ] 多次会话

**用户体验** (≥ 4/5):
- [ ] UI 美观
- [ ] 状态指示清晰
- [ ] 错误提示友好
- [ ] 性能流畅
- [ ] 实时反馈

**稳定性** (≥ 2/3):
- [ ] 无内存泄漏
- [ ] 错误可恢复
- [ ] 支持多浏览器

## 🐛 常见问题快速排查

### 问题 1: 服务器连接失败
```bash
# 检查服务器是否运行
curl http://localhost:8000/api/health

# 检查端口占用
lsof -i :8000
```

### 问题 2: WebSocket 连接失败
```bash
# 检查 Session ID 是否有效
curl http://localhost:8000/api/voice/sessions/{session_id}
```

### 问题 3: 测试超时
```bash
# 增加超时时间
pytest --timeout=120 tests/integration/voice/
```

### 问题 4: 麦克风权限被拒绝（浏览器）
- Chrome: 地址栏 🔒 → 站点设置 → 麦克风 → 允许
- Firefox: 地址栏 🔒 → 权限 → 使用麦克风 → 允许

## 📈 验收标准快速查看

| 层次 | 标准 | 状态 |
|-----|------|------|
| Level 1 自动化测试 | ≥ 15/19 (79%) | ⬜ |
| Level 2 验收脚本 | 5/5 (100%) | ⬜ |
| Level 3 浏览器测试 | 核心 7/7 + UX ≥4/5 + 稳定性 ≥2/3 | ⬜ |

**综合验收**: 所有层次必须通过 ✅

## 📚 详细文档链接

| 文档 | 内容 | 路径 |
|-----|------|------|
| 集成测试 README | 测试文件说明、运行方法 | `tests/integration/voice/README.md` |
| 浏览器测试清单 | 手动测试检查清单 | `docs/voice/BROWSER_TEST_CHECKLIST.md` |
| 测试指南 | 完整测试指南 | `docs/voice/VOICE_TESTING_GUIDE.md` |
| 验收标准 | 详细验收标准 | `docs/voice/VOICE_TESTING_ACCEPTANCE_CRITERIA.md` |
| Voice API 文档 | API 实现代码 | `agentos/webui/api/voice.py` |

## 🔧 依赖安装

```bash
# 安装 AgentOS
pip install -e .

# 安装测试依赖
pip install pytest pytest-asyncio pytest-timeout httpx websockets numpy

# 安装覆盖率工具（可选）
pip install pytest-cov

# 安装 Whisper（可选，用于真实 STT）
pip install faster-whisper
```

## 🎯 CI/CD

### GitHub Actions

- 配置文件: `.github/workflows/voice-tests.yml`
- 触发条件: Push 到 main/master/develop 或 PR
- 测试矩阵: Python 3.11, 3.12, 3.13

### 查看 CI 状态

```bash
# GitHub CLI
gh run list --workflow=voice-tests.yml

# 查看最新运行
gh run view --web
```

## 📞 获取帮助

1. **查看文档**:
   - `docs/voice/VOICE_TESTING_GUIDE.md` - 详细指南
   - `tests/integration/voice/README.md` - 测试 README

2. **运行示例**:
   - `examples/voice_websocket_demo.py` - WebSocket 客户端示例

3. **查看代码**:
   - `agentos/webui/api/voice.py` - Voice API 实现

4. **提交 Issue**:
   - GitHub Issues: 报告 bug 或提出改进建议

---

**最后更新**: 2026-02-01
**维护者**: AgentOS Voice Team
