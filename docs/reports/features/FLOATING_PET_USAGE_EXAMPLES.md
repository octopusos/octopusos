# FloatingPet 使用示例

本文档提供 FloatingPet 组件的各种使用示例和最佳实践。

---

## 基础使用

### 默认配置
```javascript
// 在 index.html 中已自动初始化
window.floatingPet = new FloatingPet({
    petType: 'default',           // 🤖
    enableShortcuts: true,
    initialPosition: 'bottom-right',
    dragThreshold: 5,
    snapToEdge: true
});
```

---

## 自定义配置

### 更换宠物形象
```javascript
// 猫咪主题 🐱
window.floatingPet = new FloatingPet({
    petType: 'cat',
    // ... 其他配置
});

// 狐狸主题 🦊
window.floatingPet = new FloatingPet({
    petType: 'fox',
    // ... 其他配置
});
```

### 调整初始位置
```javascript
// 左上角
window.floatingPet = new FloatingPet({
    initialPosition: 'top-left',
    // ... 其他配置
});

// 右上角
window.floatingPet = new FloatingPet({
    initialPosition: 'top-right',
    // ... 其他配置
});

// 左下角
window.floatingPet = new FloatingPet({
    initialPosition: 'bottom-left',
    // ... 其他配置
});
```

### 调整拖拽灵敏度
```javascript
// 更容易触发拖拽 (轻微移动即拖拽)
window.floatingPet = new FloatingPet({
    dragThreshold: 3,
    // ... 其他配置
});

// 更不容易触发拖拽 (移动较多才拖拽,适合触摸屏)
window.floatingPet = new FloatingPet({
    dragThreshold: 10,
    // ... 其他配置
});
```

### 禁用吸边
```javascript
// FAB 不会自动吸边,停留在松手位置
window.floatingPet = new FloatingPet({
    snapToEdge: false,
    // ... 其他配置
});
```

### 调整吸边距离
```javascript
// FAB 距离边缘更近
window.floatingPet = new FloatingPet({
    snapOffset: 10,
    // ... 其他配置
});

// FAB 距离边缘更远
window.floatingPet = new FloatingPet({
    snapOffset: 40,
    // ... 其他配置
});
```

### 禁用快捷入口
```javascript
// 只保留宠物动画,不显示快捷按钮
window.floatingPet = new FloatingPet({
    enableShortcuts: false,
    // ... 其他配置
});
```

---

## 编程式控制

### 手动控制面板
```javascript
// 打开面板
window.floatingPet.openPanel();

// 关闭面板
window.floatingPet.closePanel();

// 切换面板状态
window.floatingPet.togglePanel();
```

### 查询组件状态
```javascript
// 获取当前状态
const state = window.floatingPet.state;

console.log('是否正在拖拽:', state.isDragging);
console.log('面板是否打开:', state.isPanelOpen);
console.log('FAB 位置:', state.fabPosition);
console.log('当前吸边方向:', state.currentEdge);
```

### 清除保存的位置
```javascript
// 方式 1: 直接删除
localStorage.removeItem('agentos_floating_pet_position');
location.reload();

// 方式 2: 通过组件方法
window.floatingPet.setDefaultPosition();
window.floatingPet.savePosition();
```

### 销毁组件
```javascript
// 完全移除 FloatingPet
window.floatingPet.destroy();
window.floatingPet = null;
```

---

## 事件监听

### 监听面板状态变化
```javascript
// 扩展组件,添加自定义事件监听
const originalOpenPanel = window.floatingPet.openPanel.bind(window.floatingPet);
const originalClosePanel = window.floatingPet.closePanel.bind(window.floatingPet);

window.floatingPet.openPanel = function() {
    console.log('面板打开');
    // 自定义逻辑
    originalOpenPanel();
};

window.floatingPet.closePanel = function() {
    console.log('面板关闭');
    // 自定义逻辑
    originalClosePanel();
};
```

### 监听拖拽事件
```javascript
// 监听拖拽开始
document.addEventListener('pointerdown', (e) => {
    if (e.target.closest('.floating-pet-fab')) {
        console.log('FAB 按钮被按下');
    }
});

// 监听拖拽结束
document.addEventListener('pointerup', (e) => {
    if (window.floatingPet.state.isDragging) {
        console.log('拖拽结束,新位置:', window.floatingPet.state.fabPosition);
    }
});
```

---

## 样式自定义

### 修改 FAB 颜色
```css
/* 在自定义 CSS 文件中 */
.floating-pet-fab {
    background: linear-gradient(135deg, #FF6B6B 0%, #EE5A6F 100%) !important;
}

.floating-pet-fab:hover {
    background: linear-gradient(135deg, #EE5A6F 0%, #C44569 100%) !important;
}
```

### 修改面板样式
```css
.floating-pet-panel {
    border-radius: 24px !important;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3) !important;
}

.floating-pet-panel-left {
    background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%) !important;
}
```

### 修改宠物动画速度
```css
.pet-avatar.pet-animation-idle {
    animation: pet-idle 3s ease-in-out infinite !important; /* 从 2s 改为 3s */
}

.pet-avatar.pet-animation-hover {
    animation: pet-hover 0.8s ease-in-out infinite !important; /* 从 1.2s 改为 0.8s */
}
```

### 修改 FAB 大小
```css
:root {
    --pet-fab-size: 72px !important; /* 从 64px 改为 72px */
}
```

---

## 响应式调整

### 移动端专属配置
```javascript
// 根据屏幕宽度动态调整
const isMobile = window.innerWidth < 768;

window.floatingPet = new FloatingPet({
    dragThreshold: isMobile ? 10 : 5,  // 移动端阈值更大
    snapOffset: isMobile ? 10 : 20,    // 移动端更靠近边缘
    // ... 其他配置
});
```

### 平板专属配置
```javascript
const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;

if (isTablet) {
    // 平板端自定义配置
    window.floatingPet = new FloatingPet({
        initialPosition: 'top-right',
        // ... 其他配置
    });
}
```

---

## 集成示例

### 与路由集成
```javascript
// 监听路由变化,自动打开相应快捷入口
window.addEventListener('hashchange', () => {
    const hash = location.hash;

    if (hash === '#/tasks') {
        window.floatingPet.openPanel();
    }
});
```

### 与通知系统集成
```javascript
// 任务创建成功后显示通知
const originalSubmitTask = window.floatingPet.submitTask.bind(window.floatingPet);

window.floatingPet.submitTask = async function() {
    const result = await originalSubmitTask();

    if (result) {
        // 显示自定义通知
        showCustomNotification('任务创建成功!');
    }
};
```

### 与分析系统集成
```javascript
// 记录用户交互
const trackEvent = (action) => {
    console.log('Analytics:', action);
    // 发送到分析服务器
};

// 监听快捷入口点击
document.addEventListener('click', (e) => {
    const shortcutBtn = e.target.closest('.pet-shortcut-btn');
    if (shortcutBtn) {
        const action = shortcutBtn.dataset.action;
        trackEvent(`FloatingPet: ${action} clicked`);
    }
});
```

---

## 高级用法

### 动态切换宠物形象
```javascript
// 定义切换函数
function changePet(type) {
    // 销毁当前实例
    window.floatingPet.destroy();

    // 创建新实例
    window.floatingPet = new FloatingPet({
        petType: type,
        enableShortcuts: true,
        initialPosition: 'bottom-right',
    });
}

// 使用
changePet('cat');  // 切换为猫咪
changePet('fox');  // 切换为狐狸
```

### 根据时间切换主题
```javascript
// 白天使用默认主题,晚上使用暗色主题
const hour = new Date().getHours();
const isDarkTime = hour >= 18 || hour < 6;

if (isDarkTime) {
    // 添加暗色主题 CSS
    document.documentElement.classList.add('dark-theme');
}
```

### 添加自定义快捷入口
```javascript
// 修改面板 HTML,添加自定义按钮
const customButton = `
    <button class="pet-shortcut-btn" data-action="custom">
        <div class="pet-shortcut-icon">🚀</div>
        <div class="pet-shortcut-content">
            <div class="pet-shortcut-title">Custom Action</div>
            <div class="pet-shortcut-desc">Do something cool</div>
        </div>
    </button>
`;

// 在面板渲染后添加
const shortcuts = document.querySelector('.pet-shortcuts');
shortcuts.insertAdjacentHTML('beforeend', customButton);

// 绑定事件
document.querySelector('[data-action="custom"]').addEventListener('click', () => {
    console.log('自定义操作被触发!');
    // 执行自定义逻辑
});
```

---

## 性能优化

### 懒加载组件
```javascript
// 页面加载完成后延迟初始化
window.addEventListener('load', () => {
    setTimeout(() => {
        window.floatingPet = new FloatingPet({
            petType: 'default',
            enableShortcuts: true,
            initialPosition: 'bottom-right',
        });
    }, 2000); // 延迟 2 秒
});
```

### 条件加载
```javascript
// 只在桌面端加载
if (window.innerWidth >= 768) {
    window.floatingPet = new FloatingPet({
        petType: 'default',
        enableShortcuts: true,
        initialPosition: 'bottom-right',
    });
}
```

---

## 调试技巧

### 启用详细日志
```javascript
// 保存原始方法
const methods = ['openPanel', 'closePanel', 'handlePointerDown', 'handlePointerMove', 'handlePointerUp'];

methods.forEach(method => {
    const original = window.floatingPet[method].bind(window.floatingPet);
    window.floatingPet[method] = function(...args) {
        console.log(`[FloatingPet] ${method} called`, args);
        return original(...args);
    };
});
```

### 查看性能指标
```javascript
// 测量初始化时间
console.time('FloatingPet Init');
window.floatingPet = new FloatingPet({
    petType: 'default',
    enableShortcuts: true,
    initialPosition: 'bottom-right',
});
console.timeEnd('FloatingPet Init');

// 测量内存占用
console.log('Memory:', performance.memory);
```

### 模拟不同设备
```javascript
// 在开发者工具中调整视口大小
window.resizeTo(375, 667);  // iPhone SE
window.resizeTo(768, 1024); // iPad
window.resizeTo(1920, 1080); // Desktop
```

---

## 常见问题解决

### Q: FAB 按钮被其他元素遮挡?
```css
/* 增加 z-index */
.floating-pet-fab {
    z-index: 99999 !important;
}
```

### Q: 拖拽在某些元素上不工作?
```css
/* 确保元素不阻止 pointer events */
.some-element {
    pointer-events: none;
}
```

### Q: 动画卡顿?
```css
/* 强制 GPU 加速 */
.floating-pet-fab,
.floating-pet-panel {
    transform: translateZ(0);
    will-change: transform;
}
```

---

## 最佳实践

### ✅ 推荐做法
1. 使用默认配置,除非有特殊需求
2. 不要修改核心代码,通过配置选项自定义
3. 使用编程式控制而非直接操作 DOM
4. 定期清理不需要的 localStorage 数据
5. 在生产环境中使用压缩版本

### ❌ 避免做法
1. 不要同时创建多个 FloatingPet 实例
2. 不要频繁调用 destroy/init
3. 不要在拖拽过程中修改配置
4. 不要覆盖核心 CSS 变量
5. 不要在低配设备上启用复杂动画

---

## 更多资源

- **完整文档**: `FLOATING_PET_DELIVERY.md`
- **快速开始**: `FLOATING_PET_QUICKSTART.md`
- **实施总结**: `FLOATING_PET_IMPLEMENTATION_SUMMARY.md`
- **交付清单**: `FLOATING_PET_DELIVERABLES_CHECKLIST.md`

---

**祝你使用愉快! 🤖✨**
