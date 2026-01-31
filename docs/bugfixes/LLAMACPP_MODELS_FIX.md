# LlamaCpp Models API 修复

## 🐛 问题描述

**用户报告的矛盾现象**:
- ✅ Providers 页面显示 llama.cpp 有 3 个实例（glm47flash-q8, qwen3-coder-30b, qwen2.5-coder-7b）
- ❌ Chat 页面选择 llama.cpp provider 时显示 "Provider not available"
- ❌ API 调用 `/api/providers/llamacpp/models` 返回 404

---

## 🔍 根本原因

### 架构不匹配

#### 1. **静态 Provider 列表 vs 动态 Provider 注册**

**`GET /api/providers`** (line 140-188):
- 返回**硬编码的静态列表**
- 包含 `{id: "llamacpp", label: "llama.cpp"}`
- 不依赖 ProviderRegistry

```python
return ProvidersListResponse(
    local=[
        ProviderInfo(id="llamacpp", label="llama.cpp", ...),
        # ... other providers
    ]
)
```

#### 2. **ProviderRegistry 中的实际注册**

ProviderRegistry 中实际注册的是**实例级别的 providers**:
- `llamacpp:glm47flash-q8`
- `llamacpp:qwen3-coder-30b`
- `llamacpp:qwen2.5-coder-7b`

**没有**注册顶层的 `llamacpp` provider。

#### 3. **Models API 的查询逻辑**

**`GET /api/providers/{provider_id}/models`** (line 233-264):
- 从 ProviderRegistry 获取 provider
- 调用 `registry.get("llamacpp")`
- 返回 `None`（因为只有 `llamacpp:*` 实例）
- 抛出 404 错误

```python
provider = registry.get(provider_id)  # 查找 "llamacpp"
if not provider:
    raise HTTPException(status_code=404)  # ❌ 找不到
```

---

## ✅ 修复方案

### 实现 Provider 类型聚合查询

当查询 `llamacpp` 时，自动聚合所有 `llamacpp:*` 实例的 models。

### 修改的文件

**agentos/webui/api/providers.py** (line 233-305)

### 修复逻辑

```python
@router.get("/{provider_id}/models")
async def get_provider_models(provider_id: str) -> ModelsListResponse:
    registry = ProviderRegistry.get_instance()

    # Step 1: 尝试获取精确匹配的 provider
    provider = registry.get(provider_id)

    if provider:
        # 单个 provider，直接返回其 models
        models = await provider.list_models()
        return ModelsListResponse(provider_id=provider_id, models=[...])
    else:
        # Step 2: 没有精确匹配，尝试查找所有前缀匹配的实例
        # 例如: "llamacpp" -> ["llamacpp:qwen3-coder-30b", "llamacpp:qwen2.5-coder-7b"]
        all_providers = registry.list_all()
        prefix = f"{provider_id}:"
        matching_providers = [p for p in all_providers if p.id.startswith(prefix)]

        if not matching_providers:
            raise HTTPException(status_code=404)

        # Step 3: 聚合所有匹配实例的 models
        all_models = []
        seen_model_ids = set()

        for provider in matching_providers:
            try:
                models = await provider.list_models()
                for model in models:
                    # 去重
                    if model.id not in seen_model_ids:
                        all_models.append(ModelInfoResponse(...))
                        seen_model_ids.add(model.id)
            except Exception as e:
                # 容错：单个实例失败不影响其他实例
                print(f"Warning: Failed to list models from {provider.id}: {e}")
                continue

        return ModelsListResponse(provider_id=provider_id, models=all_models)
```

### 关键特性

1. **向后兼容**:
   - 仍然支持查询具体实例（如 `llamacpp:qwen3-coder-30b`）
   - 新增支持查询 provider 类型（如 `llamacpp`）

2. **自动聚合**:
   - 查询 `llamacpp` 时，自动找到所有 `llamacpp:*` 实例
   - 聚合所有实例的 models
   - 自动去重（基于 model.id）

3. **容错处理**:
   - 单个实例失败不影响其他实例
   - 使用 `try-except` 捕获异常
   - 记录警告但继续处理

---

## 🧪 验证结果

### Before (修复前)

```bash
$ curl 'http://127.0.0.1:8080/api/providers/llamacpp/models'
{"detail":"Provider 'llamacpp' not found"}
```

### After (修复后)

```bash
$ curl 'http://127.0.0.1:8080/api/providers/llamacpp/models'
{
    "provider_id": "llamacpp",
    "models": [
        {
            "id": "Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf",
            "label": "Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf",
            "context_window": null
        },
        {
            "id": "qwen2.5-coder-7b-instruct-q8_0.gguf",
            "label": "qwen2.5-coder-7b-instruct-q8_0.gguf",
            "context_window": null
        }
    ]
}
```

✅ 成功返回 2 个 models（来自 2 个可用的 llamacpp 实例）

---

## 🔧 其他修复

### 修复 ProviderRegistry 方法调用

**错误**: 使用了不存在的 `registry.list()` 方法

**修复**: 改为正确的 `registry.list_all()` 方法

```python
# 修复前
all_providers = registry.list()  # ❌ 方法不存在

# 修复后
all_providers = registry.list_all()  # ✅ 正确方法
```

---

## 📊 工作原理

### Provider 实例结构

```
ProviderRegistry
├── ollama (单实例)
├── lmstudio (单实例)
├── llamacpp:glm47flash-q8 (实例 1)
├── llamacpp:qwen3-coder-30b (实例 2)
└── llamacpp:qwen2.5-coder-7b (实例 3)
```

### API 查询行为

| 查询 | 行为 | 结果 |
|------|------|------|
| `ollama` | 精确匹配 | 返回 ollama 的 models |
| `llamacpp` | 前缀匹配 | 聚合所有 `llamacpp:*` 的 models |
| `llamacpp:qwen3-coder-30b` | 精确匹配 | 返回该实例的 models |

### 聚合逻辑示例

```
查询: /api/providers/llamacpp/models

Step 1: registry.get("llamacpp") → None (不存在)

Step 2: 查找前缀匹配
  - llamacpp:glm47flash-q8 ❌ (ERROR, 服务未运行)
  - llamacpp:qwen3-coder-30b ✅ (READY)
  - llamacpp:qwen2.5-coder-7b ✅ (READY)

Step 3: 聚合 models
  - qwen3-coder-30b → [Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf]
  - qwen2.5-coder-7b → [qwen2.5-coder-7b-instruct-q8_0.gguf]

Step 4: 去重并返回
  - 2 个 models
```

---

## 🎯 用户体验改进

### Before (修复前)

```
Chat 页面 → 选择 llama.cpp → Provider not available ❌
```

### After (修复后)

```
Chat 页面 → 选择 llama.cpp → 显示 2 个可用 models ✅
  - Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf
  - qwen2.5-coder-7b-instruct-q8_0.gguf
```

---

## 🚀 使用方法

### 1. 重启服务器

```bash
./quick_restart.sh
```

### 2. 清除浏览器缓存

```bash
# Chrome/Edge: 开发者工具 → 右键刷新按钮 → 清空缓存并硬刷新
Cmd+Shift+R (Mac)
Ctrl+Shift+R (Windows/Linux)
```

### 3. 测试 Chat 页面

1. 访问 http://127.0.0.1:8080
2. 在 Chat 页面选择 Provider: `llama.cpp`
3. ✅ 应该显示可用的 models
4. ✅ 可以选择 model 并开始对话

---

## 📋 技术细节

### ProviderRegistry 可用方法

| 方法 | 描述 |
|------|------|
| `get_instance()` | 获取单例实例 |
| `register(provider)` | 注册 provider |
| `get(provider_id)` | 获取单个 provider |
| `list_all()` | 获取所有 providers |
| `get_all_status()` | 获取所有 provider 状态 |

### Provider ID 命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 单实例 Provider | `provider_name` | `ollama`, `lmstudio` |
| 多实例 Provider | `provider_name:instance_name` | `llamacpp:qwen3-coder-30b` |

---

## ✅ 验收清单

- [x] `/api/providers/llamacpp/models` 返回 200
- [x] 返回的 models 来自所有可用的 llamacpp 实例
- [x] 自动去重相同的 model ID
- [x] 单个实例失败不影响整体结果
- [x] Chat 页面可以正常选择 llama.cpp provider
- [x] Chat 页面可以看到可用的 models
- [ ] 浏览器缓存已清除
- [ ] 用户验证功能正常

---

**修复完成时间**: 2026-01-28
**服务器状态**: ✅ 运行中
**API 测试**: ✅ 通过
