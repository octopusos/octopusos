# CommandPaletteMode.ARG_INPUT 缺失问题修复

## 问题描述

在运行 TUI 时出现以下错误：

```python
AttributeError: type object 'CommandPaletteMode' has no attribute 'ARG_INPUT'
```

**错误位置：**
- `agentos/ui/widgets/command_palette.py:81`
- 在 `_rebuild_list()` 方法中

## 根本原因

这是一个**代码不一致**的问题：

1. **使用的地方**：
   - `command_palette.py` 中多处使用了 `CommandPaletteMode.ARG_INPUT`
   - `home.py` 中也使用了这个模式值

2. **定义的地方**：
   - `CommandPaletteMode` 枚举只定义了两个值：
     - `CATEGORY = "category"`
     - `COMMANDS = "commands"`
   - **没有定义** `ARG_INPUT`

## 为什么会出现这个问题？

查看 Git 历史发现：

```bash
e65530a feat(ui): 添加 Command Palette 参数输入模式
```

在这个提交中，`command_palette.py` 添加了参数输入功能，使用了 `ARG_INPUT` 模式，但**忘记在枚举中定义这个值**。

这是一个常见的多文件协同更新时的遗漏问题。

## 修复方法

### 步骤 1：定位问题

```bash
# 搜索 ARG_INPUT 的使用
grep -r "ARG_INPUT" agentos/ui/
```

发现：
- ✅ `command_palette.py` 中有 5 处使用
- ✅ `home.py` 中有 1 处使用
- ❌ `commands.py` 中的枚举定义缺失

### 步骤 2：添加枚举值

在 `agentos/ui/commands.py` 中添加：

```python
class CommandPaletteMode(str, Enum):
    """命令面板模式"""
    CATEGORY = "category"      # 显示分类列表
    COMMANDS = "commands"       # 显示命令列表（某个分类或搜索结果）
    ARG_INPUT = "arg_input"     # 参数输入模式（等待用户输入命令参数）
```

### 步骤 3：验证修复

```python
# 测试 1：枚举值存在
from agentos.ui.commands import CommandPaletteMode
assert hasattr(CommandPaletteMode, 'ARG_INPUT')
assert CommandPaletteMode.ARG_INPUT.value == "arg_input"

# 测试 2：实例化成功
from agentos.ui.widgets.command_palette import CommandPalette
cp = CommandPalette()
assert cp.mode == CommandPaletteMode.CATEGORY

# 测试 3：模式比较正常
if cp.mode == CommandPaletteMode.ARG_INPUT:
    pass  # 不会执行，因为初始模式是 CATEGORY
```

## ARG_INPUT 模式的作用

`ARG_INPUT` 模式用于处理**需要参数的命令**：

### 工作流程

1. **用户选择命令**
   - 如果命令标记为 `needs_arg=True`
   - 命令面板进入 `ARG_INPUT` 模式

2. **等待参数输入**
   - 清空输入框
   - 更改提示文本为 "Enter argument for {command}..."
   - 用户输入参数

3. **执行命令**
   - 按 Enter 提交参数
   - 发送 `CommandSelected` 事件，带上参数
   - 返回 `CATEGORY` 模式

4. **取消操作**
   - 按 ESC 取消
   - 返回 `CATEGORY` 模式

### 使用示例

```python
# 在 command_palette.py 中

def action_accept(self):
    """Enter 接受选中项"""
    # 如果在参数输入模式，提交命令和参数
    if self.mode == CommandPaletteMode.ARG_INPUT:
        if self._pending_command:
            argument = self.query_text.strip()
            if argument:
                # 发送带参数的命令
                self.post_message(CommandSelected(self._pending_command, argument))
                # 重置状态
                self._reset_to_category()
        return
    
    # ... 其他模式的处理 ...
```

## 受影响的命令

所有标记为 `needs_arg=True` 的命令都需要这个模式：

### KB 命令
- `kb:search` - 需要查询字符串
- `kb:explain` - 需要 chunk_id
- `kb:inspect` - 需要 chunk_id
- `kb:eval` - 需要 queries_file

### Memory 命令
- `mem:search` - 需要查询字符串
- `mem:add` - 需要内容

### Task 命令
- `task:inspect` - 需要 task_id
- `task:resume` - 需要 task_id

## 最佳实践

为了避免这类问题，建议：

### 1. 枚举值管理
```python
# ✅ 好的做法：集中定义
class CommandPaletteMode(str, Enum):
    CATEGORY = "category"
    COMMANDS = "commands"
    ARG_INPUT = "arg_input"  # 记得添加新模式

# ❌ 坏的做法：硬编码字符串
if self.mode == "arg_input":  # 容易拼写错误
```

### 2. 类型检查
```python
# 使用类型提示
mode: CommandPaletteMode = CommandPaletteMode.CATEGORY

# IDE 会提示可用的枚举值
if mode == CommandPaletteMode.  # ← 自动补全
```

### 3. 测试覆盖
```python
# 测试所有模式
def test_all_modes():
    for mode in CommandPaletteMode:
        cp = CommandPalette()
        cp.mode = mode
        assert cp.mode == mode
```

## 总结

**问题**：`CommandPaletteMode` 缺少 `ARG_INPUT` 枚举值

**原因**：多文件更新时遗漏

**修复**：在枚举中添加 `ARG_INPUT = "arg_input"`

**影响**：所有需要参数的命令现在可以正常工作

**提交**：`e105c36 fix(ui): 添加缺失的 CommandPaletteMode.ARG_INPUT 枚举值`
