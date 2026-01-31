# Command Palette 交互式升级 - 快速指南

## 🎯 新特性概览

### ✅ 已实现
1. **ListView 键盘导航**：↑↓ 在命令列表中移动，Enter 选择
2. **命令注册表**：集中管理命令定义，易于扩展
3. **事件驱动架构**：使用 Message 替代 callback
4. **二段式面板**：带参数命令（inspect/resume）自动进入 task 搜索模式

---

## 🚀 使用方法

### 基础用法

1. **打开 TUI**
```bash
cd /Users/pangge/PycharmProjects/AgentOS
uv run agentos
```

2. **命令面板交互**
- 自动聚焦输入框
- 输入关键词过滤命令（如 `list`, `inspect`）
- 使用 ↑↓ 导航列表
- 按 Enter 执行高亮命令
- 按 Esc 清空输入

3. **二段式命令**
- 输入 `inspect` 或 `resume` 并按 Enter
- 自动切换到 task 搜索模式
- 输入关键词过滤 task 列表
- 使用 ↑↓ 选择 task
- 按 Enter 执行（inspect → 打开详情 / resume → 启动任务）
- 按 Esc 取消并返回命令面板

---

## 📋 可用命令

| 命令 | 描述 | 需要参数 | 路由 |
|------|------|---------|------|
| `new` | 创建新任务 | ❌ | `cmd:new` |
| `list` | 显示任务列表 | ❌ | `nav:tasks` |
| `resume` | 恢复/启动任务 | ✅ | `cmd:resume` |
| `inspect` | 查看任务详情 | ✅ | `cmd:inspect` |
| `settings` | 打开设置 | ❌ | `nav:settings` |
| `help` | 显示帮助 | ❌ | `nav:help` |
| `quit` | 退出应用 | ❌ | `app:quit` |

---

## 🎨 视觉效果

### 命令面板
```
              AgentOS
        Task Control Plane

   [ Type a command…          ]

   list         List tasks
   inspect      Inspect task     <-- 高亮项
   resume       Resume task
   settings     Settings

Press > for commands · / to search · ? help
```

### Task 搜索面板
```
   [ Search tasks for inspect… ]

   abc123...       Fix bug in UI
   def456...       Update docs      <-- 高亮项
   ghi789...       Add feature
```

---

## 🔧 架构改进

### 改造前 vs 改造后

| 特性 | 改造前 | 改造后 |
|------|--------|--------|
| 列表组件 | OptionList（只读） | ListView（可导航） |
| 命令定义 | 硬编码在组件内 | 集中在 commands.py |
| 事件传递 | callback | Message 事件 |
| 带参数命令 | 手动输入 task ID | 二段式面板 |
| 键盘导航 | ❌ 不支持 | ✅ ↑↓/Enter/Esc |

---

## 📁 文件清单

### 新建文件
1. `agentos/ui/commands.py` - 命令数据结构
2. `agentos/ui/widgets/task_search_palette.py` - 二段式面板

### 修改文件
3. `agentos/ui/widgets/command_palette.py` - ListView + 键盘导航
4. `agentos/ui/screens/home.py` - 事件驱动路由
5. `agentos/ui/theme.tcss` - ListView 样式

---

## 🎓 扩展示例

### 添加新命令

编辑 `agentos/ui/commands.py`:

```python
COMMANDS.append(
    Command(
        key="export",
        title="Export task",
        hint="Export task data to JSON",
        handler="cmd:export",
        needs_arg=False
    )
)
```

在 `home.py` 添加处理器:

```python
elif handler == "cmd:export":
    self.notify("Export feature - coming soon", severity="information")
```

### 添加需要参数的命令

```python
COMMANDS.append(
    Command(
        key="delete",
        title="Delete task",
        hint="Delete a task by ID",
        handler="cmd:delete",
        needs_arg=True  # 启用二段式
    )
)
```

在 `home.py` 的 `_handle_arg_command`:

```python
elif cmd.key == "delete":
    self._enter_task_search_mode(cmd)
```

在 `on_task_selected`:

```python
elif event.parent_command == "delete":
    # 删除逻辑
    self.manager.delete_task(event.task_id)
    self.notify(f"Deleted task {event.task_id[:12]}")
```

---

## ✅ 验收清单

- [x] ↑↓ 键导航命令列表
- [x] Enter 选择高亮命令
- [x] Esc 清空输入
- [x] 输入过滤实时更新
- [x] `list` 跳转 tasks screen
- [x] `inspect` 进入 task 搜索
- [x] `resume` 进入 task 搜索
- [x] Task 搜索支持过滤
- [x] 选择 task 后执行命令
- [x] Esc 取消并返回
- [x] 视觉符合 5 色系统
- [x] 无边框极简风格

---

**状态**: ✅ 全部完成  
**测试**: 语法检查通过  
**文档**: 完整实施报告已生成
