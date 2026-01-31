# Pipeline - NL → PR Artifacts (E2E Orchestration)

## 一句话定位

**演示闭环**：将自然语言需求串行转换为PR级工件（Intent → Graph → Execution Plan），但**不执行任何命令**。

## 版本

- **当前版本**: v0.10
- **依赖组件**:
  - v0.9.4 Intent Builder（NL → Intent）
  - v0.9.2 Coordinator（Intent → Graph）
  - v0.10 Dry-Executor（Graph → Execution Plan）

## 核心职责

Pipeline是一个**纯编排层**（Orchestration Layer），负责：

1. **串行调用**已冻结的三个组件（Builder → Coordinator → Dry-Executor）
2. **生成汇总**产出PR级工件（PR_ARTIFACTS.md）
3. **强制执行**5条红线（P1-P5）
4. **记录审计**每一步的输入/输出/状态

## 输入

- **NL Request** (YAML或JSON格式)
  - 符合`nl_request.schema.json`（v0.9.4）
  - 示例：`examples/nl/nl_001.yaml` 或 `nl_001.json`

## 输出

固定的目录结构（`outputs/pipeline/<timestamp>/`）：

```
outputs/pipeline/<run_id>/
├── 01_intent/
│   ├── intent.json             # v0.9.1 ExecutionIntent
│   └── question_pack.json      # 可能为空
├── 02_coordinator/
│   ├── execution_graph.json    # v0.9.2 ExecutionGraph
│   ├── coordinator_run_tape.json
│   └── explain.txt
├── 03_dry_executor/
│   └── dry_execution_result.json  # v0.10 DryExecutionResult
├── 04_pr_artifacts/
│   ├── PR_ARTIFACTS.md         # ⭐ 主要交付物
│   └── commit_plan.md          # 人类可读的提交计划
└── audit/
    ├── pipeline_audit_log.jsonl  # 审计日志
    └── checksums.json            # 所有产物的checksum
```

## PR_ARTIFACTS.md 结构

固定的7个章节：

1. **Summary** - Intent ID、风险级别、文件数、提交数
2. **Risk Analysis** - 风险分布、审查需求、评估时间
3. **Commit Plan** - 每个commit的详细信息
4. **Evidence Coverage** - 证据覆盖率统计
5. **Open Questions** - 阻塞问题（如果有）
6. **Verification** - "未执行"声明
7. **Checksums** - 所有产物的checksum列表

## 5条红线（P1-P5）

| 红线 | 描述 | 检查方式 |
|------|------|----------|
| **P1** | Pipeline永不执行命令 | Gate P-C静态扫描 |
| **P2** | 高风险必须标红 | PR_ARTIFACTS.md中包含警告 |
| **P3** | Question Pack阻塞 | 非空且无answers则写BLOCKERS.md |
| **P4** | Checksum必需 | 所有产物必须有checksum |
| **P5** | 审计日志完整 | 每步start/end/status必须记录 |

## 使用方法

### 基本用法

```bash
python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/nl/nl_001.yaml \
  --out outputs/pipeline/my_run
```

### 使用临时DB（测试）

```bash
python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/nl/nl_002.json \
  --db /tmp/test_registry.sqlite \
  --out outputs/pipeline/test_run
```

### 查看输出

```bash
# 主要交付物
cat outputs/pipeline/my_run/04_pr_artifacts/PR_ARTIFACTS.md

# 审计日志
cat outputs/pipeline/my_run/audit/pipeline_audit_log.jsonl

# Checksums
cat outputs/pipeline/my_run/audit/checksums.json
```

## 与v0.11真执行器的差距

当前Pipeline（v0.10）是**演示闭环**，离真实执行还差：

### v0.11 真执行器需要

1. **Command执行沙箱**
   - 隔离的执行环境
   - 文件系统写入权限控制
   - 资源限制（CPU、内存、时间）
   - 回滚机制

2. **AnswerPack回填**
   - 当Question Pack非空时，支持人工回答
   - 回答验证（类型、范围、依赖）
   - 回答记录到审计日志

3. **Review Workflow**
   - 高风险需求的审批流程
   - 审批记录和签名
   - 审批后的执行授权

4. **CI/PR集成**
   - GitHub App / PR comment bot
   - 自动触发Pipeline
   - PR中展示工件
   - 执行结果回写到PR

5. **增量执行**
   - 支持从失败点恢复
   - 部分提交的幂等性
   - 冲突检测和解决

### 时间表（非承诺）

- **v0.11**: 真执行器（Command沙箱 + AnswerPack）
- **v0.12**: Review Workflow + 人机协作
- **v0.13**: CI/PR集成 + 自动化

## Gates验证

运行所有Pipeline Gates：

```bash
bash scripts/verify_pipeline.sh
```

6个Gates：

- **Gate P-A**: 存在性验证（文件、文档、NL cases）
- **Gate P-B**: 端到端可运行性（需要环境）⚠️
- **Gate P-C**: 红线验证（静态扫描）
- **Gate P-D**: 结构稳定性（需要baseline）⚠️
- **Gate P-E**: 快照验证（explain输出）
- **Gate P-F**: 验证脚本检查

⚠️ 标记的Gates需要完整的环境设置，可能失败。

## 常见问题

### Q: 为什么coordinator未注册到CLI？

A: v0.9.2 coordinator的CLI未在`agentos/cli/main.py`中注册。需要手动导入：

```python
from agentos.cli.coordinate import coordinator
cli.add_command(coordinator, name="coordinate")
```

或直接运行：

```bash
python -m agentos.cli.coordinate ...
```

### Q: Pipeline运行失败怎么办？

A: 检查`outputs/pipeline/<run_id>/audit/pipeline_audit_log.jsonl`，查看哪一步失败。

### Q: Question Pack阻塞了怎么办？

A: 查看`outputs/pipeline/<run_id>/BLOCKERS.md`，了解需要回答的问题。v0.11将支持AnswerPack回填。

### Q: 如何生成baseline输出？

A: 运行Pipeline：

```bash
for case in nl_001 nl_002 nl_003; do
  python scripts/pipeline/run_nl_to_pr_artifacts.py \
    --nl examples/nl/${case}.yaml \
    --out examples/pipeline/expected/${case}
done
```

## 架构图

```
NL Request (YAML/JSON)
    ↓
[Intent Builder v0.9.4]
    ↓
ExecutionIntent (v0.9.1)
    ↓
[Coordinator v0.9.2]
    ↓
ExecutionGraph + Run Tape
    ↓
[Dry-Executor v0.10]
    ↓
DryExecutionResult
    ↓
[Pipeline汇总]
    ↓
PR_ARTIFACTS.md + Checksums + Audit Log
```

## 相关文档

- [RUNBOOK.md](RUNBOOK.md) - 详细操作指南
- [V10_PIPELINE_FREEZE_REPORT.md](V10_PIPELINE_FREEZE_REPORT.md) - 冻结报告
- [Intent Builder v0.9.4](../execution/V094_INTENT_BUILDER_README.md)
- [Coordinator v0.9.2](../coordinator/README.md)
- [Dry-Executor v0.10](../executor/README.md)

## 状态

- ✅ **v0.10 冻结完成** (2026-01-25)
- 📦 可演示闭环：NL → PR工件
- 🚫 不执行任何命令（Plan, Don't Execute）
- 🔒 红线P1-P5强制执行
- 📊 审计日志完整可追溯

---

**最后更新**: 2026-01-25  
**维护者**: AgentOS团队
