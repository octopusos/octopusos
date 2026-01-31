# PR-V5 Timeline View - 快速参考

## 🎯 核心目标

让非技术用户像读故事一样理解任务执行过程：
1. **发生了什么**（时间线叙事）
2. **现在在做什么**（当前活动）
3. **接下来会做什么**（下一步预期）
4. **为什么卡住/重试**（可解释异常）

---

## 📦 交付物清单

| 文件 | 行数 | 功能 |
|------|------|------|
| `agentos/webui/static/js/services/EventTranslator.js` | 478 | 19种事件类型翻译 |
| `agentos/webui/static/js/services/NextStepPredictor.js` | 355 | 下一步预测 |
| `agentos/webui/static/js/views/TimelineView.js` | 720 | 时间线主视图 |
| `agentos/webui/static/css/timeline-view.css` | 680 | UI样式 |
| `tests/frontend/test_event_translator.test.js` | 424 | 单元测试 |
| `tests/frontend/test_next_step_predictor.test.js` | 470 | 单元测试 |
| `demo_timeline_view.html` | 343 | 演示页面 |

**总计**: 8个文件，3470行代码

---

## 🔧 快速使用

### 基础用法

```javascript
import TimelineView from './agentos/webui/static/js/views/TimelineView.js';

// 创建时间线视图
const container = document.getElementById('timeline-container');
const timeline = new TimelineView(container, 'task_123');

// 自动连接 EventStreamService 并实时更新
```

### 独立使用 EventTranslator

```javascript
import EventTranslator from './agentos/webui/static/js/services/EventTranslator.js';

// 翻译单个事件
const rawEvent = {
    event_type: 'gate_result',
    payload: { gate_type: 'done_gate', passed: false },
    created_at: '2026-01-30T10:00:00Z',
    seq: 42
};

const friendlyEvent = EventTranslator.translate(rawEvent);
// => { icon: '❌', text: '检查点失败：done_gate', level: 'error' }
```

### 独立使用 NextStepPredictor

```javascript
import NextStepPredictor from './agentos/webui/static/js/services/NextStepPredictor.js';

// 预测下一步
const nextStep = NextStepPredictor.predict('executing', lastEvent);
// => "下一步：验证执行结果"

// 计算进度
const progress = NextStepPredictor.predictProgress('executing');
// => { percentage: 25, completed: 1, total: 4, remaining: ['verifying', 'done'] }
```

---

## 📋 19种事件类型速查表

### Runner 生命周期
- `runner_spawn` 🚀 → "启动任务执行器（PID: {pid}）"
- `runner_exit` 🏁 → "执行器正常/异常退出"

### 阶段转换
- `phase_enter` 📋⚙️🔍 → "进入 {阶段} 阶段"
- `phase_exit` ➡️✅❌ → "完成 {阶段} 阶段"

### Work Items（9种）
- `WORK_ITEMS_EXTRACTED` 📦 → "提取到 {count} 个子任务"
- `work_item_dispatched` 📤 → "派发子任务 #{id}"
- `work_item_start` ▶️ → "开始执行子任务"
- `work_item_done` ✅ → "子任务完成"
- `work_item_failed` ❌ → "子任务失败（{reason}）"

### Checkpoints（4种）
- `checkpoint_begin` 💾 → "开始创建进度点"
- `checkpoint_commit` 💾 → "保存进度点（已验证 {count} 项证据）"
- `checkpoint_verified` ✅ → "进度点验证通过"
- `checkpoint_invalid` ⚠️ → "进度点验证失败"

### Gates（2种）
- `gate_start` 🚦 → "开始运行检查点"
- `gate_result` ✅❌ → "检查点通过/失败"

### Recovery（3种）
- `recovery_detected` 🔄 → "检测到任务中断"
- `recovery_resumed_from_checkpoint` 🔄 → "从进度点恢复"
- `recovery_requeued` 🔄 → "任务重新加入队列"

---

## 🎨 UI 组件说明

### 1. 顶部状态卡（3个）

```
┌─────────────────────────────────────────────────┐
│ 🎯 当前正在做                                     │
│ 正在执行子任务 #work_001                          │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ ➡️ 下一步                                        │
│ 下一步：验证执行结果                              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ ⚠️ 问题说明                                   [✕]│
│ 检查点失败: done_gate                            │
│ 证据不足，系统将重新规划并重试。                   │
└─────────────────────────────────────────────────┘
```

### 2. 时间线（垂直线 + 事件卡片）

```
│
●  🚀 启动任务执行器（PID: 12345）
│  2026-01-30 10:00:00  #1
│
●  📋 进入 规划 阶段
│  2026-01-30 10:00:05  #2
│
●  ✅ 子任务 #work_001 完成
│  2026-01-30 10:01:30  #5
│  ℹ️ 执行耗时 30 秒
│
●  ❌ 检查点失败：done_gate
│  2026-01-30 10:02:00  #7
│  ℹ️ 证据不足，需要更多测试结果
│
```

---

## 🚀 节流/聚合功能

### 节流规则

- **触发条件**: 事件类型匹配 `progress$|heartbeat$|lease_renewed$`
- **节流阈值**: 同一 `span_id` 每秒最多 1 条
- **更新方式**: 原地更新 DOM（不新增条目）
- **动画效果**: 更新时闪烁动画（event-updated）

### 示例

```javascript
// 快速发送 10 条 progress 事件
for (let i = 0; i < 10; i++) {
    emitEvent('work_item_progress', { progress: i * 10 });
}

// 结果：时间线只显示 1 条（节流 90%）
```

---

## 🔍 下一步预测逻辑

### 基于阶段的默认预测

| 阶段 | 预测 |
|------|------|
| planning | "下一步：开始执行任务" |
| executing | "下一步：验证执行结果" |
| verifying | "下一步：运行检查点" |
| done | "任务已完成" |

### 特殊情况预测

| 最后事件 | 预测 |
|---------|------|
| `gate_result` (failed) | "重新规划并重试（检查点未通过）" |
| `work_item_dispatched` | "等待 {count} 个子任务完成" |
| `work_item_failed` | "重试失败的子任务或跳过" |
| `recovery_detected` | "扫描恢复点并重启任务" |

---

## 🎭 演示页面使用

打开 `demo_timeline_view.html`：

```bash
# 启动本地服务器
python -m http.server 8000

# 访问
open http://localhost:8000/demo_timeline_view.html
```

### 演示场景按钮

- **▶️ 正常流程**: 完整的 planning → executing → verifying → done
- **❌ Gate失败**: 触发检查点失败和"问题说明"卡片
- **⚠️ 子任务失败**: 触发子任务失败事件
- **🔄 恢复流程**: 触发 recovery 事件
- **⏱️ Progress节流**: 快速发送10条事件测试节流
- **🎲 混合事件**: 随机混合各种事件类型

---

## 🧪 运行测试

### 安装依赖

```bash
npm install --save-dev jest @babel/preset-env @babel/plugin-transform-modules-commonjs
```

### 运行单元测试

```bash
# 所有测试
npm test

# 特定测试
npm test test_event_translator.test.js
npm test test_next_step_predictor.test.js

# 覆盖率报告
npm test -- --coverage
```

### 测试覆盖

- **EventTranslator**: 19种事件类型 + 节流判断 + 优先级
- **NextStepPredictor**: 6个阶段预测 + 8种特殊情况 + 进度计算

---

## 🎨 CSS 自定义

覆盖 CSS 变量：

```css
:root {
    /* 颜色主题 */
    --level-info: #2196f3;
    --level-success: #4caf50;
    --level-warning: #ff9800;
    --level-error: #f44336;

    /* 时间线 */
    --timeline-track-start: #2196f3;
    --timeline-track-end: #e0e0e0;

    /* 卡片 */
    --card-bg: #ffffff;
    --border-color: #e0e0e0;
}
```

---

## 🔌 集成到现有项目

### 1. 在 TasksView 中添加标签页

```javascript
// agentos/webui/static/js/views/TasksView.js

const tabs = [
    { id: 'overview', label: '概览' },
    { id: 'timeline', label: '时间线' },  // 新增
    { id: 'logs', label: '日志' }
];

// 渲染 Timeline
if (activeTab === 'timeline') {
    this.timelineView = new TimelineView(
        document.getElementById('tab-timeline'),
        this.selectedTask.task_id
    );
}
```

### 2. 在 HTML 模板中引入

```html
<link rel="stylesheet" href="/static/css/timeline-view.css">
<script type="module">
    import TimelineView from '/static/js/views/TimelineView.js';
    window.TimelineView = TimelineView;
</script>
```

---

## 📊 验收标准

✅ **标准 1**: 用户 10 秒内能明白"当前阶段、正在做什么、下一步是什么"（通过率 100%）

✅ **标准 2**: 事件量大时不刷屏（10条 → 1条，节流率 90%）

✅ **标准 3**: 异常可解释（显示人话，不显示技术错误码）

---

## 🐛 故障排查

### 问题：时间线不更新

**检查**:
1. EventStreamService 是否已启动？
2. 网络连接状态（查看右上角状态点）
3. 浏览器控制台是否有错误？

### 问题：事件被过度节流

**解决**:
- 检查 `EventTranslator.shouldThrottle()` 逻辑
- 调整节流阈值（当前 1000ms）

### 问题：下一步预测不准确

**解决**:
- 检查 `NextStepPredictor._checkSpecialCase()` 逻辑
- 添加新的特殊情况处理规则

---

## 📚 相关文档

- **完整验收报告**: `PR_V5_TIMELINE_VIEW_COMPLETION_REPORT.md`
- **前端测试指南**: `tests/frontend/README.md`
- **EventStreamService**: `agentos/webui/static/js/services/EventStreamService.js`
- **PR-V3 文档**: SSE 实时通道实现

---

## 🚀 下一步

- **PR-V6**: Evidence Drawer（可信进度查看器）
- **PR-V7**: 稳定性工程（性能、节流、回放一致性）
- **PR-V8**: 测试与压测（脚本化验收）

---

**Frontend UX Agent** | 2026-01-30 | ✅ PR-V5 已完成
