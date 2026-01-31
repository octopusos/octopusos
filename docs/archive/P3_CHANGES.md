# P3 任务变更清单

## 删除的文件

### agentos/store/connection_factory.py
- **状态**: 完全删除
- **大小**: 259 行
- **原因**: 功能与 registry_db 完全重复，违反单一入口原则

## 修改的文件

### 1. agentos/store/__init__.py
**修改内容**:
- 删除 `from .connection_factory import ...` 导入
- 删除 `def get_db():` 函数定义（38 行）
- 添加 `__getattr__` 魔术方法实现懒加载
- 更新 `__all__` 导出列表注释

**关键改动**:
```python
# 删除
def get_db():
    # ... 38 行代码

# 添加
def __getattr__(name):
    if name == "get_db":
        from agentos.core.db.registry_db import get_db
        return get_db
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
```

### 2. agentos/core/db/registry_db.py
**修改内容**:
- 在 `get_db()` 函数中添加自动迁移逻辑

**关键改动**:
```python
def get_db() -> sqlite3.Connection:
    # ... existing code ...
    
    # 新增: 自动迁移
    try:
        from agentos.store.migrator import auto_migrate
        migrated = auto_migrate(Path(db_path))
        if migrated > 0:
            logger.info(f"Applied {migrated} pending migrations")
    except Exception as e:
        logger.warning(f"Auto-migration failed: {e}")
    
    # ... continue with connection ...
```

### 3. scripts/gates/gate_single_db_entry.py
**修改内容**:
- 添加 `_get_db_path` 检测模式到 `ENTRY_POINT_PATTERNS`
- 从 `EXPECTED_ENTRY_POINTS` 中移除不存在的 `_get_conn`

**关键改动**:
```python
# 添加
ENTRY_POINT_PATTERNS = [
    # ...
    (r"^def\s+_get_db_path\s*\(", "_get_db_path"),  # 新增
    # ...
]

# 修改
EXPECTED_ENTRY_POINTS = {
    "get_db": ["agentos/core/db/registry_db.py"],
    "_get_db_path": ["agentos/core/db/registry_db.py"],
    # 移除: "_get_conn": [...]
}
```

## Git 变更摘要

```bash
# 删除
D  agentos/store/connection_factory.py

# 修改
M  agentos/store/__init__.py
M  agentos/core/db/registry_db.py
M  scripts/gates/gate_single_db_entry.py

# 新增（文档）
A  P3_IMPLEMENTATION_REPORT.md
A  P3_SUMMARY.md
A  P3_CHANGES.md
```

## 影响范围

### 直接影响
- **删除**: 1 个文件（259 行）
- **修改**: 3 个文件
- **新增**: 3 个文档文件

### 间接影响
- **调用者**: 60+ 个文件使用 `from agentos.store import get_db`
- **需要修改**: 0 个（向后兼容）
- **破坏性变更**: 无

## 验证结果

```
✓ connection_factory.py 已删除
✓ 无 def get_db() 定义
✓ 包含 __getattr__ 懒加载
✓ registry_db.get_db() 包含自动迁移
✓ Gate 4 检查通过
✓ 向后兼容性测试通过
```

## 代码统计

| 指标 | 修改前 | 修改后 | 变化 |
|------|--------|--------|------|
| 未授权入口点 | 2 | 0 | -2 |
| connection_factory.py | 259 行 | 0 行 | -259 |
| store/__init__.py | ~200 行 | ~185 行 | -15 |
| registry_db.py | ~310 行 | ~325 行 | +15 |
| gate_single_db_entry.py | ~270 行 | ~275 行 | +5 |

## 兼容性

### 向后兼容
✓ 完全兼容 - 所有现有代码无需修改

### 前向迁移路径
推荐逐步迁移到新方式：
```python
# 从
from agentos.store import get_db

# 迁移到
from agentos.core.db import registry_db
conn = registry_db.get_db()
```

计划在 v0.5.0 移除 `agentos.store.get_db` 重导出。
