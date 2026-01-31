# Dry Executor (v0.10)

## 概述

Dry Executor 是 AgentOS 的"伪执行器"组件，负责从 ExecutionIntent (v0.9.1) 生成可审计、可评审、可冻结的执行计划，而不执行任何实际操作。

**核心承诺**：不执行、不改文件、不跑命令，只产出计划与审查工件（PR级）。

## 定位

Dry Executor 位于 AgentOS 架构的以下位置：

```
ExecutionIntent (v0.9.1)
         ↓
    [可选] Coordinator (v0.9.2) → ExecutionGraph
         ↓
    Dry Executor (v0.10)
         ↓
    DryExecutionResult
         ↓
    - ExecutionGraph (计划级 DAG)
    - PatchPlan (文件变更计划)
    - CommitPlan (提交分组策略)
    - ReviewPackStub (审查需求摘要)
```

## 与其他组件的关系

### 输入
- **ExecutionIntent (v0.9.1)**: 必需，定义执行目标和约束
- **Coordinator Outputs (v0.9.2)**: 可选，可复用 Coordinator 生成的 ExecutionGraph

### 输出
- **DryExecutionResult (v0.10)**: 完整的执行计划工件

### 不交叉的组件
- **agentos/ext/**: v0.9.3 adapters（Dry Executor 不修改）
- **agentos/store/**: DB schema（只读，不写入）
- **Content Registry**: workflow/agent/command/rule YAML（只引用，不修改）

## 核心组件

### 1. Schemas (4 个冻结级)
- `execution_graph.schema.json`: 执行图（计划级 DAG）
- `patch_plan.schema.json`: 文件变更计划
- `commit_plan.schema.json`: 提交分组策略
- `dry_execution_result.schema.json`: 总输出结构

### 2. Core Modules (5 个)
- `dry_executor.py`: 主入口，编排各组件
- `graph_builder.py`: 从 intent/coordinator 构建执行图
- `patch_planner.py`: 规划文件变更（不生成实际 patch）
- `commit_planner.py`: 将文件分组为逻辑 commits
- `review_pack_stub.py`: 生成审查需求摘要

### 3. CLI Commands
```bash
# 生成执行计划
agentos dry-run plan --intent intent.json --out outputs/

# 解释计划（人类可读）
agentos dry-run explain --result outputs/dryexec_xxx.json

# 验证计划（schema + 红线）
agentos dry-run validate --file outputs/dryexec_xxx.json
```

## 使用场景

### 场景 1：低风险变更（文档更新）
```bash
# 输入：intent_example_low_risk.json
# 输出：1-2 commits，文档类变更，quick review
agentos dry-run plan --intent examples/intents/intent_example_low_risk.json --out outputs/
```

### 场景 2：中等风险（新增 API + 测试）
```bash
# 输入：带 coordinator outputs
# 输出：3-5 commits，模块分组，thorough review
agentos dry-run plan \
  --intent intent_api.json \
  --coordinator coordinator_outputs.json \
  --out outputs/
```

### 场景 3：高风险（DB Migration）
```bash
# 输入：高风险 intent
# 输出：3 commits（强制分层），extended review，多重审查需求
agentos dry-run plan --intent intent_db_migration.json --out outputs/
```

## 红线 (DE1-DE6)

Dry Executor 严格执行 6 条红线：

1. **DE1**: 禁止执行（无 subprocess/os.system/exec/eval）
2. **DE2**: 禁止写项目文件（只写 outputs 产物）
3. **DE3**: 禁止编造路径（只用 intent 提供的路径）
4. **DE4**: 所有节点必须有 evidence_refs
5. **DE5**: 高/关键风险必须有 requires_review
6. **DE6**: 输出可冻结（checksum + lineage + 稳定 explain）

详见：[RED_LINES.md](RED_LINES.md)

## 验证与冻结

### Gates（冻结级质量保证）
- **Gate A**: 存在性验证（schemas/modules/examples/docs）
- **Gate B**: Schema 批量验证
- **Gate C**: 负向 fixtures 验证
- **Gate D**: 静态扫描禁执行
- **Gate E**: DB 路径隔离
- **Gate F**: Explain 快照稳定

### 一键验证
```bash
./scripts/verify_v10_dry_executor.sh
```

## 示例

### Low Risk Example
- 输入: `examples/executor_dry/low_risk/input_intent.json`
- 输出: `examples/executor_dry/low_risk/output_result.json`
- 解释: `examples/executor_dry/low_risk/explain.txt`

### Medium Risk Example
- 输入: `examples/executor_dry/medium_risk/input_intent.json`
- 输出: `examples/executor_dry/medium_risk/output_result.json`

### High Risk Example
- 输入: `examples/executor_dry/high_risk/input_intent.json`
- 输出: `examples/executor_dry/high_risk/output_result.json`

## 开发指南

详见：[AUTHORING_GUIDE.md](AUTHORING_GUIDE.md)

## 版本历史

- **v0.10.0**: 初始冻结版本
  - 4 个冻结级 schemas
  - 5 个核心模块
  - 3 组示例（low/medium/high risk）
  - 6 个 gates（A-F）
  - 完整文档与验证脚本

## 许可

本组件遵循 AgentOS 项目许可。
