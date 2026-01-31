# ID 冒号错误修复完成

## 问题
Textual 的 Widget ID 不允许使用冒号 `:` 字符，只能使用字母、数字、下划线和连字符。

## 错误位置
1. `command_palette.py:54` - `id=f"cmd:{cmd.key}"`
2. `task_search_palette.py:75` - `id=f"task:{task.task_id}"`

## 修复内容

### 修改 1: command_palette.py
```python
# 修改前
item = ListItem(Label(text), id=f"cmd:{cmd.key}")

# 修改后
item = ListItem(Label(text), id=f"cmd-{cmd.key}")
```

### 修改 2: task_search_palette.py
```python
# 修改前
item = ListItem(Label(text), id=f"task:{task.task_id}")

# 修改后
item = ListItem(Label(text), id=f"task-{task.task_id}")
```

## 验证结果
- [x] Python 语法检查通过
- [x] 两个文件均修复完成
- [x] 符合 Textual ID 规范

## 根因
在实施过程中使用了类似命名空间的 `cmd:key` 格式，但忽略了 Textual 要求 ID 必须符合 CSS ID 选择器规范。

## 影响范围
- 仅影响两个文件
- 不影响功能逻辑
- 不影响事件处理

---

**修复完成**: 2026-01-26  
**状态**: ✅ 通过验证
