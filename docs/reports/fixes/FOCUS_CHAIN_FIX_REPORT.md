# Home Screen 焦点链修复报告

## 问题描述

**现象**：Tab 能从 Input 进入 List，但 Shift+Tab **无法**从 List 回到 Input

**影响**：用户被"困"在列表中，必须用鼠标或重启才能回到搜索框

---

## 根因分析（4 个可能原因）

### ✅ 1. ListView 拦截了 Tab 键（主要原因）

- `CommandPalette` 虽然定义了 `BINDINGS`（第 45-46 行）：
  ```python
  ("tab", "focus_list", "Focus List"),
  ("shift+tab", "focus_input", "Focus Input"),
  ```
- 但 **ListView 本身会拦截 Tab 键**，导致这些绑定不触发
- `CommandPalette` 的 BINDINGS 优先级不够高，被子组件覆盖

### ✅ 2. HomeScreen 没有焦点环治理

- HomeScreen 没有任何 BINDINGS 或焦点管理逻辑
- 完全依赖默认的 `focus_next()`/`focus_previous()`（不可靠）

### ❌ 3. Input 不在焦点链（已排除）

- Input 可聚焦、未 disabled、可见 → 排除

### ❌ 4. tab_order / DOM 顺序问题（已排除）

- DOM 结构清晰（Input → ListView）→ 排除

---

## 修复方案（"明确焦点环"策略）

### 修复 1：HomeScreen 层面的高优先级焦点绑定

**位置**：`agentos/ui/screens/home.py:20-24`

```python
class HomeScreen(Screen):
    """Home screen with command palette"""

    # 明确的焦点环绑定（高优先级）
    BINDINGS = [
        ("tab", "cycle_focus", "Next"),
        ("shift+tab", "cycle_focus_reverse", "Previous"),
    ]
```

**原理**：
- Screen 层级的 BINDINGS 优先级高于 Widget
- 即使 ListView 拦截 Tab，Screen 层的处理会先执行

---

### 修复 2：明确的焦点切换逻辑

**位置**：`agentos/ui/screens/home.py:56-93`

#### A. `action_cycle_focus()` - Tab 键

```python
def action_cycle_focus(self) -> None:
    """Tab: Input → List（明确切换，不赌默认 focus_next）"""
    from textual.widgets import Input, ListView

    try:
        inp = self.query_one("#cp-input", Input)
        lv = self.query_one("#cp-list", ListView)

        # 如果当前焦点在 Input（或 None），切换到 List
        focused = self.app.focused
        if focused is None or focused == inp or not lv.has_ancestor(focused):
            if lv.children:  # 只有列表有内容才切换
                lv.focus()
                # 确保有高亮项
                if lv.index is None or lv.index < 0:
                    lv.index = 0
    except Exception:
        pass  # Widget 可能未挂载
```

**关键点**：
- ✅ 使用 `lv.has_ancestor(focused)` 判断焦点是否在 List 子树内
- ✅ 显式调用 `lv.focus()`，不依赖 `focus_next()`
- ✅ 确保 List 有高亮项（`lv.index = 0`）

#### B. `action_cycle_focus_reverse()` - Shift+Tab 键

```python
def action_cycle_focus_reverse(self) -> None:
    """Shift+Tab: List → Input（强制切回，不管当前在 List 哪个子项）"""
    from textual.widgets import Input, ListView

    try:
        inp = self.query_one("#cp-input", Input)
        lv = self.query_one("#cp-list", ListView)

        # 如果当前焦点在 List（或其子树内），强制切回 Input
        focused = self.app.focused
        if focused and (focused == lv or lv.has_ancestor(focused)):
            inp.focus()
    except Exception:
        pass  # Widget 可能未挂载
```

**关键点**：
- ✅ 强制切回 Input，无论焦点在 List 的哪个子项
- ✅ 判断 `lv.has_ancestor(focused)` 确保覆盖所有 List 内部焦点

---

### 修复 3：Esc 键增强（UX 优化）

**位置**：`agentos/ui/widgets/command_palette.py:258-261`

```python
def action_escape(self) -> None:
    """Esc 返回上一级或清空输入或回到 Input"""
    # ... 原有逻辑 ...
    else:
        # 已经在分类模式且无搜索文本，如果焦点在 List，切回 Input
        if lv.has_focus or (self.app.focused and lv.has_ancestor(self.app.focused)):
            inp.focus()
```

**新增功能**：
- ✅ Esc 键形成完整的"退出"链：Commands → Category → **Input**
- ✅ 用户可以用 Esc 快速回到搜索框（不需要 Shift+Tab）

---

## 焦点流设计（最终体验）

```
┌─────────────────────────────────────────┐
│         Input (搜索框)                    │
│  ↓ Tab         ↑ Shift+Tab / Esc        │
│         List (分类/命令列表)              │
│  (Tab 在 List 内保持，避免意外跳出)       │
└─────────────────────────────────────────┘
```

### 键盘导航完整矩阵

| 当前焦点 | 按键 | 目标 | 说明 |
|---------|------|------|------|
| **Input** | Tab | List | 进入列表（如果有内容） |
| **Input** | ↓ | List | CommandPalette 原有逻辑 |
| **List** | Shift+Tab | Input | **新增**：强制回 Input |
| **List** | Esc | Input | **新增**：快捷回 Input |
| **List** | ↑（第一项） | Input | CommandPalette 原有逻辑 |
| **List** | Tab | List | 保持在 List（不跳出） |

---

## 测试验证

### 1. 基础功能测试

```bash
python -m agentos.ui.main_tui
```

**测试步骤**：
1. 启动后焦点应在 Input
2. 按 **Tab** → 焦点应进入 List（第一项高亮）
3. 按 **Shift+Tab** → 焦点应回到 Input ✅
4. 再按 **Tab** → 焦点应再次进入 List
5. 按 **Esc** → 焦点应回到 Input ✅

### 2. 焦点链调试（如果有问题）

```bash
python debug_focus.py
```

**观察**：
- 顶部显示当前焦点的 widget 类型和 ID
- 按 Tab/Shift+Tab 时会有通知提示
- Footer 显示所有可用键盘绑定

**✅ 修复成功标志**：
- Tab 和 Shift+Tab 都有通知提示
- 焦点指示器正确显示 `Input` 或 `ListView`

**❌ 如果还有问题**：
- 观察焦点指示器是否更新
- 查看是否有错误通知
- 检查 `self.app.focused` 是否为 `None`

---

## "Claude 全面自查 UI 交互问题"清单

### ✅ 1. 焦点策略明确性

- [x] Input 的 id 固定（`#cp-input`）
- [x] List 的 id 固定（`#cp-list`）
- [x] Tab / Shift+Tab / Esc 都有明确绑定
- [x] Enter 在 List 上的行为明确（选择命令）
- [x] ↑↓ 在 List 上不会影响 Input

### ✅ 2. 事件传播正确性

- [x] HomeScreen 的 action 不会 `event.stop()`
- [x] Tab 键在 Screen 层拦截，优先级高于 Widget
- [x] CommandPalette 的 Esc 处理不会阻止焦点切换

### ✅ 3. 焦点链完整性

- [x] Input 没有 `disabled`
- [x] Input 没有 `display:none`
- [x] 容器（`#home-content`）不可聚焦

### ✅ 4. 焦点态样式一致性

- [x] `:focus` 只改颜色，不改 `border`/`padding`
- [x] `#cp-list` 边框常驻（`border: heavy #1a1a1a`）
- [x] 聚焦时只换颜色（`border: heavy #404040`）

---

## 修复对比

| 维度 | 修复前 | 修复后 |
|------|--------|--------|
| **焦点治理** | 依赖默认链 | Screen 层明确绑定 ✅ |
| **Shift+Tab** | 不工作（被 ListView 拦截） | 强制回 Input ✅ |
| **Esc 键** | 只清空搜索/返回分类 | 可回 Input ✅ |
| **焦点判断** | 简单 `==` 比较 | `has_ancestor()` 判断子树 ✅ |
| **可维护性** | 依赖组件内部行为 | 显式控制，可追溯 ✅ |

---

## 为什么这个修复有效（机制层）

### 1. Screen 层 BINDINGS 优先级高于 Widget

**Textual 的事件传播顺序**：
```
Screen BINDINGS (最高优先级)
    ↓
Focused Widget BINDINGS
    ↓
Parent Container BINDINGS
    ↓
App BINDINGS
```

- HomeScreen 的 `("tab", "cycle_focus")` 在 **最上层**
- 即使 ListView 内部处理了 Tab，Screen 层的 action 会先执行

### 2. 明确的焦点切换（不赌默认行为）

**修复前**：
```python
# 依赖 Textual 的默认 focus_next()
# 问题：ListView 内部可能拦截、焦点链可能断裂
```

**修复后**：
```python
# 显式调用 widget.focus()
lv.focus()  # 直接聚焦目标 widget
inp.focus()  # 直接聚焦目标 widget
```

### 3. 子树焦点判断（覆盖所有 List 内部状态）

**修复前**：
```python
if focused == lv:  # ❌ 只判断 List 本体
```

**修复后**：
```python
if focused == lv or lv.has_ancestor(focused):  # ✅ 判断整个子树
```

---

## 后续改进建议

### 1. 统一焦点环规范（所有 Screen）

建议为所有 Screen 添加统一的焦点环治理：
- 明确的 Tab/Shift+Tab 绑定
- 明确的 Esc 键"退出"逻辑
- 可选：添加 `Ctrl+[` 作为 Esc 的别名（Vim 用户友好）

### 2. 焦点状态可视化（开发调试）

建议在 Footer 添加焦点状态指示器（开发模式）：
```python
Footer(show_command_palette=True, show_focused_widget=True)
```

### 3. 键盘导航文档化

建议在 `docs/guides/user/TUI_USAGE_GUIDE.md` 中添加：
- 焦点环导航图
- 所有可用键盘快捷键矩阵
- 不同模式下的键盘行为差异

---

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `agentos/ui/screens/home.py` | 修改 | 添加 BINDINGS + 焦点切换 action |
| `agentos/ui/widgets/command_palette.py` | 修改 | 增强 Esc 键逻辑 |
| `debug_focus.py` | 新增 | 焦点链调试工具 |
| `FOCUS_CHAIN_FIX_REPORT.md` | 新增 | 本报告 |

---

## 验收标准

- [x] Tab 能从 Input 进入 List
- [x] Shift+Tab 能从 List 回到 Input
- [x] Esc 能从 List 回到 Input（分类模式）
- [x] ↑ 在 List 第一项能回到 Input（原有功能保持）
- [x] 焦点切换不会导致 UI "跳动"（边框修复已完成）
- [x] 所有键盘导航逻辑可追溯、可维护

---

**修复完成时间**：2026-01-27
**修复方法**：Screen 层明确焦点环 + 子树焦点判断 + Esc 键增强
**预期效果**：用户可以自由地在 Input 和 List 之间切换，不会被"困"在列表中
