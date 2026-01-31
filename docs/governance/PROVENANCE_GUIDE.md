# Provenance Guide

## 概述

Provenance（溯源）系统为 AgentOS 的每个能力调用结果提供"法庭级别"的可追溯性。它回答三个核心问题：

1. **这个结果从哪来？** - 追踪到具体的能力来源、版本
2. **在什么环境执行的？** - 记录完整的执行环境信息
3. **信任级别如何？** - 根据来源自动分配信任层级

## 核心价值

### 1. 可审计性（Auditability）

每个结果都带有完整的溯源信息，可以追溯到：
- 具体的工具和版本
- 执行的时间和环境
- 信任层级和来源

### 2. 可回放性（Replayability）

通过溯源信息，可以：
- 判断是否可以在当前环境回放
- 检测环境变化对结果的影响
- 进行跨环境的结果比较

### 3. 决策支持（Decision Support）

在做决策时：
- 按信任层级过滤结果
- 验证结果来源的合法性
- 比较不同来源的结果差异

## 数据模型

### ProvenanceStamp

溯源戳记录了能力调用的完整溯源信息：

```python
from agentos.core.capabilities.models.provenance import ProvenanceStamp

provenance = ProvenanceStamp(
    capability_id="mcp:filesystem:read_file",  # 能力 ID
    tool_id="read_file",                       # 工具名称
    capability_type="mcp",                      # 类型（extension/mcp）
    source_id="filesystem",                     # 来源 ID
    source_version="1.0.0",                     # 来源版本
    execution_env=execution_env,                # 执行环境
    trust_tier="T1",                            # 信任层级
    timestamp=datetime.now(),                   # 时间戳
    invocation_id="inv_123",                    # 调用 ID
    task_id="task_456",                         # 任务 ID（可选）
    project_id="proj_789",                      # 项目 ID（可选）
    spec_hash="abc123"                          # 规范哈希（可选）
)
```

### ExecutionEnv

执行环境信息：

```python
from agentos.core.capabilities.models.provenance import ExecutionEnv

env = ExecutionEnv(
    host="localhost",                 # 主机名
    pid=12345,                        # 进程 ID
    container_id="abc123",            # 容器 ID（如果在容器中）
    python_version="3.11.0",          # Python 版本
    agentos_version="0.3.0",          # AgentOS 版本
    platform="Darwin-23.0.0-arm64",   # 平台信息
    cwd="/Users/user/project"         # 工作目录
)
```

### TrustTier

信任层级（从高到低）：

- **T0**: 系统内置能力（最高信任）
- **T1**: 经过审核的扩展（高信任）
- **T2**: 用户安装的扩展（中信任）
- **T3**: 外部 MCP 服务器（需谨慎）

## 使用场景

### 场景 1: 自动溯源记录

Router 在每次工具调用时自动生成和记录 provenance：

```python
from agentos.core.capabilities import ToolRouter
from agentos.core.capabilities.capability_models import ToolInvocation

router = ToolRouter(registry)

# 调用工具
invocation = ToolInvocation(
    invocation_id="inv_123",
    tool_id="mcp:filesystem:read_file",
    inputs={"path": "/tmp/test.txt"},
    actor="user@example.com",
    timestamp=datetime.now()
)

result = await router.invoke_tool("mcp:filesystem:read_file", invocation)

# 结果自动包含 provenance
print(result.provenance.trust_tier)  # "T1"
print(result.provenance.execution_env.host)  # "localhost"
```

### 场景 2: 验证溯源完整性

```python
from agentos.core.capabilities.provenance_validator import ProvenanceValidator

validator = ProvenanceValidator()

# 验证完整性
valid, error = validator.validate_completeness(result.provenance)
if not valid:
    print(f"Provenance incomplete: {error}")

# 验证结果一致性
valid, error = validator.validate_consistency(result.provenance, result)
if not valid:
    print(f"Inconsistent: {error}")
```

### 场景 3: 按信任层级过滤结果

在决策时只使用高信任级别的结果：

```python
from agentos.core.capabilities.provenance_utils import filter_results_by_trust_tier
from agentos.core.capabilities.models.provenance import TrustTier

# 多个工具的结果
results = [result1, result2, result3]

# 只保留 T1 及以上信任级别
high_trust_results = filter_results_by_trust_tier(results, TrustTier.T1)

# 用于决策
for result in high_trust_results:
    print(f"Using result from {result.provenance.source_id}")
```

### 场景 4: 验证结果来源

确保结果来自预期的能力来源：

```python
from agentos.core.capabilities.provenance_utils import verify_result_origin

# 验证结果来自特定 extension
is_valid = verify_result_origin(
    result,
    expected_source_id="tools.postman",
    expected_trust_tier=TrustTier.T1
)

if not is_valid:
    print("Result source mismatch!")
```

### 场景 5: 比较不同环境的结果

分析同一工具在不同环境的行为差异：

```python
from agentos.core.capabilities.provenance_utils import compare_results_by_env

# 收集不同环境的结果
results = [dev_result, staging_result, prod_result]

# 生成环境对比报告
report = compare_results_by_env(results)

print(f"Total environments: {report['total_environments']}")
for env_key, env_results in report['environments'].items():
    host, platform = env_key
    print(f"Environment: {host} ({platform}) - {len(env_results)} results")
```

### 场景 6: 判断可回放性

```python
from agentos.core.capabilities.models.provenance import get_current_env

# 获取当前环境
current_env = get_current_env()

# 判断历史结果是否可以在当前环境回放
can_replay, reason = validator.can_replay(
    historical_result.provenance,
    current_env
)

if can_replay:
    print("Can replay this result in current environment")
else:
    print(f"Cannot replay: {reason}")
```

## Audit 集成

Provenance 自动集成到审计系统：

### 1. Python Logger

所有 provenance 快照记录到 Python logger：

```python
logger.info(
    "Provenance snapshot",
    extra={
        "event_type": "provenance_snapshot",
        "invocation_id": provenance.invocation_id,
        "tool_id": provenance.tool_id,
        "source_id": provenance.source_id,
        "trust_tier": provenance.trust_tier,
        "execution_env": provenance.execution_env.model_dump(),
        "timestamp": provenance.timestamp.isoformat()
    }
)
```

### 2. TaskDB task_audits 表

如果有 task_id，provenance 自动写入 task_audits 表：

```sql
SELECT * FROM task_audits
WHERE event_type = 'provenance_snapshot'
  AND task_id = 'task_456';
```

## 最佳实践

### 1. 始终检查 provenance

在使用工具结果前，检查是否有 provenance：

```python
if result.provenance is None:
    logger.warning("Result missing provenance information")
else:
    logger.info(f"Result trust tier: {result.provenance.trust_tier}")
```

### 2. 根据信任层级调整行为

```python
if result.provenance.trust_tier == TrustTier.T3.value:
    # 外部 MCP，需要额外验证
    logger.warning("Result from external MCP, verify carefully")
    # 可能需要人工审核或额外的验证步骤
elif result.provenance.trust_tier == TrustTier.T0.value:
    # 系统内置，高度信任
    logger.info("Result from built-in capability, high trust")
```

### 3. 记录环境变化

如果环境发生变化，记录在审计日志中：

```python
env_before = result1.provenance.execution_env
env_after = result2.provenance.execution_env

if env_before.agentos_version != env_after.agentos_version:
    logger.warning(
        f"AgentOS version changed: {env_before.agentos_version} -> {env_after.agentos_version}"
    )
```

### 4. 保留历史 provenance

在长期运行的系统中，保留历史 provenance 用于：
- 趋势分析
- 环境漂移检测
- 版本升级影响分析

## API 参考

### get_current_env()

```python
def get_current_env() -> ExecutionEnv
```

获取当前执行环境信息。

**返回**: ExecutionEnv 对象

### ProvenanceValidator

#### validate_completeness(provenance)

```python
def validate_completeness(self, provenance: ProvenanceStamp) -> Tuple[bool, Optional[str]]
```

验证溯源信息完整性。

**参数**:
- `provenance`: ProvenanceStamp 对象

**返回**: (valid, error_message)

#### validate_consistency(provenance, result)

```python
def validate_consistency(
    self,
    provenance: ProvenanceStamp,
    result: ToolResult
) -> Tuple[bool, Optional[str]]
```

验证溯源与结果的一致性。

**参数**:
- `provenance`: ProvenanceStamp 对象
- `result`: ToolResult 对象

**返回**: (valid, error_message)

#### can_replay(provenance, current_env)

```python
def can_replay(
    self,
    provenance: ProvenanceStamp,
    current_env: ExecutionEnv
) -> Tuple[bool, Optional[str]]
```

判断是否可以在当前环境回放。

**参数**:
- `provenance`: 原始溯源信息
- `current_env`: 当前环境

**返回**: (can_replay, reason)

### Provenance Utils

#### filter_results_by_trust_tier(results, min_trust_tier)

```python
def filter_results_by_trust_tier(
    results: List[ToolResult],
    min_trust_tier: TrustTier
) -> List[ToolResult]
```

根据信任层级过滤结果。

**参数**:
- `results`: ToolResult 列表
- `min_trust_tier`: 最低信任层级

**返回**: 过滤后的结果列表

#### verify_result_origin(result, expected_source_id, expected_trust_tier)

```python
def verify_result_origin(
    result: ToolResult,
    expected_source_id: str,
    expected_trust_tier: Optional[TrustTier] = None
) -> bool
```

验证结果来源。

**参数**:
- `result`: ToolResult 对象
- `expected_source_id`: 预期来源 ID
- `expected_trust_tier`: 预期信任层级（可选）

**返回**: 是否匹配

#### compare_results_by_env(results)

```python
def compare_results_by_env(results: List[ToolResult]) -> dict
```

比较不同环境的结果。

**参数**:
- `results`: ToolResult 列表

**返回**: 环境对比报告字典

## 安全考虑

1. **Provenance 不可篡改**: Provenance 在生成后不应被修改
2. **环境信息敏感**: 某些环境信息可能包含敏感路径，注意脱敏
3. **信任但验证**: 即使有高信任级别，也应进行适当的验证
4. **审计留存**: Provenance 信息应长期保留用于审计

## 未来扩展

- **加密签名**: 对 provenance 进行加密签名，防止篡改
- **区块链集成**: 将关键 provenance 写入区块链
- **时间戳服务**: 集成时间戳服务，确保时间准确性
- **跨系统溯源**: 支持跨 AgentOS 实例的溯源追踪
