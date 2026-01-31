# Command Palette Enter 键修复报告

## 问题描述

**症状**：
- 键盘导航（↑↓）正常工作
- Esc 键正常工作
- 但按 Enter 键没有任何反应

## 根本原因

Textual 的 `Input` 组件会**消费** Enter 键事件：
- 当焦点在 `Input` 上时，按 Enter 会触发 `Input.Submitted` 事件
- 这个事件**不会传播**到父组件的 `action_accept` 绑定
- 因此 `BINDINGS = [("enter", "accept", "Accept")]` 无法触发

## 解决方案

添加 `on_input_submitted` 事件处理器：

```python
def on_input_submitted(self, event: Input.Submitted) -> None:
    """监听 Input 的 Enter 事件"""
    self.action_accept()
```

### 工作原理

1. 用户在 Input 中按 Enter
2. Textual 触发 `Input.Submitted` 事件
3. `on_input_submitted` 捕获事件
4. 手动调用 `action_accept()`
5. `action_accept()` 发送 `CommandSelected` 消息
6. `HomeScreen` 接收并执行命令

## 修改文件

### `agentos/ui/widgets/command_palette.py`

**修改位置**：第 40-44 行

```python
# ---------- 输入处理 ----------
def on_input_changed(self, event: Input.Changed) -> None:
    self.query_text = event.value
    self._rebuild_list()

def on_input_submitted(self, event: Input.Submitted) -> None:
    """监听 Input 的 Enter 事件"""
    self.action_accept()
```

## 验证步骤

1. 启动 TUI：`python -m agentos.ui.main_tui`
2. 在 Command Palette 输入框中输入 `list`
3. 按 Enter ✅
4. 应该跳转到 Task List 页面

## Textual 事件系统说明

### Input 组件的标准事件

| 事件 | 触发时机 | 是否传播 |
|------|---------|---------|
| `Input.Changed` | 文本变化 | ✅ 传播 |
| `Input.Submitted` | 按 Enter | ❌ 不传播 |

### 最佳实践

对于 Input 组件：
- ✅ 使用 `on_input_submitted` 监听 Enter
- ❌ 不要依赖 `BINDINGS = [("enter", ...)]`

对于 ListView/其他组件：
- ✅ 使用 `BINDINGS` 处理键盘快捷键
- ✅ 事件会正常传播

## 相关文档

- [Textual Input Events](https://textual.textualize.io/widgets/input/#events)
- [Textual Message Handling](https://textual.textualize.io/guide/events/)

---

**修复时间**：2026-01-26  
**状态**：✅ 已修复  
**影响范围**：Command Palette Enter 键交互
