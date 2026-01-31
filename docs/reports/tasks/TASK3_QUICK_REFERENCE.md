# Task #3 快速参考指南

## 一句话总结
将 `mode.py` 中硬编码的权限检查替换为基于 `mode_policy.py` 的策略引擎。

---

## 核心修改

### 1. 导入策略引擎
```python
from .mode_policy import get_global_policy
```

### 2. 修改权限检查方法

**Before（硬编码）**：
```python
return self.mode_id == "implementation"
```

**After（策略驱动）**：
```python
policy = get_global_policy()
return policy.check_permission(self.mode_id, "commit")  # 或 "diff"
```

---

## 快速验证

### 运行验证脚本
```bash
python3 verify_task3_simple.py
```

### 期望输出
```
🎉 所有测试通过！Task #3 已成功完成！
```

---

## 关键行为

| Mode | allows_commit() | allows_diff() |
|------|----------------|---------------|
| implementation | ✅ True | ✅ True |
| 其他所有 | ❌ False | ❌ False |

**重要**：默认行为与修改前完全一致！

---

## 文件清单

### 修改的文件
- `agentos/core/mode/mode.py` (3 处修改)

### 依赖文件
- `agentos/core/mode/mode_policy.py`
- `configs/mode/default_policy.json`
- `configs/mode/strict_policy.json`
- `configs/mode/dev_policy.json`

### 验证脚本
- `verify_task3_simple.py`

---

## 代码示例

### 基本使用
```python
from agentos.core.mode.mode import get_mode

mode = get_mode("implementation")
print(mode.allows_commit())  # True
print(mode.allows_diff())    # True
```

### 自定义策略
```python
from pathlib import Path
from agentos.core.mode.mode_policy import load_policy_from_file

# 加载自定义策略
load_policy_from_file(Path("configs/mode/strict_policy.json"))

# 所有 mode 现在使用新策略
```

---

## 架构图

```
Mode.allows_commit/diff()
      ↓
get_global_policy()
      ↓
ModePolicy.check_permission()
      ↓
JSON 策略文件配置
```

---

## 验收标准检查清单

- [x] mode.py 可正常导入
- [x] implementation 允许 commit/diff
- [x] 其他 mode 禁止 commit/diff
- [x] 向后兼容性验证通过
- [x] 所有测试用例通过

---

## 相关任务

- Task #1: 创建 mode_policy.py ✅
- Task #2: 创建策略配置文件 ✅
- **Task #3: 集成策略引擎** ✅ (当前)
- Task #4: 创建配置指南 ⏸️
- Task #5: 编写单元测试 ⏸️

---

## 故障排查

### Q: 导入错误
A: 确保 `mode_policy.py` 在同一目录下

### Q: 权限检查失败
A: 检查策略文件配置，确保 implementation 的 allows_commit 和 allows_diff 都为 true

### Q: 向后兼容性问题
A: 默认策略确保行为一致，如有问题请运行验证脚本

---

**完成日期**: 2026-01-29
**状态**: ✅ 已完成
