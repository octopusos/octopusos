# ADR-006: 策略演化安全机制

**状态**: ✅ 已接受  
**日期**: 2026-01-25  
**决策者**: AgentOS 架构团队

## 背景

ExecutionPolicy 是 AgentOS 的核心控制机制，但目前是静态的：
- 无法根据历史效果调整
- 无法适应不同项目特点
- 参数都是人工配置

需要让 Policy 可演化，但必须满足：可审计、可冻结、可回滚。

## 决策

引入策略演化引擎（Policy Evolution Engine），但施加严格约束。

### 1. PolicyLineage（策略血缘）

每次 policy 变化必须记录完整血缘：

```json
{
  "policy_id": "pol-v2-abc123",
  "parent_policy_id": "pol-v1-def456",
  "source_learning_pack_id": "learn-789",
  "diff": {
    "changed": {
      "max_files_per_commit": {"old": 5, "new": 8}
    },
    "added": {},
    "removed": {}
  },
  "effective_from": "2026-01-26T00:00:00Z",
  "effective_until": "2026-02-26T00:00:00Z",  // canary 期限
  "rollback_conditions": {
    "failure_rate_threshold": 0.15,
    "min_runs": 10
  },
  "status": "canary",  // canary | active | frozen | rolled_back
  "applied_to": {
    "project_ids": ["test-project"],
    "task_types": ["frontend"]
  }
}
```

### 2. 演化目标（受限范围）

只允许演化以下参数：

| 参数 | 初始值 | 演化范围 | 触发条件 |
|------|--------|----------|----------|
| `max_files_per_commit` | 5 | [3, 20] | 历史 review 密度 |
| `retry_budget` | 3 | [1, 5] | 失败频率 |
| `aggressive_safe.allow_operations` | [] | 白名单扩展 | 成功率 > 95% |
| `question_budget` | 3 | [1, 5] | blocker 频率 |

**禁止演化**:
- execution_mode（interactive/semi_auto/full_auto）
- risk_profile 核心定义
- forbidden_operations（安全红线）

### 3. Canary 机制

新 policy 必须先 canary：

```
新 Policy 产生
    ↓
应用到 canary 环境（指定 project/task）
    ↓
监控 min_runs 次执行
    ↓
[达标] → promote 到 active
[不达标] → rollback
[手动] → freeze（冻结当前状态）
```

**达标标准**:
- 成功率 >= baseline * 0.95
- 无 critical 失败
- review 通过率 >= 90%

### 4. 安全约束

**硬规则**:
1. Policy 演化必须绑定 LearningPack（可追溯）
2. 演化幅度受限（不能跳跃式变化）
3. Canary 期间可随时 rollback
4. Frozen policy 不可演化（稳定版本）
5. 所有演化产出 review_pack（审计）

**Rollback 条件**:
```python
if failure_rate > threshold:
    auto_rollback()

if critical_failure_count > 0:
    auto_rollback()

# 人工触发
agentos policy rollback --policy-id pol-v2-abc123
```

### 5. 版本管理

```
pol-v1 (baseline, frozen)
    ↓ (演化)
pol-v2 (canary, test-project)
    ↓ (promote)
pol-v2 (active, all projects)
    ↓ (演化)
pol-v3 (canary, ...)
```

## 演化流程

```
LearningPack 产出
    ↓
提取 Policy Patch
    ↓
[Policy Validator] 检查是否在允许范围
    ↓
创建新 Policy (parent=当前, status=canary)
    ↓
应用到 canary 环境
    ↓
监控 min_runs
    ↓
[达标] → promote | [不达标] → rollback
```

## 护城河扩展

**新增约束**:
- Policy 演化必须 canary + lineage + rollback
- 演化参数必须在白名单内
- Frozen policy 不可变
- 所有变更可审计（diff + source）

## 验收标准

- [ ] PolicyLineage 记录完整
- [ ] Canary 机制可用（promote/rollback）
- [ ] 演化只在白名单参数内
- [ ] Rollback 可触发（auto + manual）
- [ ] 所有演化产出 review_pack

---

**相关**: ADR-004, ADR-005
