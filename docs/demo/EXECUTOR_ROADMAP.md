# Executor 完整路线图：从 P0 Demo 到真正可用的执行系统

**时间**: 2026-01-26  
**状态**: 🟢 P0 基本完成 → 📍 Step 1-3 路线图  
**目标**: OpenCode/Codex/Claude CLI 真把活干完

---

## 📊 总览

| 阶段 | 目标 | 状态 | 预计工作量 |
|------|------|------|-----------|
| **P0 (已完成)** | Demo 级闭环（landing） | ✅ 90% | - |
| **Step 1** | AnswerPack 回填 + Resume | 🔴 0% | 2-3 天 |
| **Step 2** | v0.11 真 Executor | 🔴 0% | 3-5 天 |
| **Step 3** | 执行外包给工具 | 🔴 0% | 5-7 天 |

---

## ✅ P0 现状：已完成的 Demo 级闭环

### 已实现能力

- ✅ **NL → Intent → Coordinator → Dry-Executor → Executor** 的 demo 级闭环
- ✅ **Worktree 执行 + 回收主 repo**（patch/am 或 cherry-pick）
- ✅ **Demo 路径 0 subprocess**（限定 scope + import graph 不可达）
- ✅ **6 steps → 6 commits** 的可审计证据
- ✅ **Verify + Freeze Report**（可复现）

### 具体实现

```
已交付文件：
- agentos/core/infra/git_client.py (318 行，基于 GitPython)
- agentos/core/executor/v12_executor.py (完整的 worktree + 带回逻辑)
- scripts/gates/v12_demo_gate_no_subprocess_ast.py (AST 扫描)
- outputs/demo/verify_report.json + freeze_report.json
```

### P0 验收命令

```bash
# 运行完整 pipeline
uv run python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/pipeline/nl/nl_001_doc_change.txt \
  --out outputs/pipeline/demo_run

# 验证 subprocess gate
uv run python scripts/gates/v12_demo_gate_no_subprocess_ast.py

# 验证 6 steps → 6 commits
cat outputs/pipeline/demo_run/verify_report.json | jq '.commit_count'
```

---

## 🎯 Step 1：AnswerPack 回填 + Resume（解除 BLOCKED）

### 目标

Pipeline 遇到 `question_pack` 不再"只能停住"，而是 **可保存 answers → 继续跑后半段**。

### 1.1 交付物

| 文件 | 功能 | 状态 |
|------|------|------|
| `schemas/answers/answer_pack.schema.json` | AnswerPack JSON Schema | 🔴 未实现 |
| `agentos/core/answers/answer_store.py` | answers 持久化 (run_id → answer_pack) | 🔴 未实现 |
| `agentos/pipeline/resume.py` | Resume runner（从 checkpoint 继续） | 🔴 未实现 |
| `examples/pipeline/answers/blocked_to_success.json` | Blocked → Resumed 样例 | 🔴 未实现 |

### 1.2 Gates（冻结级）

**Gate A1: Blocked must stop**  
```python
# 检查：看到 question_pack → 状态必须 BLOCKED
# 不得生成 dry/executor 产物
assert status == "BLOCKED"
assert not exists("02_dryrun/exec_request.json")
assert not exists("03_executor/")
```

**Gate A2: Resume must continue**  
```python
# 同一 run_id 写入 answer_pack 后
# resume 必须产生 02/03/04 产物，并写审计
assert exists("02_dryrun/exec_request.json")
assert exists("03_executor/sandbox_proof.json")
assert exists("04_verification/verify_report.json")
assert audit_log.contains("RESUMED from BLOCKED")
```

**Gate A3: AnswerPack schema + coverage**  
```python
# 每个 question 必须有 answer
# evidence_refs 不下降（coverage 不允许变差）
for question in question_pack:
    assert answer_pack.has_answer(question.id)
    assert answer.evidence_refs >= question.min_evidence
```

### 1.3 验收命令

```bash
# 1. 生成 BLOCKED
uv run python scripts/pipeline/run_nl_to_pr_artifacts.py \
  --nl examples/pipeline/nl/nl_001_doc_change.txt \
  --out outputs/pipeline/run_blocked

# 预期：状态 BLOCKED，产生 question_pack.json
cat outputs/pipeline/run_blocked/01_intent/status.json | jq '.status'  # → "BLOCKED"

# 2. 生成 answers（人工或 LLM 填写）
uv run agentos answers create \
  --from outputs/pipeline/run_blocked/01_intent/question_pack.json \
  --out outputs/pipeline/run_blocked/answers/answer_pack.json

# 3. Resume
uv run python scripts/pipeline/resume_run.py \
  --run outputs/pipeline/run_blocked \
  --answers outputs/pipeline/run_blocked/answers/answer_pack.json

# 预期：产生 02/03/04 产物，状态 SUCCESS
cat outputs/pipeline/run_blocked/status.json | jq '.status'  # → "SUCCESS"
ls outputs/pipeline/run_blocked/03_executor/  # → 有 commits
```

---

## 🛡️ Step 2：v0.11 真 Executor（受控执行、可回滚、可审计）

### 目标

把"可签 demo"升级成 **可泛化、可恢复、可审计的工程系统**。

### 2.1 交付物

| 文件 | 功能 | 状态 |
|------|------|------|
| `schemas/executor/sandbox_policy.schema.json` | 沙箱策略 Schema | 🔴 未实现 |
| `agentos/core/executor/sandbox_policy.py` | SandboxPolicy 加载与校验 | 🔴 未实现 |
| `agentos/core/executor/run_tape.py` | RunTape 审计日志（start/end/checksum） | 🔴 未实现 |
| `agentos/core/executor/rollback.py` | 回滚到任意 step（commit sha + checksums） | 🟡 部分实现 |
| `agentos/core/executor/lock.py` | 同 repo 同 run_id 防并发踩踏 | 🔴 未实现 |
| `agentos/core/executor/review_gate.py` | requires_review 审批机制 | 🔴 未实现 |
| `policies/sandbox_policy.json` | 默认沙箱策略 | 🔴 未实现 |

### 2.2 Gates（冻结级，8 个）

**EX-A: Allowlist only**  
```python
# executor 只能执行允许的 op
allowed_ops = {"write_file", "update_file", "git_add", "git_commit"}
for step in exec_request.steps:
    assert step.action in allowed_ops
```

**EX-B: No shell / no subprocess**  
```python
# executor 路径 0 subprocess（scope gate）
violations = scan_ast(["agentos/core/executor/"], ["subprocess"])
assert len(violations) == 0
```

**EX-C: Sandbox proof**  
```python
# 必须 worktree 执行；主 repo 不允许直接写
assert exec_context.is_worktree == True
assert exec_context.main_repo_modified == False  # 带回前
```

**EX-D: Bring-back proof**  
```python
# 带回后主 repo commit 数量与 step 数一致
main_commits = git.log("--oneline", "HEAD~6..HEAD")
assert len(main_commits) == 6
```

**EX-E: Audit completeness**  
```python
# run_tape.jsonl 必须包含每 step 的 start/end 与 checksum
tape = load_jsonl("run_tape.jsonl")
assert len(tape) == len(exec_request.steps) * 2  # start + end
for entry in tape:
    assert "checksum" in entry
```

**EX-F: Rollback proof**  
```python
# 回滚到 step_03 后校验 checksums 与 snapshot 一致
rollback(run_id, to_step=3)
checksums_after = compute_checksums()
assert checksums_after == snapshot.step_03.checksums
```

**EX-G: Review gate**  
```python
# 高风险 plan 未审批 → 必须失败（BLOCKED/REQUIRES_REVIEW）
if exec_request.requires_review and not approval_file_exists():
    assert status == "REQUIRES_REVIEW"
    assert not exists("03_executor/commits/")
```

**EX-H: Determinism baseline**  
```python
# 同输入（固定 seed/fixture）输出结构稳定
run1 = execute(exec_request, seed=42)
run2 = execute(exec_request, seed=42)
assert run1.structure == run2.structure  # 至少结构+字段稳定
```

### 2.3 验收命令

```bash
# 1. 运行 executor（必须 sandbox）
uv run agentos exec run \
  --request outputs/pipeline/demo_run/02_dryrun/exec_request.json \
  --policy policies/sandbox_policy.json \
  --out outputs/exec/run_001

# 预期：产生 sandbox_proof.json + run_tape.jsonl
cat outputs/exec/run_001/sandbox_proof.json | jq '.is_worktree'  # → true
wc -l outputs/exec/run_001/run_tape.jsonl  # → 12 行（6 steps * 2）

# 2. 回滚验证
uv run agentos exec rollback \
  --run outputs/exec/run_001 \
  --to step_03

# 预期：git log 只有 3 commits，checksums 匹配
git -C outputs/exec/run_001/.worktree log --oneline | wc -l  # → 3
cat outputs/exec/run_001/rollback_proof.json | jq '.checksums_match'  # → true

# 3. Review gate 验证
uv run agentos exec run \
  --request outputs/.../high_risk_exec_request.json \
  --policy policies/sandbox_policy.json \
  --out outputs/exec/run_002

# 预期：未审批时状态 REQUIRES_REVIEW
cat outputs/exec/run_002/status.json | jq '.status'  # → "REQUIRES_REVIEW"

# 添加审批
echo "APPROVED by user@example.com" > outputs/exec/run_002/approval.txt

# 重新运行
uv run agentos exec run \
  --run outputs/exec/run_002 \
  --resume

# 预期：状态 SUCCESS
cat outputs/exec/run_002/status.json | jq '.status'  # → "SUCCESS"
```

---

## 🔧 Step 3：执行外包给工具（OpenCode / Codex / Claude CLI）

### 目标

Executor 不一定亲自改代码，而是 **生成 Tool Task Pack → 调工具执行 → 收回产物 → 验收**。

### 3.1 交付物

| 文件 | 功能 | 状态 |
|------|------|------|
| `schemas/tools/tool_task_pack.schema.json` | 工具任务包 Schema | 🔴 未实现 |
| `schemas/tools/tool_result_pack.schema.json` | 工具结果包 Schema | 🔴 未实现 |
| `agentos/ext/tools/claude_cli/adapter.py` | Claude CLI 适配器 | 🟡 存在但未完整 |
| `agentos/ext/tools/codex/adapter.py` | Codex 适配器 | 🟡 存在但未完整 |
| `agentos/ext/tools/opencode/adapter.py` | OpenCode 适配器 | 🔴 未实现 |
| `agentos/tool/dispatch.py` | 派发执行：生成命令、运行工具、收集输出 | 🔴 未实现 |
| `agentos/tool/verify.py` | 验收：对 result_pack 做 gates | 🔴 未实现 |

### 3.2 Gates（冻结级，6 个）

**TL-A: Pack completeness**  
```python
# task_pack 必须包含：目标、允许操作、约束、预期文件、commit plan
required_fields = ["goal", "allowed_ops", "constraints", "expected_files", "commit_plan"]
for field in required_fields:
    assert field in task_pack
```

**TL-B: No direct execute**  
```python
# tool adapter 只能执行"工具 CLI"，不允许绕过策略写文件
violations = scan_ast(["agentos/ext/tools/"], ["write_file", "subprocess.run"])
assert len(violations) == 0  # 只能调用 CLI
```

**TL-C: Evidence required**  
```python
# result_pack 必须包含 diff + test logs + commit hashes
assert "diff" in result_pack
assert "test_logs" in result_pack
assert "commit_hashes" in result_pack
assert len(result_pack.commit_hashes) > 0
```

**TL-D: Policy match**  
```python
# diff 不能超出 allowlist/paths/size 限制
for file in result_pack.diff.files:
    assert file.path in task_pack.allowed_paths
    assert file.size <= task_pack.max_file_size
```

**TL-E: Replay**  
```python
# 同一 task_pack 可重跑（记录 tool version + prompt_hash + seed）
assert result_pack.metadata.tool_version is not None
assert result_pack.metadata.prompt_hash is not None
assert result_pack.metadata.seed is not None
```

**TL-F: Human review**  
```python
# requires_review 时 result_pack 必须包含 reviewer_signoff
if task_pack.requires_review:
    assert "reviewer_signoff" in result_pack
    assert result_pack.reviewer_signoff.approved == True
```

### 3.3 验收命令

```bash
# 1. 生成工具任务包
uv run agentos tool pack \
  --from outputs/pipeline/demo_run/02_dryrun/exec_request.json \
  --tool claude_cli \
  --out outputs/tools/task_pack.json

# 预期：task_pack.json 包含完整字段
cat outputs/tools/task_pack.json | jq 'keys'
# → ["goal", "allowed_ops", "constraints", "expected_files", "commit_plan"]

# 2. 派发执行（真正调用 CLI）
uv run agentos tool dispatch \
  --pack outputs/tools/task_pack.json \
  --out outputs/tools/run_001

# 预期：调用 claude_cli，产生 stdout/stderr/diff/commits
ls outputs/tools/run_001/
# → stdout.log, stderr.log, diff.patch, commits/

# 3. 收回并验收
uv run agentos tool collect \
  --run outputs/tools/run_001 \
  --out outputs/tools/result_pack.json

cat outputs/tools/result_pack.json | jq '.commit_hashes | length'  # → 6

# 4. 验收 gates
uv run agentos tool verify \
  --result outputs/tools/result_pack.json

# 预期：所有 gates 通过
cat outputs/tools/run_001/verify_report.json | jq '.gates_passed'  # → true
```

---

## 📋 完整清单：从 P0 到 Step 3

### 已完成 ✅（P0）

- [x] NL → Intent → Coordinator → Dry-Executor → Executor 闭环
- [x] Worktree 执行 + 回收主 repo（patch/am）
- [x] Demo 路径 0 subprocess（限定 scope）
- [x] 6 steps → 6 commits 可审计证据
- [x] Verify + Freeze Report（可复现）

### 待完成 🔴（Step 1 - AnswerPack）

- [ ] `schemas/answers/answer_pack.schema.json`
- [ ] `agentos/core/answers/answer_store.py`
- [ ] `agentos/pipeline/resume.py`
- [ ] `examples/pipeline/answers/blocked_to_success.json`
- [ ] Gate A1: Blocked must stop
- [ ] Gate A2: Resume must continue
- [ ] Gate A3: AnswerPack schema + coverage

### 待完成 🔴（Step 2 - 真 Executor）

- [ ] `schemas/executor/sandbox_policy.schema.json`
- [ ] `agentos/core/executor/sandbox_policy.py`
- [ ] `agentos/core/executor/run_tape.py`
- [x] `agentos/core/executor/rollback.py`（部分实现）
- [ ] `agentos/core/executor/lock.py`
- [ ] `agentos/core/executor/review_gate.py`
- [ ] `policies/sandbox_policy.json`
- [ ] Gate EX-A: Allowlist only
- [x] Gate EX-B: No shell / no subprocess（已实现）
- [x] Gate EX-C: Sandbox proof（已实现）
- [x] Gate EX-D: Bring-back proof（已实现）
- [ ] Gate EX-E: Audit completeness
- [ ] Gate EX-F: Rollback proof
- [ ] Gate EX-G: Review gate
- [ ] Gate EX-H: Determinism baseline

### 待完成 🔴（Step 3 - 工具外包）

- [ ] `schemas/tools/tool_task_pack.schema.json`
- [ ] `schemas/tools/tool_result_pack.schema.json`
- [ ] 完善 `agentos/ext/tools/claude_cli/adapter.py`
- [ ] 完善 `agentos/ext/tools/codex/adapter.py`
- [ ] `agentos/ext/tools/opencode/adapter.py`
- [ ] `agentos/tool/dispatch.py`
- [ ] `agentos/tool/verify.py`
- [ ] Gate TL-A: Pack completeness
- [ ] Gate TL-B: No direct execute
- [ ] Gate TL-C: Evidence required
- [ ] Gate TL-D: Policy match
- [ ] Gate TL-E: Replay
- [ ] Gate TL-F: Human review

---

## 🎯 总结：能对外讲的故事

### 现在（P0）

> "我们已经有一个 demo 级的 Executor，可以把自然语言转成 6 个 git commits，全程在 worktree 执行，0 subprocess（限定 scope），可审计、可复现。"

### Step 1 之后

> "Pipeline 不再卡在 question_pack，可以保存 answers 并从断点继续，支持 BLOCKED → RESUMED 工作流。"

### Step 2 之后

> "Executor 变成真正的生产系统，有沙箱策略、审计日志、回滚能力、并发锁、审批机制，所有操作可验收。"

### Step 3 之后

> "Executor 不再限于自己改代码，可以把任务外包给 Claude CLI / Codex / OpenCode，收回产物后验收，变成真正的'任务调度器'。"

---

**最后更新**: 2026-01-26  
**下一步**: 等待决策 - 开始实施 Step 1 / Step 2 / Step 3
