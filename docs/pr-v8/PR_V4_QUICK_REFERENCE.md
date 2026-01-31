# PR-V4: Pipeline Visualization Quick Reference

快速参考指南，用于开发、调试和扩展 Pipeline Visualization。

---

## 快速启动

### 1. 访问演示页面
```bash
# 启动 WebUI
python -m agentos.webui.app

# 打开演示页面
open http://localhost:8000/demo_pipeline_view.html
```

### 2. 在 WebUI 中查看真实任务
```bash
# 访问 WebUI
open http://localhost:8000

# 点击侧边栏 "Pipeline"
# 输入 task_id
# 或访问 URL: http://localhost:8000/#pipeline?task_id=xxx
```

---

## 组件 API

### StageBar
```javascript
// 创建
const stageBar = new StageBar(containerElement);

// 激活阶段
stageBar.activateStage('executing');

// 完成阶段
stageBar.completeStage('planning');

// 失败阶段
stageBar.failStage('verifying');

// 重置
stageBar.reset();

// 查询
stageBar.getCurrentStage();        // 返回 'executing'
stageBar.isCompleted('planning');  // 返回 true/false
```

---

### WorkItemCard
```javascript
// 创建
const card = new WorkItemCard('span_123', {
    work_item_id: 'WI-001',
    status: 'dispatched',
    payload: { description: 'Process data' }
});

// 获取 DOM 元素
const element = card.getElement();
container.appendChild(element);

// 更新状态
card.markDispatched();
card.markRunning();
card.markDone({ result: 'success' });
card.markFailed('Connection timeout');

// 更新进度（仅 running 状态）
card.updateProgress(50); // 0-100

// 销毁
card.destroy();
```

---

### MergeNode
```javascript
// 创建
const mergeNode = new MergeNode(containerElement, {
    totalItems: 3
});

// 更新进度
mergeNode.updateProgress(2, 3); // 2/3 完成

// 显示/隐藏
mergeNode.show();
mergeNode.hide();

// 重置
mergeNode.reset();
```

---

### BranchArrow
```javascript
// 创建（需要 SVG 容器）
const arrow = new BranchArrow(svgElement, {
    from: 'verifying',
    to: 'planning',
    reason: 'Gate failed: tests not passing'
});

// 销毁
arrow.destroy();
```

---

### PipelineView
```javascript
// 创建
const pipelineView = new PipelineView(containerElement, 'task_abc123');

// 手动触发事件（用于测试）
pipelineView.handleEvent({
    event_id: 1,
    task_id: 'task_abc123',
    event_type: 'phase_enter',
    phase: 'executing',
    actor: 'runner',
    span_id: 'span_root',
    seq: 1,
    payload: {},
    created_at: new Date().toISOString()
});

// 刷新
pipelineView.refresh();

// 重置
pipelineView.reset();

// 销毁
pipelineView.destroy();
```

---

## 事件类型速查表

### Phase Events
| Event Type | Phase | 触发时机 | 视觉效果 |
|-----------|-------|---------|---------|
| `phase_enter` | planning | 进入 planning 阶段 | 激活 planning 阶段 |
| `phase_exit` | planning | 退出 planning 阶段 | 完成 planning 阶段 |
| `phase_enter` | executing | 进入 executing 阶段 | 激活 executing 阶段 |
| `phase_exit` | executing | 退出 executing 阶段 | 完成 executing 阶段 |
| `phase_enter` | verifying | 进入 verifying 阶段 | 激活 verifying 阶段 |
| `phase_exit` | verifying | 退出 verifying 阶段 | 完成 verifying 阶段 |

### Work Item Events
| Event Type | 触发时机 | 视觉效果 |
|-----------|---------|---------|
| `work_item_dispatched` | 工位派发 | 创建卡片（黄色边框） |
| `work_item_picked` | 工位被领取 | 卡片变蓝 + 显示进度条 |
| `work_item_done` | 工位完成 | 卡片变绿 + 更新汇总节点 |
| `work_item_failed` | 工位失败 | 卡片变红 + 显示错误 |

### Gate Events
| Event Type | Payload | 视觉效果 |
|-----------|---------|---------|
| `gate_result` | `{ passed: true }` | 无特殊效果 |
| `gate_result` | `{ passed: false, reason: '...' }` | 显示回流箭头 + 重置 planning |

### Task Events
| Event Type | 触发时机 | 视觉效果 |
|-----------|---------|---------|
| `task_completed` | 任务成功完成 | 激活 + 完成 done 阶段 |
| `task_failed` | 任务失败 | 当前阶段标记为 failed |

---

## CSS 类名速查表

### Stage Bar
```css
/* 阶段状态 */
.stage.pending      /* 待执行（灰色） */
.stage.active       /* 执行中（蓝色 + 流动动画） */
.stage.completed    /* 已完成（绿色 + ✓） */
.stage.failed       /* 失败（红色 + ✗） */

/* 阶段元素 */
.stage-indicator    /* 圆形指示器 */
.stage-label        /* 阶段标签 */
.stage-connector    /* 连接线 */
```

### Work Item Card
```css
/* 卡片状态 */
.work-item-card.dispatched  /* 已派发（黄色边框） */
.work-item-card.running     /* 运行中（蓝色边框 + 进度条） */
.work-item-card.done        /* 完成（绿色边框） */
.work-item-card.failed      /* 失败（红色边框） */

/* 卡片元素 */
.work-item-header          /* 顶部（ID + 状态徽章） */
.work-item-id              /* 工位 ID */
.work-item-status-badge    /* 状态徽章 */
.work-item-body            /* 内容区 */
.work-item-progress        /* 进度条容器 */
.work-item-progress-bar    /* 进度条 */
```

### Merge Node
```css
.merge-node        /* 汇总节点容器 */
.merge-icon        /* 图标（⚡） */
.merge-label       /* 标签 */
.merge-stats       /* 统计（3/3） */
```

### Branch Arrow
```css
.branch-arrow       /* SVG 箭头路径 */
.branch-arrow-head  /* 箭头头部 */
.branch-label       /* 文字标签 */
```

---

## 颜色编码

### 状态颜色
- 🟡 **Dispatched**: `#fbbf24` (黄色)
- 🔵 **Running**: `#3b82f6` (蓝色)
- 🟢 **Done**: `#10b981` (绿色)
- 🔴 **Failed**: `#ef4444` (红色)
- ⚪ **Pending**: `#e2e8f0` (灰色)

### 主题色
- **Primary**: `#3b82f6` (蓝色)
- **Success**: `#10b981` (绿色)
- **Danger**: `#ef4444` (红色)
- **Warning**: `#fbbf24` (黄色)
- **Neutral**: `#64748b` (灰蓝)

---

## 动画速查表

### CSS Animations
```css
/* 流动动画（连接线、进度条） */
@keyframes flow-right {
    /* 2s linear infinite */
}

/* 脉冲光晕（active 阶段） */
@keyframes pulse-glow {
    /* 2s ease-in-out infinite */
}

/* 盖章效果（completed 阶段） */
@keyframes stamp {
    /* 0.5s ease-out */
}

/* 闪烁效果（进度条） */
@keyframes shimmer {
    /* 2s linear infinite */
}

/* 弹跳箭头（汇总节点） */
@keyframes bounce-down {
    /* 1.5s ease-in-out infinite */
}

/* 虚线流动（回流箭头） */
@keyframes dash-flow {
    /* 2s linear infinite */
}

/* 淡入透明度（event feed） */
@keyframes pulse-opacity {
    /* 1.5s ease-in-out infinite */
}

/* 右侧滑入（event feed item） */
@keyframes slide-in-right {
    /* 0.3s ease-out */
}
```

---

## 调试技巧

### 1. 查看事件流
```javascript
// 在浏览器控制台
pipelineView.eventFeed  // 查看最近 10 条事件

// 实时监听所有事件
pipelineView.eventStream.options.onEvent = (event) => {
    console.log('[DEBUG]', event.event_type, event);
};
```

### 2. 手动触发事件
```javascript
// 测试单个事件
pipelineView.handleEvent({
    event_type: 'work_item_dispatched',
    span_id: 'test_span_1',
    payload: { work_item_id: 'TEST-001' }
});
```

### 3. 查看组件状态
```javascript
// 查看所有 work_items
console.log(pipelineView.workItems);

// 查看当前阶段
console.log(pipelineView.currentPhase);

// 查看 stageBar 状态
console.log(pipelineView.stageBar.getCurrentStage());
```

### 4. 强制刷新
```javascript
// 重新加载初始状态
await pipelineView.loadInitialState();

// 完全重置
pipelineView.reset();

// 刷新（reset + reload）
pipelineView.refresh();
```

---

## 扩展指南

### 添加新的阶段
1. 修改 `StageBar.STAGES` 数组
2. 添加对应的 CSS 样式
3. 更新 `PipelineView.PHASE_TO_STAGE` 映射

### 添加新的工位状态
1. 在 `WorkItemCard.STATUS` 添加常量
2. 添加对应的 CSS 样式（`.work-item-card.new_status`）
3. 实现 `markNewStatus()` 方法

### 自定义动画
1. 在 `pipeline-view.css` 添加 `@keyframes`
2. 应用到对应的 CSS 类
3. 调整 `animation` 属性（duration, timing-function, iteration-count）

---

## 性能优化

### 1. 大量 work_items (> 20)
```javascript
// 使用虚拟滚动
// TODO: 实现 VirtualScroll 组件
```

### 2. 高频事件更新 (> 100 events/s)
```javascript
// 节流更新
const throttledUpdate = throttle(() => {
    pipelineView.renderEventFeed();
}, 100); // 100ms 节流
```

### 3. 内存泄漏预防
```javascript
// 始终调用 destroy()
if (pipelineView) {
    pipelineView.destroy();
    pipelineView = null;
}
```

---

## 常见问题

### Q: 为什么看不到实时更新？
**A**: 检查 EventStreamService 是否正常连接
```javascript
console.log(pipelineView.eventStream.getState());
// 应该返回 'connected'
```

### Q: 回流箭头没有显示？
**A**: 检查：
1. `gate_result` 事件的 `payload.passed` 是否为 `false`
2. SVG 容器是否存在
3. 阶段元素是否已渲染

### Q: 工位卡片状态不更新？
**A**: 检查：
1. `span_id` 是否匹配
2. 事件是否按正确顺序触发（dispatched → picked → done）

### Q: 动画不流畅？
**A**: 检查：
1. 浏览器 FPS（应该 60 FPS）
2. CSS `animation` 是否使用 GPU 加速属性（transform, opacity）
3. 避免在动画中使用 `width`, `height` 等会触发 reflow 的属性

---

## 测试命令

### E2E 测试
```bash
# 运行所有测试
npx playwright test tests/e2e/test_pipeline_visualization.spec.js

# 运行单个测试
npx playwright test tests/e2e/test_pipeline_visualization.spec.js -g "should load demo page"

# Headed 模式（看到浏览器）
npx playwright test tests/e2e/test_pipeline_visualization.spec.js --headed

# Debug 模式
npx playwright test tests/e2e/test_pipeline_visualization.spec.js --debug
```

---

## 相关文档

- **完整报告**: `PR_V4_PIPELINE_VISUALIZATION_REPORT.md`
- **API 文档**: `docs/api/V31_API_REFERENCE.md`
- **事件模型**: `PR_V1_IMPLEMENTATION_REPORT.md`
- **实时通道**: `PR_V3_IMPLEMENTATION_REPORT.md`

---

## 联系方式

- **Agent**: Frontend Visualization Agent
- **PR**: PR-V4
- **Status**: ✅ Complete
- **Date**: 2026-01-30
