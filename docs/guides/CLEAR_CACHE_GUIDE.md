# 清除浏览器缓存指南

## 🔄 快速刷新方法

### 方法 1: 硬刷新（推荐）

**Mac**:
```
Cmd + Shift + R
```

**Windows/Linux**:
```
Ctrl + Shift + R
```

### 方法 2: 清空缓存并硬刷新（最彻底）

#### Chrome / Edge

1. **打开开发者工具**
   - Mac: `Cmd + Option + I`
   - Windows/Linux: `Ctrl + Shift + I`

2. **右键点击刷新按钮**
   - 在浏览器地址栏左侧找到刷新按钮
   - 按住 `右键` 不放

3. **选择 "清空缓存并硬性重新加载"**
   - Chrome: "Empty Cache and Hard Reload"
   - Edge: "清空缓存并硬性重新加载"

#### Firefox

1. **打开开发者工具**
   - Mac: `Cmd + Option + I`
   - Windows/Linux: `Ctrl + Shift + I`

2. **打开网络面板**
   - 点击 "Network" 标签

3. **禁用缓存**
   - 勾选 "Disable Cache" 复选框

4. **刷新页面**
   - `Cmd + R` (Mac) 或 `Ctrl + R` (Windows/Linux)

#### Safari

1. **启用开发菜单**
   - Safari → 偏好设置 → 高级
   - 勾选 "在菜单栏中显示开发菜单"

2. **清空缓存**
   - 开发 → 清空缓存
   - 或 `Cmd + Option + E`

3. **刷新页面**
   - `Cmd + R`

---

## 🛠️ 版本号更新

已将 main.js 的版本号从 `v=12` 更新到 `v=13`，这将强制浏览器重新下载最新文件。

**修改的文件**:
- `agentos/webui/templates/index.html` (line 325)

```html
<!-- 修改前 -->
<script src="/static/js/main.js?v=12"></script>

<!-- 修改后 -->
<script src="/static/js/main.js?v=13"></script>
```

---

## 🔍 验证缓存已清除

### 方法 1: 检查加载的文件版本

1. **打开开发者工具**
   - `F12` 或 `Cmd/Ctrl + Option/Shift + I`

2. **打开 Network (网络) 面板**

3. **刷新页面**

4. **查找 main.js**
   - 应该看到 `main.js?v=13`
   - 如果仍然是 `v=12`，说明缓存未清除

### 方法 2: 检查修复是否生效

1. **打开 Console (控制台)**

2. **触发 provider models API 调用**
   - 访问需要选择 model 的页面
   - 选择 `llamacpp` provider

3. **检查输出**

   **修复前** (❌ 错误):
   ```
   GET http://127.0.0.1:8080/api/providers/llamacpp/models 404 (Not Found)
   Failed to load models: ...
   ```

   **修复后** (✅ 正确):
   ```
   Provider llamacpp not available: Provider 'llamacpp' not found
   ```

---

## 🚨 如果问题仍然存在

### 1. 完全清除浏览器缓存

#### Chrome / Edge

1. **打开设置**
   - Chrome: `chrome://settings/clearBrowserData`
   - Edge: `edge://settings/clearBrowserData`

2. **选择时间范围**: "所有时间" / "All time"

3. **勾选以下选项**:
   - ✅ 缓存的图片和文件
   - ✅ Cookies 和其他网站数据（可选）

4. **点击 "清除数据"**

5. **关闭并重新打开浏览器**

6. **访问**: `http://127.0.0.1:8080`

#### Firefox

1. **打开设置**
   - `about:preferences#privacy`

2. **Cookies 和网站数据** → **清除数据**

3. **勾选 "缓存的 Web 内容"**

4. **清除**

#### Safari

1. **Safari → 偏好设置 → 高级**

2. **勾选 "在菜单栏中显示开发菜单"**

3. **开发 → 清空缓存**

4. **Safari → 历史记录 → 清除历史记录**

---

### 2. 使用无痕/隐私模式

如果清除缓存仍然无效，使用无痕/隐私模式测试：

- **Chrome/Edge**: `Cmd/Ctrl + Shift + N`
- **Firefox**: `Cmd/Ctrl + Shift + P`
- **Safari**: `Cmd + Shift + N`

在无痕模式下访问: `http://127.0.0.1:8080`

如果在无痕模式下正常工作，说明是缓存问题。

---

### 3. 直接访问 main.js 文件

在浏览器中直接访问:
```
http://127.0.0.1:8080/static/js/main.js?v=13
```

检查第 822-826 行是否包含修复代码:
```javascript
if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    console.warn(`Provider ${provider} not available:`, error.detail);
    modelSelect.innerHTML = '<option value="">Provider not available</option>';
    return;
}
```

如果没有这段代码，说明文件未更新。

---

### 4. 检查 Service Worker

某些应用使用 Service Worker 缓存资源。

#### 检查并清除 Service Worker

1. **打开开发者工具**

2. **Application (应用) 标签**

3. **Service Workers**

4. **点击 "Unregister" (注销)**

5. **刷新页面**

---

## 📋 完整的故障排除步骤

```bash
# 步骤 1: 硬刷新
Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows/Linux)

# 步骤 2: 如果仍有问题，清空缓存并硬刷新
1. 打开开发者工具 (F12)
2. 右键点击刷新按钮
3. 选择 "清空缓存并硬性重新加载"

# 步骤 3: 如果仍有问题，完全清除浏览器缓存
Chrome: chrome://settings/clearBrowserData
选择 "所有时间" → 清除 "缓存的图片和文件"

# 步骤 4: 如果仍有问题，使用无痕模式测试
Cmd/Ctrl + Shift + N

# 步骤 5: 如果无痕模式正常，说明是缓存问题
关闭所有浏览器窗口，重新打开

# 步骤 6: 如果问题依然存在
检查是否有浏览器扩展干扰（禁用所有扩展重试）
```

---

## ✅ 确认修复成功

当看到以下行为时，说明修复成功：

1. **控制台输出**:
   ```
   ⚠️ Provider llamacpp not available: Provider 'llamacpp' not found
   ```
   （警告而不是错误）

2. **下拉菜单显示**:
   ```
   Provider not available
   ```
   （而不是 "Error loading models"）

3. **Network 面板**:
   - `main.js?v=13` 加载成功
   - 404 错误不再显示为红色

---

**更新时间**: 2026-01-28
**版本**: main.js v13
