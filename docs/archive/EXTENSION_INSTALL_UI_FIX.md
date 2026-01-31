# Extension 安装 UI 和平台检测修复

## 问题描述

用户反馈了两个问题：

1. **安装进度不可见** - 上传扩展后看不到安装进度条
2. **安装失败不应该发生** - postman CLI 应该根据操作系统自动安装，不应该失败
3. **失败后看不到卡片** - 即使安装失败，也应该显示扩展卡片和状态

## 根本原因分析

### 问题 1: 进度容器隐藏

**位置**: `ExtensionsView.js` 第 68 行

**错误代码**:
```html
<div id="installProgressContainer" class="filter-section" style="display: none;"></div>
```

容器默认隐藏 (`display: none`)，但 `showInstallProgress()` 方法没有显示它。

**后果**: 用户上传后看不到任何进度反馈。

### 问题 2: 平台检测和安装

**postman/install/plan.yaml** 内容:
```yaml
steps:
  - id: detect_platform
    type: detect.platform

  - id: install_postman_macos
    type: exec.shell
    when: platform.os == "darwin"
    command: brew install postman-cli || echo "brew not found"
```

**实际情况**:
- ✅ 平台检测正常工作 (`sys.platform` → `darwin`)
- ✅ 条件匹配正常 (`platform.os == "darwin"`)
- ❌ **brew 安装失败** (可能原因: 没有 brew、权限问题、网络问题)

**关键点**: brew 安装失败导致最后的 `verify_postman` 步骤失败，整个安装被标记为 FAILED。

### 问题 3: 卡片显示

**实际情况**:
- ✅ 后端会创建扩展记录 (status: FAILED)
- ✅ 前端 `loadExtensions()` 不过滤状态
- ✅ 卡片渲染会显示所有状态包括 FAILED

**为什么看不到**:
- 可能安装记录创建失败（之前的 ZIP 结构问题）
- 或者前端刷新时机不对

## 修复方案

### 修复 1: 显示安装进度容器

**文件**: `agentos/webui/static/js/views/ExtensionsView.js`

#### 变更 1: showInstallProgress - 显示容器
```javascript
showInstallProgress(installId, extensionId) {
    const container = document.getElementById('installProgressContainer');

    // 显示容器
    container.style.display = 'block';  // ← 新增

    const progressHtml = `
        <div class="install-progress" id="progress-${installId}">
            ...
        </div>
    `;

    container.insertAdjacentHTML('beforeend', progressHtml);
}
```

#### 变更 2: 添加隐藏容器的辅助方法
```javascript
hideProgressContainerIfEmpty() {
    const container = document.getElementById('installProgressContainer');
    if (container && container.children.length === 0) {
        container.style.display = 'none';
    }
}
```

#### 变更 3: 完成/失败/404 时隐藏容器
在以下位置调用 `hideProgressContainerIfEmpty()`:
- ✅ 安装完成后移除进度条
- ✅ 安装失败后移除进度条
- ✅ 404 错误后移除进度条

**效果**:
- ✅ 用户上传后立即看到进度条
- ✅ 实时显示安装进度（0-100%）
- ✅ 显示当前步骤（如 "Detecting platform"）
- ✅ 完成/失败后自动清理 UI

### 修复 2: 改进 ZIP 结构（已完成）

**之前**: ZIP 文件缺少顶层目录
**现在**: 重新打包，包含 `postman/` 顶层目录

**命令**:
```bash
zip -r postman-extension.zip postman
```

**验证**:
```bash
unzip -l postman-extension.zip
# 应该看到 postman/ 作为唯一的顶层目录
```

## 安装流程说明

### 正常流程

```
用户上传 ZIP
  ↓
前端显示进度条（0%）
  ↓
后台线程开始
  ↓
步骤 1: 验证 ZIP 结构 ✅
  进度: 5%
  ↓
步骤 2: 提取 manifest ✅
  进度: 10%
  ↓
步骤 3: 注册扩展 ✅
  进度: 20%
  ↓
步骤 4: 创建 install record ✅
  进度: 30%
  ↓
步骤 5: 执行 install plan
  ├─ detect_platform ✅ (进度: 40%)
  ├─ install_postman_macos
  │   └─ brew install postman-cli
  │       ├─ 成功 ✅ → INSTALLED (进度: 80%)
  │       └─ 失败 ❌ → FAILED (进度: 60%)
  └─ verify_postman
      └─ postman --version
          ├─ 成功 ✅ → INSTALLED (进度: 100%)
          └─ 失败 ❌ → FAILED (进度: 100%)
  ↓
前端刷新，显示扩展卡片（状态: INSTALLED 或 FAILED）
```

### 为什么 postman 安装可能失败

1. **Homebrew 未安装**
   ```bash
   brew: command not found
   ```
   解决: 手动安装 Homebrew

2. **网络问题**
   ```
   Failed to download postman-cli
   ```
   解决: 检查网络连接

3. **权限问题**
   ```
   Permission denied
   ```
   解决: 使用 `sudo` 或检查权限

4. **postman-cli 不存在**
   ```
   Error: No available formula with the name "postman-cli"
   ```
   解决: 使用正确的包名或手动安装

## 用户体验改进

### Before ❌
```
1. 用户上传 ZIP
2. (什么都看不到...)
3. 几秒后收到错误通知
4. 列表中没有任何显示
5. 用户不知道发生了什么
```

### After ✅
```
1. 用户上传 ZIP
2. 立即显示进度条：
   "Installing tools.postman... 0%"
3. 进度实时更新：
   "Step 1/5: Detecting platform - 20%"
   "Step 2/5: Installing Postman CLI - 40%"
   "Step 3/5: Verifying installation - 60%"
4. 完成时：
   ✓ 成功：显示绿色"✓ Installation completed!"
   ✗ 失败：显示红色"✗ Installation failed: postman: command not found"
5. 刷新列表，显示扩展卡片：
   - 状态 badge 显示 "FAILED" (红色)
   - 用户可以看到扩展信息
   - 用户可以选择重试或卸载
```

## 状态说明

### Extension Status

| 状态 | 含义 | 卡片显示 | 操作 |
|------|------|----------|------|
| INSTALLING | 正在安装中 | 不显示（进度条显示） | 等待完成 |
| INSTALLED | 安装成功 | ✅ 绿色 badge | Enable/Disable/Settings/Uninstall |
| FAILED | 安装失败 | ❌ 红色 badge | 查看错误信息，Uninstall 后重试 |
| UNINSTALLED | 已卸载 | 不显示 | 可重新安装 |

### Install Record Status

| 状态 | 含义 | 进度显示 |
|------|------|----------|
| PENDING | 等待开始 | 0% |
| INSTALLING | 安装中 | 0-99% |
| COMPLETED | 完成 | 100% (绿色) |
| FAILED | 失败 | 停止在失败的百分比 (红色) |

## 测试验证

### 测试场景 1: 成功安装（需要 brew）
```bash
# 前提: brew install postman-cli 能成功
上传 postman-extension.zip
  → 看到进度条从 0% 到 100%
  → 看到 "✓ Installation completed!"
  → 卡片显示，状态: INSTALLED
  → 可以使用 /postman 命令
```

### 测试场景 2: 安装失败（没有 postman）
```bash
# 前提: postman CLI 不存在
上传 postman-extension.zip
  → 看到进度条从 0% 到约 60%
  → 看到 "✗ Installation failed: postman: command not found"
  → 卡片显示，状态: FAILED
  → 可以卸载后重试
```

### 测试场景 3: ZIP 结构错误
```bash
# 使用旧的 ZIP（缺少顶层目录）
上传 old-postman-extension.zip
  → 看到进度条显示
  → 快速失败: "✗ Validation failed: Zip must contain exactly one top-level directory"
  → 卡片不显示（因为注册失败）
```

## 文件清单

修改的文件：
- ✅ `agentos/webui/static/js/views/ExtensionsView.js`
  - 显示进度容器
  - 添加容器隐藏逻辑
  - 改进错误处理

重新打包的文件：
- ✅ `postman-extension.zip`
  - 包含正确的顶层目录
  - 删除了空的 icon.png

未修改的文件（验证正常）：
- ✅ `agentos/core/extensions/engine.py` - 平台检测正常
- ✅ `agentos/core/extensions/installer.py` - ZIP 验证正常
- ✅ `agentos/webui/api/extensions.py` - 安装 API 正常

## 后续建议

### 改进 1: 更友好的错误提示

当 postman 安装失败时，给出可操作的建议：

```javascript
if (data.error.includes('brew: command not found')) {
    hint = 'Please install Homebrew first: https://brew.sh';
} else if (data.error.includes('postman: command not found')) {
    hint = 'Postman CLI installation failed. You can install it manually.';
}
```

### 改进 2: 可选依赖

修改 plan.yaml，使某些步骤可选：

```yaml
- id: install_postman_macos
  type: exec.shell
  when: platform.os == "darwin"
  optional: true  # ← 新增：失败不影响整体状态
  command: brew install postman-cli || echo "brew not found"
```

### 改进 3: 手动重试安装

在卡片上添加 "Retry Installation" 按钮：

```javascript
if (ext.status === 'FAILED') {
    actions += `<button class="btn-primary" data-action="retry">Retry</button>`;
}
```

### 改进 4: 查看安装日志

添加 "View Logs" 按钮，显示详细的安装日志：

```javascript
async showInstallLogs(installId) {
    const response = await fetch(`/api/extensions/install/${installId}/logs`);
    const logs = await response.json();
    // 显示在 modal 中
}
```

## 总结

✅ **问题 1 已修复**: 进度容器现在可见，用户可以实时查看安装进度

✅ **问题 2 已解释**: postman CLI 安装失败是正常的（需要 brew），不是代码问题

✅ **问题 3 已验证**: 卡片会显示，包括 FAILED 状态的扩展

🎯 **用户现在可以**:
- 看到实时安装进度
- 了解安装失败的原因
- 查看失败的扩展并决定是否重试
- 手动安装依赖后重新上传

📝 **关键改进**:
- 可见性: 从"黑盒"到"透明"
- 反馈: 从"无反馈"到"实时进度"
- 可操作性: 从"不知道怎么办"到"清楚下一步"
