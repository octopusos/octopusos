# Guardian Contract

## Overview

Guardian Contract 定义了 GuardianVerdictSnapshot 的不可变契约,确保治理决策的可靠性和可审计性。

## Core Principle

**Verdict 是治理事实 (Governance Fact)**

一旦 GuardianVerdictSnapshot 被写入数据库,它就是不可改变的治理事实。所有后续决策都基于这个事实。

## GuardianVerdictSnapshot Contract

### Schema Definition

```python
@dataclass(frozen=True)
class GuardianVerdictSnapshot:
    verdict_id: str              # 唯一标识符
    assignment_id: str           # 关联的 assignment
    task_id: str                 # 被验证的任务
    guardian_code: str           # Guardian 标识
    status: VerdictStatus        # PASS | FAIL | NEEDS_CHANGES
    flags: list[dict[str, Any]]  # 问题标记列表
    evidence: dict[str, Any]     # 证据数据
    recommendations: list[str]   # 建议列表
    created_at: str              # 创建时间(ISO 8601)
```

### Field Constraints

#### verdict_id
- **类型**: `str`
- **格式**: `verdict_{12位hex}`
- **唯一性**: 全局唯一
- **生成**: 自动生成 (UUID)

#### assignment_id
- **类型**: `str`
- **必填**: 是
- **关联**: 必须对应有效的 GuardianAssignment

#### task_id
- **类型**: `str`
- **必填**: 是
- **关联**: 必须对应有效的 Task

#### guardian_code
- **类型**: `str`
- **必填**: 是
- **值域**: 注册在 GuardianRegistry 中的 Guardian code

#### status
- **类型**: `VerdictStatus`
- **必填**: 是
- **值域**:
  - `"PASS"` - 验证通过
  - `"FAIL"` - 验证失败
  - `"NEEDS_CHANGES"` - 需要修改

#### flags
- **类型**: `list[dict[str, Any]]`
- **必填**: 是(可以为空列表)
- **用途**: 记录验证过程中发现的问题
- **格式示例**:
```python
[
    {
        "severity": "critical",
        "code": "TEST_FAILURE",
        "message": "Unit test failed: test_login",
        "location": "tests/test_auth.py:42"
    },
    {
        "severity": "warning",
        "code": "COVERAGE_LOW",
        "message": "Code coverage below 80%",
        "actual": 65.5
    }
]
```

#### evidence
- **类型**: `dict[str, Any]`
- **必填**: 是(可以为空字典)
- **用途**: 存储验证证据(测试结果、日志、快照等)
- **格式示例**:
```python
{
    "test_results": {
        "passed": 45,
        "failed": 3,
        "skipped": 2
    },
    "execution_time_ms": 1234,
    "log_url": "s3://logs/task-123/test.log",
    "artifacts": ["coverage.xml", "test-report.html"]
}
```

#### recommendations
- **类型**: `list[str]`
- **必填**: 是(可以为空列表)
- **用途**: 给出可操作的建议
- **格式**: 清晰、具体、可执行的建议
- **示例**:
```python
[
    "Fix failing test: test_login in tests/test_auth.py",
    "Increase code coverage to >80% by adding tests",
    "Review security scan findings in evidence.security_report"
]
```

#### created_at
- **类型**: `str`
- **格式**: ISO 8601 with timezone (e.g., `2024-01-28T10:30:00+00:00`)
- **生成**: 自动生成
- **时区**: UTC

## Immutability Contract

### Frozen Dataclass

```python
@dataclass(frozen=True)
class GuardianVerdictSnapshot:
    # ...
```

**Implications:**
- 创建后任何字段都不可修改
- 尝试修改会抛出 `FrozenInstanceError`
- 必须通过创建新 Verdict 来表达新的验证结果

### Why Immutable?

1. **审计性** - 保证历史记录不被篡改
2. **可追溯** - 每个决策都有明确的依据
3. **并发安全** - 避免竞态条件
4. **信任** - 建立治理信任基础

## Validation Rules

### Schema Validation

```python
def validate_verdict_snapshot(obj: dict[str, Any]) -> None:
    """验证 verdict snapshot 格式"""
    required_fields = [
        "verdict_id", "assignment_id", "task_id",
        "guardian_code", "status", "flags",
        "evidence", "recommendations", "created_at"
    ]

    # Check required fields
    for field in required_fields:
        if field not in obj:
            raise ValueError(f"Missing required field: {field}")

    # Validate status
    if obj["status"] not in ["PASS", "FAIL", "NEEDS_CHANGES"]:
        raise ValueError(f"Invalid status: {obj['status']}")

    # Validate types
    if not isinstance(obj["flags"], list):
        raise ValueError("flags must be a list")
    if not isinstance(obj["evidence"], dict):
        raise ValueError("evidence must be a dict")
    if not isinstance(obj["recommendations"], list):
        raise ValueError("recommendations must be a list")
```

### Business Logic Validation

1. **assignment_id 存在性检查**
   - Verdict 必须关联到有效的 Assignment
   - 防止孤儿 Verdict

2. **task_id 存在性检查**
   - Task 必须存在于数据库中
   - 防止针对不存在任务的 Verdict

3. **guardian_code 有效性检查**
   - Guardian 必须在 GuardianRegistry 中注册
   - 防止来自未知 Guardian 的 Verdict

## Change Policy

### Versioning Strategy

#### Schema Version
当前版本: `v1.0.0`

#### Breaking Changes

如果需要修改 schema,必须:
1. 增加 schema version (e.g., `v2.0.0`)
2. 保持向后兼容(支持读取旧版本)
3. 提供迁移工具
4. 更新文档

#### Non-Breaking Changes

可以安全添加:
- 新的可选字段(带默认值)
- flags/evidence 中的新字段
- recommendations 中的新格式

### Deprecation Policy

1. **公告期**: 至少 2 个版本周期
2. **兼容期**: 旧版本至少支持 6 个月
3. **迁移工具**: 提供自动迁移脚本
4. **文档**: 清晰标注 deprecated 字段

## Serialization

### To Dict

```python
verdict.to_dict() -> dict[str, Any]
```

返回可序列化的字典,用于:
- JSON API 响应
- 数据库存储
- 日志记录

### From Dict

```python
GuardianVerdictSnapshot(**verdict_dict)
```

从字典重建 Verdict,用于:
- 数据库读取
- API 请求解析
- 测试构造

### Database Storage

Verdict 在数据库中的存储格式:

```sql
CREATE TABLE guardian_verdicts (
    verdict_id TEXT PRIMARY KEY,
    assignment_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    guardian_code TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    verdict_json TEXT NOT NULL  -- 完整的 verdict.to_dict() JSON
);
```

**Design Rationale:**
- `verdict_json` 存储完整 snapshot,确保不丢失信息
- 核心字段提取为列,方便查询和索引
- JSON 字段提供灵活性,支持未来扩展

## Usage Examples

### Creating a Verdict

```python
from agentos.core.governance.guardian.models import GuardianVerdictSnapshot

verdict = GuardianVerdictSnapshot.create(
    assignment_id="assignment_abc123",
    task_id="task_xyz789",
    guardian_code="smoke_test",
    status="PASS",
    flags=[],
    evidence={
        "test_results": {"passed": 50, "failed": 0}
    },
    recommendations=[]
)
```

### Validating a Verdict

```python
from agentos.core.governance.guardian.models import validate_verdict_snapshot

# From external source
verdict_dict = {
    "verdict_id": "verdict_abc123",
    "assignment_id": "assignment_abc123",
    "task_id": "task_xyz789",
    "guardian_code": "smoke_test",
    "status": "PASS",
    "flags": [],
    "evidence": {},
    "recommendations": [],
    "created_at": "2024-01-28T10:30:00+00:00"
}

validate_verdict_snapshot(verdict_dict)  # Raises ValueError if invalid
```

### Saving to Database

```python
import json

cursor.execute(
    """
    INSERT INTO guardian_verdicts (
        verdict_id, assignment_id, task_id, guardian_code,
        status, created_at, verdict_json
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    (
        verdict.verdict_id,
        verdict.assignment_id,
        verdict.task_id,
        verdict.guardian_code,
        verdict.status,
        verdict.created_at,
        json.dumps(verdict.to_dict())
    )
)
```

### Loading from Database

```python
import json

cursor.execute(
    "SELECT verdict_json FROM guardian_verdicts WHERE verdict_id = ?",
    (verdict_id,)
)
row = cursor.fetchone()
verdict_dict = json.loads(row[0])
verdict = GuardianVerdictSnapshot(**verdict_dict)
```

## Migration Example

### Adding a New Field (v1.1.0)

```python
@dataclass(frozen=True)
class GuardianVerdictSnapshot:
    # ... existing fields ...
    schema_version: str = "v1.1.0"  # New field with default
    metadata: dict[str, Any] = field(default_factory=dict)  # New optional field
```

### Reading Old Format

```python
def load_verdict(verdict_dict: dict) -> GuardianVerdictSnapshot:
    # Auto-upgrade old format
    if "schema_version" not in verdict_dict:
        verdict_dict["schema_version"] = "v1.0.0"
    if "metadata" not in verdict_dict:
        verdict_dict["metadata"] = {}

    return GuardianVerdictSnapshot(**verdict_dict)
```

## Related Documentation
- [Guardian Workflow](./guardian_workflow.md)
- [Verification Runbook](./verification_runbook.md)
