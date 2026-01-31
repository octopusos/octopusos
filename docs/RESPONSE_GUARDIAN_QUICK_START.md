# Response Guardian 快速入门

## 🎯 一句话说明

**Response Guardian 防止系统在 Execution Phase 说"我无法访问实时数据",当它实际上有 AutoComm 能力时。**

---

## 🚀 立即验证

### 1. 运行测试 (30 秒)

```bash
pytest tests/unit/core/chat/test_response_guardian.py -v
```

预期输出: `10 passed`

### 2. 运行演示 (1 分钟)

```bash
python3 examples/response_guardian_demo.py
```

你会看到 6 个场景,展示 Guardian 如何拦截能力拒绝响应。

---

## 💡 核心行为

### Planning Phase (不拦截)

```
用户: 悉尼天气?
系统: 我无法访问实时数据,建议使用 /comm search
Guardian: ✅ 允许 (Planning Phase 可以建议)
```

### Execution Phase + AutoComm (拦截)

```
用户: 悉尼天气?
系统: 我无法访问实时数据...
Guardian: ⚠️ 拦截! (系统有能力,不允许拒绝)
        → 替换为: "使用 /comm search 或重试"
```

### Execution Phase + 正确行为 (不拦截)

```
用户: 悉尼天气?
系统: 🌤️ 根据实时查询,悉尼晴,25°C
Guardian: ✅ 允许 (正确使用了能力)
```

---

## 🔧 它在哪里工作

Response Guardian 已集成到:

1. **`ChatEngine._invoke_model()`** - 非流式响应
2. **`ChatEngine._stream_response()`** - 流式响应

每次 LLM 生成响应后,返回给用户前,都会经过 Guardian 检查。

---

## 📊 如何观察它

### 查看日志

```bash
grep "RESPONSE_GUARDIAN_BLOCK" logs/agentos.log
```

你会看到:
```
2026-01-31 23:29:51 - WARNING - Response Guardian BLOCKED capability denial
  event: RESPONSE_GUARDIAN_BLOCK
  matched_pattern: 我无法.*访问.*实时
```

### 查看 Metadata

响应的 metadata 中会包含:

```json
{
  "response_guardian": {
    "execution_phase": "execution",
    "auto_comm_enabled": true,
    "matched_pattern": "我无法.*访问.*实时",
    "guardian_action": "blocked"
  }
}
```

---

## 🎛️ 配置 (可选)

Guardian 默认启用,如需自定义:

```python
from agentos.core.chat.response_guardian import ResponseGuardian

guardian = ResponseGuardian(config={
    'enabled': True,        # 启用/禁用
    'strict_mode': True     # 严格模式
})
```

Session 需要正确的 metadata:

```python
session.metadata = {
    'execution_phase': 'execution',  # 或 'planning'
    'auto_comm_enabled': True        # AutoComm 是否可用
}
```

---

## 🔍 故障排查

### Guardian 没有拦截?

**检查 3 件事**:

```python
# 1. execution_phase = 'execution'?
print(session.metadata['execution_phase'])

# 2. auto_comm_enabled = True?
print(session.metadata['auto_comm_enabled'])

# 3. 响应匹配拦截模式?
from agentos.core.chat.response_guardian import ResponseGuardian
guardian = ResponseGuardian()
denied, pattern = guardian._detect_capability_denial("我无法访问实时数据")
print(f"Denied: {denied}, Pattern: {pattern}")
```

---

## 📚 更多信息

- **完整文档**: [docs/RESPONSE_GUARDIAN.md](./RESPONSE_GUARDIAN.md)
- **实施报告**: [RESPONSE_GUARDIAN_IMPLEMENTATION_REPORT.md](../RESPONSE_GUARDIAN_IMPLEMENTATION_REPORT.md)
- **测试文件**: [tests/unit/core/chat/test_response_guardian.py](../tests/unit/core/chat/test_response_guardian.py)

---

## ✅ 验收清单

- [x] 测试全部通过 (10/10)
- [x] 演示场景验证 (6/6)
- [x] 与 AutoComm 协同工作
- [x] 日志和 metadata 可观测
- [x] 文档完整

---

**状态**: ✅ Ready for Production

**下一步**: 在实际 session 中测试,观察 Guardian 行为
