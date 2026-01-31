# CommandPalette Focus Debug Guide

## 问题描述
从分类列表进入命令列表（如选择 Chat → 进入 chat_open 页面）后，按 Tab、Up/Down 箭头没有反应，无法选中命令。

## 已实施的修复

### Fix 1: Tab 键拦截
- 在 `on_key()` 中拦截 Tab 键（line 114-119）
- 调用 `action_focus_list()` 将焦点移到 ListView

### Fix 2: ListView 可 focus
- 在 `compose()` 中设置 `lv.can_focus = True`（line 69-70）
- 在 `on_mount()` 中再次确保（line 75-76）

### Fix 3: 进入命令页时强制 focus
- 在搜索模式（line 128-131）
- 在分类进入命令模式（line 139-142）
- 在 `action_accept()` 从分类进入命令时（line 289-295）

### Fix 4: Enter 触发 action_accept
- `on_input_submitted()` 确保 Input 按 Enter 时调用 `action_accept()`（line 93-95）

## 调试模式

运行带调试日志的版本：

```bash
AGENTOS_DEBUG_FOCUS=1 uv run agentos --tui
```

## 测试步骤

1. **启动应用**
   ```bash
   AGENTOS_DEBUG_FOCUS=1 uv run agentos --tui
   ```

2. **进入分类列表**
   - 应看到：chat, task, model, system, kb, memory, history

3. **选择 Chat 分类**
   - 按 Down arrow 移到 "chat" 项
   - 按 Enter

4. **检查日志**
   查看终端输出，应该看到：
   ```
   [ENTER] Entering category: chat
   [ENTER] Focused ListView, index=0, children=1
   ```

5. **测试焦点和键盘**
   此时应该在 "chat_open Open Chat" 页面：

   **测试 Tab 键**：
   - 按 Tab
   - 应看到日志：
     ```
     [KEY] Tab intercepted, calling action_focus_list()
     [TAB] action_focus_list called, lv.children=1, lv.can_focus=True
     [TAB] Focused ListView, index=0
     ```

   **测试 Down 键**：
   - 按 Down arrow
   - 应看到日志：
     ```
     [KEY] Down arrow intercepted, calling action_down()
     [DOWN] lv.children=1, lv.can_focus=True, lv.index=0
     [DOWN] Moved focus from Input to ListView, index=0
     ```

   **测试 Enter 键**：
   - 按 Enter（在 chat_open 项高亮时）
   - 应看到日志：
     ```
     [ENTER] Command selected: chat_open, needs_arg=False
     ```
   - 应该进入 **ChatModeScreen**（3 列布局）

## 预期结果

成功的表现：
- ✅ 按 Tab → 焦点移到列表，"chat_open" 高亮
- ✅ 按 Down arrow → 焦点移到列表，"chat_open" 高亮
- ✅ 按 Enter → 进入 ChatModeScreen
- ✅ 日志显示所有 focus 操作成功

## 可能的问题和诊断

### 问题 1: 没有看到日志输出
**原因**: 环境变量没设置
**解决**: 确保使用 `AGENTOS_DEBUG_FOCUS=1`

### 问题 2: 日志显示 "ListView has no children"
**原因**: `_render_commands()` 没有正确渲染
**检查**:
- 命令是否注册（`filter_commands("chat")` 应返回结果）
- `get_commands_by_category(CommandCategory.CHAT)` 是否有命令

### 问题 3: 日志显示 "lv.can_focus=False"
**原因**: ListView 在某个时刻被重置
**解决**: 已在多处强制设置 `can_focus=True`

### 问题 4: 按键没有被拦截（没有 "[KEY]" 日志）
**原因**:
- Input 没有焦点
- HomeScreen 的 BINDINGS 优先级更高
**检查**: 日志应显示当前焦点在哪个 widget

### 问题 5: Enter 没有反应
**原因**: `action_accept()` 没有找到 item
**检查**:
- 日志应显示 "Highlighted item: ..."
- `lv.index` 是否有效
- `item.command` 属性是否存在

## 日志文件位置

如果终端日志太多，可以查看文件：
```bash
tail -f ~/.agentos/logs/textual.log
```

## 下一步

如果问题仍然存在，请提供：
1. 完整的日志输出（从启动到卡住的所有 `[KEY]`, `[ENTER]`, `[DOWN]`, `[TAB]` 日志）
2. 具体卡住时的屏幕截图
3. 当前焦点在哪个 widget（从日志中看）

这将帮助精确定位问题所在。
