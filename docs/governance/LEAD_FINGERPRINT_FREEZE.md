# Lead Agent Fingerprint 生成规则冻结文档

## 变更摘要

**日期**: 2026-01-28
**状态**: 🔒 FROZEN (Snapshot Tested)
**影响范围**: LeadFinding fingerprint 生成逻辑

## 变更背景

### 问题

旧的 fingerprint 生成逻辑存在关键缺陷：

1. **包含具体时间戳**：旧实现包含 `window.start_ts` 和 `window.end_ts`
   ```python
   # ❌ 旧实现（有问题）
   parts = [rule_code, window.kind.value, window.start_ts, window.end_ts]
   ```

2. **导致重复 findings**：每天扫描相同风险会产生不同 fingerprint
   ```python
   # Day 1: fingerprint = hash("blocked_reason_spike|24h|2025-01-01|2025-01-02|...")
   # Day 2: fingerprint = hash("blocked_reason_spike|24h|2025-01-02|2025-01-03|...")
   # 结果：两个不同的 fingerprint，去重失败！
   ```

3. **24h/7d 混淆风险**：虽然包含 window.kind，但时间戳的存在让规则变得脆弱

### 目标

1. **正确去重**：相同规则 + 窗口类型 + 维度 → 相同 fingerprint（即使时间不同）
2. **避免混淆**：24h 和 7d 窗口必须产生不同 fingerprint
3. **幂等性**：确保 fingerprint 生成逻辑稳定、可预测
4. **冻结验证**：通过 snapshot 测试锁定逻辑，防止意外变更

## 新的 Fingerprint 生成规则

### 算法

```python
def generate_fingerprint(
    rule_code: str,
    window: ScanWindow,
    dimensions: Dict[str, Any]
) -> str:
    """
    生成幂等指纹 (FROZEN - Snapshot tested)

    fingerprint = SHA256(rule_code|window_kind|dimensions)[:16]

    ⚠️ CRITICAL: 只包含 window.kind，不包含 start_ts/end_ts
    """
    parts = [
        rule_code,
        window.kind.value,  # ✅ 只使用 window.kind（24h/7d），不使用具体时间
    ]

    # 添加排序后的维度（确保幂等性）
    for key in sorted(dimensions.keys()):
        parts.append(f"{key}={dimensions[key]}")

    input_str = "|".join(parts)
    return hashlib.sha256(input_str.encode()).hexdigest()[:16]
```

### 关键特性

| 特性 | 说明 | 示例 |
|------|------|------|
| **只包含 window.kind** | 不包含具体时间范围 | `24h` 或 `7d`，不包含 `2025-01-01` |
| **区分窗口类型** | 24h 和 7d 产生不同 fingerprint | `blocked_reason_spike\|24h\|...` ≠ `blocked_reason_spike\|7d\|...` |
| **幂等性** | 相同输入永远产生相同输出 | 今天扫描 = 明天扫描（去重生效） |
| **维度排序** | dimensions 按 key 排序 | `{a:1, b:2}` = `{b:2, a:1}` |

## Snapshot 测试锁定

### 锁定的 Fingerprint 值

以下 fingerprint 值已通过 snapshot 测试冻结：

| 规则 | 窗口 | 维度 | Fingerprint |
|------|------|------|-------------|
| `blocked_reason_spike` | 24h | `finding_code=NETWORK_TIMEOUT` | `cdb89e41216d9128` |
| `blocked_reason_spike` | 7d | `finding_code=NETWORK_TIMEOUT` | `f5b13c0a1407aa9e` |
| `pause_block_churn` | 24h | `task_id=task-123` | `8c55aee9ca31e774` |
| `high_risk_allow` | 7d | 空维度 | `4e7080891b7977f1` |
| `decision_lag_anomaly` | 24h | 空维度 | `bbbf6d5574ed170f` |

### 验证方法

```bash
# 运行 fingerprint 冻结测试
cd tests/unit/lead
python3 run_fingerprint_freeze_tests.py

# 期望输出：
# ✅ All fingerprint freeze tests passed!
#    Fingerprint generation logic is stable and locked.
```

### 测试覆盖范围

1. **结构测试** (4 tests)
   - 包含 rule_code
   - 包含 window_kind (24h vs 7d)
   - 包含 finding_code
   - 排除时间范围 (time-independent)

2. **幂等性测试** (2 tests)
   - 相同输入 → 相同输出
   - 跨重启一致性

3. **维度处理测试** (3 tests)
   - 多维度处理
   - 空维度处理
   - 维度顺序无关

4. **Snapshot 锁定测试** (5 tests)
   - 锁定 5 个典型场景的 fingerprint 值
   - 任何变更都会触发测试失败

5. **真实场景测试** (3 tests)
   - 每日扫描去重
   - 不同错误码区分
   - 24h/7d 窗口分离

## 变更对比

### Before (有问题)

```python
# ❌ 旧实现
parts = [
    rule_code,
    window.kind.value,
    window.start_ts,      # 🐛 问题：包含具体时间
    window.end_ts,        # 🐛 问题：包含具体时间
]
```

**问题示例**：
```python
# Day 1 扫描
fingerprint_day1 = hash("blocked_reason_spike|24h|2025-01-01T00:00:00Z|2025-01-02T00:00:00Z|finding_code=ERR1")
# → "abc123def456"

# Day 2 扫描（相同风险）
fingerprint_day2 = hash("blocked_reason_spike|24h|2025-01-02T00:00:00Z|2025-01-03T00:00:00Z|finding_code=ERR1")
# → "xyz789ghi012" (不同！去重失败)
```

### After (修复)

```python
# ✅ 新实现
parts = [
    rule_code,
    window.kind.value,    # ✅ 只包含 window.kind，不包含时间
]
```

**修复示例**：
```python
# Day 1 扫描
fingerprint_day1 = hash("blocked_reason_spike|24h|finding_code=ERR1")
# → "cdb89e41216d9128"

# Day 2 扫描（相同风险）
fingerprint_day2 = hash("blocked_reason_spike|24h|finding_code=ERR1")
# → "cdb89e41216d9128" (相同！去重成功)
```

## 影响分析

### 对现有数据的影响

⚠️ **历史 findings 的 fingerprint 会变化**

- **旧数据**：使用旧算法生成的 fingerprint（包含时间戳）
- **新数据**：使用新算法生成的 fingerprint（不包含时间戳）
- **结果**：旧 fingerprint 无法与新 fingerprint 匹配

### 迁移策略

**推荐方案**：不迁移历史数据

**理由**：
1. Lead Agent 是新功能，历史数据量小
2. 旧 fingerprint 本身有缺陷（会产生重复）
3. 新扫描会自动使用新算法，无需迁移

**如果确实需要迁移**：
```sql
-- 为历史 findings 重新计算 fingerprint
UPDATE lead_findings
SET fingerprint = new_calculate_fingerprint(rule_code, window_kind, evidence)
WHERE created_at < '2026-01-28';
```

### 对新功能的影响

✅ **正向影响**：

1. **去重更准确**：每日扫描不会产生重复 findings
2. **逻辑更清晰**：fingerprint 只包含"识别维度"，不包含"时间维度"
3. **维护更容易**：snapshot 测试确保逻辑稳定

## 验收标准

- ✅ fingerprint 包含 rule_code + window_kind + dimensions
- ✅ fingerprint 不包含 window.start_ts/end_ts
- ✅ snapshot 测试锁定 fingerprint 生成逻辑
- ✅ 同输入产生相同 fingerprint（幂等性测试）
- ✅ 不同 window 产生不同 fingerprint（24h vs 7d 测试）
- ✅ 文档说明 fingerprint 生成规则
- ✅ 所有现有测试仍然通过

## 测试结果

### Fingerprint Freeze Tests

```
======================================================================
🔒 Running Fingerprint Freeze Tests (Snapshot Tests)
======================================================================

1. Fingerprint Structure Tests
  ✓ 包含 rule_code
  ✓ 包含 window_kind (24h vs 7d)
  ✓ 包含 finding_code
  ✓ 排除时间范围 (time-independent)

2. Fingerprint Idempotence Tests
  ✓ 幂等性 (相同输入 → 相同输出)
  ✓ 确定性 (跨重启一致)

3. Fingerprint Dimension Handling Tests
  ✓ 多维度处理
  ✓ 空维度处理 (全局规则)
  ✓ 维度顺序无关

4. 🔒 Fingerprint Snapshot Lock Tests (FROZEN)
  ✓ Snapshot: blocked_reason_spike + 24h + NETWORK_TIMEOUT
  ✓ Snapshot: blocked_reason_spike + 7d + NETWORK_TIMEOUT
  ✓ Snapshot: pause_block_churn + 24h + task-123
  ✓ Snapshot: high_risk_allow + 7d + 空维度
  ✓ Snapshot: decision_lag_anomaly + 24h + 空维度

5. Real-World Scenario Tests
  ✓ 每日扫描产生相同 fingerprint (去重)
  ✓ 同一扫描的不同错误码
  ✓ 24h 和 7d 窗口分离

======================================================================
Test Summary: 17/17 passed
======================================================================
```

### Existing Miner Tests

```
============================================================
Running Lead Agent Miner Rules Tests
============================================================

Rule 1-6: All rules ✓
Integration & Quality: ✓

============================================================
Test Summary: 17/17 passed
============================================================
```

## 文件变更清单

### 修改的文件

1. **`agentos/core/lead/models.py`**
   - 更新 `LeadFinding.generate_fingerprint()` 方法
   - 移除 `window.start_ts` 和 `window.end_ts`
   - 添加详细注释和 docstring

2. **`docs/governance/lead_agent.md`**
   - 更新 "Fingerprint 机制" 章节
   - 添加详细算法说明和示例
   - 添加变更管理指南

### 新增的文件

1. **`tests/unit/lead/test_fingerprint_freeze.py`**
   - 17 个 fingerprint 冻结测试
   - 包含结构、幂等性、维度处理、snapshot、真实场景测试

2. **`tests/unit/lead/run_fingerprint_freeze_tests.py`**
   - 测试运行器脚本

3. **`docs/governance/LEAD_FINGERPRINT_FREEZE.md`** (本文档)
   - 完整的变更文档

## 未来维护指南

### 何时需要修改 Fingerprint 逻辑

**谨慎修改**！Fingerprint 变更会导致历史数据失效。

只在以下情况下修改：
1. 发现新的去重错误（误判或漏判）
2. 新增维度字段（需向后兼容）
3. 性能优化（保持输出不变）

### 如何安全修改

1. **更新实现**：修改 `generate_fingerprint()` 方法
2. **更新测试**：
   ```bash
   # 重新计算期望值
   python3 test_fingerprint_freeze.py

   # 更新 snapshot 测试中的 expected 值
   ```
3. **更新文档**：
   - 更新本文档
   - 记录变更原因
   - 更新 `lead_agent.md`
4. **数据迁移**：如果需要，编写迁移脚本

### 如何验证稳定性

```bash
# 定期运行 fingerprint 冻结测试（CI/CD）
cd tests/unit/lead
python3 run_fingerprint_freeze_tests.py

# 如果测试失败：
# ❌ 说明 fingerprint 逻辑已变更（可能是意外修改）
# → 检查代码变更
# → 如果是意外修改，回滚
# → 如果是有意修改，更新测试和文档
```

## 参考资料

- **ADR-004**: Supervisor Contract Freeze
- **测试文件**: `tests/unit/lead/test_fingerprint_freeze.py`
- **实现文件**: `agentos/core/lead/models.py`
- **设计文档**: `docs/governance/lead_agent.md`

---

**变更作者**: Claude Sonnet 4.5
**审核状态**: 待审核
**生效日期**: 2026-01-28
