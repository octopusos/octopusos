# Supervisor 契约白名单快速参考

> **目的**：快速查阅 Lead Agent 依赖的 Supervisor 事件和 payload 字段白名单。
>
> **详细文档**：[Lead Agent 设计文档 - Supervisor 事件依赖白名单](./lead_agent.md#supervisor-事件依赖白名单)
>
> **测试文件**：`tests/unit/lead/test_supervisor_contract.py`

## 版本信息

- **契约版本**: v1.0.0
- **最后更新**: 2025-01-28
- **状态**: 🔒 LOCKED（通过测试锁定）

## 事件类型白名单

| Event Type | 必需? | 关联规则 |
|-----------|------|---------|
| `SUPERVISOR_BLOCKED` | ✅ | 规则1,3 |
| `SUPERVISOR_PAUSED` | ✅ | 规则2 |
| `SUPERVISOR_RETRY_RECOMMENDED` | ✅ | 规则3 |
| `SUPERVISOR_DECISION` | ✅ | 规则4,5 |
| `SUPERVISOR_ALLOWED` | ✅ | 规则6 |

## Payload 字段白名单

### 通用字段（所有事件必需）

```python
{
  "decision_id": str,      # ✅ 必需
  "decision_type": str,    # ✅ 必需 (allow/pause/block/retry)
  "timestamp": str,        # ✅ 必需 (ISO8601)
  "findings": list,        # ✅ 必需 (可以为空列表)
  "reason": str,           # ❌ 可选
}
```

### SUPERVISOR_BLOCKED 特定字段

```python
{
  "findings": [
    {
      "code": str,         # ✅ 必需 - 规则1: blocked_reason_spike
      "kind": str,         # ❌ 可选 - 规则5: redline_ratio_increase
      "severity": str,     # ❌ 可选
    }
  ]
}
```

### SUPERVISOR_DECISION 特定字段

```python
{
  "source_event_ts": str,  # ✅ 必需 - 规则4: decision_lag_anomaly
  # 延迟计算: lag_ms = (timestamp - source_event_ts) * 1000
}
```

### SUPERVISOR_ALLOWED 特定字段

```python
{
  "findings": [
    {
      "severity": str,     # ✅ 必需 - 规则6: high_risk_allow
      # 有效值: LOW, MEDIUM, HIGH, CRITICAL
    }
  ]
}
```

## 兼容性速查表

| 变更类型 | 兼容性 | 处理方式 |
|---------|--------|---------|
| 新增字段 | ✅ 兼容 | Lead Agent 使用 `.get()` 安全访问 |
| 删除字段 | ❌ 破坏性 | 必须同步更新 Lead Agent |
| 重命名字段 | ❌ 破坏性 | 必须同步更新 Lead Agent |
| 修改枚举值 | ❌ 破坏性 | 必须同步更新 Lead Agent |
| 新增事件类型 | ✅ 兼容 | Lead Agent 只查询白名单事件 |
| 删除事件类型 | ❌ 破坏性 | 必须同步更新 Lead Agent |

## 测试命令

```bash
# 运行契约测试
. .venv/bin/activate
python -m pytest tests/unit/lead/test_supervisor_contract.py -v

# 验证通过标志
✓ 15 passed in 0.08s
```

## 破坏性变更检测

如果 Supervisor 变更导致以下测试失败，说明存在破坏性变更：

```python
# 测试：Supervisor 删除了必需事件类型
test_supervisor_has_not_removed_required_events
# 失败信息：
# ❌ BREAKING CHANGE DETECTED!
# Supervisor removed required event types: {'SUPERVISOR_BLOCKED'}

# 测试：事件类型定义不一致
test_event_types_match_supervisor_constants
# 失败信息：
# Whitelist contains events not defined in Supervisor: ...

# 测试：Fixture 缺少必需字段
test_blocked_event_fixture_has_required_fields
# 失败信息：
# BLOCKED event fixture missing required common field: decision_id
```

## 规则与字段映射

| 规则代码 | 依赖事件 | 依赖字段 |
|---------|---------|---------|
| blocked_reason_spike | SUPERVISOR_BLOCKED | findings[].code |
| pause_block_churn | SUPERVISOR_PAUSED, SUPERVISOR_BLOCKED | event_type 序列 |
| retry_recommended_but_fails | SUPERVISOR_RETRY_RECOMMENDED, SUPERVISOR_BLOCKED | event_type 序列, findings[].code |
| decision_lag_anomaly | SUPERVISOR_DECISION | source_event_ts, timestamp |
| redline_ratio_increase | SUPERVISOR_DECISION | findings[].kind |
| high_risk_allow | SUPERVISOR_ALLOWED | findings[].severity |

## Payload 示例

### BLOCKED 事件

```json
{
  "decision_id": "dec_abc123",
  "decision_type": "block",
  "timestamp": "2025-01-28T10:00:00Z",
  "findings": [
    {
      "code": "REDLINE_001",
      "severity": "HIGH",
      "kind": "REDLINE"
    }
  ]
}
```

### DECISION 事件（用于延迟计算）

```json
{
  "decision_id": "dec_def456",
  "decision_type": "allow",
  "timestamp": "2025-01-28T10:00:05Z",
  "source_event_ts": "2025-01-28T10:00:00Z",
  "findings": []
}
```

### ALLOWED 事件（高风险场景）

```json
{
  "decision_id": "dec_ghi789",
  "decision_type": "allow",
  "timestamp": "2025-01-28T10:00:00Z",
  "findings": [
    {
      "severity": "HIGH"
    }
  ]
}
```

## 版本升级清单

修改 Supervisor 事件或 payload 结构时，按以下清单操作：

- [ ] 评估变更是否涉及白名单
- [ ] 确定是否为破坏性变更
- [ ] 运行 `test_supervisor_contract.py`
- [ ] 如果测试失败，同步更新 Lead Agent：
  - [ ] 更新 `LeadStorage` 查询逻辑
  - [ ] 更新 `ContractMapper` 转换层
  - [ ] 更新测试 fixture
  - [ ] 更新白名单定义
- [ ] 更新契约版本号（如果是破坏性变更）
- [ ] 协调发布（Supervisor + Lead Agent）

## 常见错误

### 错误 1：静默失效（findings=0）

**原因**：Supervisor 删除了白名单中的字段，但 Lead Agent 查询仍然成功（返回空结果）。

**检测**：运行 `test_supervisor_contract.py`，检查 `test_supervisor_has_not_removed_required_events` 是否通过。

**修复**：同步更新 Lead Agent 的查询逻辑，或恢复 Supervisor 中被删除的字段。

### 错误 2：KeyError 异常

**原因**：直接访问可选字段（`payload["optional_field"]`）而不是使用 `.get()`。

**检测**：运行 `test_use_safe_dict_access_for_optional_fields` 验证访问模式。

**修复**：使用 `.get()` 方法：`payload.get("optional_field", default_value)`。

### 错误 3：契约版本不匹配

**原因**：Storage 和 Miner 的契约版本号不一致。

**检测**：运行 Lead Agent 扫描时会自动检查版本号。

**修复**：同步更新 `LeadStorage.CONTRACT_VERSION` 和 `RiskMiner.CONTRACT_VERSION`。

## 联系方式

- **文档维护者**：Lead Agent Team
- **问题反馈**：创建 Issue 并标记 `lead-agent` 标签
- **紧急联系**：Slack #lead-agent-alerts

## 参考链接

- [Lead Agent 完整设计文档](./lead_agent.md)
- [契约测试源码](../../tests/unit/lead/test_supervisor_contract.py)
- [Supervisor Audit Schema](../../agentos/core/supervisor/audit_schema.py)
- [LeadStorage 实现](../../agentos/core/lead/adapters/storage.py)
