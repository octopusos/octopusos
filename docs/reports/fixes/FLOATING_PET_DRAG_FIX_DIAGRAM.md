# FloatingPet 拖拽修复架构图

## 事件流程图

```
用户交互流程
═══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│                        用户操作                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  点击/触摸 FAB   │
                    └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  pointerdown 事件 (只在 FAB 上监听)                         │
│  ▸ _onFabPointerDown(e)                                     │
│    • 检查 button === 0                                       │
│    • 初始化 _drag 状态                                       │
│    • setPointerCapture(e.pointerId) ← 锁定指针              │
│    • 记录起始位置                                            │
│    • 关闭面板                                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  pointermove 事件 (document 监听，但有检查)                  │
│  ▸ _onDocPointerMove(e)                                     │
│    • if (!_drag.active) return ← 检查 1                     │
│    • if (e.pointerId !== _drag.pointerId) return ← 检查 2   │
│    • 计算移动距离 dist = Math.hypot(dx, dy)                 │
│    • if (dist < 6px && !moved) return ← 阈值检查            │
│    • 标记 moved = true                                       │
│    • 添加 is-dragging 类                                     │
│    • 更新 FAB 位置                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────┴────────────────────┐
         │                                          │
         ▼                                          ▼
┌──────────────────┐                      ┌──────────────────┐
│  pointerup 事件  │                      │ pointercancel    │
│  (document 监听) │                      │  (document 监听) │
└──────────────────┘                      └──────────────────┘
         │                                          │
         ▼                                          ▼
┌─────────────────────────────────────────────────────────────┐
│  清理与决策                                                  │
│  ▸ _onDocPointerUp(e) / _onDocPointerCancel(e)             │
│    • if (!_drag.active) return                              │
│    • if (e.pointerId !== _drag.pointerId) return            │
│    • 清理状态 _drag.active = false                          │
│    • releasePointerCapture(e.pointerId) ← 释放指针          │
│    • 移除 is-dragging 类                                     │
│    •                                                         │
│    ┌─── if (moved) ────┐        ┌─── else ────┐            │
│    │  吸边动画         │        │  打开面板   │            │
│    │  保存位置         │        │  togglePanel │            │
│    └──────────────────┘        └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  click 事件 (捕获阶段拦截)                                   │
│  ▸ _onFabClick(e, useCapture=true)                          │
│    • if (_drag.moved) {                                     │
│        e.preventDefault()                                    │
│        e.stopPropagation()                                   │
│        e.stopImmediatePropagation() ← 彻底阻止              │
│      }                                                       │
└─────────────────────────────────────────────────────────────┘
```

## 状态机图

```
拖拽状态机
═══════════════════════════════════════════════════════════════

                    ┌──────────┐
                    │  IDLE    │  (初始状态)
                    └──────────┘
                         │
                         │ pointerdown on FAB
                         │ (_drag.active = true)
                         ▼
                    ┌──────────┐
                    │ PRESSED  │  (按下，未移动)
                    └──────────┘
                         │
                         │ pointermove (dist < 6px)
                         │ (保持 moved = false)
                         ▼
                    ┌──────────┐
                    │ PRESSED  │  (仍在阈值内)
                    └──────────┘
                         │
            ┌────────────┼────────────┐
            │                         │
            │ pointermove             │ pointerup
            │ (dist >= 6px)           │ (moved = false)
            │ (moved = true)          │
            ▼                         ▼
      ┌──────────┐              ┌──────────┐
      │ DRAGGING │              │  CLICK   │ → togglePanel()
      └──────────┘              └──────────┘
            │                         │
            │ pointerup               │
            │ (moved = true)          │
            ▼                         ▼
      ┌──────────┐              ┌──────────┐
      │   SNAP   │ → 吸边动画   │   IDLE   │
      └──────────┘              └──────────┘
            │
            │ 动画完成
            ▼
      ┌──────────┐
      │   IDLE   │
      └──────────┘

注意: pointercancel 在任何状态都会立即回到 IDLE
```

## Pointer Capture 机制

```
Pointer Capture 流程
═══════════════════════════════════════════════════════════════

用户在 FAB 上按下
      │
      ▼
┌─────────────────────────────────────┐
│  setPointerCapture(pointerId)       │
│  ▸ 锁定指针到 FAB 元素              │
│  ▸ 即使指针移出 FAB，事件仍发送到 FAB│
└─────────────────────────────────────┘
      │
      ▼
  ┌────────────────────────────────┐
  │  指针被 FAB "捕获"             │
  │  • 所有 pointer 事件 → FAB    │
  │  • 其他元素无法接收            │
  │  • 防止事件泄漏                │
  └────────────────────────────────┘
      │
      │ (用户拖拽，指针移动)
      ▼
  ┌────────────────────────────────┐
  │  pointermove 事件持续触发      │
  │  ▸ 目标: FAB (被捕获)          │
  │  ▸ 即使指针在 document 上方    │
  └────────────────────────────────┘
      │
      ▼
用户松开 / 取消
      │
      ▼
┌─────────────────────────────────────┐
│  releasePointerCapture(pointerId)   │
│  ▸ 释放指针锁定                     │
│  ▸ 恢复正常事件传播                 │
└─────────────────────────────────────┘
```

## 点击 vs 拖拽决策树

```
决策树: 点击还是拖拽?
═══════════════════════════════════════════════════════════════

pointerdown
    │
    ├─ 记录起始位置 (startX, startY)
    └─ moved = false

pointermove
    │
    ├─ 计算距离 dist = √(dx² + dy²)
    │
    ├─ if (dist < 6px)
    │   └─ moved = false (保持)
    │       ▸ 不移动 FAB
    │       ▸ 等待更多移动
    │
    └─ if (dist >= 6px)
        └─ moved = true (标记)
            ▸ 添加 is-dragging 类
            ▸ 开始拖拽

pointerup
    │
    ├─ if (moved === false)
    │   └─ 识别为 "点击"
    │       ▸ togglePanel()
    │       ▸ 打开/关闭面板
    │
    └─ if (moved === true)
        └─ 识别为 "拖拽"
            ▸ 吸边动画
            ▸ 保存位置
            ▸ 不打开面板

click 事件 (捕获阶段)
    │
    ├─ if (moved === true)
    │   └─ 阻止冒泡
    │       ▸ preventDefault()
    │       ▸ stopImmediatePropagation()
    │       ▸ 不触发菜单
    │
    └─ if (moved === false)
        └─ 允许传播
            ▸ 正常点击行为
```

## 事件检查流程

```
事件检查门卫 (Gatekeeper Pattern)
═══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│  pointermove / pointerup / pointercancel                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  检查点 1: active │
                    │  if (!_drag.active)│
                    │     return;       │
                    └──────────────────┘
                              │ 通过
                              ▼
                    ┌──────────────────┐
                    │  检查点 2: pointerId│
                    │  if (e.pointerId │
                    │     !== _drag.   │
                    │     pointerId)   │
                    │     return;      │
                    └──────────────────┘
                              │ 通过
                              ▼
                    ┌──────────────────┐
                    │  检查点 3: threshold│
                    │  (仅 move 事件)  │
                    │  if (dist < 6px &&│
                    │      !moved)     │
                    │     return;      │
                    └──────────────────┘
                              │ 通过
                              ▼
                    ┌──────────────────┐
                    │  执行拖拽逻辑    │
                    └──────────────────┘

只有通过所有检查点，才会执行实际逻辑
这确保了:
  • 只处理我们的拖拽会话
  • 忽略其他指针
  • 防止误触
  • 性能优化
```

## 关键修复对比

```
修复前 vs 修复后
═══════════════════════════════════════════════════════════════

问题 1: 点击其他区域触发拖拽
────────────────────────────────────────────────────
【之前】
document.addEventListener('pointerdown', handler);
// ❌ 任何地方按下都会触发

【现在】
fabButton.addEventListener('pointerdown', handler);
// ✅ 只有 FAB 上按下才触发


问题 2: 没有 pointerId 追踪
────────────────────────────────────────────────────
【之前】
handlePointerMove(e) {
    if (e.buttons === 0) return;
    // ❌ 无法区分多个指针
}

【现在】
_onDocPointerMove(e) {
    if (!_drag.active) return;
    if (e.pointerId !== _drag.pointerId) return;
    // ✅ 只处理正确的指针
}


问题 3: 拖拽触发点击
────────────────────────────────────────────────────
【之前】
handlePointerUp(e) {
    if (wasDragging) {
        snapToEdge();
    } else {
        togglePanel();
    }
    // ❌ click 事件仍会冒泡
}

【现在】
_onFabClick(e) {
    if (_drag.moved) {
        e.stopImmediatePropagation();
        // ✅ 在捕获阶段彻底阻止
    }
}


问题 4: 没有拖拽阈值
────────────────────────────────────────────────────
【之前】
// ❌ 任何移动都立即触发拖拽

【现在】
const dist = Math.hypot(dx, dy);
if (!_drag.moved && dist < 6) return;
// ✅ 6px 阈值，防止误触


问题 5: 没有 pointercancel 处理
────────────────────────────────────────────────────
【之前】
// ❌ 没有处理 pointercancel

【现在】
document.addEventListener('pointercancel', _onDocPointerCancel);
_onDocPointerCancel(e) {
    // ... 清理逻辑
}
// ✅ 完整的事件处理
```

## CSS 修复示意图

```
CSS 防护层
═══════════════════════════════════════════════════════════════

.floating-pet-fab {
    cursor: grab;                 ← 视觉反馈
    user-select: none;            ← 防止文本选择
    -webkit-user-select: none;    ← Safari 兼容
    touch-action: none;           ← 禁用默认触摸行为
}

.floating-pet-fab.is-dragging {
    cursor: grabbing;             ← 拖拽时的视觉反馈
}

效果:
┌─────────────────────────────────────┐
│  触摸/点击 FAB                      │
│  ▸ 不会选中周围文本                 │
│  ▸ 不会触发浏览器默认滚动/缩放      │
│  ▸ 光标显示正确状态                 │
└─────────────────────────────────────┘
```

## 完整数据流

```
从用户交互到状态更新的完整流程
═══════════════════════════════════════════════════════════════

1. 用户按下 FAB
   ↓
2. pointerdown 触发 (_onFabPointerDown)
   ↓
3. 初始化 _drag 状态
   {
     active: true,
     pointerId: 12345,
     startX: 100,
     startY: 200,
     originLeft: 50,
     originTop: 150,
     moved: false,
     movedPx: 0
   }
   ↓
4. setPointerCapture(12345)
   ↓
5. 用户移动指针
   ↓
6. pointermove 触发 (_onDocPointerMove)
   ↓
7. 检查 active ✓ & pointerId ✓
   ↓
8. 计算距离: dist = 8px
   ↓
9. dist >= 6px? YES
   ↓
10. 更新 _drag.moved = true
    ↓
11. 添加 is-dragging 类
    ↓
12. 计算新位置并更新 FAB
    ↓
13. 用户松开
    ↓
14. pointerup 触发 (_onDocPointerUp)
    ↓
15. 检查 active ✓ & pointerId ✓
    ↓
16. 保存 wasMoved = true
    ↓
17. 清理状态
    _drag.active = false
    ↓
18. releasePointerCapture(12345)
    ↓
19. wasMoved === true?
    ↓
20. 执行吸边动画
    ↓
21. 保存位置到 localStorage
    ↓
22. click 事件触发 (_onFabClick, 捕获阶段)
    ↓
23. _drag.moved === true?
    ↓
24. stopImmediatePropagation()
    ↓
25. 完成 (不打开面板)
```

---

**架构设计**: 基于 Pointer Events API + 状态机模式
**关键模式**: Gatekeeper Pattern, Threshold Detection, Capture Phase Interception
**性能优化**: GPU 加速, 事件节流, CSS Containment
