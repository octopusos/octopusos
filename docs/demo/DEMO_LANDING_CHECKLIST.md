# AgentOS 真 Executor E2E Demo Checklist（空目录 Landing Site）

**目标**: 在全新空目录中，通过 AgentOS Executor 自动生成一个完整的 Landing Page，并产生不可抵赖的执行证据。

**核心价值**: 证明"真 Executor"能够在受控环境下完成复杂任务，所有动作可审计、可回滚。

---

## 0) Demo 约束（必须）

- **输入**: 一个全新空目录（只包含 `.git/` 或甚至连 `.git/` 都没有也行）
- **执行方式**: 必须走 Executor（非 Dry-Executor）
- **受控执行**: 所有动作必须在 sandbox / worktree 内完成（主工作区不被污染）
- **allowlist**: 只允许白名单动作（见下）
- **审计**: 每一步必须写入 `audit/run_tape.jsonl`（start/end/status + inputs/outputs + hashes）
- **可回滚**: 必须证明 rollback 能回到任意一步的 commit

---

## 1) 必须生成的文件（最终工作区内容）

### 网站文件（最小集合）

- `index.html`（包含 5 个 section：Hero / Features / Architecture / Use cases / Footer）
- `style.css`（包含响应式：至少 1 个 breakpoint）
- `script.js`（可选；如果没有交互可省略，但若有动画/交互则必须存在）
- `assets/`（可选；如有图标/图片则统一放这里）

### 工程文件（演示可用）

- `README.md`（必须含：本地运行方式、目录结构、如何重放 audit、如何 rollback）
- `.gitignore`（至少忽略 `outputs/`, `audit/` 中的临时输出，按规范来）

---

## 2) 必须的 Commit 计划（最少 6 个，边界清晰）

### Commit Message 固定口径（便于演示与验收）

1. **chore: init landing skeleton**
   - `index.html` 基本骨架 + `style.css` 空壳 + `README.md` 初版

2. **feat: add hero section**
   - Hero 区块（标题、副标题、CTA 按钮）

3. **feat: add features section**
   - Features 卡片（3-4 个核心特性）

4. **feat: add architecture section**
   - 可用 Mermaid 或纯 HTML/CSS 图示

5. **feat: add use cases section**
   - 2-3 个真实使用场景

6. **feat: add footer and polish**
   - Footer + 响应式 + 细节收口

### 强制规则

- 每个 commit 对应 **一个 PatchPlan step**（1:1 对齐）
- 每个 commit 必须产生对应 diff 证据（见 artifacts）

---

## 3) Allowlist（执行白名单，Demo 最小集合）

Demo 的"安全震撼"来自：只能做这几类操作，其它一律拒绝并记录

### 允许的操作

- `fs.write_text(path, content)`: 仅允许写入项目目录内（禁止绝对路径）
- `fs.mkdir(path)`
- `fs.read_text(path)`（只读项目内文件）
- `git.init()`（如目录无 git）
- `git.add(paths)`
- `git.commit(message)`
- `git.status()`, `git.diff()`（只读）
- （可选）`http.fetch(url)`: 默认关闭；若要用 icon CDN，必须显式打开并记录

### 硬禁止（必须 Gate）

- 任意 shell / subprocess
- 任意网络（除非你开了 `http.fetch` 且列入 allowlist）
- 触碰 `~/.ssh`, `~/.gitconfig`, `$HOME` 等宿主敏感路径

---

## 4) 必须跑的 Gates（Demo 专用最小套件）

### A. 执行安全类

- **G_EX_ALLOWLIST_STRICT**: 执行记录中只出现 allowlist 动作（否则 FAIL）
- **G_EX_NO_SHELL**: 代码与 run_tape 均不得出现 subprocess / shell / exec / eval
- **G_EX_SANDBOX_WORKTREE**: 证明在 worktree/临时目录执行；主目录无污染（机器验证）

### B. 审计与可复现

- **G_EX_AUDIT_COMPLETE**: run_tape.jsonl 每步都有 start/end，且包含输入/输出 hash
- **G_EX_DIFF_PER_STEP**: 每个 step 都有对应 diff 文件（见 artifacts）
- **G_EX_CHECKSUMS_PRESENT**: audit/checksums.json 覆盖关键产物

### C. 结果验收

- **G_EX_SITE_STRUCTURE**: 最终产物必须包含 5 个 section（HTML 结构检查）
- **G_EX_ROLLBACK_PROOF**: 自动执行 rollback 测试：回到第 2 步 commit，文件状态匹配预期

---

## 5) 必须产出的 Artifacts（不可抵赖证据）

### 审计

- `audit/run_tape.jsonl`（每一步一段事件流：start → actions → end）
- `audit/checksums.json`（至少包含：index.html/style.css/README.md + 每个 diff 的 hash）
- `audit/execution_summary.json`（汇总：steps、commits、风险、耗时、failures=0）

### 差异证据

- `diff/step_01.patch`
- `diff/step_02.patch`
- …
- `diff/step_06.patch`

### 执行环境证明

- `reports/sandbox_proof.json`（worktree 路径、cwd、env 摘要、禁止项检查结果）
- `reports/rollback_proof.json`（回滚前后 git rev-parse HEAD + 文件 hash 对比）

---

## 6) E2E 通过标准（对外展示用的一句话）

✅ **在全新空目录里，一条命令触发真 Executor**
- 产生 **6 个 commits** + 每步 diff + 完整 audit
- 所有 Gates **100% PASS**
- rollback 可回到任意一步且可机器验证

---

## 7) 关键决策（已定版）

- **输入格式**: 使用 `examples/pipeline/nl/*.txt`（最适合演示）
- **question_pack 处理**: 默认严格 BLOCKED，但 demo 提供 `answer_pack.json`（演示"解除阻塞"必须用它）
- **并行执行**: Executor 内部用 asyncio（I/O 为主，审计友好）

---

## 8) 一键运行命令

```bash
# 在 AgentOS 根目录执行
./scripts/demo/run_landing_demo.sh

# 验证 Gates
./scripts/gates/run_demo_landing_gates.sh
```

---

## 9) 验收流程

1. **运行 Demo**: `./scripts/demo/run_landing_demo.sh`
2. **检查产物**: 
   - `demo_output/landing_site/` 目录下有 6 个 commits
   - `demo_output/audit/run_tape.jsonl` 完整
   - `demo_output/diff/` 有 6 个 patch 文件
3. **运行 Gates**: `./scripts/gates/run_demo_landing_gates.sh`（exit code 0）
4. **测试 Rollback**: `git reset --hard <commit_2>` → 验证文件状态

---

**最后更新**: 2026-01-25
**状态**: ✅ Checklist 已冻结
