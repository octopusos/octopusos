# 快速测试指南 - Phase Selector 修复

## ⚡ 30 秒快速测试

### 1. 验证修复 (5 秒)

```bash
./verify_phase_selector.sh
```

看到所有 ✓ 表示修复成功。

### 2. 启动应用 (5 秒)

```bash
python3 -m agentos.webui.app
```

### 3. 浏览器测试 (20 秒)

1. 打开 http://localhost:5000
2. 按 F12 打开开发者工具
3. 在 Console 输入: `window.Dialog`
   - ✅ 应该看到: `class Dialog { ... }`
   - ❌ 如果看到: `undefined`，说明修复未生效，需要清除缓存

4. 进入 Chat 页面
5. 点击顶部 Phase 切换按钮 (Planning → Execution)
   - ✅ 应该看到: 漂亮的自定义弹窗（中文）
   - ❌ 不应该看到: 浏览器原生灰色弹窗

## 🎯 成功标志

**Console 输出**:
```javascript
> window.Dialog
< class Dialog { alert: function, confirm: function, prompt: function }

> typeof window.Dialog.confirm
< "function"
```

**Phase 切换弹窗**:
- ✅ 标题: "确认阶段变更"
- ✅ 内容: "切换到执行阶段？"
- ✅ 按钮: "切换到执行" 和 "取消"
- ✅ 样式: 圆角、阴影、半透明背景
- ✅ 动画: 淡入效果

**Console 日志**:
```
[PhaseSelector] 尝试切换阶段: planning -> execution, session: main
[PhaseSelector] 发送 API 请求: {...}
[PhaseSelector] API 响应状态: 200 OK
[PhaseSelector] 阶段更新成功
```

## ❌ 如果还有问题

### 问题 1: 仍显示 "Dialog 组件未加载"

**解决方案**: 清除浏览器缓存
```
Cmd + Shift + R (Mac)
Ctrl + Shift + R (Windows/Linux)
```

或者在开发者工具中:
1. 打开 Network 标签
2. 勾选 "Disable cache"
3. 刷新页面

### 问题 2: `window.Dialog` 仍是 `undefined`

**检查步骤**:
```bash
# 1. 确认 Dialog.js 包含浏览器导出
grep "window.Dialog" agentos/webui/static/js/components/Dialog.js

# 应该看到: if (typeof window !== 'undefined') {
#          window.Dialog = Dialog;
```

```bash
# 2. 确认版本号已更新
grep "Dialog.js?v=" agentos/webui/templates/index.html

# 应该看到: Dialog.js?v=3
```

```bash
# 3. 重启应用
# 按 Ctrl+C 停止应用
python3 -m agentos.webui.app
```

### 问题 3: 仍显示原生浏览器弹窗

**检查 PhaseSelector.js**:
```bash
grep "return confirm(" agentos/webui/static/js/components/PhaseSelector.js
```

应该**没有**任何输出（fallback 已移除）。

## 🧪 高级测试（可选）

### 测试 Dialog 的所有功能

在 Console 中运行：

```javascript
// 测试 alert
await window.Dialog.alert('这是测试消息', {
    title: '测试 Alert',
    confirmText: '好的'
});

// 测试 confirm
const result = await window.Dialog.confirm('你确定吗？', {
    title: '测试 Confirm',
    confirmText: '确定',
    cancelText: '取消'
});
console.log('用户选择:', result);  // true 或 false

// 测试 prompt
const name = await window.Dialog.prompt('请输入你的名字:', {
    title: '测试 Prompt',
    defaultValue: '',
    placeholder: '请输入...'
});
console.log('用户输入:', name);
```

### 使用独立测试页面

```bash
open test_dialog_export.html
# 或在浏览器中打开该文件
```

点击各个测试按钮验证所有功能。

## 📋 完整测试清单

复制以下清单，逐项验证：

```
测试清单（复制到新文件记录测试结果）
========================================

基础验证
[ ] 运行 ./verify_phase_selector.sh - 所有检查通过
[ ] 应用启动无错误
[ ] 浏览器访问 http://localhost:5000 正常

Dialog 组件验证
[ ] Console: window.Dialog 存在
[ ] Console: typeof window.Dialog.alert === "function"
[ ] Console: typeof window.Dialog.confirm === "function"
[ ] Console: typeof window.Dialog.prompt === "function"

Phase 切换功能验证
[ ] 点击 Phase 按钮，显示自定义 Dialog（非原生）
[ ] Dialog 标题为中文："确认阶段变更"
[ ] Dialog 按钮为中文："切换到执行" "取消"
[ ] Dialog 样式正确（圆角、阴影、动画）
[ ] 点击"取消"可关闭弹窗
[ ] 点击"切换到执行"成功切换 Phase
[ ] Console 显示 [PhaseSelector] 日志
[ ] 无 "Dialog component not loaded" 错误

回归测试
[ ] Mode 切换功能正常
[ ] Chat 消息发送正常
[ ] Session 创建/删除正常
[ ] 无其他功能受影响

测试完成
[ ] 所有测试通过
[ ] 准备部署到生产环境

测试人: _______________
测试日期: _______________
```

## 📚 详细文档

需要更多信息？查看：

- `PHASE_DIALOG_COMPLETE_FIX.md` - **完整修复总结**（推荐先看）
- `DIALOG_EXPORT_FIX.md` - Dialog 导出问题详解
- `PHASE_SELECTOR_FIX_REPORT.md` - 详细修复报告
- `PHASE_SELECTOR_CHECKLIST.md` - 完整验证清单

## ✅ 测试通过？

恭喜！修复成功。现在可以：

1. 正常使用 Phase 切换功能
2. 将修复部署到生产环境
3. 关闭相关的 issue/ticket

## 🆘 测试失败？

如果测试失败，提供以下信息寻求帮助：

1. 运行 `./verify_phase_selector.sh` 的输出
2. 浏览器 Console 的错误信息
3. `window.Dialog` 的值（在 Console 中查看）
4. Network 标签中 Dialog.js 的加载状态
5. 使用的浏览器和版本

---

**快速测试指南** | AgentOS v0.3.1 | 2026-01-31
