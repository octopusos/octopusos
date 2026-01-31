# Dry Executor Authoring Guide

## 概述

本指南说明如何使用 Dry Executor 从 ExecutionIntent 生成执行计划，以及如何解读和使用输出。

## 从 Intent 到计划的流程

### 1. 准备 ExecutionIntent (v0.9.1)

Intent 必须包含以下关键信息：

#### 必需字段
- `scope.targets.files[]`: 明确列出要操作的文件路径
- `planned_commands[]`: 计划执行的命令及其 effects
- `selected_workflows[]`: 选择的工作流及 phases
- `selected_agents[]`: 分配的 agent 角色
- `risk`: 风险评估（overall + drivers + requires_review）
- `evidence_refs[]`: 证据引用

#### 关键约束
```json
{
  "constraints": {
    "execution": "forbidden",
    "no_fabrication": true,
    "registry_only": true,
    "lock_scope": {
      "mode": "files",
      "paths": ["file1.py", "file2.py"]
    }
  }
}
```

### 2. 运行 Dry Executor

#### 基本用法
```bash
agentos dry-run plan \
  --intent examples/intents/my_intent.json \
  --out outputs/dry/
```

#### 带 Coordinator 输出
```bash
agentos dry-run plan \
  --intent my_intent.json \
  --coordinator coordinator_outputs.json \
  --out outputs/dry/
```

#### 输出
生成 `outputs/dry/dryexec_<hash>.json`，包含：
- ExecutionGraph (计划级 DAG)
- PatchPlan (文件变更计划)
- CommitPlan (提交分组)
- ReviewPackStub (审查需求)
- AuditLog (决策日志)

### 3. 解读 DryExecutionResult

#### 使用 CLI explain
```bash
agentos dry-run explain \
  --result outputs/dry/dryexec_xxx.json \
  --format text
```

输出示例：
```
=================================================================
DRY EXECUTION RESULT EXPLANATION
=================================================================

Result ID: dryexec_163e4e86532c880e
Schema Version: 0.10.0
Created: 2026-01-25T10:20:19Z

Source Intent: intent_example_low_risk

--- Execution Graph ---
Nodes: 6 (3 phases + 2 actions + 1 review)
Edges: 5
Swimlanes: 1

--- Patch Plan ---
Files: 2
  - modify: agentos/utils/format.py (risk: low)
  - modify: agentos/utils/validation.py (risk: low)

--- Commit Plan ---
Commits: 1
  - commit_0001: feat(agentos): update 2 file(s)
    Files: 2, Risk: low

--- Review Requirements ---
Dominant Risk: low
Required Reviews: release
Estimated Review Time: quick
```

## 理解各组件

### ExecutionGraph

**用途**: 表达执行步骤的 DAG 结构。

**节点类型**:
- `phase`: 工作流阶段（如 analysis, implementation）
- `action_plan`: 计划的操作（从 planned_commands）
- `decision_point`: 决策点（规则应用）
- `review_checkpoint`: 审查检查点

**关键字段**:
- `nodes[]`: 所有节点，每个必须有 `evidence_refs`
- `edges[]`: 节点依赖关系（sequential/parallel/conditional）
- `swimlanes[]`: Agent 分配（哪个 agent 负责哪些节点）

### PatchPlan

**用途**: 规划文件变更，但不生成实际 patch。

**文件条目**:
```json
{
  "path": "agentos/api/routes.py",
  "action": "modify",  // add | modify | delete
  "rationale": "为何要改这个文件",
  "risk": "medium",
  "evidence_refs": ["scan://file/...", "design://spec"],
  "lock_intent": {
    "mode": "exclusive",
    "scope": "file",
    "reason": "需要独占锁的原因"
  }
}
```

**红线**:
- 所有 `path` 必须来自 intent.scope.targets.files 或 evidence_refs
- 不得编造不存在的路径（DE3）
- 如果无法确定路径，放到 `unknowns[]`

**Estimated Diffs**:
- `diff_hash_placeholder`: 未来 diff 的占位符（不是真实 diff）
- `intent_summary`: 预期变更的摘要
- `estimated_lines_changed`: 粗略估计的行数变化

### CommitPlan

**用途**: 将文件分组为逻辑 commits，建立提交顺序。

**分组策略**:
1. **按模块/目录**: 同一目录的文件优先分组
2. **按风险级别**: 高风险单独 commit
3. **按可回滚性**: 可独立回滚的分一组
4. **尊重预算**: 遵守 intent.budgets.max_commits

**Commit 字段**:
```json
{
  "commit_id": "commit_0001",
  "title": "feat(api): add notification endpoint",
  "scope": "api",
  "files": ["api/routes.py", "api/models.py"],
  "rationale": "为何这些文件分组在一起",
  "depends_on": [],  // 依赖的其他 commits
  "risk": "medium",
  "evidence_refs": ["..."],
  "rollback_strategy": "revert",  // revert | forward_fix | requires_manual
  "estimated_review_time": "moderate",  // quick | moderate | thorough | extended
  "tags": ["breaking", "security", "data", "tests"]
}
```

**依赖关系**:
- `depends_on[]`: 此 commit 依赖的其他 commit IDs
- 用于建立 commit DAG，确保正确的提交顺序

### ReviewPackStub

**用途**: 生成审查需求的摘要（不是完整 ReviewPack）。

**Risk Summary**:
```json
{
  "dominant_risk": "high",  // 最高风险级别
  "risk_factors": [
    "Database schema change",
    "Production deployment"
  ],
  "mitigation_notes": [
    "Require multiple reviewers",
    "Test rollback procedures"
  ]
}
```

**Required Reviews**:
- 从 intent.risk.requires_review 继承
- 根据文件类型推断（如 security 文件 → security review）
- 高风险自动添加 release review

**Evidence Coverage**:
```json
{
  "total_nodes": 10,
  "nodes_with_evidence": 10,
  "coverage_percentage": 100.0,
  "gaps": []  // 缺失 evidence_refs 的节点
}
```

## Commit 分组最佳实践

### 场景 1：文档更新（Low Risk）
```
Commit 1: chore(docs): update function docstrings (all files)
- 单个 commit 包含所有文档变更
- Risk: low
- Rollback: revert
```

### 场景 2：新增 API（Medium Risk）
```
Commit 1: feat(models): add notification model
Commit 2: feat(api): add notification routes
Commit 3: test(api): add notification tests
Commit 4: docs(api): update API documentation

依赖: 1 → 2 → 3 → 4
风险分层: model → api → tests → docs
```

### 场景 3：DB Migration（High Risk）
```
Commit 1: feat(db): add user_credentials table schema + rollback
- 包含 forward 和 rollback SQL
- Risk: critical
- Rollback: requires_manual

Commit 2: feat(models): add UserCredentials ORM model
- depends_on: [commit_0001]
- Risk: medium

Commit 3: test(db): add migration integration tests
- depends_on: [commit_0001, commit_0002]
- Risk: medium
```

## Evidence Refs 最佳实践

### 来源类型

#### 1. Intent References
```
intent://intent_id/scope/targets/files/path.py
intent://intent_id/planned_commands/command_id
```

#### 2. Scan References
```
scan://file/path/to/file.py
scan://python_modules/agentos.api
```

#### 3. Design References
```
design://api_spec/notifications_endpoint
design://db_schema/credentials_table
```

#### 4. Documentation References
```
doc://architecture/api_patterns.md
doc://security/encryption_standards
```

#### 5. External References
```
threat_model://credentials_storage
api_spec://rest_api_v2
```

### 证据覆盖率目标

- **P0（必须）**: 所有 action_plan 节点 100% 覆盖
- **P1（推荐）**: 所有 phase 节点 ≥ 80% 覆盖
- **P2（可选）**: decision_point 节点尽可能覆盖

## Unknowns 处理

当无法从 intent/evidence 确定某些信息时，Dry Executor 会输出到 `unknowns[]`：

```json
{
  "type": "missing_path",  // missing_path | ambiguous_target | insufficient_evidence
  "description": "Cannot determine file path for configuration update",
  "reason": "Path not in intent.scope.targets.files",
  "needed_evidence": "Explicit path in intent or scan://file/ reference"
}
```

**处理方式**:
1. 补充 intent 中的 evidence_refs
2. 在 scope.targets.files 中明确列出路径
3. 或在 QuestionPack 中询问用户（如果支持交互模式）

## 验证计划

### 运行验证
```bash
agentos dry-run validate --file outputs/dry/dryexec_xxx.json
```

### 检查项
- ✅ Schema 验证
- ✅ Checksum 一致性
- ✅ 红线执行（DE1-DE6）

## 常见问题

### Q1: 为什么某些文件没有出现在 PatchPlan 中？

**A**: 检查以下几点：
1. 文件路径是否在 intent.scope.targets.files 中？
2. 是否有 evidence_refs 明确引用该文件？
3. 如果缺失，查看 patch_plan.unknowns[] 是否有相关条目

### Q2: Commit Plan 的 depends_on 是如何确定的？

**A**: 基于以下规则：
1. 风险级别：高风险依赖低风险
2. 文件关系：Model → Service → API → Tests
3. 用户指定：intent 中可包含提示

### Q3: 如何调整 Commit 分组粒度？

**A**: 在 intent 中设置：
```json
{
  "budgets": {
    "max_commits": 3  // 限制最多 3 个 commits
  }
}
```

Dry Executor 会自动合并低风险 commits 以满足预算。

### Q4: ReviewPackStub 与 ReviewPackGenerator (v0.2/v0.3) 的区别？

**A**: 
- **ReviewPackStub**: 预审查摘要，只包含风险总结和审查需求
- **ReviewPackGenerator**: 完整审查工件，包含详细的审查清单和验收标准
- 两者不冲突，Stub 用于 Dry Executor，Generator 用于实际审查流程

## 高级用法

### 与 Coordinator 集成

```bash
# Step 1: 运行 Coordinator
agentos coordinate plan --intent intent.json --out coordinator/

# Step 2: 使用 Coordinator 输出
agentos dry-run plan \
  --intent intent.json \
  --coordinator coordinator/run_xxx.json \
  --out dry/
```

Dry Executor 会复用 Coordinator 生成的 ExecutionGraph 作为基础。

### 生成 JSON 格式的 Explain

```bash
agentos dry-run explain \
  --result outputs/dry/dryexec_xxx.json \
  --format json > explain.json
```

用于自动化分析和快照测试（Gate F）。

## 相关文档

- [README.md](README.md): Dry Executor 概述
- [RED_LINES.md](RED_LINES.md): 红线详细说明
- [V10_FREEZE_CHECKLIST_REPORT.md](V10_FREEZE_CHECKLIST_REPORT.md): 冻结验收报告
