# 焦点调试快速指南

## 问题：Tab 键不工作？

如果遇到 Tab/Shift+Tab 键盘导航问题，按以下步骤排查：

---

## 1️⃣ 快速功能测试（30 秒）

```bash
python -m agentos.ui.main_tui
```

**关键测试**（最能暴露问题）：
1. 按 **Tab** → 焦点应进入 List ✅
2. 按 **↓↓** → 确保焦点在 **List Item** 上 ✅
3. 按 **Shift+Tab** → 焦点**必须**回到 Input ✅

**如果第 3 步失败** → 说明 `has_ancestor` 可能写反了，或焦点链断裂

---

## 2️⃣ 启用调试日志（实时监控）

```bash
# 启用焦点调试日志
AGENTOS_DEBUG_FOCUS=1 python -m agentos.ui.main_tui
```

**观察日志**（在终端/Textual dev console 中）：

```
[FOCUS] → Cycle: #input → #list
[FOCUS] ✓ Focus: cp-input → #cp-list        # ✅ 成功切换
[FOCUS] ⊘ Cycle skipped: cp-list not within #input  # ⊘ 条件不满足
[FOCUS] ❌ Focus failed: #target - Widget not found  # ❌ 失败
```

**日志含义**：
- `✓` = 焦点成功切换
- `⊘` = 条件不满足，跳过切换（如焦点不在指定子树内）
- `❌` = 失败（widget 不存在、不可聚焦等）

---

## 3️⃣ 使用可视化调试工具（焦点指示器）

```bash
python debug_focus.py
```

**功能**：
- 顶部实时显示当前焦点：`Focus: ListView (#cp-list)`
- Tab/Shift+Tab 时有通知提示
- Footer 显示所有可用快捷键

**测试步骤**：
1. 观察顶部焦点指示器
2. 按 Tab → 应显示 `ListView (#cp-list)`
3. 按 ↓↓ → 可能显示 `ListItem` 或保持 `ListView`
4. 按 Shift+Tab → **必须**显示 `Input (#cp-input)`

**如果焦点指示器不更新** → 事件传播可能被拦截

---

## 4️⃣ 常见问题诊断

### 问题 A：Shift+Tab 在 List Item 上无效

**根因**：`has_ancestor` 调用方向写反

**检查**：
```bash
# 检查是否有错误的调用
grep "lv.has_ancestor(focused)" agentos/ui/screens/*.py
# 应该返回 0 个结果（正确的是 focused.has_ancestor(lv)）
```

---

### 问题 B：Re-render 后报错

**根因**：旧 widget 引用失效，没有异常处理

**检查**：
```bash
# 确保所有焦点切换都有 try/except
grep -A5 "action_cycle_focus" agentos/ui/screens/*.py | grep "try\|except"
```

---

### 问题 C：Tab 被完全拦截

**根因**：某个 Widget 的 `on_key` 拦截了 Tab

**检查**：
```bash
# 检查是否有 on_key 拦截 Tab
grep -n "def on_key\|event.stop" agentos/ui/widgets/*.py
```

---

## 5️⃣ 完整回归测试

详见 `FOCUS_CHAIN_REGRESSION_TESTS.md`（12 条测试）

**P0 级别**（必须通过）：
- [ ] 测试 1-3：基础功能
- [ ] 测试 4：焦点在 Item 上 Shift+Tab 回 Input（**最关键**）
- [ ] 测试 5：Re-render 后仍有效（**最容易踩坑**）

---

## 6️⃣ 使用焦点治理工具函数

如果需要添加新的焦点管理逻辑，使用工具函数而不是重复写判断：

```python
from agentos.ui.utils import is_within, safe_focus, focus_cycle

# 判断焦点是否在子树内
if is_within(self.app.focused, lv):
    safe_focus(self.app, "#input")

# 焦点循环（一行代码）
focus_cycle(self.app, "#list", "#input", only_if_within="#list")
```

---

## 7️⃣ 环境变量参考

| 环境变量 | 功能 | 用法 |
|---------|------|------|
| `AGENTOS_DEBUG_FOCUS=1` | 启用焦点调试日志 | `AGENTOS_DEBUG_FOCUS=1 python -m agentos.ui.main_tui` |

---

## 8️⃣ 治理文档参考

**详细治理规范**：`docs/governance/UI_FOCUS_GOVERNANCE.md`

**核心原则**：
1. ✅ 明确性优于默认行为
2. ✅ 工具函数优于重复逻辑
3. ✅ Screen 层绑定优于 Widget 层
4. ✅ 子树判断必须正确（`focused.has_ancestor(container)`）
5. ✅ 异常处理必须完整
6. ✅ 不得拦截 Tab/Shift+Tab（除非明确治理）

---

## 快速命令索引

```bash
# 基础测试
python -m agentos.ui.main_tui

# 启用调试日志
AGENTOS_DEBUG_FOCUS=1 python -m agentos.ui.main_tui

# 可视化调试
python debug_focus.py

# 检查代码
grep "has_ancestor" agentos/ui/**/*.py
grep "action_cycle_focus" agentos/ui/**/*.py
```

---

**维护者**：AgentOS TUI Team
**最后更新**：2026-01-27
