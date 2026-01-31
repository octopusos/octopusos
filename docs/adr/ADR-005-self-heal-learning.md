# ADR-005: 自愈与学习机制

**状态**: ✅ 已接受  
**日期**: 2026-01-25  
**决策者**: AgentOS 架构团队

## 背景

AgentOS v0.2 中，任务失败只会标记为 FAILED：
- 无失败分类
- 无自动恢复机制
- 无从失败中学习的能力

这导致：
- 相同错误重复出现
- 人工介入成本高
- 知识无法沉淀

## 决策

引入结构化的自愈（Self-healing）和学习（Learning）机制：

### 1. 失败分类（FailurePack）

所有失败必须产出结构化的 FailurePack：

```json
{
  "failure_type": "test_failure",
  "root_cause_summary": "Jest test failed: UserAuth.test.ts",
  "evidence_refs": ["ev042", "step:apply:123"],
  "suggested_actions": [
    {
      "action_type": "retry_with_backoff",
      "parameters": {...},
      "risk_delta": "low"
    }
  ],
  "retriable": true
}
```

**失败类型枚举**:
- `schema_validation_failure`
- `lock_conflict`
- `git_conflict`
- `command_not_found`
- `test_failure`
- `gate_failure`
- `timeout`
- `policy_violation`

### 2. 自愈动作白名单（Healing Actions）

只允许预定义的自愈动作：

| Action | 描述 | 风险 | 条件 |
|--------|------|------|------|
| `RetryWithBackoff` | 指数退避重试 | Low | retriable=true |
| `RebuildContext` | 重新拉取 MemoryPack | Low | - |
| `ReplanStep` | 重新规划 | Medium | 必须产出新 plan + evidence |
| `RollbackToCommit` | 回滚到上一个 commit | Medium | 有 commit_links |
| `SplitCommit` | 拆分大 commit | Low | max_files 违规 |
| `EscalateMode` | 模式升级 | High | policy 允许 |
| `CreateBlocker` | 创建 blocker 问题 | Low | - |

**约束**:
- full_auto 模式只能执行 Low 风险动作
- Medium/High 风险动作需要 policy 明确允许
- 所有动作必须产出 review_pack

### 3. 学习管线（Learning Pipeline）

从历史中提炼知识：

```
ReviewPack + FailurePack + RunTape
    ↓ (分析)
Pattern Extraction
    ↓
LearningPack (提案)
    ↓ (人工批准 或 auto-apply 规则)
Memory Items (沉淀)
```

**LearningPack 结构**:

```json
{
  "source_runs": [123, 124, 125],
  "pattern": "Jest tests timeout when files > 50",
  "proposed_memory_items": [
    {
      "type": "constraint",
      "content": {
        "summary": "Split test files if count > 50"
      },
      "confidence": 0.85
    }
  ],
  "verification_plan": "Apply to next 3 runs and measure success rate"
}
```

## 自愈流程

```
Task Execution
    ↓ (失败)
FailurePack Generation
    ↓
Healing Action Selection (白名单)
    ↓
[Policy Check]
    ↓
Execute Healing Action
    ↓
Record to run_tape
    ↓
[Success] → Continue
[Still Fail] → Escalate or Block
```

## 学习应用策略

**Auto-apply 条件**:
- confidence >= 0.9
- 已在 canary 环境验证
- 属于 low-risk memory types (convention, glossary)

**人工批准条件**:
- confidence < 0.9
- 涉及 constraint 或 decision
- 会修改 execution_policy

## 护城河扩展

**新增约束**:
- 自愈动作必须白名单（不能自由发挥）
- Learning 先提案后应用
- 应用必须可撤销（产出 review_pack）
- full_auto 模式 question_budget=0（不变）

## 验收标准

- [ ] 所有失败产出 FailurePack
- [ ] 自愈只执行白名单动作
- [ ] Learning 产出 LearningPack（默认不自动应用）
- [ ] Apply 可回滚
- [ ] v0.2 护城河 10 条继续满足

---

**相关**: ADR-004, ADR-006
