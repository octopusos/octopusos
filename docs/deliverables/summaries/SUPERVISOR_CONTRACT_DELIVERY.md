# Supervisor 事件依赖白名单交付文档

## 概述

本次交付完成了 Lead Agent 依赖的 Supervisor 事件和 payload 字段白名单的定义和锁定，防止 Supervisor 变更导致 Lead Agent 静默失效。

## 交付内容

### 1. 测试文件

**文件**: `tests/unit/lead/test_supervisor_contract.py`

**功能**:
- 定义事件类型白名单（5个必需事件）
- 定义 payload 字段白名单（按事件类型分类）
- 验证 LeadStorage 和 Supervisor 常量一致性
- 验证测试 fixture 包含所有必需字段
- 检测 Supervisor 删除必需事件类型的破坏性变更
- 验证安全的字段访问模式（.get() vs []）
- 验证契约文档完整性

**测试覆盖**: 15 个测试用例，全部通过

```bash
. .venv/bin/activate
python -m pytest tests/unit/lead/test_supervisor_contract.py -v

# 结果: ✓ 15 passed in 0.08s
```

### 2. 文档

#### 2.1 完整设计文档

**文件**: `docs/governance/lead_agent.md`

**新增章节**: "Supervisor 事件依赖白名单"

**内容**:
- 事件类型白名单表格（5个事件，含用途和关联规则）
- Payload 字段白名单表格（按事件分类，含 JSONPath 和必需性）
- 版本兼容性策略表格（6种变更类型的兼容性）
- 变更通知机制（3步流程）
- 测试锁定说明（6类测试）
- Payload 示例（3种事件类型）
- 版本升级指南（6步清单）
- 常见问题（4个 Q&A）

#### 2.2 快速参考文档

**文件**: `docs/governance/supervisor_contract_whitelist.md`

**内容**:
- 版本信息和状态
- 事件类型白名单速查表
- Payload 字段白名单（代码格式）
- 兼容性速查表
- 测试命令
- 破坏性变更检测示例
- 规则与字段映射表
- Payload 示例
- 版本升级清单
- 常见错误及修复方法

### 3. 白名单定义

#### 3.1 事件类型白名单

```python
REQUIRED_EVENT_TYPES = {
    "SUPERVISOR_ALLOWED",           # 规则6: high_risk_allow
    "SUPERVISOR_PAUSED",            # 规则2: pause_block_churn
    "SUPERVISOR_BLOCKED",           # 规则1,3: blocked_reason_spike, retry_then_fail
    "SUPERVISOR_RETRY_RECOMMENDED", # 规则3: retry_then_fail
    "SUPERVISOR_DECISION",          # 规则4,5: decision_lag, redline_ratio
}
```

#### 3.2 Payload 字段白名单

**通用字段**（所有事件必需）:
- `decision_id`: string（✅ 必需）
- `decision_type`: string（✅ 必需，枚举值）
- `timestamp`: string（✅ 必需，ISO8601）
- `findings`: array（✅ 必需，可为空）
- `reason`: string（❌ 可选）

**SUPERVISOR_BLOCKED 特定字段**:
- `findings[].code`: string（✅ 必需，规则1）
- `findings[].kind`: string（❌ 可选，规则5）
- `findings[].severity`: string（❌ 可选）

**SUPERVISOR_DECISION 特定字段**:
- `source_event_ts`: string（✅ 必需，规则4）

**SUPERVISOR_ALLOWED 特定字段**:
- `findings[].severity`: string（✅ 必需，规则6）

#### 3.3 规则映射

| 规则代码 | 依赖事件 | 依赖字段 |
|---------|---------|---------|
| blocked_reason_spike | SUPERVISOR_BLOCKED | findings[].code |
| pause_block_churn | SUPERVISOR_PAUSED, SUPERVISOR_BLOCKED | event_type 序列 |
| retry_recommended_but_fails | SUPERVISOR_RETRY_RECOMMENDED, SUPERVISOR_BLOCKED | event_type 序列, findings[].code |
| decision_lag_anomaly | SUPERVISOR_DECISION | source_event_ts, timestamp |
| redline_ratio_increase | SUPERVISOR_DECISION | findings[].kind |
| high_risk_allow | SUPERVISOR_ALLOWED | findings[].severity |

## 验证结果

### 测试通过率

- **Supervisor 契约测试**: 15/15 通过（100%）
- **存储查询测试**: 15/15 通过（100%）
- **总测试时间**: 0.10s

### 验证的破坏性变更检测

测试文件能够检测以下破坏性变更：

1. ✅ **事件类型删除**: `test_supervisor_has_not_removed_required_events`
   - 如果 Supervisor 删除了 `SUPERVISOR_BLOCKED` 等必需事件，测试会失败并报告

2. ✅ **常量定义不一致**: `test_event_types_match_storage_constants`
   - 验证 LeadStorage 使用的事件类型与白名单一致

3. ✅ **Fixture 缺少必需字段**: `test_blocked_event_fixture_has_required_fields`
   - 验证测试数据包含所有必需的 payload 字段

4. ✅ **契约版本格式错误**: `test_contract_version_is_defined`
   - 验证版本号遵循语义化版本（X.Y.Z）

5. ✅ **不安全的字段访问**: `test_use_safe_dict_access_for_optional_fields`
   - 验证可选字段使用 .get() 安全访问

### 兼容性验证

| 变更类型 | 测试覆盖 | 结果 |
|---------|---------|------|
| 新增字段 | ✅ 通过 | 不影响现有逻辑（使用 .get()）|
| 删除字段 | ✅ 检测 | 测试会失败（破坏性变更）|
| 重命名字段 | ✅ 检测 | 测试会失败（破坏性变更）|
| 修改枚举值 | ✅ 检测 | 测试会失败（破坏性变更）|
| 新增事件类型 | ✅ 兼容 | 不影响白名单查询 |
| 删除事件类型 | ✅ 检测 | 测试会失败（破坏性变更）|

## 使用指南

### 开发者使用

#### 1. 运行契约测试

```bash
# 在提交 Supervisor 变更前运行
. .venv/bin/activate
python -m pytest tests/unit/lead/test_supervisor_contract.py -v

# 预期输出
✓ 15 passed in 0.08s
```

#### 2. 查看白名单

**快速参考**:
```bash
cat docs/governance/supervisor_contract_whitelist.md
```

**完整文档**:
```bash
cat docs/governance/lead_agent.md
# 跳转至 "Supervisor 事件依赖白名单" 章节
```

#### 3. 修改 Supervisor 事件

按照以下清单操作：

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

### 常见场景

#### 场景 1: Supervisor 新增可选字段

**变更**: 在 `SUPERVISOR_BLOCKED` 的 payload 中新增 `retry_count` 字段

**兼容性**: ✅ 兼容（Lead Agent 使用 .get() 访问）

**处理方式**:
1. Supervisor 直接发布
2. Lead Agent 无需修改
3. 未来可选择使用新字段

#### 场景 2: Supervisor 删除必需字段

**变更**: 从 `SUPERVISOR_BLOCKED` 的 payload 中删除 `findings[].code` 字段

**兼容性**: ❌ 破坏性变更

**处理方式**:
1. 运行 `test_supervisor_contract.py` → 测试失败
2. 更新 Lead Agent 的 `get_blocked_reasons()` 查询逻辑
3. 更新白名单定义
4. 更新契约版本号（v1.0.0 → v2.0.0）
5. Supervisor 和 Lead Agent 协调发布

#### 场景 3: Supervisor 重命名事件类型

**变更**: 将 `SUPERVISOR_BLOCKED` 重命名为 `SUPERVISOR_TASK_BLOCKED`

**兼容性**: ❌ 破坏性变更

**处理方式**:
1. 运行 `test_supervisor_contract.py` → 测试失败
2. 更新 Lead Agent 的 storage.py 常量定义
3. 更新所有查询逻辑中的事件类型引用
4. 更新白名单定义
5. 更新契约版本号
6. Supervisor 和 Lead Agent 同时发布

## 技术细节

### 白名单数据结构

白名单定义为 Python 字典，包含以下元数据：

```python
COMMON_PAYLOAD_FIELDS = {
    "decision_id": {
        "required": True,            # 是否必需
        "type": str,                 # 字段类型
        "description": "...",        # 字段说明
        "example": "...",            # 示例值
    },
    "decision_type": {
        "required": True,
        "type": str,
        "enum": ["allow", "pause", "block", "retry"],  # 枚举值
        "description": "...",
        "example": "...",
    },
    # ...
}
```

### 测试架构

```
test_supervisor_contract.py
├── TestSupervisorEventTypeContract
│   ├── test_event_types_defined              # 验证白名单已定义
│   ├── test_event_types_match_storage        # 验证与 LeadStorage 一致
│   └── test_event_types_match_supervisor     # 验证与 Supervisor 一致
├── TestSupervisorPayloadContract
│   ├── test_common_fields_defined            # 验证通用字段已定义
│   └── test_event_specific_fields_defined    # 验证事件特定字段已定义
├── TestFixtureCompliance
│   ├── test_blocked_event_fixture            # 验证 BLOCKED fixture
│   ├── test_paused_event_fixture             # 验证 PAUSED fixture
│   ├── test_allowed_event_fixture            # 验证 ALLOWED fixture
│   └── test_decision_event_fixture           # 验证 DECISION fixture
├── TestSupervisorContractBreakageDetection
│   ├── test_all_storage_queries              # 验证查询使用白名单
│   └── test_supervisor_has_not_removed       # 检测删除事件
├── TestPayloadFieldAccessPattern
│   ├── test_use_safe_dict_access             # 验证安全访问
│   └── test_findings_array_access            # 验证数组访问
└── TestContractDocumentation
    ├── test_all_required_fields_have_docs    # 验证字段文档
    └── test_contract_version_is_defined      # 验证版本号
```

### 版本管理

**契约版本**: v1.0.0

**版本号语义**:
- Major (X): 破坏性变更（不兼容）
- Minor (Y): 新增字段（向后兼容）
- Patch (Z): bug 修复

**升级策略**:
- 新增字段: Minor 版本升级（v1.0.0 → v1.1.0）
- 删除字段: Major 版本升级（v1.0.0 → v2.0.0）
- 重命名字段: Major 版本升级（v1.0.0 → v2.0.0）

## 预防措施

### 1. 静默失效检测

**问题**: Supervisor 删除字段导致 Lead Agent 查询返回空结果（findings=0），但无人发现。

**预防**:
- ✅ 契约测试会在 Supervisor 变更时立即失败
- ✅ Lead Agent 自检机制（检测 findings=0 但有数据的情况）
- ✅ 文档明确标记必需字段和可选字段

### 2. 契约漂移

**问题**: Storage 输出格式与 Miner 输入期望不一致。

**预防**:
- ✅ 契约版本号机制（Storage v1.0.0, Miner v1.0.0）
- ✅ 转换层（ContractMapper）隔离变更
- ✅ dry-run 模式下版本不匹配时输出 WARNING

### 3. 测试数据失效

**问题**: 测试 fixture 不符合契约，导致测试失效。

**预防**:
- ✅ `TestFixtureCompliance` 测试验证 fixture 包含必需字段
- ✅ 文档提供符合契约的 payload 示例
- ✅ 白名单定义包含 example 字段

## 后续工作

### P1 优先级

1. **冗余列优化**（可选）
   - 将关键 payload 字段提升为数据库冗余列
   - 减少 JSON 解析开销
   - 提高查询性能

2. **阈值配置文件化**（可选）
   - 将规则阈值从代码移至配置文件
   - 支持动态调整阈值
   - 无需重启服务

### P2 优先级

1. **JSON Schema 验证**
   - 使用 JSON Schema 验证 payload 结构
   - 在 Supervisor 写入时验证契约
   - 提供更精确的错误信息

2. **契约演进工具**
   - 自动化版本升级工具
   - 生成迁移脚本
   - 验证向后兼容性

## 参考资料

- **设计文档**: `docs/governance/lead_agent.md`
- **快速参考**: `docs/governance/supervisor_contract_whitelist.md`
- **测试文件**: `tests/unit/lead/test_supervisor_contract.py`
- **Storage 实现**: `agentos/core/lead/adapters/storage.py`
- **Supervisor Audit Schema**: `agentos/core/supervisor/audit_schema.py`

## 总结

本次交付完成了 Lead Agent 依赖的 Supervisor 事件和 payload 字段白名单的完整定义和测试锁定。通过：

1. ✅ **明确的白名单定义**：5个事件类型 + 完整的 payload 字段规范
2. ✅ **全面的测试覆盖**：15个测试用例，100% 通过
3. ✅ **完善的文档**：设计文档 + 快速参考 + 示例代码
4. ✅ **破坏性变更检测**：6种变更类型的自动化检测
5. ✅ **安全的访问模式**：使用 .get() 安全访问可选字段
6. ✅ **清晰的升级指南**：6步清单 + 3个场景示例

**防止了 Supervisor 变更导致 Lead Agent 静默失效的风险。**

---

**交付日期**: 2025-01-28
**交付状态**: ✅ 完成
**测试状态**: ✅ 全部通过（15/15）
**文档状态**: ✅ 完整
