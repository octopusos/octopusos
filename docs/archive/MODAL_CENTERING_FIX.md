# Modal 弹窗居中问题修复

## 问题描述

Uninstall Extension 和 Configure Extension 弹窗不是全屏居中显示，而是出现在左上角。

## 根本原因

这两个弹窗使用了错误的 HTML 结构:

**错误结构** ❌:
```html
<div class="modal-overlay">
    <div class="modal-content">
        <!-- 内容 -->
    </div>
</div>
```

**正确结构** ✅:
```html
<div class="modal active">
    <div class="modal-overlay"></div>
    <div class="modal-content">
        <!-- 内容 -->
    </div>
</div>
```

## CSS 原理

项目中的 modal 样式基于以下结构:

1. `.modal.active` - 外层容器，提供全屏覆盖
2. `.modal-overlay` - 半透明背景遮罩层
3. `.modal-content` - 居中的内容区域

当使用 `modal-overlay` 作为外层时，缺少 `.modal.active` 的定位和布局样式，导致内容定位错误。

## 修复内容

### 文件: `agentos/webui/static/js/views/ExtensionsView.js`

#### 1. 卸载弹窗 (uninstallExtension 方法)

**修改前**:
```javascript
const modal = document.createElement('div');
modal.className = 'modal-overlay';
modal.innerHTML = `
    <div class="modal-content" style="max-width: 500px;">
        ...
    </div>
`;
```

**修改后**:
```javascript
const modal = document.createElement('div');
modal.className = 'modal active';
modal.innerHTML = `
    <div class="modal-overlay"></div>
    <div class="modal-content" style="max-width: 500px;">
        ...
    </div>
`;
```

#### 2. 配置弹窗 (showExtensionConfig 方法)

**修改前**:
```javascript
const modal = document.createElement('div');
modal.className = 'modal-overlay';
modal.innerHTML = `
    <div class="modal-content" style="max-width: 600px;">
        ...
    </div>
`;
```

**修改后**:
```javascript
const modal = document.createElement('div');
modal.className = 'modal active';
modal.innerHTML = `
    <div class="modal-overlay"></div>
    <div class="modal-content" style="max-width: 600px;">
        ...
    </div>
`;
```

#### 3. 背景点击关闭逻辑

**修改前**:
```javascript
modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
});
```

**修改后**:
```javascript
modal.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal();
    }
});
```

## 效果对比

### 修复前 ❌
- 弹窗出现在左上角
- 背景遮罩不完整
- 点击背景无法关闭

### 修复后 ✅
- 弹窗全屏居中显示
- 半透明背景遮罩覆盖整个屏幕
- 点击背景可以关闭弹窗

## 验证步骤

1. 刷新浏览器页面 (Ctrl+F5 / Cmd+Shift+R)
2. 进入 Extensions 页面
3. 点击任意 Extension 的 "Settings" 按钮 → 应该全屏居中显示
4. 点击任意 Extension 的 "Uninstall" 按钮 → 应该全屏居中显示
5. 点击背景遮罩 → 应该关闭弹窗

## 技术说明

项目中其他弹窗(上传、安装等)都使用了正确的结构，只有这两个弹窗使用了错误的结构。

此次修复统一了所有弹窗的实现方式，确保一致的用户体验。

## 相关文件

- `agentos/webui/static/js/views/ExtensionsView.js` - 弹窗逻辑
- `agentos/webui/static/css/modal-unified.css` - Modal 样式定义(如果存在)

## 总结

✅ 修复了 Uninstall 弹窗居中问题
✅ 修复了 Configure 弹窗居中问题
✅ 统一了背景点击关闭逻辑
✅ 与其他弹窗保持一致的结构

修复完成后需要硬刷新浏览器以清除缓存的 JavaScript 文件。
