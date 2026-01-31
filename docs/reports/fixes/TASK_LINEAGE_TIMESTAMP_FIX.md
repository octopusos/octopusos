# TaskLineageEntry Timestamp 属性修复报告

**修复日期**: 2026-01-27  
**问题等级**: P1 - 高优先级  
**状态**: ✅ 已修复并提交

## 问题描述

### 错误表现

在 TUI 的任务检查页面（Inspect Screen）加载 timeline 时出现错误：

```
Error loading timeline: 'TaskLineageEntry' object has no attribute 'timestamp'
```

### 根本原因

代码中存在字段命名不一致的问题：

1. **模型定义**: `TaskLineageEntry` 类中定义的字段名为 `created_at`
2. **UI 代码**: `agentos/ui/screens/inspect.py` 中访问 `entry.timestamp`
3. **CLI 代码**: `agentos/cli/interactive.py` 中访问 `entry.timestamp`
4. **数据库**: Schema 中使用 `created_at` 字段

### 影响范围

- ❌ TUI Timeline 显示功能无法使用
- ❌ CLI 任务跟踪相关功能报错
- ❌ 所有依赖 `TaskLineageEntry.timestamp` 的代码

## 技术分析

### 代码位置

1. **模型定义** (`agentos/core/task/models.py:78-97`)

```python
@dataclass
class TaskLineageEntry:
    task_id: str
    kind: str
    ref_id: str
    phase: Optional[str] = None
    created_at: Optional[str] = None  # ❌ 与使用不一致
    metadata: Dict[str, Any] = field(default_factory=dict)
```

2. **UI 使用** (`agentos/ui/screens/inspect.py:130`)

```python
timestamp = self._format_datetime(entry.timestamp)  # ❌ 访问不存在的属性
```

3. **CLI 使用** (`agentos/cli/interactive.py:372`)

```python
print(f"{i}. [{entry.kind}] {entry.ref_id} @ {entry.timestamp}")  # ❌ 访问不存在的属性
```

4. **数据加载** (`agentos/core/task/manager.py:315`)

```python
entries.append(TaskLineageEntry(
    task_id=row["task_id"],
    kind=row["kind"],
    ref_id=row["ref_id"],
    phase=row["phase"],
    created_at=row["created_at"],  # 从数据库加载
    metadata=metadata,
))
```

### 数据库 Schema

```sql
CREATE TABLE IF NOT EXISTS task_lineage (
    ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ...
);
```

## 修复方案

### 方案选择

考虑了两种方案：

1. **方案 A**: 将模型字段改为 `timestamp`
   - ✅ 与代码使用一致
   - ✅ 语义更清晰（timestamp vs created_at）
   - ⚠️ 需要处理数据库字段映射

2. **方案 B**: 将代码中的 `timestamp` 改为 `created_at`
   - ✅ 与数据库字段一致
   - ❌ 需要修改多处代码
   - ❌ `timestamp` 语义更适合 lineage entry

**选择方案 A**，理由：
- `timestamp` 更符合 lineage entry 的语义（事件时间戳）
- 大部分代码已经使用 `timestamp`
- 通过字段映射可以保持数据库兼容性

### 实现细节

#### 1. 修改模型定义

```python
@dataclass
class TaskLineageEntry:
    """Single lineage entry"""
    
    task_id: str
    kind: str
    ref_id: str
    phase: Optional[str] = None
    timestamp: Optional[str] = None  # ✅ 主字段改为 timestamp
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # ✅ 添加向后兼容别名
    @property
    def created_at(self) -> Optional[str]:
        """Alias for timestamp (backward compatibility)"""
        return self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "ref_id": self.ref_id,
            "phase": self.phase,
            "created_at": self.timestamp,  # ✅ 保持数据库兼容性
            "metadata": self.metadata,
        }
```

**关键设计**:
- 主字段使用 `timestamp`
- 添加 `created_at` 作为 `@property` 别名，保持向后兼容
- `to_dict()` 返回 `created_at`，保持数据库 schema 兼容

#### 2. 修改数据加载

```python
entries.append(TaskLineageEntry(
    task_id=row["task_id"],
    kind=row["kind"],
    ref_id=row["ref_id"],
    phase=row["phase"],
    timestamp=row["created_at"],  # ✅ 映射数据库字段
    metadata=metadata,
))
```

#### 3. 统一代码使用

```python
# CLI (task.py)
timestamp = entry.timestamp[:19] if entry.timestamp else "N/A"  # ✅ 统一使用 timestamp
```

## 测试验证

### 单元测试

```python
from agentos.core.task.models import TaskLineageEntry

# 测试 1: 基本属性访问
entry = TaskLineageEntry(
    task_id='test', 
    kind='test', 
    ref_id='test', 
    timestamp='2024-01-01'
)

assert entry.timestamp == '2024-01-01'  # ✅
assert entry.created_at == '2024-01-01'  # ✅ 别名正常工作

# 测试 2: 字典序列化
dict_data = entry.to_dict()
assert dict_data['created_at'] == '2024-01-01'  # ✅ 数据库兼容
```

### 集成测试

- ✅ TUI Timeline 加载正常
- ✅ CLI 任务跟踪正常
- ✅ 数据库读写正常
- ✅ 向后兼容性保持

## 影响文件

### 修改文件

1. `agentos/core/task/models.py`
   - 将 `created_at` 字段改为 `timestamp`
   - 添加 `created_at` property 别名
   - 修改 `to_dict()` 方法

2. `agentos/core/task/manager.py`
   - 修改数据加载时的字段映射
   - `created_at=row["created_at"]` → `timestamp=row["created_at"]`

3. `agentos/cli/task.py`
   - 统一使用 `entry.timestamp`
   - `entry.created_at` → `entry.timestamp`

### Git Commit

```
Commit: 6c2eda9
Message: fix(task): 修复 TaskLineageEntry timestamp 属性错误
```

## 兼容性保证

### 向后兼容

- ✅ 旧代码使用 `entry.created_at` 仍然有效（通过 property 别名）
- ✅ 数据库 schema 无需修改（`to_dict()` 返回 `created_at`）
- ✅ JSON 序列化格式保持不变

### 迁移路径

**无需迁移**，修复透明兼容：

1. 数据库 schema 不变
2. 旧代码访问 `created_at` 仍然有效
3. 新代码使用 `timestamp` 更语义化

## 经验总结

### 问题根源

1. **命名不一致**: 模型定义和代码使用不一致
2. **缺少类型检查**: 如果有 mypy/pyright 检查会提前发现
3. **测试覆盖不足**: UI 代码缺少集成测试

### 改进建议

#### 1. 代码质量工具

```bash
# 启用静态类型检查
mypy agentos/

# 启用 linter
ruff check agentos/
```

#### 2. 测试覆盖

```python
# 添加 TaskLineageEntry 单元测试
def test_task_lineage_entry_timestamp():
    entry = TaskLineageEntry(...)
    assert entry.timestamp is not None
    assert entry.created_at == entry.timestamp
```

#### 3. 命名规范

建立统一的字段命名规范：
- 事件时间戳统一使用 `timestamp`
- 对象创建时间使用 `created_at`
- Lineage entry 使用 `timestamp`（事件时间点）

## 后续行动

### 立即行动

- [x] 修复 `TaskLineageEntry.timestamp` 问题
- [x] 验证 TUI Timeline 功能
- [x] 验证 CLI 任务跟踪功能
- [x] 提交修复代码
- [x] 创建修复报告

### 后续改进

- [ ] 添加 `TaskLineageEntry` 单元测试
- [ ] 启用静态类型检查（mypy/pyright）
- [ ] 增加 UI 组件集成测试覆盖
- [ ] 审查其他模型的字段命名一致性
- [ ] 建立字段命名规范文档

## 参考资料

- 数据库 Schema: `agentos/store/schema_v06.sql`
- 相关模型: `agentos/core/task/models.py`
- 错误位置: `agentos/ui/screens/inspect.py`

---

**修复人**: AI Agent  
**审核**: 待审核  
**状态**: ✅ 已修复并验证
