# Task #1 快速参考 - Mode Policy Engine

## 状态: ✅ 已完成

## 核心文件

```
agentos/core/mode/mode_policy.py  (460 行)
```

## 快速导入

```python
# 导入核心类
from agentos.core.mode.mode_policy import ModePolicy, ModePermissions

# 导入全局策略管理
from agentos.core.mode.mode_policy import (
    get_global_policy,
    set_global_policy,
    load_policy_from_file
)

# 导入便捷函数
from agentos.core.mode.mode_policy import (
    check_mode_permission,
    get_mode_permissions
)

# 或者从 mode 模块直接导入
from agentos.core.mode import ModePolicy, get_global_policy
```

## 使用示例

### 1. 基本权限检查

```python
policy = ModePolicy()

# 检查 commit 权限
policy.check_permission("implementation", "commit")  # True
policy.check_permission("design", "commit")          # False

# 检查 diff 权限
policy.check_permission("implementation", "diff")    # True
policy.check_permission("design", "diff")            # False
```

### 2. 获取完整权限配置

```python
perms = policy.get_permissions("implementation")

print(perms.mode_id)             # "implementation"
print(perms.allows_commit)       # True
print(perms.allows_diff)         # True
print(perms.allowed_operations)  # {"read", "write", "execute", "commit", "diff"}
print(perms.risk_level)          # "high"
```

### 3. 使用全局策略

```python
# 获取全局策略（自动初始化）
policy = get_global_policy()

# 或使用便捷函数
if check_mode_permission("implementation", "commit"):
    print("允许 commit")
```

### 4. 加载自定义策略

```python
from pathlib import Path

# 从文件加载并设置为全局策略
policy = load_policy_from_file(Path("./policy.json"))

# 或手动创建并设置
custom_policy = ModePolicy(Path("./policy.json"))
set_global_policy(custom_policy)
```

## 默认策略配置

| Mode          | allows_commit | allows_diff | risk_level |
|---------------|---------------|-------------|------------|
| implementation| ✅ True       | ✅ True     | high       |
| design        | ❌ False      | ❌ False    | low        |
| chat          | ❌ False      | ❌ False    | low        |
| planning      | ❌ False      | ❌ False    | low        |
| debug         | ❌ False      | ❌ False    | low        |
| ops           | ❌ False      | ❌ False    | low        |
| test          | ❌ False      | ❌ False    | low        |
| release       | ❌ False      | ❌ False    | low        |

## JSON 策略文件格式

```json
{
    "version": "1.0",
    "modes": {
        "implementation": {
            "allows_commit": true,
            "allows_diff": true,
            "allowed_operations": ["read", "write", "execute", "commit", "diff"],
            "risk_level": "high"
        },
        "custom_mode": {
            "allows_commit": false,
            "allows_diff": false,
            "allowed_operations": ["read"],
            "risk_level": "low"
        }
    }
}
```

## API 参考

### ModePermissions (dataclass)

```python
@dataclass
class ModePermissions:
    mode_id: str
    allows_commit: bool = False
    allows_diff: bool = False
    allowed_operations: Set[str] = field(default_factory=set)
    risk_level: str = "low"  # low/medium/high/critical
```

### ModePolicy

```python
class ModePolicy:
    def __init__(self, policy_path: Optional[Path] = None)
    def get_permissions(self, mode_id: str) -> ModePermissions
    def check_permission(self, mode_id: str, permission: str) -> bool
    def get_all_modes(self) -> Set[str]
    def get_policy_version(self) -> str
```

### 全局函数

```python
def get_global_policy() -> ModePolicy
def set_global_policy(policy: ModePolicy) -> None
def load_policy_from_file(policy_path: Path) -> ModePolicy
def check_mode_permission(mode_id: str, permission: str) -> bool
def get_mode_permissions(mode_id: str) -> ModePermissions
```

## 安全特性

1. **未知 mode 安全默认**:
   ```python
   perms = policy.get_permissions("unknown_mode")
   # 返回: allows_commit=False, allows_diff=False, risk_level="low"
   ```

2. **回退机制**: 策略文件加载失败时自动使用默认策略

3. **风险等级验证**: 无效的 risk_level 自动降级为 "low"

## 验证测试

```bash
# 运行验证脚本
python3 test_mode_policy_verification.py

# 预期输出: ALL 10 TESTS PASSED
```

## 下一步

- [ ] Task #2: 创建策略配置文件和 JSON Schema
- [ ] Task #3: 集成策略引擎到 mode.py
- [ ] Task #5: 编写单元测试
- [ ] Task #6: Gate GM3 验证

## 相关文档

- 完整实现报告: `TASK1_MODE_POLICY_IMPLEMENTATION_REPORT.md`
- 源代码: `agentos/core/mode/mode_policy.py`
- 验证脚本: `test_mode_policy_verification.py`
