# Dialog 组件浏览器导出修复

## 🔴 关键问题

**问题**: Dialog 组件没有导出到浏览器的 `window` 对象，导致 PhaseSelector 无法使用

**错误信息**:
```
无法显示确认对话框，Dialog 组件未加载
Dialog component not loaded! Cannot show confirmation.
```

## 🔧 根本原因

Dialog.js 原来的导出代码只支持 Node.js 环境：

```javascript
// ❌ 仅在 Node.js 环境下导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Dialog;
}
```

在浏览器中，`module` 是 `undefined`，所以 Dialog 类没有被导出到全局对象。

## ✅ 修复方案

添加浏览器环境的导出：

```javascript
// ✅ 导出到浏览器 window 对象
if (typeof window !== 'undefined') {
    window.Dialog = Dialog;
}

// ✅ 同时保持 Node.js 导出（用于测试）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Dialog;
}
```

## 📝 修改的文件

1. **Dialog.js** - 添加浏览器导出
   - 文件: `agentos/webui/static/js/components/Dialog.js`
   - 行数: 340-348

2. **index.html** - 更新版本号清除缓存
   - 文件: `agentos/webui/templates/index.html`
   - Dialog.js: v=2 → v=3
   - PhaseSelector.js: v=1 → v=2

## 🧪 验证方法

### 方法 1: 自动化测试

```bash
python3 test_phase_selector_fix.py
```

应该看到：
```
✓ Dialog 组件已正确导出到 window.Dialog
```

### 方法 2: 浏览器控制台

1. 启动应用并打开浏览器
2. 打开开发者工具 Console
3. 输入以下命令验证：

```javascript
// 检查 Dialog 是否存在
console.log('Dialog 对象:', window.Dialog);

// 应该输出: class Dialog { ... }
console.log('typeof window.Dialog:', typeof window.Dialog);

// 应该输出: function
console.log('Dialog.alert 存在:', typeof window.Dialog.alert);
console.log('Dialog.confirm 存在:', typeof window.Dialog.confirm);
console.log('Dialog.prompt 存在:', typeof window.Dialog.prompt);

// 快速测试
window.Dialog.alert('测试成功！');
```

### 方法 3: 使用测试页面

打开 `test_dialog_export.html` 在浏览器中测试：

```bash
open test_dialog_export.html
# 或者在浏览器中直接打开该文件
```

点击各个测试按钮验证 Dialog 组件的所有功能。

## ✨ 修复效果

### 修复前

```
[PhaseSelector] 尝试切换阶段...
❌ 无法显示确认对话框，Dialog 组件未加载
```

### 修复后

```
[PhaseSelector] 尝试切换阶段: planning -> execution
✅ 显示 Dialog 确认对话框
✅ 用户点击确认
✅ 阶段已切换至: execution
```

## 📋 测试清单

在浏览器中验证以下功能：

- [ ] 打开浏览器控制台，输入 `window.Dialog`，应该看到 Dialog 类定义
- [ ] 输入 `typeof window.Dialog.alert`，应该返回 `"function"`
- [ ] 输入 `typeof window.Dialog.confirm`，应该返回 `"function"`
- [ ] 输入 `typeof window.Dialog.prompt`，应该返回 `"function"`
- [ ] 在 Chat 页面切换 Phase，应该显示自定义 Dialog 弹窗（不是浏览器原生弹窗）
- [ ] Dialog 弹窗应该有漂亮的样式和动画
- [ ] 点击"取消"应该关闭弹窗
- [ ] 点击"确定"应该执行操作
- [ ] 按 Escape 键应该关闭弹窗

## ⚠️ 重要提示

1. **清除浏览器缓存**: 修复后必须清除浏览器缓存或强制刷新（Cmd/Ctrl + Shift + R）
2. **版本号更新**: 已更新 Dialog.js (v=3) 和 PhaseSelector.js (v=2) 的版本号
3. **其他组件**: Toast 组件已经正确导出到 `window.Toast`，无需修改

## 🎯 影响范围

### 受益的功能

- ✅ Phase 切换确认对话框
- ✅ 所有使用 `window.Dialog` 的组件
- ✅ 未来需要显示对话框的功能

### 不受影响的功能

- ✅ Mode 切换（不需要确认对话框）
- ✅ Toast 提示（已正确导出）
- ✅ 其他现有功能

## 📚 相关文档

- `PHASE_SELECTOR_FIX_REPORT.md` - Phase Selector 完整修复报告
- `PHASE_SELECTOR_FIX_SUMMARY.md` - 快速参考指南
- `test_dialog_export.html` - Dialog 组件交互测试页面

## 🚀 部署说明

1. **清除缓存**: 部署后通知用户清除浏览器缓存
2. **监控**: 通过 Sentry 监控是否还有 "Dialog component not loaded" 错误
3. **回滚**: 如有问题，恢复 Dialog.js 和 index.html 的旧版本即可

## 👨‍💻 开发建议

### 未来创建组件时的最佳实践

```javascript
// 组件定义
class MyComponent {
    // ...
}

// ✅ 推荐: 同时支持浏览器和 Node.js
if (typeof window !== 'undefined') {
    window.MyComponent = MyComponent;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = MyComponent;
}
```

### 检查组件是否已加载

```javascript
// 在使用前检查
if (typeof window.MyComponent === 'undefined') {
    console.error('MyComponent not loaded!');
    // 显示友好错误提示
    return;
}

// 然后安全使用
window.MyComponent.doSomething();
```

## ✅ 修复验证

运行验证脚本确认所有修复都已生效：

```bash
./verify_phase_selector.sh
```

应该看到所有检查都通过 ✓

---

**修复时间**: 2026-01-31
**修复者**: Claude Code
**版本**: AgentOS v0.3.1
**状态**: ✅ 已修复并验证
