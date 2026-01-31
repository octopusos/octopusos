# Providers API 404 错误修复

## 🐛 错误信息

```
fetch.js:75  GET http://127.0.0.1:8080/api/providers/llamacpp/models 404 (Not Found)
```

## 🔍 问题分析

### 原因

1. **后端行为**: 当 provider 在 ProviderRegistry 中不存在时，API 返回 404 错误
   ```json
   {
       "detail": "Provider 'llamacpp' not found"
   }
   ```

2. **前端问题**: `loadAvailableModels()` 函数没有检查 HTTP 状态码，直接解析 JSON，期望得到 `{models: []}` 格式，但实际收到 `{detail: "..."}`

### 观察到的行为

| Provider | 状态 | 响应 |
|----------|------|------|
| `ollama` | ✅ 存在 | `{"provider_id": "ollama", "models": []}` |
| `llamacpp` | ❌ 不存在 | `{"detail": "Provider 'llamacpp' not found"}` (404) |

### 为什么 llamacpp 返回 404？

**可能的原因**:

1. **Provider 未初始化**: ProviderRegistry 在启动时可能没有正确注册 llamacpp provider
2. **条件性注册**: llamacpp 可能需要特定的环境变量或配置才会被注册
3. **依赖缺失**: llamacpp provider 可能依赖于某些未安装的包或二进制文件

**验证**:
```bash
# Ollama 可用
$ curl 'http://127.0.0.1:8080/api/providers/ollama/models'
{"provider_id":"ollama","models":[]}

# Llamacpp 不可用
$ curl 'http://127.0.0.1:8080/api/providers/llamacpp/models'
{"detail":"Provider 'llamacpp' not found"}
```

---

## ✅ 修复方案

### 修改的文件
`agentos/webui/static/js/main.js` (line 810-831)

### 修改内容

**修复前**:
```javascript
try {
    const response = await fetch(`/api/providers/${provider}/models`);
    const data = await response.json();

    if (data.models && data.models.length > 0) {
        // ... render models
    } else {
        modelSelect.innerHTML = '<option value="">No models available</option>';
    }
} catch (err) {
    console.error('Failed to load models:', err);
    modelSelect.innerHTML = '<option value="">Error loading models</option>';
}
```

**问题**:
- ❌ 没有检查 `response.ok`
- ❌ 404 响应也被解析为 JSON，但格式不符合预期
- ❌ 用户看到控制台错误，但不清楚问题

**修复后**:
```javascript
try {
    const response = await fetch(`/api/providers/${provider}/models`);

    // ✅ 检查 HTTP 状态码
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        console.warn(`Provider ${provider} not available:`, error.detail);
        modelSelect.innerHTML = '<option value="">Provider not available</option>';
        return;
    }

    const data = await response.json();

    if (data.models && data.models.length > 0) {
        // ... render models
    } else {
        modelSelect.innerHTML = '<option value="">No models available</option>';
    }
} catch (err) {
    console.error('Failed to load models:', err);
    modelSelect.innerHTML = '<option value="">Error loading models</option>';
}
```

**改进**:
- ✅ 检查 `response.ok` (status 200-299)
- ✅ 404 时显示 "Provider not available" 而不是错误
- ✅ 使用 `console.warn` 而不是 `console.error`（因为这不是致命错误）
- ✅ 优雅地处理 JSON 解析失败

---

## 🎯 用户体验改进

### 修复前
- ❌ 控制台显示红色错误
- ❌ 下拉菜单显示 "Error loading models"
- ❌ 不清楚是 provider 不可用还是网络错误

### 修复后
- ✅ 控制台显示警告（黄色）而不是错误（红色）
- ✅ 下拉菜单显示 "Provider not available"（更准确）
- ✅ 清楚地知道 provider 不存在或未配置

---

## 🧪 验证步骤

### 1. 刷新浏览器

```bash
# 强制刷新以加载新的 main.js
Cmd+Shift+R  # Mac
Ctrl+Shift+R # Windows/Linux
```

### 2. 测试 Provider 选择

1. 访问需要选择 model 的页面（如 Chat 设置）
2. 在 Provider 下拉菜单中选择 `ollama`
   - ✅ 应该显示可用的 models（或 "No models available"）
3. 在 Provider 下拉菜单中选择 `llamacpp`
   - ✅ 应该显示 "Provider not available"
   - ✅ 控制台显示警告而不是错误

### 3. 检查控制台

**修复前**:
```
❌ GET http://127.0.0.1:8080/api/providers/llamacpp/models 404 (Not Found)
❌ Failed to load models: ...
```

**修复后**:
```
⚠️ Provider llamacpp not available: Provider 'llamacpp' not found
```

---

## 📋 后续建议

### 短期（可选）

1. **前端：隐藏不可用的 providers**
   - 在填充 provider 下拉菜单之前，先检查每个 provider 是否可用
   - 或者从 `/api/providers/status` 获取可用的 providers

2. **后端：返回 200 而不是 404**
   - 当 provider 不存在时，返回 `200 OK` 和空的 models 列表
   - 这样前端不需要特殊处理 404 情况
   ```python
   if not provider:
       return ModelsListResponse(provider_id=provider_id, models=[])
   ```

### 中期（推荐）

3. **添加 Provider 健康检查**
   - 在 `/api/providers` 响应中添加 `is_available` 字段
   - 前端只显示可用的 providers

4. **改进错误信息**
   - 提供更详细的错误信息（如："llamacpp binary not found"）
   - 提供修复建议（如："Install llama.cpp to use this provider"）

### 长期（可选）

5. **Provider 自动发现**
   - 自动检测系统中可用的 providers
   - 提供一键安装缺失的 providers

---

## 🔍 相关代码

### Frontend: loadAvailableModels()
**文件**: `agentos/webui/static/js/main.js:801-832`

### Backend: get_provider_models()
**文件**: `agentos/webui/api/providers.py:233-264`

```python
@router.get("/{provider_id}/models")
async def get_provider_models(provider_id: str) -> ModelsListResponse:
    registry = ProviderRegistry.get_instance()
    provider = registry.get(provider_id)

    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")

    # ...
```

---

## ✅ 修复验证清单

- [x] 添加 HTTP 状态码检查
- [x] 优雅地处理 404 响应
- [x] 改进错误信息显示
- [x] 使用 `console.warn` 而不是 `console.error`
- [ ] 刷新浏览器验证
- [ ] 测试 ollama provider（应该正常工作）
- [ ] 测试 llamacpp provider（应该显示 "Provider not available"）

---

**修复完成时间**: 2026-01-28
**修复状态**: ✅ 完成，等待浏览器刷新验证
