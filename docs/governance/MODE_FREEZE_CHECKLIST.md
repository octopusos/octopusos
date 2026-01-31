# Mode 系统功能冻结检查清单

**版本**: 1.0.0
**生效日期**: 2026-01-30
**适用于**: 所有开发人员
**状态**: Active

---

## 目录

1. [提交代码前的检查清单](#1-提交代码前的检查清单)
2. [异常申请检查清单](#2-异常申请检查清单)
3. [Bug 修复检查清单](#3-bug-修复检查清单)
4. [工具使用指南](#4-工具使用指南)
5. [常见问题 FAQ](#5-常见问题-faq)

---

## 1. 提交代码前的检查清单

### 1.1 基础检查

在提交任何代码前，请确认：

- [ ] **已阅读冻结规范**: [MODE_FREEZE_SPECIFICATION.md](./MODE_FREEZE_SPECIFICATION.md)
- [ ] **了解冻结期限**: 2026-01-30 至 2026-04-30
- [ ] **了解冻结范围**: 14+ 个 Mode 系统文件

### 1.2 文件修改检查

运行自动检查工具：

```bash
# 检查当前变更
./scripts/verify_mode_freeze.sh

# 详细输出
./scripts/verify_mode_freeze.sh --verbose

# JSON 格式输出
./scripts/verify_mode_freeze.sh --json
```

手动检查：

- [ ] **我修改的文件不在冻结列表中**
- [ ] **如果修改了冻结文件，我有正当理由（P0/P1 bug、安全补丁等）**
- [ ] **我已获得必要的审批**

### 1.3 冻结文件列表

以下文件在冻结期间禁止修改（除非获得批准）：

**核心模块** (6 个文件):
- [ ] `agentos/core/mode/mode_policy.py`
- [ ] `agentos/core/mode/mode_alerts.py`
- [ ] `agentos/core/mode/mode.py`
- [ ] `agentos/core/mode/mode_proposer.py`
- [ ] `agentos/core/mode/mode_selector.py`
- [ ] `agentos/core/mode/pipeline_runner.py`

**API 层** (1 个文件):
- [ ] `agentos/webui/api/mode_monitoring.py`

**前端层** (1 个文件):
- [ ] `agentos/webui/static/js/views/ModeMonitorView.js`

**配置文件** (5 个文件):
- [ ] `configs/mode/default_policy.json`
- [ ] `configs/mode/dev_policy.json`
- [ ] `configs/mode/strict_policy.json`
- [ ] `configs/mode/alert_config.json`
- [ ] `agentos/core/mode/mode_policy.schema.json`

**文档** (2 个文件):
- [ ] `agentos/core/mode/README.md`
- [ ] `agentos/core/mode/README_POLICY.md`

### 1.4 Commit Message 检查

如果修改了冻结文件，确认 commit message 包含以下标记之一：

- [ ] **Bug 修复**: 包含 `fix`, `bugfix`, 或 `bug fix`
- [ ] **安全补丁**: 包含 `security`, `CVE`, 或 `vulnerability`
- [ ] **文档更新**: 包含 `docs` 或 `documentation`
- [ ] **测试增强**: 包含 `test` 或 `testing`
- [ ] **例外批准**: 包含 `[mode-freeze-exception]`

**示例 commit messages**:

```bash
# Bug 修复
git commit -m "fix(mode): correct policy evaluation logic for edge case"

# 安全补丁
git commit -m "security(mode): fix path traversal in policy loader (CVE-2026-1234)"

# 文档更新
git commit -m "docs(mode): clarify policy configuration examples"

# 例外批准
git commit -m "feat(mode): add new alert type [mode-freeze-exception] (EXC-20260130123456)"
```

### 1.5 测试检查

- [ ] **所有现有测试通过**: `pytest tests/`
- [ ] **添加了回归测试**（对于 bug 修复）
- [ ] **性能测试通过**（对于性能优化）
- [ ] **安全扫描通过**（对于安全补丁）

### 1.6 文档检查

- [ ] **更新了相关文档**
- [ ] **添加了变更说明**（如果是 bug 修复）
- [ ] **记录了例外批准**（如果适用）

---

## 2. 异常申请检查清单

### 2.1 申请前的准备

在提交例外申请前，请确认：

- [ ] **问题严重级别**: 必须是 P0 (Critical) 或 P1 (High)
- [ ] **无替代方案**: 已充分调研非侵入式方案
- [ ] **影响范围评估**: 完成技术、用户、风险评估

### 2.2 P2/P3 级别问题

如果你的问题是 P2 或 P3 级别：

- [ ] **推迟到冻结期结束后处理**
- [ ] **记录到待办事项**: 创建 GitHub Issue 并标记 `mode-freeze-deferred`
- [ ] **评估临时缓解措施**: 是否可以通过配置、文档等方式临时解决

### 2.3 申请文档准备

使用模板创建例外申请：

```bash
# 复制模板
cp docs/governance/MODE_EXCEPTION_REQUEST_TEMPLATE.md \
   docs/governance/exception_requests/EXC-$(date +%Y%m%d%H%M%S).md

# 编辑申请文档
# 填写所有必需字段
```

必需字段检查：

- [ ] **申请编号**: 使用格式 `EXC-YYYYMMDDHHmmss`
- [ ] **申请日期**: 填写当前日期
- [ ] **申请人**: 你的姓名和联系方式
- [ ] **严重级别**: P0 或 P1
- [ ] **问题描述**: 清晰、详细、可重现
- [ ] **修改的文件**: 列出所有将修改的文件
- [ ] **变更描述**: 详细说明代码变更内容
- [ ] **API 变更**: 明确说明是否改变 API
- [ ] **替代方案分析**: 至少列出 3 个替代方案及其不可行原因
- [ ] **影响范围评估**: 技术影响、用户影响、风险评估
- [ ] **测试计划**: 详细的测试步骤和验收标准
- [ ] **回滚方案**: 清晰的回滚步骤

### 2.4 提交申请

- [ ] **创建 GitHub Issue**: 使用标签 `mode-freeze-exception`
- [ ] **提前 3 个工作日提交**（非紧急情况）
- [ ] **通知技术负责人**: mode-system-owner@company.com
- [ ] **等待初审结果**: 1 个工作日内

### 2.5 审批后流程

获得批准后：

- [ ] **记录例外批准**: 使用 `scripts/record_mode_freeze_exception.py`
- [ ] **更新 commit message**: 添加 `[mode-freeze-exception]` 和例外编号
- [ ] **执行变更**: 严格按照批准的方案
- [ ] **完整的代码审查**: 至少 2 人审查
- [ ] **验证和测试**: 按照测试计划执行
- [ ] **后续跟踪**: 1 周内完成验证

---

## 3. Bug 修复检查清单

### 3.1 Bug 严重级别判断

根据以下标准判断 bug 严重级别：

#### Critical (P0) - 致命级

- [ ] 系统崩溃或无法启动
- [ ] 数据丢失或数据损坏
- [ ] 严重安全漏洞（CVE >= 9.0）
- [ ] 核心功能完全不可用
- [ ] 影响 > 80% 用户

**SLA**: 1 小时响应，24 小时修复

#### High (P1) - 高级

- [ ] 核心功能不可用但系统可运行
- [ ] 性能严重下降（> 50% 退化）
- [ ] 影响 30-80% 用户
- [ ] 中等安全漏洞（CVE 7.0-8.9）
- [ ] 数据一致性问题

**SLA**: 4 小时响应，3 天修复

#### Medium (P2) - 中级

- [ ] 次要功能不可用
- [ ] 性能轻微下降
- [ ] 影响 < 30% 用户
- [ ] 有可行的临时缓解措施

**处理**: 推迟到冻结期结束后

#### Low (P3) - 低级

- [ ] 边缘情况错误
- [ ] 用户体验问题
- [ ] 文档错误
- [ ] 不影响功能

**处理**: 推迟到冻结期结束后

### 3.2 Bug 修复前检查

- [ ] **确认 bug 可重现**: 有明确的重现步骤
- [ ] **创建 GitHub Issue**: 记录 bug 详情
- [ ] **评估严重级别**: 使用上述标准
- [ ] **搜索已知问题**: 检查是否已有修复
- [ ] **评估影响范围**: 多少用户受影响

### 3.3 修复过程检查

- [ ] **根因分析**: 找到问题的根本原因
- [ ] **最小化变更**: 只修复必要的部分，不重构
- [ ] **保持 API 兼容**: 不改变公共 API 签名
- [ ] **添加回归测试**: 确保 bug 不会再次出现
- [ ] **更新文档**: 如果行为有变化
- [ ] **代码审查**: 至少 2 人审查

### 3.4 修复后检查

- [ ] **验证修复**: bug 已解决
- [ ] **无副作用**: 没有引入新问题
- [ ] **性能测试**: 性能无退化
- [ ] **用户验证**: 征求受影响用户的反馈
- [ ] **更新冻结日志**: 记录 bug 修复（如果修改了冻结文件）

---

## 4. 工具使用指南

### 4.1 验证脚本

#### 基础使用

```bash
# 检查当前变更
cd /path/to/AgentOS
./scripts/verify_mode_freeze.sh
```

#### 高级选项

```bash
# 详细输出
./scripts/verify_mode_freeze.sh --verbose

# 检查特定 commit
./scripts/verify_mode_freeze.sh --commit abc123

# 检查 PR
./scripts/verify_mode_freeze.sh --pr 123

# JSON 输出（用于 CI/CD）
./scripts/verify_mode_freeze.sh --json

# 自定义基准分支
./scripts/verify_mode_freeze.sh --base-branch develop
```

#### 输出解读

```bash
# 退出码
0 - 验证通过
1 - 发现违规
2 - 脚本错误

# 检查退出码
./scripts/verify_mode_freeze.sh
echo $?
```

### 4.2 Git Hook 安装

#### 自动安装

```bash
# 安装 pre-commit hook
./scripts/install_mode_freeze_hooks.sh

# 按提示选择安装方式
```

#### 配置选项

```bash
# 启用 hook
git config hooks.modeFreezeVerify true

# 禁用 hook
git config hooks.modeFreezeVerify false

# 临时绕过（不推荐）
git commit --no-verify
```

#### 手动安装

如果自动安装失败，可以手动集成：

1. 编辑 `.git/hooks/pre-commit`
2. 添加以下内容：

```bash
# Mode Freeze Verification
MODE_FREEZE_HOOK="$(git rev-parse --show-toplevel)/scripts/hooks/pre-commit-mode-freeze"
if [[ -f "$MODE_FREEZE_HOOK" ]]; then
    "$MODE_FREEZE_HOOK" || exit 1
fi
```

3. 确保可执行：

```bash
chmod +x .git/hooks/pre-commit
```

### 4.3 例外记录工具

#### 基础使用

```bash
# 记录 bug 修复例外
python scripts/record_mode_freeze_exception.py \
  --file agentos/core/mode/mode.py \
  --type bug_fix \
  --severity P1 \
  --approval "John Doe" \
  --reason "Fix critical mode selection bug"
```

#### 完整示例

```bash
# 带 issue 和 PR 引用
python scripts/record_mode_freeze_exception.py \
  --file agentos/core/mode/mode_policy.py \
  --type security_patch \
  --severity P0 \
  --approval "Jane Smith" \
  --reason "Fix CVE-2026-1234 path traversal vulnerability" \
  --issue 456 \
  --pr 789

# 干运行（预览不写入）
python scripts/record_mode_freeze_exception.py \
  --file agentos/core/mode/mode_alerts.py \
  --type bug_fix \
  --severity P1 \
  --approval "Bob Wilson" \
  --reason "Fix alert delivery failure" \
  --dry-run
```

#### 参数说明

- `--file`: 被修改的冻结文件（必需）
- `--type`: 变更类型（必需）
  - `bug_fix`: Bug 修复
  - `security_patch`: 安全补丁
  - `performance_optimization`: 性能优化
  - `docs_update`: 文档更新
  - `test_enhancement`: 测试增强
- `--severity`: 严重级别（必需，仅 P0/P1）
- `--approval`: 审批人姓名（必需）
- `--reason`: 例外原因（必需）
- `--issue`: 相关 issue 编号（可选）
- `--pr`: 相关 PR 编号（可选）
- `--dry-run`: 预览不写入（可选）

#### 工作流示例

```bash
# 1. 记录例外
python scripts/record_mode_freeze_exception.py \
  --file agentos/core/mode/mode.py \
  --type bug_fix \
  --severity P1 \
  --approval "Alice" \
  --reason "Fix mode selection deadlock"

# 输出: Exception ID: EXC-20260130123456

# 2. 提交例外记录
git add docs/governance/MODE_FREEZE_LOG.md
git commit -m "chore: record mode freeze exception EXC-20260130123456 [mode-freeze-exception]"

# 3. 进行实际修复
# ... 修改代码 ...

# 4. 提交修复
git add agentos/core/mode/mode.py
git commit -m "fix(mode): resolve selection deadlock (Exception: EXC-20260130123456)"

# 5. 创建 PR
git push origin fix/mode-selection-deadlock
gh pr create --title "fix: mode selection deadlock (P1)" --body "Exception: EXC-20260130123456"
```

---

## 5. 常见问题 FAQ

### 5.1 关于冻结规范

**Q: 为什么要冻结 Mode 系统？**

A: Mode 系统在 Task #30 评估中获得 100/100 分，已达到生产就绪状态。冻结期用于观察系统稳定性，避免特性蔓延，专注于集成和生态建设。

**Q: 冻结期多长？**

A: 最短 2-3 个月（2026-01-30 至 2026-04-30），可能根据实际情况延长。

**Q: 什么时候会解冻？**

A: 满足以下所有条件时：
- 已度过最短冻结期
- 生产环境运行稳定
- 用户反馈良好（满意度 > 80%）
- 性能指标达标
- 架构委员会批准

---

### 5.2 关于允许的变更

**Q: 我可以修改 Mode 系统的 Bug 吗？**

A: 可以，但仅限于 P0 和 P1 级别的 bug。P2/P3 级别的 bug 请推迟到冻结期结束后。

**Q: 我可以优化 Mode 系统的性能吗？**

A: 可以，但必须满足：
- 不改变功能行为
- 不改变 API
- 输出完全一致
- 通过性能基准测试

**Q: 我可以更新 Mode 系统的文档吗？**

A: 可以，文档更新是允许的。但仅限于修正错误、澄清歧义、添加示例等，不能添加新功能的文档。

**Q: 我可以添加 Mode 系统的测试吗？**

A: 可以，增加测试覆盖率是鼓励的。但不能修改被测代码。

**Q: 什么是"不改变 API"？**

A: 不改变 API 意味着：
- 不修改函数/方法签名（参数、返回值）
- 不添加/删除公共方法
- 不修改类继承关系
- 不修改配置文件格式
- 不改变错误类型

---

### 5.3 关于例外申请

**Q: 我需要添加一个小功能，但不复杂，可以不申请例外吗？**

A: 不可以。任何新功能添加，无论多小，都必须申请例外并获得批准。建议推迟到冻结期结束后。

**Q: 我的 P2 bug 影响了很多用户，可以申请例外吗？**

A: 不可以。例外申请仅接受 P0 和 P1 级别。P2 bug 请评估临时缓解措施，或推迟到冻结期结束后。

**Q: 例外申请多久能获得批准？**

A:
- P0: 24 小时内（初审 4 小时，终审 12 小时）
- P1: 3 天内（初审 1 天，终审 2 天）

**Q: 如果我的例外申请被拒绝了怎么办？**

A: 审查拒绝理由，评估替代方案。可以：
1. 寻找非侵入式解决方案
2. 降低变更范围重新申请
3. 推迟到冻结期结束后

**Q: 紧急情况下可以先修复后申请吗？**

A: 仅在极端情况下（P0 级别，影响 > 80% 用户，生产环境完全宕机），可启动紧急绿色通道，先执行修复。但必须：
- 需 CTO 或技术负责人授权
- 24 小时内补充完整审批文档
- 进行事后分析（Postmortem）

---

### 5.4 关于工具使用

**Q: verify_mode_freeze.sh 检测失败，但我确定没有修改冻结文件？**

A: 可能是以下原因：
1. 文件路径问题：检查是否使用了正确的相对路径
2. 分支问题：检查基准分支是否正确（`--base-branch`）
3. 缓存问题：尝试 `git status` 确认实际变更

如果确认是误报，请联系技术负责人。

**Q: pre-commit hook 太严格了，每次 commit 都被拦截？**

A:
- 确认你的 commit 是否确实修改了冻结文件
- 如果是合法的 bug 修复，添加正确的 commit message 标记
- 如果有例外批准，确保已记录到 MODE_FREEZE_LOG.md
- 临时禁用：`git commit --no-verify`（不推荐）

**Q: record_mode_freeze_exception.py 提示文件不在冻结列表？**

A:
- 检查文件路径是否正确（使用相对于仓库根目录的路径）
- 如果文件确实应该被冻结但不在列表中，请联系架构委员会

**Q: 工具报错 "Not in a git repository"？**

A: 确保你在 AgentOS 仓库目录内运行工具。

---

### 5.5 关于 commit 和 PR

**Q: commit message 应该怎么写？**

A: 使用 Conventional Commits 格式，并添加适当的标记：

```bash
# Bug 修复
fix(mode): correct policy evaluation logic

# 安全补丁
security(mode): fix CVE-2026-1234

# 文档更新
docs(mode): clarify configuration

# 例外批准
feat(mode): add feature [mode-freeze-exception] (EXC-xxx)
```

**Q: 如何在 PR 中说明这是例外批准的变更？**

A: 在 PR 描述中明确标注：

```markdown
## Exception Approval

- Exception ID: EXC-20260130123456
- Severity: P1
- Type: Bug Fix
- Approval: Architecture Committee
- Reference: docs/governance/MODE_FREEZE_LOG.md

## Description
...
```

**Q: PR 被 CI 检查拦截了怎么办？**

A:
1. 检查 CI 日志，确认失败原因
2. 如果是 Mode Freeze 检查失败，按照上述流程申请例外
3. 如果有例外批准，确保已正确记录并在 commit 中标注
4. 联系 reviewer 说明情况

---

### 5.6 关于流程和政策

**Q: 我不同意冻结政策，可以向谁反馈？**

A:
- 技术讨论：mode-system-owner@company.com
- 政策反馈：architecture-committee@company.com
- 在下次定期评审时提出建议（每月一次）

**Q: 冻结政策会被修改吗？**

A: 冻结规范会定期评审（每月一次）。如果实际执行中发现问题，架构委员会可能会调整政策。

**Q: 我发现了冻结规范的漏洞或不合理之处？**

A: 请立即报告：
- 创建 GitHub Issue，标签 `mode-freeze-policy`
- 发邮件给 architecture-committee@company.com
- 说明问题和建议的改进方案

---

### 5.7 获取帮助

**Q: 我遇到了这里没有解答的问题？**

A: 联系方式：

- **技术负责人**: mode-system-owner@company.com
- **架构委员会**: architecture-committee@company.com
- **紧急热线**: mode-emergency@company.com（仅 P0 故障）

**Q: 哪里可以找到更多文档？**

A: 相关文档：

- [MODE_FREEZE_SPECIFICATION.md](./MODE_FREEZE_SPECIFICATION.md) - 冻结规范
- [MODE_BUG_FIX_PROCESS.md](./MODE_BUG_FIX_PROCESS.md) - Bug 修复流程
- [MODE_EXCEPTION_REQUEST_TEMPLATE.md](./MODE_EXCEPTION_REQUEST_TEMPLATE.md) - 例外申请模板
- [MODE_FREEZE_LOG.md](./MODE_FREEZE_LOG.md) - 冻结日志
- [MODE_FREEZE_QUICK_REFERENCE.md](./MODE_FREEZE_QUICK_REFERENCE.md) - 快速参考

---

## 附录 A: 快速决策树

```
开始
  |
  ├─ 我要修改 Mode 系统文件吗？
  │   ├─ 否 → ✅ 可以正常提交
  │   └─ 是 → 继续
  │
  ├─ 文件在冻结列表中吗？
  │   ├─ 否 → ✅ 可以正常提交
  │   └─ 是 → 继续
  │
  ├─ 这是什么类型的变更？
  │   ├─ 文档更新 → ✅ 允许（标记 commit）
  │   ├─ 测试增强 → ✅ 允许（标记 commit）
  │   ├─ Bug 修复 → 继续检查严重级别
  │   ├─ 性能优化 → 继续检查是否改变行为
  │   ├─ 安全补丁 → 继续检查严重级别
  │   └─ 新功能 → ❌ 禁止（申请例外或推迟）
  │
  ├─ Bug 严重级别？
  │   ├─ P0/P1 → 可以修复（遵循流程）
  │   └─ P2/P3 → ❌ 推迟到冻结期结束
  │
  ├─ 性能优化是否改变行为？
  │   ├─ 否 → ✅ 允许（标记 commit）
  │   └─ 是 → ❌ 禁止（申请例外）
  │
  ├─ 安全补丁严重级别？
  │   ├─ Critical/High → 可以修复（遵循流程）
  │   └─ Medium/Low → ❌ 推迟到冻结期结束
  │
  └─ 总结
      ├─ 如果允许 → 标记 commit → 提交 → 验证
      ├─ 如果需例外 → 申请 → 等待批准 → 记录 → 提交
      └─ 如果禁止 → 创建 Issue → 标记延期 → 冻结期后处理
```

---

## 附录 B: Commit Message 模板

### Bug 修复

```
fix(mode): <简短描述>

<详细说明问题和修复方法>

Fixes: #<issue-number>
Severity: P0/P1
Tested-by: <测试者>
Reviewed-by: <审查者>
```

### 安全补丁

```
security(mode): <简短描述>

<详细说明漏洞和修复方法>

CVE: CVE-YYYY-XXXXX
Severity: Critical/High
Security-Review: <审查者>
```

### 例外批准

```
<type>(mode): <简短描述> [mode-freeze-exception]

<详细说明变更内容>

Exception: EXC-<编号>
Approval: <审批人>
Reason: <例外原因>
```

---

**文档状态**: ✅ Active
**最后更新**: 2026-01-30
**维护者**: Architecture Committee
**反馈渠道**: architecture-committee@company.com
