# Model 选择持久化修复

## 🐛 问题描述

**用户报告**:
- ✅ 在 Chat 页面选择了 Provider 和 Model
- ❌ 刷新页面后，选择丢失，需要重新选择
- ❌ 每次都要重新选 Provider 和 Model

**期望行为**:
- 选择 Provider 和 Model 后，刷新页面应该记住之前的选择

---

## 🔍 根本原因

### 缺少持久化逻辑

#### Before (修复前)

**1. 选择时没有保存**:
```javascript
// Provider change handler
modelProviderSelect.addEventListener('change', () => {
    state.currentProvider = modelProviderSelect.value;
    loadAvailableModels();
    refreshProviderStatus();
    // ❌ 没有保存到 localStorage
});

// Model change handler
modelNameSelect.addEventListener('change', () => {
    console.log('Model selected:', modelNameSelect.value);
    // ❌ 没有保存到 localStorage
});
```

**2. 初始化时使用硬编码默认值**:
```javascript
// Initialize
updateProviderOptions('local');
state.currentProvider = 'ollama';  // ❌ 硬编码，总是 ollama
loadAvailableModels();
```

**结果**:
- 每次刷新页面，都会重置为 `ollama` provider
- 之前选择的 provider 和 model 丢失

---

## ✅ 修复方案

### 实现 localStorage 持久化

使用 `localStorage` 保存和恢复 Provider 和 Model 选择。

### 修改的文件

**agentos/webui/static/js/main.js** (line 762-808)

### 修复逻辑

#### 1. 保存选择到 localStorage

```javascript
// Provider change handler
modelProviderSelect.addEventListener('change', () => {
    state.currentProvider = modelProviderSelect.value;

    // ✅ 保存到 localStorage
    localStorage.setItem('agentos_model_provider', modelProviderSelect.value);

    loadAvailableModels();
    refreshProviderStatus();
});

// Model change handler
modelNameSelect.addEventListener('change', () => {
    console.log('Model selected:', modelNameSelect.value);

    // ✅ 保存到 localStorage
    if (modelNameSelect.value) {
        localStorage.setItem('agentos_model_name', modelNameSelect.value);
    }
});
```

#### 2. 初始化时恢复选择

```javascript
// Initialize - restore from localStorage or use defaults
const savedProvider = localStorage.getItem('agentos_model_provider');
const savedModel = localStorage.getItem('agentos_model_name');

updateProviderOptions('local');

// ✅ 恢复 provider 选择
if (savedProvider && modelProviderSelect) {
    modelProviderSelect.value = savedProvider;
    state.currentProvider = savedProvider;
} else {
    // 默认值（仅首次访问）
    state.currentProvider = 'ollama';
}

// ✅ 加载 models，然后恢复 model 选择
loadAvailableModels().then(() => {
    // 恢复 model 选择（在 models 加载完成后）
    if (savedModel && modelNameSelect) {
        // 检查 saved model 是否存在于选项中
        const modelOption = Array.from(modelNameSelect.options).find(
            opt => opt.value === savedModel
        );
        if (modelOption) {
            modelNameSelect.value = savedModel;
            console.log('Restored model selection:', savedModel);
        }
    }
});
```

### 关键特性

1. **自动保存**:
   - 每次选择 provider 或 model 时，自动保存到 localStorage
   - 无需用户手动操作

2. **智能恢复**:
   - 页面加载时，自动从 localStorage 读取之前的选择
   - 验证 model 是否存在于当前 provider 的 models 列表中
   - 如果 model 不存在（如 provider 已更改），则不恢复

3. **容错处理**:
   - 如果 localStorage 中没有保存的值，使用默认值
   - 如果保存的 model 不再可用，只恢复 provider

---

## 🧪 测试场景

### 场景 1: 正常持久化

```
Step 1: 首次访问
  - Provider: ollama (默认)
  - Model: (空)

Step 2: 选择 provider 和 model
  - Provider: llama.cpp
  - Model: qwen2.5-coder-7b-instruct-q8_0.gguf
  - localStorage 保存: ✅

Step 3: 刷新页面
  - Provider: llama.cpp ✅ (恢复成功)
  - Model: qwen2.5-coder-7b-instruct-q8_0.gguf ✅ (恢复成功)
```

### 场景 2: Model 不再可用

```
Step 1: 选择
  - Provider: llama.cpp
  - Model: model-A

Step 2: 停止 model-A 实例

Step 3: 刷新页面
  - Provider: llama.cpp ✅ (恢复成功)
  - Model: (空) ✅ (model-A 不再可用，不恢复)
```

### 场景 3: 切换浏览器

```
Browser A:
  - Provider: llama.cpp
  - Model: qwen2.5-coder-7b

Browser B:
  - Provider: ollama (默认)
  - Model: (空)

说明: localStorage 是独立的
```

---

## 📊 localStorage 存储

### 存储的键值对

| Key | Value | 示例 |
|-----|-------|------|
| `agentos_model_provider` | Provider ID | `"llamacpp"` |
| `agentos_model_name` | Model ID | `"qwen2.5-coder-7b-instruct-q8_0.gguf"` |
| `agentos_current_view` | 当前视图 | `"chat"` (已存在) |

### 查看 localStorage

在浏览器控制台执行:
```javascript
// 查看所有 AgentOS 相关的存储
Object.keys(localStorage)
    .filter(k => k.startsWith('agentos_'))
    .forEach(k => console.log(k, '=', localStorage.getItem(k)));

// 输出示例:
// agentos_model_provider = llamacpp
// agentos_model_name = qwen2.5-coder-7b-instruct-q8_0.gguf
// agentos_current_view = chat
```

### 清除持久化数据

如果需要清除保存的选择:
```javascript
// 清除 model 选择
localStorage.removeItem('agentos_model_provider');
localStorage.removeItem('agentos_model_name');

// 或清除所有 AgentOS 数据
Object.keys(localStorage)
    .filter(k => k.startsWith('agentos_'))
    .forEach(k => localStorage.removeItem(k));
```

---

## 🎯 用户体验改进

### Before (修复前)

```
1. 用户选择: llama.cpp + qwen2.5-coder-7b
2. 刷新页面
3. Provider 重置为: ollama ❌
4. Model 重置为: (空) ❌
5. 用户需要重新选择 ❌
```

### After (修复后)

```
1. 用户选择: llama.cpp + qwen2.5-coder-7b
2. 自动保存到 localStorage ✅
3. 刷新页面
4. Provider 恢复为: llama.cpp ✅
5. Model 恢复为: qwen2.5-coder-7b ✅
6. 用户可以直接开始对话 ✅
```

---

## 🚀 使用方法

### 1. 清除浏览器缓存（必须）

服务器已重启，main.js 版本已更新到 v15。

**Chrome/Edge**:
```
1. F12 打开开发者工具
2. 右键点击刷新按钮
3. 选择 "清空缓存并硬性重新加载"
```

**或使用快捷键**:
```
Mac: Cmd + Shift + R
Windows/Linux: Ctrl + Shift + R
```

### 2. 验证修复

**Step 1: 选择 Provider 和 Model**
1. 访问 http://127.0.0.1:8080
2. 在 Chat 页面选择:
   - Provider: `llama.cpp`
   - Model: `qwen2.5-coder-7b-instruct-q8_0.gguf`
3. 查看控制台，应该显示:
   ```
   Model selected: qwen2.5-coder-7b-instruct-q8_0.gguf
   ```

**Step 2: 刷新页面**
1. 按 `F5` 或点击刷新按钮
2. 等待页面加载完成
3. ✅ Provider 应该仍然是 `llama.cpp`
4. ✅ Model 应该仍然是 `qwen2.5-coder-7b-instruct-q8_0.gguf`
5. 查看控制台，应该显示:
   ```
   Restored model selection: qwen2.5-coder-7b-instruct-q8_0.gguf
   ```

**Step 3: 跨标签页测试**
1. 打开新标签页，访问 http://127.0.0.1:8080
2. ✅ 应该自动恢复之前的 Provider 和 Model 选择

---

## 🔍 调试方法

### 检查 localStorage

打开控制台，执行:
```javascript
// 检查保存的值
console.log('Provider:', localStorage.getItem('agentos_model_provider'));
console.log('Model:', localStorage.getItem('agentos_model_name'));
```

### 检查恢复逻辑

刷新页面后，检查控制台输出:
```javascript
// 应该看到
Restored model selection: qwen2.5-coder-7b-instruct-q8_0.gguf
```

如果没有看到，可能原因：
1. **localStorage 没有保存** - 检查选择时是否触发了 change 事件
2. **Model 不存在** - 检查 model 是否还在 provider 的 models 列表中
3. **缓存问题** - 清除浏览器缓存并刷新

---

## 📋 相关修复

本次修复与以下修复配套使用：

1. **LLAMACPP_MODELS_FIX.md** - 修复了 llamacpp provider 的 models API
2. **PROVIDER_STATUS_FIX.md** - 修复了 provider 状态显示
3. **MODEL_PERSISTENCE_FIX.md** (本文档) - 修复了 model 选择持久化

这三个修复共同提供了完整的 model 选择体验。

---

## 💡 技术细节

### 为什么使用 localStorage？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **localStorage** | • 永久存储<br>• 跨标签页共享<br>• 简单易用 | • 仅限同一浏览器<br>• 5MB 限制 |
| sessionStorage | • 隔离性好 | ❌ 关闭标签页后丢失<br>❌ 不跨标签页 |
| Cookie | • 可跨域 | ❌ 大小限制 4KB<br>❌ 每次请求都发送 |
| 服务器端 | • 跨设备 | ❌ 需要 API<br>❌ 增加延迟 |

**选择 localStorage 的原因**:
- ✅ 适合客户端偏好设置
- ✅ 无需服务器存储
- ✅ 跨标签页生效（用户期望）

### 恢复时机

```javascript
// 在 setupModelToolbar() 中
updateProviderOptions('local');  // 1. 先填充 provider 选项

// 恢复 provider
modelProviderSelect.value = savedProvider;  // 2. 恢复 provider 选择

// 加载 models
loadAvailableModels().then(() => {  // 3. 加载该 provider 的 models
    // 恢复 model（必须在 models 加载完成后）
    modelNameSelect.value = savedModel;  // 4. 恢复 model 选择
});
```

**为什么 model 恢复必须在 then() 中？**
- `loadAvailableModels()` 是异步的，需要从 API 获取 models
- 如果在 models 加载完成前设置 `modelNameSelect.value`，会失败（因为 `<option>` 还不存在）

---

## ✅ 验收清单

- [x] Provider 选择时保存到 localStorage
- [x] Model 选择时保存到 localStorage
- [x] 页面加载时从 localStorage 恢复 provider
- [x] Models 加载完成后从 localStorage 恢复 model
- [x] 验证 model 是否存在于选项中
- [x] 更新 main.js 版本到 v15
- [x] 重启服务器
- [ ] 清除浏览器缓存
- [ ] 验证选择持久化功能
- [ ] 验证跨标签页同步

---

**修复完成时间**: 2026-01-28
**main.js 版本**: v15
**服务器状态**: ✅ 运行中
**需要操作**: 清除浏览器缓存并验证
