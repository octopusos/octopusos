# Command Palette Argument Input Fix Report

**日期**: 2026-01-26  
**类型**: Bug 修复 + 功能增强  
**严重性**: 🟡 中（功能缺失）  
**状态**: ✅ 已修复

## 问题概述

### 用户报告的症状

用户选择需要参数的命令（如 `kb_search`）后，输入框仍然在过滤命令列表，无法输入参数进行搜索。提示 `kb_search requires an argument`，但没有提供输入参数的方式。

### 根本原因

Command Palette 只有两种模式：
1. **CATEGORY**: 显示分类列表
2. **COMMANDS**: 显示命令列表

当用户选择了需要参数的命令（`needs_arg=True`）后，直接发送 `CommandSelected` 事件，但没有切换到**参数输入模式**，导致：
- 输入框继续过滤命令（没有意义）
- 用户无法输入参数
- 只有 `task_inspect` 和 `task_resume` 通过特殊的 `TaskSearchPalette` 解决了这个问题

### 受影响的命令

所有 `needs_arg=True` 的命令，除了有特殊 UI 的 task 命令：
- ✅ `kb_search` - KB 搜索
- ✅ `kb_explain` - KB 解释
- ✅ `mem_inspect` - Memory 检查
- ✅ 所有其他需要参数的命令

## 解决方案

### 策略

引入**第三种模式**：`ARG_INPUT`（参数输入模式），在用户选择需要参数的命令后自动切换。

### 核心修改

#### 1. 添加新模式

```python
class CommandPaletteMode(str, Enum):
    CATEGORY = "category"      # 显示分类列表
    COMMANDS = "commands"       # 显示命令列表
    ARG_INPUT = "arg_input"     # 参数输入模式 ✅ 新增
```

#### 2. 修改事件携带参数

```python
class CommandSelected(Message):
    def __init__(self, command: Command, argument: str = None) -> None:
        self.command = command
        self.argument = argument  # ✅ 新增：携带参数
```

#### 3. 参数输入模式流程

```python
# 用户选择需要参数的命令
→ 进入 ARG_INPUT 模式
→ 清空输入框，更新 placeholder: "Enter argument for {cmd.title}..."
→ 清空列表（不再过滤命令）
→ 用户输入参数
→ 按 Enter 提交 → 发送 CommandSelected(cmd, argument)
→ 按 ESC 取消 → 返回 CATEGORY 模式
```

## 修复详情

### 1. CommandPalette 修改

**文件**: `agentos/ui/widgets/command_palette.py`

**修改**:

1. **添加 ARG_INPUT 模式**
   ```python
   ARG_INPUT = "arg_input"
   ```

2. **添加 _pending_command 字段**
   ```python
   self._pending_command: Optional[Command] = None
   ```

3. **修改 _rebuild_list()**
   - 如果在 ARG_INPUT 模式，直接返回（不过滤命令）
   ```python
   if self.mode == CommandPaletteMode.ARG_INPUT:
       return  # 参数输入模式：不过滤命令
   ```

4. **修改 action_accept()**
   - 如果在 ARG_INPUT 模式，提交命令+参数
   - 如果选择的命令需要参数，进入 ARG_INPUT 模式
   ```python
   if self.mode == CommandPaletteMode.ARG_INPUT:
       argument = self.query_text.strip()
       if argument:
           self.post_message(CommandSelected(self._pending_command, argument))
           self._reset_to_category()
   ```

5. **添加 _enter_arg_input_mode()**
   ```python
   def _enter_arg_input_mode(self, cmd: Command) -> None:
       self._pending_command = cmd
       self.mode = CommandPaletteMode.ARG_INPUT
       
       # 清空输入框，准备接受参数
       inp = self.query_one("#cp-input", Input)
       inp.value = ""
       inp.placeholder = f"Enter argument for {cmd.title}..."
       
       # 清空列表
       lv = self.query_one("#cp-list", ListView)
       lv.remove_children()
   ```

6. **添加 _reset_to_category()**
   ```python
   def _reset_to_category(self) -> None:
       self._pending_command = None
       self.mode = CommandPaletteMode.CATEGORY
       inp.placeholder = "Type to search or select category…"
   ```

7. **修改 action_escape()**
   - 如果在 ARG_INPUT 模式，返回 CATEGORY 模式
   ```python
   if self.mode == CommandPaletteMode.ARG_INPUT:
       self._reset_to_category()
       return
   ```

### 2. HomeScreen 修改

**文件**: `agentos/ui/screens/home.py`

**修改**:

1. **更新 _update_hint_text()**
   - 添加 ARG_INPUT 模式的提示
   ```python
   if cp.mode == CommandPaletteMode.ARG_INPUT:
       hint.update("Type argument · Enter submit · ESC cancel")
   ```

2. **修改 on_command_selected()**
   - 接收 `event.argument` 参数
   - 处理有参数的命令，根据命令类型传递参数
   ```python
   argument = event.argument
   
   if argument:
       if command_id.startswith("kb:"):
           kwargs["query"] = argument
       elif command_id.startswith("mem:"):
           kwargs["query"] = argument
       elif command_id.startswith("task:"):
           kwargs["task_id"] = argument
   ```

3. **特殊处理 task 命令**
   - `task_inspect` 和 `task_resume` 仍然使用 `TaskSearchPalette`（更好的 UX）
   - 其他需要参数的命令使用通用的参数输入模式
   ```python
   if cmd.key in ("inspect", "task_inspect", "resume", "task_resume"):
       self._enter_task_search_mode(cmd)
       return
   ```

4. **改进 _execute_registry_command()**
   - 对于有输出的命令，显示结果数量
   ```python
   if isinstance(result.data, list) and len(result.data) > 0:
       self.notify(f"✓ {result.summary} ({len(result.data)} results)", ...)
   ```

5. **移除 _handle_arg_command()**
   - 不再需要，由 CommandPalette 统一处理

## 用户体验改进

### 修复前

```
1. 用户选择 "kb_search"
2. 提示: "kb_search requires an argument"
3. 输入框仍在过滤命令
4. 用户不知道如何输入参数 ❌
```

### 修复后

```
1. 用户选择 "kb_search"
2. 自动进入参数输入模式 ✅
3. Placeholder 变为: "Enter argument for Search knowledge base..."
4. 提示变为: "Type argument · Enter submit · ESC cancel"
5. 用户输入: "test query"
6. 按 Enter 执行搜索
7. 显示结果: "✓ Search completed (15 results)"
```

## 测试验证

### 测试场景

#### 1. KB 命令测试
```
- 选择 "Knowledge Base" 分类
- 选择 "Search knowledge base"
- 输入: "TODO"
- 按 Enter
- 预期: 执行 kb:search，显示搜索结果
```

#### 2. 参数模式取消
```
- 选择需要参数的命令
- 进入参数输入模式
- 按 ESC
- 预期: 返回分类列表，不执行命令
```

#### 3. Task 命令（特殊 UI）
```
- 选择 "Resume task"
- 预期: 显示 TaskSearchPalette（搜索界面）
- 而不是简单的参数输入框
```

#### 4. Hint 文本更新
```
- 检查不同模式下的 hint 文本
- CATEGORY: "↑↓ navigate · Enter select · Type to search"
- COMMANDS: "↑↓ navigate · Enter select · ESC back"
- ARG_INPUT: "Type argument · Enter submit · ESC cancel"
```

### 预期结果

- ✅ 所有需要参数的命令都能正常输入参数
- ✅ 参数输入模式下不会过滤命令列表
- ✅ Placeholder 清晰提示当前需要输入什么
- ✅ Hint 文本正确显示操作提示
- ✅ ESC 可以取消参数输入
- ✅ Task 命令仍使用特殊的搜索 UI

## 架构改进

### 模式状态机

```
CATEGORY ←────────┐
   ↓              │
   ↓ (选择分类)    │
   ↓              │ (ESC)
COMMANDS ←────────┤
   ↓              │
   ↓ (选择命令)    │
   ↓              │
   ├→ 不需要参数: 直接执行
   │
   └→ 需要参数
       ↓
   ARG_INPUT
       ↓
       ├→ Enter: 提交命令+参数
       └→ ESC: 返回 CATEGORY
```

### 参数类型映射

不同类型的命令使用不同的参数名：

| 命令类型 | 参数名 | 示例 |
|---------|-------|------|
| kb:* | query | `query="test"` |
| mem:* | query | `query="task-123"` |
| task:* | task_id | `task_id="abc123"` |
| 其他 | arg | `arg="value"` |

## 向后兼容性

- ✅ **完全兼容**: `TaskSearchPalette` 仍然用于 task 命令
- ✅ **API 不变**: `CommandSelected` 事件增加了可选的 `argument` 字段
- ✅ **旧代码兼容**: 不传 `argument` 的旧代码仍然工作

## 经验教训

### 1. UI 状态管理

对于多模式 UI，需要清晰定义：
- 每种模式的职责
- 模式之间的转换条件
- 模式切换时的清理工作

### 2. 通用 vs 特殊

- 通用方案：参数输入模式（适合简单参数）
- 特殊方案：TaskSearchPalette（适合复杂选择）
- 需要权衡 UX 和实现复杂度

### 3. Placeholder 的重要性

用户不会猜测，需要通过 Placeholder 和 Hint 明确告诉用户：
- 当前应该做什么
- 如何取消操作
- 如何提交输入

## 后续优化建议

### 1. 参数验证

在参数输入模式下，可以添加实时验证：
```python
def on_input_changed(self, event: Input.Changed) -> None:
    if self.mode == CommandPaletteMode.ARG_INPUT:
        # 验证参数格式
        # 显示错误提示
        pass
```

### 2. 参数历史

记录用户输入过的参数，支持自动补全：
```python
if self.mode == CommandPaletteMode.ARG_INPUT:
    # 显示历史参数建议
    self._show_history_suggestions()
```

### 3. 多参数支持

某些命令可能需要多个参数，可以扩展为：
```python
ARG_INPUT_MULTI = "arg_input_multi"
# 使用表单或分步输入
```

## 影响范围

### 修改的文件

- `agentos/ui/widgets/command_palette.py` - 核心修改
- `agentos/ui/screens/home.py` - 事件处理修改

### 未修改的文件

- `agentos/ui/widgets/task_search_palette.py` - 保持不变
- `agentos/ui/commands.py` - 保持不变（Command 定义）

### 测试覆盖

建议添加以下测试：
```python
# tests/ui/test_command_palette_arg_input.py
def test_arg_input_mode_entry(pilot):
    """测试进入参数输入模式"""
    # 选择需要参数的命令
    # 验证进入 ARG_INPUT 模式
    # 验证 placeholder 更新

def test_arg_input_mode_submit(pilot):
    """测试提交参数"""
    # 进入参数输入模式
    # 输入参数
    # 按 Enter
    # 验证发送的事件包含参数

def test_arg_input_mode_cancel(pilot):
    """测试取消参数输入"""
    # 进入参数输入模式
    # 按 ESC
    # 验证返回 CATEGORY 模式
```

## 检查清单

- ✅ 添加 ARG_INPUT 模式
- ✅ CommandSelected 事件携带参数
- ✅ 参数输入流程完整（进入/提交/取消）
- ✅ Placeholder 动态更新
- ✅ Hint 文本动态更新
- ✅ Task 命令仍使用特殊 UI
- ✅ 其他命令使用通用参数输入
- ✅ 参数正确传递给命令处理器
- ✅ 无 linter 错误
- ✅ 向后兼容

## 总结

这次修复通过引入 **ARG_INPUT 模式**，彻底解决了需要参数的命令无法输入参数的问题。现在用户可以：

1. **选择命令** → 自动进入参数输入模式
2. **输入参数** → 清晰的 Placeholder 和 Hint
3. **提交执行** → Enter 键
4. **取消操作** → ESC 键

同时保留了 `TaskSearchPalette` 的特殊 UI，为不同类型的参数输入提供了最佳的用户体验。

**关键要点**:
1. **问题**: 需要参数的命令无法输入参数
2. **根因**: 缺少参数输入模式
3. **方案**: 添加 ARG_INPUT 模式
4. **结果**: 所有需要参数的命令都能正常使用

---

**状态**: ✅ 修复完成  
**创建日期**: 2026-01-26  
**作者**: AI Agent  
**相关文档**: 
- [ListView Duplicate ID Fix Report](./LISTVIEW_DUPLICATE_ID_FIX_REPORT.md)
- [TUI Development Guide](../../guides/developer/TUI_DEVELOPMENT_GUIDE.md)
