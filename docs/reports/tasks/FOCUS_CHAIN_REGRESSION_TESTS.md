# 焦点链回归测试清单

## 基础功能测试（3 条）

### 测试 1：Tab 从 Input 进入 List

**步骤**：
1. 启动 TUI：`python -m agentos.ui.main_tui`
2. 确认焦点在 Input（光标闪烁）
3. 按 **Tab**

**预期结果**：
- ✅ 焦点进入 List
- ✅ List 第一项高亮
- ✅ Input 失去焦点

---

### 测试 2：Shift+Tab 从 List 回到 Input

**步骤**：
1. 接上一步（焦点在 List）
2. 按 **Shift+Tab**

**预期结果**：
- ✅ 焦点回到 Input
- ✅ List 高亮消失或保持（不影响）
- ✅ Input 重新获得焦点（光标闪烁）

---

### 测试 3：Esc 从 List 回到 Input

**步骤**：
1. Tab 进入 List
2. 按 **Esc**

**预期结果**：
- ✅ 焦点回到 Input（分类模式）
- ✅ 搜索框清空（如果之前有内容）

---

## 关键回归测试（2 条新增 - 最容易暴露问题）

### 测试 4：焦点在 List Item 上时切换（**最重要**）

**步骤**：
1. 启动 TUI
2. Tab 进入 List（焦点在 List 本体）
3. **按 ↓↓ 两次**（确保焦点在 List 的 **Item** 上，而不是 List 本体）
4. 按 **Shift+Tab**

**预期结果**：
- ✅ 焦点必须回到 Input
- ✅ 不应该"卡住"或无响应

**失败标志**（修复前的症状）：
- ❌ Shift+Tab 无效，焦点仍在 Item 上
- ❌ 必须按多次 Shift+Tab 才能回到 Input

**为什么这条最重要**：
- 如果 `has_ancestor` 写反了，这条会失败
- 如果只判断 `focused == lv`（不判断子树），这条会失败

---

### 测试 5：List Re-render 后焦点行为（**容易踩坑**）

**步骤**：
1. 启动 TUI
2. 在 Input 输入一些内容（如 `mem`）触发搜索/过滤
3. Tab 进入过滤后的 List
4. 按 **↓** 选择第二项（焦点在 Item 上）
5. 按 **Esc** 清空搜索（触发 List re-render/重建）
6. 再次输入内容（如 `task`）
7. Tab 进入新 List
8. 按 **Shift+Tab**

**预期结果**：
- ✅ 焦点必须回到 Input
- ✅ 不应该出现"找不到 widget"的错误
- ✅ Shift+Tab 在 re-render 后仍然有效

**失败标志**：
- ❌ Shift+Tab 无效或报错（widget not found）
- ❌ 焦点"丢失"（focused = None）

**为什么这条容易踩坑**：
- `_rebuild_list()` 会移除旧 items 并创建新的（`lv.remove_children()`）
- 如果焦点引用了旧的 Item 对象，`has_ancestor` 可能失效
- 如果没有正确的异常处理（`try/except`），会抛错

---

## 边界条件测试（6 条）

### 测试 6：输入框输入中按 Tab（**新增 - 未来扩展必测**）

**步骤**：
1. 启动 TUI
2. 在 Input 输入内容（如 `mem`）
3. 光标在输入内容中间（不在末尾）
4. 按 **Tab**

**预期结果**：
- ✅ 焦点必须进入 List（不能插入制表符）
- ✅ 输入内容保持不变（不被 Tab 字符破坏）
- ✅ 不卡住、无错误

**为什么重要**：
- 很多 TUI 框架的 Input 默认会处理 Tab（插入制表符或自动补全）
- 必须确保 Tab 的"焦点切换"语义优先于"输入字符"语义

---

### 测试 7：List 过滤无结果时的焦点回退（**新增 - 最容易被忽略**）

**步骤**：
1. 启动 TUI
2. 在 Input 输入不存在的关键字（如 `zzz`）
3. List 应该为空（无匹配结果）
4. 按 **Tab**

**预期结果**：
- ✅ 焦点保持在 Input（因为 List 无内容）
- ✅ 或焦点进入空 List 容器，但 Shift+Tab 仍能回 Input
- ✅ 不应该报错或崩溃

**失败标志**：
- ❌ 焦点"丢失"（focused = None）
- ❌ Shift+Tab 无法回到 Input
- ❌ 报错：list index out of range

**为什么重要**：
- 过滤无结果是常见场景，焦点不应"卡住"
- 用户应该能清空搜索或继续输入，而不是"困在空列表"

---

### 测试 8：从其他 Screen 返回 Home 的焦点复位（**新增 - 控制平面入口体验**）

**步骤**：
1. 启动 TUI（焦点在 Input）
2. Tab 进入 List，↓↓ 选择某一项
3. Enter 进入某个 Screen（如 Tasks / KB / Chat）
4. 按 **Esc** 或 **q** 返回 Home

**预期结果**：
- ✅ 返回 Home 后，焦点**必须**在 Input
- ✅ List 高亮清除（或回到第一项）
- ✅ 不应该残留在 List 的某个 Item 上

**为什么重要**：
- Home 是"控制平面入口"，用户每次回来应该从搜索框开始
- 如果焦点残留在 List，用户一回来就被"卡"在某个位置，体验很差
- 这是"焦点状态持久化"的治理要求

---

### 测试 9：List 为空时按 Tab（原测试 6 - 已在测试 7 覆盖）

此测试已被**测试 7**（List 过滤无结果）覆盖，可跳过。

---

### 测试 10：连续按 Tab 在 List 内

**步骤**：
1. Tab 进入 List
2. 连续按 **Tab 3 次**

**预期结果**：
- ✅ 焦点保持在 List（不跳出）
- ✅ List 内的高亮保持或循环（取决于实现）

---

### 测试 11：在 Input 按 Shift+Tab

**步骤**：
1. 确认焦点在 Input
2. 按 **Shift+Tab**

**预期结果**：
- ✅ 焦点保持在 Input（或循环到某处，但不应报错）
- ✅ 不应该崩溃或无响应

---

## 集成测试（完整流程）

### 测试 12：完整导航流程

**步骤**：
1. 启动 TUI（焦点在 Input）
2. Tab → 焦点到 List
3. ↓↓ → 选择第 3 项
4. Shift+Tab → 焦点回 Input
5. 输入 `kb` → 触发搜索
6. Tab → 焦点到过滤后的 List
7. Esc → 焦点回 Input + 清空搜索
8. Tab → 焦点到 List（回到分类模式）
9. Enter → 进入某个分类的命令列表
10. Shift+Tab → 焦点回 Input（在命令模式）
11. Esc → 返回分类模式 + 焦点回 Input

**预期结果**：
- ✅ 所有步骤的焦点切换都正确
- ✅ 无错误、无崩溃
- ✅ 焦点切换流畅，无"卡住"

---

## 调试验证（如果任何测试失败）

### 使用焦点调试工具

```bash
python debug_focus.py
```

**观察指标**：
1. 顶部 "Focus indicator" 实时显示当前焦点的 widget 类型和 ID
2. Tab/Shift+Tab 时会有通知提示
3. Footer 显示所有可用键盘绑定

**调试检查点**：
- [ ] Tab 时 Focus indicator 从 `Input` 变成 `ListView`
- [ ] Shift+Tab 时 Focus indicator 从 `ListView` 变成 `Input`
- [ ] ↓↓ 后 Focus indicator 显示 `ListItem` 或保持 `ListView`（取决于实现）
- [ ] Shift+Tab（在 Item 上）仍能回到 `Input`

---

## 验收标准（全部通过才算修复成功）

### P0 级别（必须通过，否则不能合并）

- [ ] **测试 1-3**：基础功能（Tab / Shift+Tab / Esc）全部通过
- [ ] **测试 4**：焦点在 List Item 上时 Shift+Tab 必须能回 Input（**最关键**）
- [ ] **测试 5**：Re-render 后焦点切换仍然有效（**最容易踩坑**）

### P1 级别（加固测试，可以合并后补）

- [ ] **测试 6**：输入框输入中按 Tab（未来扩展必测）
- [ ] **测试 7**：List 过滤无结果时焦点回退（最容易被忽略）
- [ ] **测试 8**：从其他 Screen 返回 Home 的焦点复位（控制平面入口体验）
- [ ] **测试 10-11**：边界条件无错误
- [ ] **测试 12**：完整流程流畅无卡顿

---

## 常见失败模式与诊断

### 模式 1：Shift+Tab 在 List Item 上无效

**根因**：`has_ancestor` 调用方向写反

**检查**：
```python
# ❌ 错误（lv 的祖先是 focused？永远 false）
if lv.has_ancestor(focused):

# ✅ 正确（focused 的祖先是 lv？判断子树）
if focused.has_ancestor(lv):
```

**修复**：已在 `home.py:91`、`command_palette.py:261`、`debug_focus.py:85` 修复

---

### 模式 2：Re-render 后 Shift+Tab 报错

**根因**：旧的 Item 对象引用失效，`has_ancestor` 抛异常

**检查**：
```python
# ❌ 没有异常处理
focused.has_ancestor(lv)

# ✅ 有异常处理
try:
    if focused and focused.has_ancestor(lv):
        inp.focus()
except Exception:
    pass  # Widget 已被移除
```

**修复**：已在 `home.py:77-78`、`94-95` 添加 `try/except`

---

### 模式 3：Tab 被 Widget 拦截

**根因**：ListView 内部处理了 Tab，Screen 的 BINDINGS 没触发

**检查**：
```python
# ✅ 确保 HomeScreen 有 BINDINGS
BINDINGS = [
    ("tab", "cycle_focus", "Next"),
    ("shift+tab", "cycle_focus_reverse", "Previous"),
]

# ✅ 确保有对应的 action
def action_cycle_focus(self): ...
def action_cycle_focus_reverse(self): ...
```

**修复**：已在 `home.py:20-24` 添加 BINDINGS

---

## 后续改进建议

### 1. 自动化测试

考虑添加 Textual Pilot 测试：
```python
async def test_focus_chain():
    async with app.run_test() as pilot:
        # Tab 进入 List
        await pilot.press("tab")
        assert pilot.app.focused.id == "cp-list"

        # Shift+Tab 回 Input
        await pilot.press("shift+tab")
        assert pilot.app.focused.id == "cp-input"
```

### 2. 焦点状态持久化

如果用户从 List 切换到其他 Screen，再回来时：
- 焦点应该回到 Input（而不是保持在 List）
- 或者记住上次的焦点位置（根据 UX 需求决定）

### 3. 键盘导航文档

更新 `docs/guides/user/TUI_USAGE_GUIDE.md`：
- 焦点环导航图
- 所有可用快捷键矩阵
- 不同模式下的行为差异

---

**创建时间**：2026-01-27
**测试级别**：P0（必须全部通过）
**预计测试时间**：5 分钟（手动）+ 2 分钟（调试工具）
