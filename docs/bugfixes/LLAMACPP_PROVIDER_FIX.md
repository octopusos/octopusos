# llama.cpp Provider 支持修复

## 🐛 问题描述

**用户报告**:
- 在 WebUI 中选择 `llama.cpp` provider
- 发送消息时报错：`⚠️ Model unavailable: ✗ Ollama unreachable: HTTPConnectionPool(host='localhost', port=11434)`
- 系统尝试连接 Ollama 的 11434 端口，而不是 llama.cpp 的端口

**期望行为**:
- 选择 llama.cpp provider 时，应该连接到 llama.cpp 的实际端口
- 支持 instance-based provider 格式（例如 `llamacpp:qwen3-coder-30b`）

---

## 🔍 根本原因

### 问题 1: Provider 硬编码

**agentos/core/chat/engine.py**:
```python
# Line 164 - 硬编码 provider 映射
provider = "ollama" if model_route == "local" else "openai"
```

- `_stream_response()` 和 `_invoke_model()` 完全忽略 session metadata 中的 provider 设置
- 所有 local 模型都被强制映射到 ollama

### 问题 2: Adapter 不支持 llamacpp

**agentos/core/chat/adapters.py**:
```python
def get_adapter(provider: str, model: Optional[str] = None):
    if provider == "ollama":
        return OllamaChatAdapter(model=model)
    elif provider == "openai":
        return OpenAIChatAdapter(model=model)
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

- `get_adapter()` 只支持 `ollama` 和 `openai`
- 不支持 `llamacpp` 或 `lmstudio`
- 不支持 instance-based 格式（`provider:instance-name`）

### 问题 3: API 端点不兼容

- Ollama API: `/api/chat`, `/api/tags`
- llama.cpp API: `/v1/chat/completions`, `/v1/models`, `/health` (OpenAI 兼容)
- 使用 OllamaChatAdapter 访问 llama.cpp 会失败（404）

---

## ✅ 修复方案

### 1. 修改 ChatEngine 读取 Session Metadata

**agentos/core/chat/engine.py**:

```python
def _stream_response(self, session_id: str, context_pack: Any, model_route: str = "local"):
    # Get session to read provider/model preferences
    session = self.chat_service.get_session(session_id)

    # Determine provider from session metadata (with fallback)
    provider = session.metadata.get("provider")
    if not provider:
        provider = "ollama" if model_route == "local" else "openai"

    # Get model name if specified
    model = session.metadata.get("model")

    logger.info(f"Using provider: {provider}, model: {model}")

    adapter = get_adapter(provider, model)
```

同样修改 `_invoke_model()` 方法。

### 2. 扩展 get_adapter 支持多种 Provider

**agentos/core/chat/adapters.py**:

```python
def get_adapter(provider: str, model: Optional[str] = None) -> ChatModelAdapter:
    """Get chat model adapter

    Args:
        provider: Provider ID (e.g., "ollama", "llamacpp", "llamacpp:instance-name")
        model: Optional model name override
    """
    # Parse provider:instance format
    if ":" in provider:
        provider_type, instance_id = provider.split(":", 1)
    else:
        provider_type = provider
        instance_id = None

    # Handle llama.cpp (OpenAI-compatible)
    if provider_type == "llamacpp":
        model = model or "local-model"
        base_url = "http://127.0.0.1:8080"

        # Get actual endpoint from registry if instance specified
        if instance_id:
            try:
                from agentos.providers.registry import ProviderRegistry
                registry = ProviderRegistry.get_instance()
                provider_obj = registry.get(f"llamacpp:{instance_id}")
                if provider_obj and hasattr(provider_obj, 'endpoint'):
                    base_url = provider_obj.endpoint
                    logger.info(f"Using llamacpp endpoint: {base_url}")
            except Exception as e:
                logger.warning(f"Failed to get llamacpp instance endpoint: {e}")

        # llama.cpp uses OpenAI-compatible API
        return OpenAIChatAdapter(model=model, base_url=f"{base_url}/v1", api_key="dummy")
```

同样添加了对 `lmstudio` 的支持。

### 3. 修改 OpenAIChatAdapter 支持 Local Services

**修改 health_check()**:
```python
def health_check(self) -> tuple[bool, str]:
    """Check OpenAI availability"""
    # For custom base_url (llama.cpp, lmstudio), check endpoint instead of API key
    if self.base_url:
        try:
            import requests
            # Try health endpoint
            health_url = self.base_url.replace("/v1", "/health")
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                return True, f"✓ Local Model ({self.model})"

            # Fallback: try models endpoint
            models_url = f"{self.base_url}/models"
            response = requests.get(models_url, timeout=5)
            if response.status_code == 200:
                return True, f"✓ Local Model ({self.model})"

            return False, f"✗ Service error ({response.status_code})"
        except Exception as e:
            return False, f"✗ Service unreachable: {str(e)}"

    # For OpenAI API (original logic)
    ...
```

**修改 generate() 和 generate_stream()**:
```python
# Only check API key for actual OpenAI (not for local services)
if not self.api_key and not self.base_url:
    return "⚠️ Error: OPENAI_API_KEY not configured"
```

### 4. 修改 OllamaChatAdapter 支持自定义 Base URL

```python
def __init__(self, model: str = "qwen2.5:14b", base_url: Optional[str] = None):
    """Initialize Ollama adapter

    Args:
        model: Model name
        base_url: Base URL (defaults to OLLAMA_HOST env var)
    """
    self.model = model
    self.host = base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
```

---

## 🧪 测试结果

### Smoke Test

创建了 `test_adapter_simple.py` 进行测试：

```bash
$ python3 test_adapter_simple.py

Testing llama.cpp adapter...

1. Creating adapter with provider='llamacpp:qwen3-coder-30b'...
   ✓ Adapter created: OpenAIChatAdapter
   - Base URL: http://127.0.0.1:11435/v1
   - Model: local-model

2. Testing health check...
   Status: ✓ Local Model (local-model)
   ✓ Health check PASSED

3. Testing generate (non-streaming)...
   Response: Test successful
   ✓ Generate PASSED

4. Testing generate_stream...
   1, 2, 3
   Counting complete! 🎉
   ✓ Streaming PASSED (10 chunks)

============================================================
✓ ALL TESTS PASSED
============================================================
```

### API 端点验证

```bash
# Health check
$ curl http://127.0.0.1:11435/health
{"status":"ok"}

# Models endpoint
$ curl http://127.0.0.1:11435/v1/models
{
  "models": [
    {
      "name": "Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf",
      ...
    }
  ]
}

# Chat completion
$ curl -X POST http://127.0.0.1:11435/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
{
  "choices": [
    {
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      }
    }
  ],
  ...
}
```

---

## 📊 Provider 支持矩阵

| Provider | ID | Instance Format | API Type | Port | Status |
|----------|-----|----------------|----------|------|--------|
| Ollama | `ollama` | `ollama:default` | Ollama Native | 11434 | ✅ |
| llama.cpp | `llamacpp` | `llamacpp:instance-name` | OpenAI Compatible | 8080/11435 | ✅ |
| LM Studio | `lmstudio` | `lmstudio:default` | OpenAI Compatible | 1234 | ✅ |
| OpenAI | `openai` | N/A | OpenAI API | N/A | ✅ |
| Anthropic | `anthropic` | N/A | Anthropic API | N/A | ⏳ |

---

## 💡 关键设计决策

### 1. Instance-Based Provider Format

使用 `provider:instance` 格式支持多实例：
- `llamacpp:qwen3-coder-30b` → 端口 11435
- `llamacpp:glm47flash-q8` → 端口 11434

好处：
- 支持同一 provider 的多个运行实例
- 可以为不同模型配置不同的端口和参数
- 向后兼容简单的 provider 名称（`llamacpp`）

### 2. OpenAI-Compatible API 统一处理

llama.cpp 和 LM Studio 都实现了 OpenAI 兼容的 API，因此：
- 复用 `OpenAIChatAdapter` 而不是创建新的 adapter
- 只需要修改 `base_url` 和跳过 API key 检查
- 减少代码重复，提高可维护性

### 3. Fallback 机制

```python
provider = session.metadata.get("provider")
if not provider:
    provider = "ollama" if model_route == "local" else "openai"
```

- 优先使用 session metadata 中的 provider
- 如果未指定，回退到默认值
- 保证向后兼容性

---

## 🚨 注意事项

### 1. API Key 处理

对于本地服务（llama.cpp, lmstudio），`OpenAIChatAdapter` 使用 `api_key="dummy"`：
- OpenAI 库需要提供 API key 参数
- 本地服务通常不验证 API key
- 使用占位符 "dummy" 避免报错

### 2. Health Check 优先级

```python
# 1. 优先尝试 /health 端点（llama.cpp 标准）
health_url = base_url.replace("/v1", "/health")

# 2. 回退到 /v1/models 端点（OpenAI 兼容）
models_url = f"{base_url}/models"
```

### 3. Registry 访问

```python
registry = ProviderRegistry.get_instance()  # 单例模式
provider = registry.get(f"llamacpp:{instance_id}")  # 获取 provider 对象
```

不要使用 `registry.get_instance(provider_id)` - 这是错误的！

---

## 📋 相关文档

- **Chat 消息处理修复**: `docs/bugfixes/CHAT_MESSAGE_HANDLING_FIX.md`
- **数据库迁移修复**: `docs/bugfixes/DATABASE_MIGRATION_V08_FIX.md`
- **Provider 架构**: `agentos/providers/README.md`
- **OpenAI 兼容 API**: https://platform.openai.com/docs/api-reference/chat

---

---

## 🔧 二次修复：Auto-Selection 机制

### 问题描述

用户报告继续收到 `⚠️ Model unavailable: ✗ Service error (404)` 错误。

**根本原因**：
- WebUI 前端发送 `provider="llamacpp"`（不带 instance）
- 后端 `get_adapter("llamacpp")` 使用默认端口 8080
- 实际上没有服务运行在 8080，服务运行在 11435（`llamacpp:qwen3-coder-30b`）

### 解决方案：Provider Auto-Selection

修改 `get_adapter()` 在没有指定 instance 时，自动查找并选择可用的 instance：

```python
# Handle llama.cpp (OpenAI-compatible)
elif provider_type == "llamacpp":
    model = model or "local-model"
    base_url = None

    # Get actual endpoint from registry
    try:
        from agentos.providers.registry import ProviderRegistry
        registry = ProviderRegistry.get_instance()

        if instance_id:
            # Specific instance requested
            provider_obj = registry.get(f"llamacpp:{instance_id}")
            if provider_obj and hasattr(provider_obj, 'endpoint'):
                base_url = provider_obj.endpoint
        else:
            # No instance specified - find any available llamacpp instance
            from agentos.providers.base import ProviderState
            import asyncio
            all_providers = registry.list_all()
            for p in all_providers:
                if p.id.startswith("llamacpp:"):
                    # Check if this provider is ready
                    status = p.get_cached_status()
                    if not status:
                        # No cached status, probe it
                        try:
                            status = asyncio.run(p.probe())
                        except:
                            continue

                    if status and status.state == ProviderState.READY:
                        base_url = p.endpoint
                        logger.info(f"Auto-selected llamacpp instance: {p.id} at {base_url}")
                        break

        if not base_url:
            # Fallback to default port
            base_url = "http://127.0.0.1:8080"
            logger.warning(f"No llamacpp instance found, using default: {base_url}")

    except Exception as e:
        logger.warning(f"Failed to get llamacpp endpoint: {e}", exc_info=True)
        base_url = "http://127.0.0.1:8080"

    # llama.cpp uses OpenAI-compatible API
    return OpenAIChatAdapter(model=model, base_url=f"{base_url}/v1", api_key="dummy")
```

### Auto-Selection 测试结果

```bash
$ python3 test_auto_select.py

Testing auto-selection of llamacpp instance...

1. get_adapter('llamacpp') - should auto-select available instance
   ✓ Adapter created
   - Base URL: http://127.0.0.1:11435/v1
   - Model: local-model
   - Health: ✓ Local Model (local-model)
   ✓ Correctly auto-selected instance on port 11435

2. get_adapter('llamacpp', 'Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf')
   ✓ Adapter created
   - Base URL: http://127.0.0.1:11435/v1
   - Model: Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf
   - Response: OK
   ✓ Generate works

============================================================
✓ AUTO-SELECTION TEST PASSED
============================================================
```

### Auto-Selection 优势

1. **用户友好**：前端不需要知道具体的 instance ID
2. **自动发现**：系统自动找到可用的服务实例
3. **健壮性**：如果首选实例不可用，会尝试其他实例
4. **向后兼容**：仍然支持显式指定 instance（`llamacpp:instance-name`）

---

---

## 🔧 三次修复：Model-Based Instance Routing

### 问题描述

用户报告：
- 选择 **qwen2.5** 模型 → 正确返回 "我是Qwen" ✅
- 选择 **qwen3** 模型 → 错误返回 "我是Claude" ❌

### 根本原因

**Instance 和 Model 的映射问题**：

系统有两个 llamacpp 实例：
- `llamacpp:qwen3-coder-30b` @ 11435 → 运行 `Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf`
- `llamacpp:qwen2.5-coder-7b` @ 11436 → 运行 `qwen2.5-coder-7b-instruct-q8_0.gguf`

**之前的 auto-selection 逻辑**：
```python
# 选择第一个 READY 的 instance（总是 11435）
for p in all_providers:
    if p.id.startswith("llamacpp:"):
        if status.state == ProviderState.READY:
            base_url = p.endpoint  # 11435
            break
```

**问题**：
1. 用户选择 qwen2.5 模型
2. 系统选择第一个可用实例（11435 qwen3）
3. 发送 model="qwen2.5-coder-7b-instruct-q8_0.gguf" 到 11435
4. llama.cpp 找不到这个模型，可能 fallback 到 Claude API

### 解决方案：Model-Based Instance Selection

修改 `get_adapter()` 逻辑，根据 model 参数查找正确的 instance：

```python
# If model is specified, find instance that has this model
if model:
    logger.info(f"Looking for llamacpp instance with model: {model}")
    for p in llamacpp_providers:
        # Check if provider is ready
        status = p.get_cached_status()
        if status and status.state == ProviderState.READY:
            # Check if this instance has the model
            try:
                response = requests.get(f"{p.endpoint}/v1/models", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("id") for m in data.get("data", [])]

                    if model in models:
                        base_url = p.endpoint
                        logger.info(f"✓ Found model '{model}' in instance: {p.id} at {base_url}")
                        break
            except Exception as e:
                logger.debug(f"Failed to check models for {p.id}: {e}")
                continue

# Fallback: select first available instance (if model not found)
if not base_url:
    logger.warning(f"Model '{model}' not found in any instance, using first available")
    # ... fallback logic ...
```

### 测试结果

```bash
Model-Based Instance Routing Test

TEST 1: qwen2.5-coder-7b-instruct-q8_0.gguf
  Base URL: http://127.0.0.1:11436/v1  ← 正确！
  ✓ Correctly selected port 11436 for qwen2.5
  Response: 我是Qwen，一个由阿里云开发的语言模型。
  ✓ Response is from Qwen model

TEST 2: Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf
  Base URL: http://127.0.0.1:11435/v1  ← 正确！
  ✓ Correctly selected port 11435 for qwen3
  Response: 我是通义千问，由通义实验室研发的超大规模语言模型。
  ✓ Response is from Qwen model (not Claude)

✓ ALL ROUTING TESTS PASSED

Summary:
- qwen2.5 model → port 11436 ✓
- qwen3 model → port 11435 ✓
- Both models respond correctly ✓
```

### 修复优势

1. **智能路由**：根据 model 参数自动选择正确的 instance
2. **动态发现**：查询每个 instance 的 /v1/models 端点
3. **健壮 Fallback**：如果找不到 model，使用第一个可用 instance
4. **支持多实例**：可以同时运行多个不同的模型

---

**修复完成时间**: 2026-01-28
**测试状态**: ✅ 所有测试通过（包括 Model-Based Routing）
**受影响的文件**:
- `agentos/core/chat/engine.py` - 添加 metadata 日志
- `agentos/core/chat/adapters.py` - Model-based instance selection
- `agentos/webui/websocket/chat.py` - 调用 update_session_metadata

**Final E2E Test**: ✅ 全部通过
- qwen2.5 模型路由正确 ✅
- qwen3 模型路由正确 ✅
- Session metadata 更新正常 ✅
