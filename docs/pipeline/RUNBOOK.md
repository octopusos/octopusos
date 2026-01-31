# Pipeline Runbook - 操作手册

## 目录

1. [快速开始](#快速开始)
2. [运行3个NL Case](#运行3个nl-case)
3. [理解输出目录](#理解输出目录)
4. [调试失败](#调试失败)
5. [常见场景](#常见场景)
6. [环境设置](#环境设置)

---

## 快速开始

### 前置条件

```bash
# 1. 确保Python 3.13+
python3 --version

# 2. 确保项目依赖已安装
pip install -e .

# 3. 验证NL examples存在
ls examples/nl/nl_00*.{yaml,json}
```

### 运行第一个Pipeline

```bash
cd /path/to/AgentOS

# 使用nl_001（低风险文档变更）
python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/nl/nl_001.json \
  --out outputs/pipeline/first_run

# 查看结果
cat outputs/pipeline/first_run/04_pr_artifacts/PR_ARTIFACTS.md
```

预期输出：

```
======================================================================
Pipeline Runner v0.10 - NL → PR Artifacts
======================================================================
NL Request: examples/nl/nl_001.json
Output: outputs/pipeline/first_run
Audit Log: outputs/pipeline/first_run/audit/pipeline_audit_log.jsonl

======================================================================
步骤1：NL → Intent Builder (v0.9.4)
======================================================================
📝 NL Request ID: nl_req_low_risk_doc
📝 Input text: 请为 IntentBuilder 类添加完整的文档注释...
✅ Intent generated: intent_xxx
   Risk: low
   Workflows: 1
   Agents: 2
   Commands: 3
   Questions: 0 (no blocking questions)

======================================================================
步骤2：Intent → Coordinator (v0.9.2)
======================================================================
...
```

---

## 运行3个NL Case

### Case 1: nl_001（低风险文档变更）

```bash
python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/nl/nl_001.json \
  --out examples/pipeline/expected/nl_001
```

**预期行为**：
- ✅ 不产生Question Pack
- ✅ Risk Level = low
- ✅ 无需Review
- ⏱️ 耗时：~30秒

### Case 2: nl_002（中风险API需求）

```bash
python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/nl/nl_002.json \
  --out examples/pipeline/expected/nl_002
```

**预期行为**：
- ⚠️ 可能产生Question Pack（semi_auto模式）
- ✅ Risk Level = medium
- ✅ 需要基本Review
- ⏱️ 耗时：~60秒

### Case 3: nl_003（高风险数据库迁移）

```bash
python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/nl/nl_003.json \
  --out examples/pipeline/expected/nl_003
```

**预期行为**：
- ⚠️ 可能产生Question Pack（需要澄清）
- ❌ Risk Level = high
- ❌ **必须Review**
- ⏱️ 耗时：~90秒

**高风险检查清单**：
- [ ] PR_ARTIFACTS.md包含⚠️警告
- [ ] requires_review列表非空
- [ ] estimated_review_time = "thorough"或"extended"
- [ ] 所有commits都有rollback_strategy

---

## 理解输出目录

### 目录树

```
outputs/pipeline/<timestamp>/
├── 01_intent/                 # Intent Builder输出
│   ├── nl_request.json        # 转换后的NL请求
│   ├── intent.json            # ⭐ v0.9.1 ExecutionIntent
│   ├── question_pack.json     # 问题（可能为空）
│   └── nl_req_xxx.output.json # Builder完整输出
│
├── 02_coordinator/            # Coordinator输出
│   ├── execution_graph.json   # ⭐ v0.9.2 执行图（DAG）
│   ├── coordinator_run_tape.json  # 状态机磁带
│   ├── review_pack.json       # 审查包（可能为空）
│   └── explain.txt            # 人类可读解释
│
├── 03_dry_executor/           # Dry-Executor输出
│   ├── dry_execution_result.json  # ⭐ v0.10 完整结果
│   └── coordinator_merged.json    # 临时文件
│
├── 04_pr_artifacts/           # PR级工件（汇总层）
│   ├── PR_ARTIFACTS.md        # ⭐⭐⭐ 主要交付物
│   └── commit_plan.md         # 人类可读的提交计划
│
└── audit/                     # 审计层
    ├── pipeline_audit_log.jsonl  # ⭐ 每步审计记录
    └── checksums.json         # 所有产物checksum
```

### 关键文件说明

#### PR_ARTIFACTS.md

**位置**: `04_pr_artifacts/PR_ARTIFACTS.md`

**用途**: PR级工件汇总，包含：
- Summary（Intent ID、风险、文件数、提交数）
- Risk Analysis（风险分布、审查需求）
- Commit Plan（每个commit详情）
- Evidence Coverage（证据覆盖率）
- Checksums（所有产物）

**示例片段**：

```markdown
# PR Artifacts Summary

## Summary
- Intent ID: intent_nlreq001_20260125
- Dominant Risk: low
- Requires Review: release
- Total Files: 2
- Total Commits: 1

## Risk Analysis
- Dominant Risk: low
- Risk Counts:
  - low: 2
  - medium: 0
  - high: 0
- Estimated Review Time: quick

## Commit Plan
### commit_0001: docs(intent_builder): add comprehensive docstrings

- Scope: intent_builder
- Risk: low
- Files: 2
- Rollback: revert

...
```

#### pipeline_audit_log.jsonl

**位置**: `audit/pipeline_audit_log.jsonl`

**用途**: 审计日志（每行一个JSON事件）

**示例**：

```json
{"timestamp": "2026-01-25T10:20:19Z", "event": "pipeline_start", "inputs": {"nl_request": "examples/nl/nl_001.json"}}
{"timestamp": "2026-01-25T10:20:19Z", "event": "command_start", "description": "Intent Builder", "command": "python -m agentos.cli.main builder run ..."}
{"timestamp": "2026-01-25T10:20:45Z", "event": "command_end", "description": "Intent Builder", "exit_code": 0, "stdout_lines": 25}
{"timestamp": "2026-01-25T10:20:45Z", "event": "command_start", "description": "Coordinator coordinate", "command": "python -m agentos.cli.coordinate ..."}
...
{"timestamp": "2026-01-25T10:21:30Z", "event": "pipeline_complete", "status": "success"}
```

**查询审计日志**：

```bash
# 查看所有事件
cat outputs/pipeline/my_run/audit/pipeline_audit_log.jsonl | jq .

# 查看失败事件
cat outputs/pipeline/my_run/audit/pipeline_audit_log.jsonl | jq 'select(.event == "command_error")'

# 计算总耗时
cat outputs/pipeline/my_run/audit/pipeline_audit_log.jsonl | jq -r 'select(.event == "pipeline_start" or .event == "pipeline_complete") | .timestamp'
```

#### checksums.json

**位置**: `audit/checksums.json`

**用途**: 所有产物的SHA-256 checksum

**示例**：

```json
{
  "intent": "abc123...",
  "graph": "def456...",
  "dry_result": "789ghi...",
  "pr_artifacts": "jkl012..."
}
```

**验证完整性**：

```bash
# 验证intent.json
sha256sum outputs/pipeline/my_run/01_intent/intent.json
cat outputs/pipeline/my_run/audit/checksums.json | jq -r .intent
```

---

## 调试失败

### 步骤1失败：Intent Builder

**症状**：Pipeline在"步骤1：NL → Intent"失败

**排查**：

```bash
# 1. 检查audit log
cat outputs/pipeline/my_run/audit/pipeline_audit_log.jsonl | grep "Intent Builder"

# 2. 查看完整输出（如果存在）
cat outputs/pipeline/my_run/01_intent/*.output.json | jq .

# 3. 手动运行Intent Builder
python -m agentos.cli.main builder run \
  --input examples/nl/nl_001.json \
  --policy semi_auto \
  --out /tmp/test_builder
```

**常见原因**：
- ContentRegistry未初始化
- NL请求格式错误
- 依赖未安装（pyyaml、click等）

### 步骤2失败：Coordinator

**症状**：Pipeline在"步骤2：Intent → Coordinator"失败

**排查**：

```bash
# 1. 检查audit log
cat outputs/pipeline/my_run/audit/pipeline_audit_log.jsonl | grep "Coordinator"

# 2. 检查intent是否有效
cat outputs/pipeline/my_run/01_intent/intent.json | jq .

# 3. 手动运行Coordinator
python -m agentos.cli.coordinate coordinate \
  --intent outputs/pipeline/my_run/01_intent/intent.json \
  --policy semi_auto \
  --output /tmp/test_coordinator
```

**常见原因**：
- Coordinator CLI未注册到main.py
- Intent格式不符合v0.9.1
- 缺少必需字段（workflows、agents、commands）

**修复**：

```python
# 在agentos/cli/main.py中添加：
from agentos.cli.coordinate import coordinator
cli.add_command(coordinator, name="coordinate")
```

### 步骤3失败：Dry-Executor

**症状**：Pipeline在"步骤3：Coordinator/Intent → Dry-Executor"失败

**排查**：

```bash
# 1. 检查audit log
cat outputs/pipeline/my_run/audit/pipeline_audit_log.jsonl | grep "Dry-Executor"

# 2. 检查coordinator输出
cat outputs/pipeline/my_run/02_coordinator/execution_graph.json | jq .

# 3. 手动运行Dry-Executor
python -m agentos.cli.main dry-run plan \
  --intent outputs/pipeline/my_run/01_intent/intent.json \
  --coordinator outputs/pipeline/my_run/03_dry_executor/coordinator_merged.json \
  --out /tmp/test_dry
```

**常见原因**：
- Graph结构不完整
- 缺少evidence_refs
- Checksum缺失

### Pipeline被BLOCKED

**症状**：Pipeline输出"❌ Pipeline BLOCKED"，并生成`BLOCKERS.md`

**原因**：Intent Builder产生了Question Pack（需要回答问题）

**排查**：

```bash
# 查看问题清单
cat outputs/pipeline/my_run/BLOCKERS.md

# 或直接看question_pack
cat outputs/pipeline/my_run/01_intent/question_pack.json | jq .
```

**示例BLOCKERS.md**：

```markdown
# Pipeline Blocked

## Reason
Intent Builder generated questions that must be answered before proceeding.

## Questions
- [high] Which API authentication method to use? (OAuth2 / API Key / JWT)
- [medium] Should we add rate limiting? (Yes / No)

## Solution
1. Provide an answer_pack.json file
2. Re-run the pipeline with --answers parameter
```

**解决方案**（v0.11将支持）：

```json
// answer_pack.json
{
  "question_pack_id": "qp_xxx",
  "answers": [
    {"question_id": "q1", "answer": "OAuth2"},
    {"question_id": "q2", "answer": "Yes"}
  ]
}
```

---

## 常见场景

### 场景1：验证Pipeline设计（不运行环境）

```bash
# 运行静态Gates（不需要环境）
python scripts/gates/pipeline_gate_a_existence.py  # 存在性
bash scripts/gates/pipeline_gate_c_red_lines.sh    # 红线
python scripts/gates/pipeline_gate_e_snapshot.py   # 快照

# 不运行P-B（需要环境）和P-D（需要baseline）
```

### 场景2：生成所有baseline输出

```bash
#!/bin/bash
for case in nl_001 nl_002 nl_003; do
  echo "Generating baseline for $case..."
  python scripts/pipeline/run_nl_to_pr_artifacts.py \
    --nl examples/nl/${case}.json \
    --out examples/pipeline/expected/${case}
done
```

### 场景3：使用临时DB（测试隔离）

```bash
# 创建临时DB
TEMP_DB=$(mktemp)
echo "Using temp DB: $TEMP_DB"

# 初始化DB（假设有init脚本）
python scripts/register_workflows.py --db $TEMP_DB
python scripts/register_agents.py --db $TEMP_DB
python scripts/register_commands.py --db $TEMP_DB

# 运行Pipeline
python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/nl/nl_001.json \
  --db $TEMP_DB \
  --out outputs/pipeline/isolated_test

# 清理
rm $TEMP_DB
```

### 场景4：对比两次运行的差异

```bash
# 第一次运行
python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/nl/nl_002.json \
  --out outputs/pipeline/run1

# 第二次运行（修改后）
python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/nl/nl_002.json \
  --out outputs/pipeline/run2

# 对比PR_ARTIFACTS
diff outputs/pipeline/run1/04_pr_artifacts/PR_ARTIFACTS.md \
     outputs/pipeline/run2/04_pr_artifacts/PR_ARTIFACTS.md

# 对比checksums
diff <(jq . outputs/pipeline/run1/audit/checksums.json) \
     <(jq . outputs/pipeline/run2/audit/checksums.json)
```

---

## 环境设置

### 完整环境（运行P-B和P-D）

```bash
# 1. 安装项目依赖
pip install -e .

# 2. 初始化ContentRegistry
python -m agentos.cli.main migrate --init

# 3. 注册内容
python scripts/register_workflows.py
python scripts/register_agents.py
python scripts/register_commands.py
python scripts/register_rules.py

# 4. 注册Coordinator CLI（手动编辑）
# 在agentos/cli/main.py中添加：
# from agentos.cli.coordinate import coordinator
# cli.add_command(coordinator, name="coordinate")

# 5. 验证环境
python -m agentos.cli.main --help | grep coordinate
python -m agentos.cli.main builder --help
python -m agentos.cli.main dry-run --help

# 6. 运行完整验证
bash scripts/verify_pipeline.sh
```

### 最小环境（只运行静态Gates）

```bash
# 只需要Python 3.13+和文件系统
python3 --version

# 验证文件存在
python scripts/gates/pipeline_gate_a_existence.py

# 验证红线
bash scripts/gates/pipeline_gate_c_red_lines.sh
```

---

## 性能基准

基于本地开发机（MacBook Pro M1, 16GB RAM）：

| NL Case | 风险 | 耗时 | 文件数 | 提交数 |
|---------|------|------|--------|--------|
| nl_001  | low  | ~30s | 2      | 1      |
| nl_002  | medium | ~60s | 5    | 2      |
| nl_003  | high | ~90s | 8      | 3      |

**耗时分解**：
- Intent Builder: 40%
- Coordinator: 30%
- Dry-Executor: 25%
- PR汇总: 5%

---

## 故障排除清单

运行Pipeline前检查：

- [ ] Python 3.13+已安装
- [ ] 项目依赖已安装（`pip install -e .`）
- [ ] NL examples存在（`ls examples/nl/nl_00*.json`）
- [ ] Runner脚本可执行（`chmod +x scripts/pipeline/run_nl_to_pr_artifacts.py`）
- [ ] ContentRegistry已初始化（`python -m agentos.cli.main migrate --init`）
- [ ] Coordinator CLI已注册（`python -m agentos.cli.main --help | grep coordinate`）

运行失败后检查：

- [ ] 审计日志（`cat outputs/.../audit/pipeline_audit_log.jsonl`）
- [ ] 标准错误输出（Pipeline打印的错误信息）
- [ ] 中间产物是否生成（`ls outputs/.../01_intent/`）
- [ ] 手动运行失败步骤（复制audit log中的命令）

---

**最后更新**: 2026-01-25  
**维护者**: AgentOS团队
