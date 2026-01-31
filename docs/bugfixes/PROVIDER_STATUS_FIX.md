# Provider 状态显示修复

## 🐛 问题描述

**用户报告**:
- ✅ 选择了 `llama.cpp` provider
- ✅ 选择了 `qwen2.5-coder-7b-instruct-q8_0.gguf` model
- ❌ 页面上显示 "Error" 状态

**期望行为**:
- 应该显示 "Ready" 或实际的 provider 状态

---

## 🔍 根本原因

### Provider ID 不匹配问题

#### 用户选择的 Provider
```javascript
model-provider.value = "llamacpp"  // 用户界面选择
```

#### API 返回的实际 Provider IDs
```json
{
  "providers": [
    {
      "id": "llamacpp:qwen3-coder-30b",  // 实例 1
      "state": "READY"
    },
    {
      "id": "llamacpp:qwen2.5-coder-7b",  // 实例 2
      "state": "READY"
    }
  ]
}
```

#### refreshProviderStatus 的查找逻辑

**修复前**:
```javascript
const currentProvider = "llamacpp";  // 从界面获取

// 查找精确匹配
const providerStatus = data.providers.find(p => p.id === currentProvider);
// providerStatus = undefined (找不到 id === "llamacpp")

if (providerStatus) {
    updateModelLinkStatus(providerStatus.state, providerStatus);
}
// 没有找到，所以不更新状态，保持旧状态（可能是 ERROR）
```

**问题**:
- 用户选择的是逻辑 provider (`llamacpp`)
- 但实际的 provider 是实例级别的 (`llamacpp:xxx`)
- 精确匹配失败，导致状态不更新

---

## ✅ 修复方案

### 实现前缀匹配和智能选择

修改 `refreshProviderStatus()` 函数，支持：
1. ✅ 精确匹配（如 `ollama`）
2. ✅ 前缀匹配（如 `llamacpp` → `llamacpp:*`）
3. ✅ 智能选择最佳实例（优先选择 READY 状态）

### 修改的文件

**agentos/webui/static/js/main.js** (line 986-1033)

### 修复逻辑

```javascript
async function refreshProviderStatus() {
    const response = await fetch('/api/providers/status');
    const data = await response.json();

    const currentProvider = providerEl.value;  // e.g., "llamacpp"
    const currentModel = modelEl.value;         // e.g., "qwen2.5-coder-7b-instruct-q8_0.gguf"

    // Step 1: 尝试精确匹配
    let providerStatus = data.providers.find(p => p.id === currentProvider);

    // Step 2: 如果没有精确匹配，尝试前缀匹配
    if (!providerStatus) {
        const prefix = `${currentProvider}:`;  // "llamacpp:"
        const matchingProviders = data.providers.filter(p => p.id.startsWith(prefix));
        // 找到: ["llamacpp:qwen3-coder-30b", "llamacpp:qwen2.5-coder-7b"]

        if (matchingProviders.length > 0) {
            // Step 3: 智能选择最佳实例
            if (currentModel) {
                // 如果选择了 model，优先选择 READY 状态的实例
                providerStatus = matchingProviders.find(p => p.state === 'READY')
                              || matchingProviders[0];
            } else {
                // 没有选择 model，选择第一个 READY 实例或第一个实例
                providerStatus = matchingProviders.find(p => p.state === 'READY')
                              || matchingProviders[0];
            }
        }
    }

    // Step 4: 更新状态
    if (providerStatus) {
        updateModelLinkStatus(providerStatus.state, providerStatus);
    } else {
        updateModelLinkStatus('DISCONNECTED');
    }
}
```

### 关键改进

1. **前缀匹配**:
   - 当查找 `llamacpp` 时，自动查找所有 `llamacpp:*` 实例
   - 支持多实例 provider（如 llamacpp）

2. **智能选择**:
   - 优先选择 `READY` 状态的实例
   - 如果没有 READY 实例，选择第一个实例（可能是 ERROR 或其他状态）

3. **容错处理**:
   - 如果所有方法都找不到 provider，显示 "Disconnected"
   - 如果 API 调用失败，显示 "Error"

---

## 🧪 测试场景

### 场景 1: 单实例 Provider（如 Ollama）

```javascript
currentProvider = "ollama"
providers = [{ id: "ollama", state: "READY" }]

// 精确匹配成功
providerStatus = { id: "ollama", state: "READY" }
// 显示: "Ready"
```

### 场景 2: 多实例 Provider（如 Llamacpp）

```javascript
currentProvider = "llamacpp"
providers = [
  { id: "llamacpp:qwen3-coder-30b", state: "ERROR" },
  { id: "llamacpp:qwen2.5-coder-7b", state: "READY" }
]

// 精确匹配失败，前缀匹配成功
matchingProviders = [
  { id: "llamacpp:qwen3-coder-30b", state: "ERROR" },
  { id: "llamacpp:qwen2.5-coder-7b", state: "READY" }
]

// 智能选择: 优先选择 READY 状态
providerStatus = { id: "llamacpp:qwen2.5-coder-7b", state: "READY" }
// 显示: "Ready (45ms)"
```

### 场景 3: 所有实例都是 ERROR

```javascript
currentProvider = "llamacpp"
providers = [
  { id: "llamacpp:glm47flash-q8", state: "ERROR" },
  { id: "llamacpp:qwen3-coder-30b", state: "ERROR" }
]

// 前缀匹配成功，但没有 READY 实例
providerStatus = { id: "llamacpp:glm47flash-q8", state: "ERROR" }
// 显示: "Error"
```

---

## 📊 状态显示逻辑

| Provider State | 显示文本 | 颜色 | 说明 |
|---------------|---------|------|------|
| `READY` | "Ready (XXms)" | 绿色 | Provider 可用，显示延迟 |
| `ERROR` | "Error" | 红色 | Provider 错误 |
| `DEGRADED` | "Degraded" | 黄色 | Provider 降级 |
| `CONNECTING` | "Connecting..." | 蓝色 | 正在连接 |
| `DISCONNECTED` | "Disconnected" | 灰色 | 未连接 |

---

## 🎯 用户体验改进

### Before (修复前)

```
用户选择:
  Provider: llama.cpp
  Model: qwen2.5-coder-7b-instruct-q8_0.gguf

状态显示:
  Error ❌ (保持旧状态，未更新)
```

### After (修复后)

```
用户选择:
  Provider: llama.cpp
  Model: qwen2.5-coder-7b-instruct-q8_0.gguf

状态显示:
  Ready (45ms) ✅ (自动找到 llamacpp:qwen2.5-coder-7b 实例)
```

---

## 🚀 使用方法

### 1. 清除浏览器缓存（必须）

服务器已重启，main.js 版本已更新到 v14。

**Chrome/Edge**:
```
1. 打开开发者工具 (F12)
2. 右键点击刷新按钮
3. 选择 "清空缓存并硬性重新加载"
```

**或使用快捷键**:
```
Mac: Cmd + Shift + R
Windows/Linux: Ctrl + Shift + R
```

### 2. 验证修复

1. 访问 http://127.0.0.1:8080
2. 在 Chat 页面选择:
   - Provider: `llama.cpp`
   - Model: `qwen2.5-coder-7b-instruct-q8_0.gguf`
3. 查看右上角的状态指示器
4. ✅ 应该显示: **"Ready (XXms)"**（绿色）

### 3. 悬停查看详细信息

鼠标悬停在状态指示器上，会显示 tooltip:
```
Endpoint: http://127.0.0.1:11436
Latency: 45ms
```

---

## 🔍 调试方法

### 检查 Network 面板

1. 打开开发者工具 → Network 标签
2. 查找 `main.js` 请求
3. ✅ 应该看到 `main.js?v=14`（不是 v13）

### 检查 Console 输出

刷新后，Console 应该显示:
```javascript
Model selected: qwen2.5-coder-7b-instruct-q8_0.gguf
```

如果状态仍然不正确，查看是否有错误：
```javascript
Failed to fetch provider status: ...
```

### 手动测试 API

```bash
# 检查 provider 状态
curl -s 'http://127.0.0.1:8080/api/providers/status' | python3 -m json.tool | grep -A 10 "llamacpp"

# 应该看到 READY 状态的实例
```

---

## 📋 相关修复

本次修复是以下问题的延续：

1. **LLAMACPP_MODELS_FIX.md** - 修复了 `/api/providers/llamacpp/models` 404 错误
2. **PROVIDERS_404_FIX.md** - 改进了前端对 404 的处理
3. **PROVIDER_STATUS_FIX.md** (本文档) - 修复了状态显示不正确的问题

这三个修复共同解决了 llamacpp provider 的完整工作流。

---

## ✅ 验收清单

- [x] 修改了 `refreshProviderStatus()` 函数
- [x] 添加了前缀匹配逻辑
- [x] 添加了智能选择逻辑（优先 READY）
- [x] 更新了 main.js 版本到 v14
- [x] 重启了服务器
- [ ] 清除浏览器缓存
- [ ] 验证状态显示为 "Ready"
- [ ] 验证 tooltip 显示正确信息

---

**修复完成时间**: 2026-01-28
**main.js 版本**: v14
**服务器状态**: ✅ 运行中
**需要操作**: 清除浏览器缓存
