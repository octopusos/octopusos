# FloatingPet 拖拽修复自查清单

## ✅ 修复完成检查

### A. 代码结构修复

- [x] **拖拽状态对象** - 创建独立的 `this._drag` 对象
- [x] **拖拽阈值** - 设置 `this._DRAG_THRESHOLD = 6`
- [x] **pointerId 追踪** - `this._drag.pointerId` 记录当前指针
- [x] **moved 标志** - `this._drag.moved` 区分点击和拖拽

### B. 事件监听器修复

- [x] **pointerdown 绑定** - 只在 `this.elements.fabButton` 上绑定
- [x] **pointermove 绑定** - 在 `document` 上，但检查 active 和 pointerId
- [x] **pointerup 绑定** - 在 `document` 上，但检查 active 和 pointerId
- [x] **pointercancel 处理** - 添加 `_onDocPointerCancel` 清理状态
- [x] **click 拦截** - 在捕获阶段拦截 (第三个参数 `true`)
- [x] **保存绑定函数** - `this._boundPointerMove` 等用于清理

### C. 指针事件处理器

- [x] **_onFabPointerDown**
  - [x] 检查 `e.button !== 0`
  - [x] `e.preventDefault()` 和 `e.stopPropagation()`
  - [x] 初始化 `_drag` 状态
  - [x] 立即调用 `setPointerCapture(e.pointerId)`
  - [x] 关闭已打开的面板

- [x] **_onDocPointerMove**
  - [x] 检查 `!this._drag.active` 和 `e.pointerId !== this._drag.pointerId`
  - [x] `e.preventDefault()`
  - [x] 计算移动距离 `Math.hypot(dx, dy)`
  - [x] 检查阈值 `dist < this._DRAG_THRESHOLD`
  - [x] 超过阈值才标记 `moved = true` 和添加 `is-dragging` 类
  - [x] 应用边界约束

- [x] **_onDocPointerUp**
  - [x] 检查 `!this._drag.active` 和 `e.pointerId !== this._drag.pointerId`
  - [x] `e.preventDefault()`
  - [x] 保存 `wasMoved` 标志
  - [x] 清理状态 `_drag.active = false`
  - [x] 移除 `is-dragging` 类
  - [x] 调用 `releasePointerCapture(e.pointerId)`
  - [x] 根据 `wasMoved` 决定吸边或打开面板

- [x] **_onDocPointerCancel**
  - [x] 检查 `!this._drag.active` 和 `e.pointerId !== this._drag.pointerId`
  - [x] 清理状态
  - [x] 调用 `releasePointerCapture(e.pointerId)`

- [x] **_onFabClick**
  - [x] 检查 `this._drag.moved`
  - [x] 如果拖拽过，调用 `e.stopImmediatePropagation()`

### D. CSS 修复

- [x] **user-select** - 添加 `user-select: none`
- [x] **webkit-user-select** - 添加 `-webkit-user-select: none`
- [x] **touch-action** - 添加 `touch-action: none`
- [x] **cursor** - 修改为 `cursor: grab`
- [x] **is-dragging cursor** - 添加 `cursor: grabbing`

### E. 清理与销毁

- [x] **destroy() 方法**
  - [x] 移除 `document` 事件监听器
  - [x] 销毁 Lottie 实例
  - [x] 移除 DOM 元素

### F. Lottie 动画验证

- [x] **Lottie-web 加载** - 在 `index.html` 中已加载
- [x] **JSON 文件存在** - `/static/assets/lottie/pet-cute.json` 存在
- [x] **容器创建** - `#fp-lottie` 容器正确创建
- [x] **初始化逻辑** - `_initLottie()` 方法正确
- [x] **降级方案** - `_fallbackPet()` 静态图标降级

## 🧪 功能测试清单

### 基础拖拽测试

- [ ] **FAB 显示** - 在正确位置显示 (默认右下角)
- [ ] **点击打开** - 点击 FAB 打开面板
- [ ] **点击关闭** - 再次点击 FAB 关闭面板
- [ ] **Lottie 显示** - 面板中 Lottie 动画正确显示
- [ ] **拖拽移动** - 按住 FAB 拖拽，FAB 跟随移动
- [ ] **吸边效果** - 松开后 FAB 吸附到最近的边

### 点击 vs 拖拽分离

- [ ] **轻点识别** - 点击不移动，识别为点击
- [ ] **小幅移动** - 移动小于 6px，识别为点击
- [ ] **大幅移动** - 移动超过 6px，识别为拖拽
- [ ] **拖拽不开面板** - 拖拽后松开，面板不打开

### 边界测试

- [ ] **点击其他区域** - 点击页面其他地方，FAB 不移动
- [ ] **边界约束** - FAB 不会拖出视口边界
- [ ] **多点触控** - 只响应第一个指针
- [ ] **指针取消** - pointercancel 正确清理状态

### 视觉反馈

- [ ] **默认光标** - 鼠标悬停显示 `grab` 光标
- [ ] **拖拽光标** - 拖拽时显示 `grabbing` 光标
- [ ] **拖拽样式** - 拖拽时添加增强阴影
- [ ] **激活样式** - 面板打开时 FAB 背景变深

### 持久化

- [ ] **位置保存** - 拖拽后位置保存到 localStorage
- [ ] **位置加载** - 刷新页面后位置恢复
- [ ] **边缘保存** - 记住吸附的边缘方向

### 响应式

- [ ] **窗口 resize** - 调整窗口大小，FAB 位置正确调整
- [ ] **面板位置** - 面板根据 FAB 位置显示在正确侧
- [ ] **移动端布局** - 移动端面板切换为纵向布局
- [ ] **触摸拖拽** - 触摸拖拽正常工作

## 🐛 Bug 复现验证

### 原始问题 1: Lottie 动画不显示

**测试步骤**:
1. 打开页面
2. 点击 FAB 打开面板
3. 检查左侧动画区域

**预期结果**: ✅ 显示 Lottie 卡通动画
**实际结果**: (待测试)

### 原始问题 2: 点击其它区域也触发拖拽

**测试步骤**:
1. 打开页面
2. 点击页面中央某个位置
3. 移动鼠标

**预期结果**: ✅ FAB 不移动
**实际结果**: (待测试)

### 原始问题 3: 拖拽时闪一下

**测试步骤**:
1. 打开页面
2. 按住 FAB 并拖拽
3. 观察拖拽过程

**预期结果**: ✅ 平滑移动，无闪烁或跳跃
**实际结果**: (待测试)

### 原始问题 4: 拖拽还触发菜单点击

**测试步骤**:
1. 打开页面
2. 按住 FAB 拖拽超过 6px
3. 松开鼠标

**预期结果**: ✅ 面板不打开，FAB 吸边
**实际结果**: (待测试)

## 📊 性能检查

- [ ] **GPU 加速** - 检查 DevTools Performance，确认使用 GPU 合成
- [ ] **重绘范围** - 拖拽时只重绘 FAB 区域
- [ ] **内存泄漏** - 打开/关闭多次，检查内存是否稳定
- [ ] **触摸延迟** - 触摸拖拽无明显延迟 (< 100ms)

## 🔍 代码审查自查

### 事件监听器

```javascript
// ✅ 正确：pointerdown 只在 FAB 上
this.elements.fabButton.addEventListener('pointerdown', this._onFabPointerDown.bind(this));

// 🚫 错误：不要在 document 上监听 pointerdown
// document.addEventListener('pointerdown', ...);

// ✅ 正确：move/up 在 document 上，但检查状态
document.addEventListener('pointermove', this._boundPointerMove);
document.addEventListener('pointerup', this._boundPointerUp);
document.addEventListener('pointercancel', this._boundPointerCancel);
```

### Pointer Move 检查

```javascript
// ✅ 必须的检查
_onDocPointerMove(e) {
    if (!this._drag.active) return;           // 检查 active
    if (e.pointerId !== this._drag.pointerId) return;  // 检查 pointerId
    e.preventDefault();                        // 阻止默认行为

    // ... 拖拽逻辑
}
```

### Pointer Capture

```javascript
// ✅ pointerdown 时立即 capture
this.elements.fabButton.setPointerCapture(e.pointerId);

// ✅ pointerup/pointercancel 时释放
try {
    this.elements.fabButton.releasePointerCapture(e.pointerId);
} catch (err) {
    // 忽略可能的异常
}
```

### 拖拽阈值

```javascript
// ✅ 使用阈值区分点击和拖拽
const dist = Math.hypot(dx, dy);
if (!this._drag.moved && dist < this._DRAG_THRESHOLD) {
    return; // 未超过阈值，不移动
}
```

### Click 拦截

```javascript
// ✅ 在捕获阶段拦截 (第三个参数 true)
this.elements.fabButton.addEventListener('click', this._onFabClick.bind(this), true);

_onFabClick(e) {
    if (this._drag.moved) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation(); // ✅ 彻底阻止
    }
}
```

## 📝 文档检查

- [x] **修复总结** - 创建 `FLOATING_PET_DRAG_FIX_SUMMARY.md`
- [x] **测试清单** - 创建 `FLOATING_PET_DRAG_FIX_CHECKLIST.md`
- [x] **测试页面** - 创建 `test_floating_pet_drag_fix.html`
- [ ] **用户文档** - 更新用户使用文档
- [ ] **API 文档** - 更新 FloatingPet API 文档

## 🚀 部署前检查

- [ ] **本地测试** - 在本地环境测试所有功能
- [ ] **多浏览器测试** - Chrome, Firefox, Safari, Edge
- [ ] **移动设备测试** - iOS Safari, Chrome Android
- [ ] **回归测试** - 确保未破坏现有功能
- [ ] **代码审查** - 团队成员审查代码变更
- [ ] **版本号更新** - 更新 CSS/JS 文件版本号

## 📦 文件清单

### 修改的文件
- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/components/FloatingPet.js`
- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/css/floating-pet.css`

### 新增的文件
- `/Users/pangge/PycharmProjects/AgentOS/test_floating_pet_drag_fix.html`
- `/Users/pangge/PycharmProjects/AgentOS/FLOATING_PET_DRAG_FIX_SUMMARY.md`
- `/Users/pangge/PycharmProjects/AgentOS/FLOATING_PET_DRAG_FIX_CHECKLIST.md`

## ✅ 最终确认

- [x] 所有代码修复已完成
- [x] 所有必需的检查已实现
- [x] CSS 修复已应用
- [x] 清理逻辑已完善
- [x] 文档已创建
- [ ] 测试已通过
- [ ] 准备合并/部署

---

**修复状态**: ✅ 代码修复完成，等待测试验证
**下一步**: 运行 `test_floating_pet_drag_fix.html` 进行功能测试
