# Enter 键修复报告

## 问题描述

**现象**：焦点在 List 上（蓝色高亮），按 **Enter 没反应**

**根因**：CommandPalette 没有处理 `ListView.Selected` 事件

---

## 根因分析

### 当前行为

| 焦点位置 | 按 Enter | 事件触发 | Handler | 结果 |
|---------|---------|---------|---------|------|
| **Input** | ✅ | `Input.Submitted` | `on_input_submitted` → `action_accept()` | ✅ 工作 |
| **ListView** | ❌ | `ListView.Selected` | **无 handler** | ❌ 无反应 |

### 问题链路

```
用户按 Enter（焦点在 ListView）
    ↓
ListView 发送 ListView.Selected 事件
    ↓
CommandPalette 没有 on_list_view_selected handler
    ↓
事件未被处理 → 无反应
```

---

## 修复方案

### 修复 1：添加 ListView.Selected handler

**位置**：`agentos/ui/widgets/command_palette.py:82-84`

```python
def on_list_view_selected(self, event: ListView.Selected) -> None:
    """监听 ListView 的 Enter 事件（焦点在列表上按 Enter）"""
    self.action_accept()
```

**原理**：
- ListView 按 Enter 会发送 `Selected` 事件
- 添加 handler 捕获事件并调用 `action_accept()`
- `action_accept()` 已有完整的逻辑处理选中项

---

### 修复 2：添加调试日志

**位置**：`agentos/ui/widgets/command_palette.py:197-260`

```python
def action_accept(self) -> None:
    import os
    _DEBUG = os.environ.get("AGENTOS_DEBUG_FOCUS") == "1"

    # 调试日志贯穿所有分支
    if _DEBUG:
        self.app.log.info(f"[ENTER] ...")
```

**日志覆盖**：
- ✅ 参数输入模式（有参数 / 无参数）
- ✅ 无高亮项
- ✅ 分类选择（成功 / 失败）
- ✅ 命令选择（成功 / 失败 / 需要参数）

---

## 修复后行为

| 焦点位置 | 按 Enter | 事件触发 | Handler | 结果 |
|---------|---------|---------|---------|------|
| **Input** | ✅ | `Input.Submitted` | `on_input_submitted` → `action_accept()` | ✅ 工作 |
| **ListView** | ✅ | `ListView.Selected` | `on_list_view_selected` → `action_accept()` | ✅ **修复** |

---

## 验证步骤

### 1️⃣ 快速功能测试（30 秒）

```bash
python -m agentos.ui.main_tui
```

**测试步骤**：
1. 启动后焦点在 Input
2. 按 **Tab** → 焦点进入 List（蓝色高亮）
3. 按 **↓** 选择 "chat" 或其他分类
4. 按 **Enter** → **应该进入分类的命令列表** ✅

**预期结果**：
- ✅ Enter 有反应（进入下一级或执行命令）
- ✅ 不卡住、不报错

---

### 2️⃣ 启用调试日志（详细验证）

```bash
AGENTOS_DEBUG_FOCUS=1 python -m agentos.ui.main_tui
```

**观察日志**（在终端或 Textual dev console）：

**分类选择**（Tab → ↓ → Enter）：
```
[ENTER] Highlighted item: chat         📬 Chat, mode=CommandPaletteMode.CATEGORY
[ENTER] Entering category: CommandCategory.CHAT
```

**命令选择**（进入分类后 → ↓ → Enter）：
```
[ENTER] Highlighted item: open         Open chat interface, mode=CommandPaletteMode.COMMANDS
[ENTER] Command selected: open, needs_arg=False
```

**如果没有日志**：
- 说明 `on_list_view_selected` 没被触发
- 可能是 ListView 的 Enter 被其他地方拦截

---

## 完整流程测试

### 测试 A：分类 → 命令 → 执行

```
1. 启动 TUI（焦点在 Input）
2. Tab → 焦点到 List
3. ↓↓ → 选择 "chat" 分类
4. Enter → 进入 chat 分类的命令列表
5. ↓ → 选择 "open" 命令
6. Enter → 执行命令（应该打开 Chat Screen）
```

**预期结果**：
- ✅ 每个 Enter 都有反应
- ✅ 最后进入 Chat Screen

---

### 测试 B：搜索 → 命令 → 执行

```
1. 启动 TUI（焦点在 Input）
2. 输入 "chat" → 触发搜索
3. Tab → 焦点到过滤后的 List
4. Enter → 选择第一个匹配的命令
```

**预期结果**：
- ✅ Enter 执行命令或进入下一级

---

### 测试 C：参数输入

```
1. 选择需要参数的命令（如 kb:search）
2. Enter → 进入参数输入模式
3. 输入参数（如 "test"）
4. Enter → 提交命令
```

**预期结果**：
- ✅ 第一个 Enter 进入参数输入模式
- ✅ 第二个 Enter 执行命令

---

## 常见问题诊断

### 问题 A：Enter 仍然无反应

**可能原因**：
1. ListView 的 Enter 被拦截（某个父容器或 Screen 处理了）
2. `action_accept()` 执行了但逻辑有问题（如 `highlighted_child` 为 None）

**诊断**：
```bash
AGENTOS_DEBUG_FOCUS=1 python -m agentos.ui.main_tui
# 按 Enter 后观察是否有 [ENTER] 日志
```

**如果有日志**：
- 说明 handler 工作了，问题在 `action_accept()` 内部
- 检查日志中的 "No highlighted child" 或 "Item has no category/command attribute"

**如果无日志**：
- 说明 `on_list_view_selected` 没被触发
- 检查是否有其他地方拦截了 Enter（如 Screen 层）

---

### 问题 B：Enter 触发但没有导航

**症状**：日志显示 `[ENTER] Command selected: ...`，但没有进入 Screen

**根因**：`HomeScreen` 的 `on_command_selected` handler 有问题

**检查**：
```bash
grep -n "def on_command_selected" agentos/ui/screens/home.py
# 查看 handler 是否正确处理 CommandSelected 事件
```

---

### 问题 C：某些命令有反应，某些无反应

**根因**：ListItem 没有正确绑定 `category` 或 `command` 属性

**检查**（`command_palette.py:131-133, 156-158`）：
```python
# 分类渲染
item.category = cat  # ✅ 必须有这句

# 命令渲染
item.command = cmd  # ✅ 必须有这句
```

---

## 治理规则更新

### 规则 7：监听 Widget 的 Selected/Activated 事件

**原则**：使用可选择 widget（ListView / OptionList / DataTable）时，必须处理其 Selected 事件。

**✅ 好的做法**：
```python
class MyWidget(Widget):
    def compose(self):
        yield ListView(id="my-list")

    def on_list_view_selected(self, event: ListView.Selected):
        # 处理选择事件
        self._handle_selection(event.item)
```

**❌ 坏的做法**：
```python
class MyWidget(Widget):
    BINDINGS = [
        ("enter", "accept", "Accept")
    ]
    # ❌ 只定义 action，不处理 ListView.Selected
    # 当焦点在 ListView 上时，Enter 会触发 ListView.Selected，而不是 action_accept
```

**统一方案**（推荐）：
```python
# 同时处理 action 和事件
def on_list_view_selected(self, event: ListView.Selected):
    self.action_accept()

def action_accept(self):
    # 统一的接受逻辑
    ...
```

---

## 文件变更清单

| 文件 | 变更 | 说明 |
|------|------|------|
| `agentos/ui/widgets/command_palette.py` | 修改 | 添加 `on_list_view_selected` + 调试日志 |
| `ENTER_KEY_FIX_REPORT.md` | 新增 | 本报告 |

---

## 验收标准

- [ ] **测试 A 通过**：分类 → 命令 → 执行（完整流程）
- [ ] **测试 B 通过**：搜索 → 命令 → 执行
- [ ] **测试 C 通过**：参数输入模式正常工作
- [ ] **调试日志可用**：`AGENTOS_DEBUG_FOCUS=1` 能看到 `[ENTER]` 日志

---

## 与焦点链修复的关系

| 修复 | 解决的问题 | 影响的键 |
|------|-----------|---------|
| **焦点链修复** | Tab/Shift+Tab 在 List 和 Input 之间切换 | Tab / Shift+Tab / Esc |
| **Enter 键修复** | 焦点在 List 上按 Enter 执行命令 | Enter |

**配合效果**：
- ✅ Tab 进入 List
- ✅ ↓↑ 在 List 内导航
- ✅ Enter 执行选中项（**本次修复**）
- ✅ Shift+Tab 回到 Input
- ✅ Esc 也能回到 Input

---

**修复完成时间**：2026-01-27
**修复类型**：添加事件 handler
**预期效果**：焦点在 List 上按 Enter 能正常执行命令或进入下一级
