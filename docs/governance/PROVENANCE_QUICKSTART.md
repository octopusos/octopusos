# Provenance 快速开始

5 分钟了解 AgentOS Provenance（溯源）系统的基本使用。

## 什么是 Provenance？

Provenance 是 AgentOS 的能力溯源系统，为每个工具调用结果提供"法庭级别"的可追溯性。

它回答三个核心问题：
1. 这个结果从哪来？
2. 在什么环境执行的？
3. 信任级别如何？

## 快速演示

### 1. 运行演示脚本

```bash
python3 examples/provenance_demo.py
```

你会看到 6 个演示，展示 Provenance 系统的核心功能。

### 2. 运行测试

```bash
pytest tests/core/capabilities/test_provenance.py -v
```

所有 8 个测试应该通过。

## 基本使用

### 自动模式（推荐）

Provenance 由 Router 自动生成，你无需手动调用：

```python
from agentos.core.capabilities import ToolRouter

router = ToolRouter(registry)
result = await router.invoke_tool(tool_id, invocation)

# 结果自动包含 provenance
print(result.provenance.trust_tier)  # "T1"
print(result.provenance.execution_env.host)  # "localhost"
```

### 手动验证

如果需要，可以手动验证 provenance：

```python
from agentos.core.capabilities.provenance_validator import ProvenanceValidator

validator = ProvenanceValidator()

# 验证完整性
valid, error = validator.validate_completeness(result.provenance)
if not valid:
    print(f"Provenance incomplete: {error}")
```

### 按信任层级过滤

在决策时只使用高信任级别的结果：

```python
from agentos.core.capabilities.provenance_utils import filter_results_by_trust_tier
from agentos.core.capabilities.governance_models.provenance import TrustTier

# 只保留 T1 及以上信任级别
high_trust_results = filter_results_by_trust_tier(
    all_results,
    TrustTier.T1
)
```

## 信任层级

AgentOS 使用 4 级信任层级：

| 层级 | 名称 | 描述 | 示例 |
|------|------|------|------|
| T0 | 系统内置 | 最高信任 | 内置文件系统工具 |
| T1 | 经审核扩展 | 高信任 | 官方审核的扩展 |
| T2 | 用户扩展 | 中信任 | 用户安装的扩展 |
| T3 | 外部 MCP | 需谨慎 | 互联网上的 MCP 服务器 |

## 查看审计记录

### Python Logger

```python
import logging

logging.basicConfig(level=logging.INFO)
# 会看到 provenance_snapshot 事件
```

### TaskDB 查询

```sql
-- 查询特定工具的所有执行记录
SELECT * FROM task_audits
WHERE event_type = 'provenance_snapshot'
  AND json_extract(payload, '$.tool_id') = 'read_file'
ORDER BY created_at DESC;
```

## 常见问题

### Q: Provenance 会影响性能吗？

A: 影响很小。生成 provenance 只需要几毫秒，审计写入是异步的，不阻塞主流程。

### Q: 我可以禁用 Provenance 吗？

A: Provenance 是系统的核心功能，不建议禁用。但 `provenance` 字段是 Optional 的，不会强制要求。

### Q: Provenance 会存储敏感信息吗？

A: Provenance 记录执行环境信息（如工作目录），但不记录工具的输入/输出。如需脱敏，可以配置审计策略。

### Q: 如何自定义 Trust Tier？

A: 目前 Trust Tier 由 ToolDescriptor 的 `trust_tier` 字段指定。可以在注册工具时设置。

## 下一步

1. 阅读完整指南: [PROVENANCE_GUIDE.md](./PROVENANCE_GUIDE.md)
2. 查看实施总结: [PROVENANCE_IMPLEMENTATION_SUMMARY.md](./PROVENANCE_IMPLEMENTATION_SUMMARY.md)
3. 浏览测试用例: `tests/core/capabilities/test_provenance.py`
4. 运行演示脚本: `python3 examples/provenance_demo.py`

## 反馈

如有问题或建议，请联系 AgentOS 团队。
