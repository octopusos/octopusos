# Mode Bug 修复快速参考手册

**版本**: 1.0.0
**生效日期**: 2026-01-30
**状态**: Active

---

## 📋 目录

1. [快速判定表](#1-快速判定表)
2. [SLA 时间表](#2-sla-时间表)
3. [常用命令速查](#3-常用命令速查)
4. [联系人列表](#4-联系人列表)
5. [常见问题 FAQ](#5-常见问题-faq)
6. [快速检查清单](#6-快速检查清单)

---

## 1. 快速判定表

### 1.1 严重级别快速判定

| 问题特征 | 级别 | 示例 |
|---------|------|------|
| 🔴 系统崩溃/数据丢失 | **P0** | 进程退出、数据库损坏 |
| 🔴 影响 >80% 用户 | **P0** | 所有用户无法登录 |
| 🔴 CVE >= 9.0 | **P0** | 严重安全漏洞 |
| 🟠 核心功能不可用 | **P1** | 无法创建任务 |
| 🟠 性能下降 >50% | **P1** | 响应时间从100ms到250ms |
| 🟠 CVE 7.0-8.9 | **P1** | 中等安全漏洞 |
| 🟡 次要功能异常 | **P2** | 监控面板显示错误 |
| 🟡 UI/UX 问题 | **P2** | 按钮对齐不正确 |
| ⚪ 文档错误 | **P3** | 文档拼写错误 |
| ⚪ 代码风格 | **P3** | 代码格式不一致 |

### 1.2 是否可在冻结期修复

```
┌─────────────────────────────────────────┐
│ 开始：发现 Bug                           │
└──────────────┬──────────────────────────┘
               │
               ▼
       ┌───────────────┐
       │ Bug 级别？    │
       └───┬───────┬───┘
           │       │
    P0/P1  │       │  P2/P3
           │       │
           ▼       ▼
    ┌──────────┐  ┌─────────────────┐
    │ 可以修复 │  │ 推迟到冻结期后  │
    └──────┬───┘  └─────────────────┘
           │
           ▼
    ┌─────────────────────┐
    │ 是否改变 API？      │
    └───┬─────────┬───────┘
        │         │
      是 │         │ 否
        │         │
        ▼         ▼
   ┌────────┐  ┌────────────┐
   │ 申请例外│  │ 直接修复   │
   └────────┘  └────────────┘
```

### 1.3 判定评分表

| 维度 | 权重 | 评分标准 |
|------|------|---------|
| **系统可用性** | 40% | 0=正常, 20=部分故障, 40=完全不可用 |
| **影响用户数** | 30% | 0=<10%, 10=10-30%, 20=30-80%, 30=>80% |
| **数据影响** | 20% | 0=无, 10=不一致, 20=损坏/丢失 |
| **安全影响** | 10% | 0=无, 5=低, 10=中高 |

**总分判定**:
- **90-100**: P0 (Critical)
- **60-89**: P1 (High)
- **30-59**: P2 (Medium)
- **0-29**: P3 (Low)

---

## 2. SLA 时间表

### 2.1 响应和修复 SLA

| 级别 | 响应时间 | 修复时间 | 工作方式 |
|------|----------|----------|---------|
| **P0** | 1 小时 | 24 小时 | 7×24 全天候 |
| **P1** | 4 小时 | 3 天 | 工作时间优先 |
| **P2** | 1 周 | 2 周 | 正常排期 |
| **P3** | 2 周 | 下个版本 | 积压处理 |

### 2.2 审批时限

| 级别 | 初审 | 终审 | 总时限 |
|------|------|------|--------|
| **P0** | 4小时 | 12小时 | 24小时 |
| **P1** | 1天 | 2天 | 3天 |
| **P2/P3** | - | - | 不受理 |

### 2.3 典型时间线

**P0 Bug 完整流程** (24小时):
```
00:00  发现问题
00:30  紧急响应
02:00  根因分析完成
06:00  修复完成
08:00  Code Review
10:00  合并发布
12:00  部署生产
24:00  监控验证完成
```

**P1 Bug 完整流程** (3天):
```
Day 1: 问题分析和方案设计
Day 2: 修复开发和测试
Day 3: Code Review 和发布
```

---

## 3. 常用命令速查

### 3.1 Bug 分析命令

```bash
# 检查最近的错误日志
tail -f /var/log/agentos/agentos.log | grep ERROR

# 搜索特定错误
grep "AttributeError" /var/log/agentos/*.log

# 检查系统状态
systemctl status agentos

# 查看最近的提交
git log --oneline -10

# 检查文件修改历史
git log -p -- agentos/core/mode/mode_policy.py
```

### 3.2 测试命令

```bash
# 运行单元测试
pytest tests/unit/mode/ -v

# 运行集成测试
pytest tests/integration/mode/ -v

# 运行特定测试
pytest tests/unit/mode/test_mode_policy_bugfix_123.py -v

# 检查代码覆盖率
pytest tests/unit/mode/ --cov=agentos/core/mode --cov-report=term-missing

# 性能测试
pytest tests/performance/test_mode_policy_performance.py -v

# 运行所有测试
pytest tests/ -v
```

### 3.3 代码质量检查

```bash
# 代码风格检查
flake8 agentos/core/mode/

# 类型检查
mypy agentos/core/mode/

# 安全扫描
bandit -r agentos/core/mode/

# 复杂度检查
radon cc agentos/core/mode/ -a

# 所有检查
flake8 agentos/core/mode/ && \
mypy agentos/core/mode/ && \
bandit -r agentos/core/mode/
```

### 3.4 Git 工作流命令

```bash
# 创建修复分支
git checkout -b fix/mode-{issue-number}-{description}

# 提交修复
git add {files}
git commit -m "fix(mode): {description} (#{issue})"

# 推送分支
git push origin fix/mode-{issue-number}-{description}

# 创建 PR
gh pr create --title "fix: {title}" --body "{description}"

# 合并 PR
gh pr merge {pr-number} --squash

# 创建 tag
git tag -a v{version} -m "Release v{version}: {description}"
git push origin v{version}
```

### 3.5 发布命令

```bash
# 更新版本
echo "{version}" > VERSION

# 更新 CHANGELOG
vim CHANGELOG.md

# 提交版本
git add VERSION CHANGELOG.md
git commit -m "chore: bump version to v{version}"

# 创建 release tag
git tag -a v{version} -m "Release v{version}"
git push origin master --tags

# 部署到预发布
./scripts/deploy.sh staging

# 部署到生产
./scripts/deploy.sh production
```

### 3.6 冻结检查命令

```bash
# 检查当前变更
./scripts/verify_mode_freeze.sh

# 详细输出
./scripts/verify_mode_freeze.sh --verbose

# 检查特定 commit
./scripts/verify_mode_freeze.sh --commit {commit-hash}

# JSON 输出
./scripts/verify_mode_freeze.sh --json

# 记录例外
python scripts/record_mode_freeze_exception.py \
  --file {file} \
  --type {type} \
  --severity {P0/P1} \
  --approval "{approver}" \
  --reason "{reason}"
```

---

## 4. 联系人列表

### 4.1 紧急联系

| 角色 | 联系方式 | 使用场景 |
|------|---------|---------|
| **紧急热线** | mode-emergency@company.com | P0 Critical 故障 |
| **技术负责人** | mode-system-owner@company.com | 技术问题咨询 |
| **On-call 工程师** | +1-555-0100 | 24/7 紧急响应 |

### 4.2 团队联系

| 团队 | 联系方式 | 职责 |
|------|---------|------|
| **架构委员会** | architecture-committee@company.com | 例外审批 |
| **安全团队** | security-team@company.com | 安全问题 |
| **QA 团队** | qa-team@company.com | 测试支持 |
| **DevOps 团队** | devops-team@company.com | 部署支持 |

### 4.3 Mode 系统专家

| 模块 | 专家 | 联系方式 |
|------|------|---------|
| **mode_policy** | Alice Chen | alice@company.com |
| **mode_alerts** | Bob Wilson | bob@company.com |
| **mode_selector** | Carol Liu | carol@company.com |
| **mode_monitoring** | David Zhang | david@company.com |

---

## 5. 常见问题 FAQ

### 5.1 如何快速判断 Bug 级别？

**快速判定法**:
1. **系统能正常启动吗？** 否 → P0
2. **核心功能能用吗？** 否 → P0/P1
3. **影响多少用户？** >80% → P0, 30-80% → P1, <30% → P2
4. **有数据丢失吗？** 是 → P0
5. **有安全漏洞吗？** CVE >= 9.0 → P0, 7.0-8.9 → P1

**示例**:
- 系统崩溃 + 100% 用户 = **P0**
- 写操作失败 + 40% 用户 = **P1**
- UI 显示错误 + 10% 用户 = **P2**

### 5.2 P2 Bug 为什么不能在冻结期修复？

**原因**:
1. 冻结期专注于 **稳定性**，非关键问题应推迟
2. P2 Bug 不影响核心功能，有缓解措施
3. 修复 P2 可能引入新风险，得不偿失

**正确做法**:
- 创建 Issue 记录
- 标记 `mode-freeze-deferred`
- 安排到冻结期后处理
- 提供临时缓解措施

### 5.3 什么情况下需要申请例外？

**需要例外的情况**:
- ❌ 修改公共 API
- ❌ 修改配置文件格式
- ❌ 破坏向后兼容性
- ❌ 添加新功能
- ❌ 架构重构

**不需要例外**:
- ✅ 不改变 API 的 Bug 修复
- ✅ 不改变行为的性能优化
- ✅ 安全补丁
- ✅ 文档更新
- ✅ 测试增强

### 5.4 如何快速定位 Bug 根因？

**5 步定位法**:

1. **重现问题** - 按照报告步骤重现
   ```bash
   python reproduce_bug.py
   ```

2. **查看日志** - 找到错误堆栈
   ```bash
   grep ERROR /var/log/agentos/agentos.log
   ```

3. **代码审查** - 检查相关代码
   ```bash
   git log -p -- {file}
   ```

4. **断点调试** - 使用 pdb 调试
   ```python
   import pdb; pdb.set_trace()
   ```

5. **5 Whys 分析** - 深入挖掘根本原因
   ```
   为什么崩溃？ → 访问 None 对象
   为什么是 None？ → 配置加载失败
   为什么加载失败？ → 文件不存在
   为什么不存在？ → 用户误删
   为什么没检测？ → 缺少验证
   ```

### 5.5 修复需要多长时间？

**典型时间估计**:

| Bug 类型 | 分析 | 修复 | 测试 | 审查 | 发布 | 总计 |
|---------|------|------|------|------|------|------|
| **简单** | 1h | 2h | 1h | 2h | 1h | **7h** |
| **中等** | 2h | 4h | 2h | 4h | 2h | **14h** |
| **复杂** | 4h | 8h | 4h | 8h | 4h | **28h** |

**影响因素**:
- 问题复杂度
- 测试覆盖要求
- 审查人数和响应速度
- 发布流程

### 5.6 如何确保修复质量？

**质量保证清单**:

1. **完整测试**
   - ✅ 单元测试（新增 + 现有）
   - ✅ 集成测试
   - ✅ 回归测试
   - ✅ 性能测试（P0/P1）

2. **充分审查**
   - ✅ 至少 2 人审查
   - ✅ 包含 Maintainer
   - ✅ 功能审查
   - ✅ 冻结规范审查

3. **文档完整**
   - ✅ CHANGELOG 更新
   - ✅ 代码注释
   - ✅ API 文档（如需要）

4. **部署验证**
   - ✅ 预发布环境测试
   - ✅ 生产环境监控
   - ✅ 回滚方案准备

---

## 6. 快速检查清单

### 6.1 Bug 报告检查

**提交前检查**:
- [ ] 问题描述清晰
- [ ] 重现步骤完整
- [ ] 错误日志已粘贴
- [ ] 环境信息完整
- [ ] 影响范围已评估
- [ ] 严重级别已标记
- [ ] 临时缓解措施已说明

**提交方式**:
```bash
# GitHub Issue
https://github.com/company/agentos/issues/new

# 邮件 (P0 紧急)
To: mode-emergency@company.com
Subject: [P0] Mode System: {brief description}
```

### 6.2 修复开发检查

**开发前**:
- [ ] 已充分理解根因
- [ ] 已选择最小化方案
- [ ] 已确认符合冻结规范
- [ ] 已准备测试计划

**开发中**:
- [ ] 只修改必要代码
- [ ] 添加详细注释
- [ ] 不改变 API
- [ ] 向后兼容

**开发后**:
- [ ] 所有测试通过
- [ ] 代码风格检查通过
- [ ] 性能无退化
- [ ] 文档已更新

### 6.3 Code Review 检查

**功能检查**:
- [ ] Bug 已修复
- [ ] 回归测试已添加
- [ ] 无新 Bug 引入
- [ ] 边界条件已处理

**冻结规范检查**:
- [ ] 符合冻结规范
- [ ] 不改变 API
- [ ] 向后兼容
- [ ] 最小化变更

**质量检查**:
- [ ] 代码清晰
- [ ] 注释充分
- [ ] 无安全问题
- [ ] 性能合理

### 6.4 发布检查

**发布前**:
- [ ] 所有审查通过
- [ ] 版本号已更新
- [ ] CHANGELOG 已更新
- [ ] Tag 已创建
- [ ] 回滚方案已准备

**发布后**:
- [ ] 部署成功
- [ ] 冒烟测试通过
- [ ] 监控正常
- [ ] 无新增错误

---

## 7. 快速参考卡片

### 7.1 P0 紧急响应卡片

```
═══════════════════════════════════════
   🚨 P0 CRITICAL BUG 紧急响应卡
═══════════════════════════════════════

立即行动:
1. 通知: mode-emergency@company.com
2. 评估影响: 用户数、数据、SLA
3. 临时缓解: 回滚/降级/禁用功能
4. 开始修复: 创建紧急分支

时间要求:
• 响应: 1 小时内
• 修复: 24 小时内
• 工作: 7×24 全天候

关键联系:
• 紧急热线: mode-emergency@company.com
• On-call: +1-555-0100
• 技术负责人: mode-system-owner@company.com

记住:
✓ 安全第一 - 先止损
✓ 快速响应 - 每分钟都重要
✓ 清晰沟通 - 及时更新进度
✓ 完整记录 - 事后分析
═══════════════════════════════════════
```

### 7.2 修复流程速查卡

```
═══════════════════════════════════════
   🔧 BUG 修复流程速查卡
═══════════════════════════════════════

1️⃣ 报告 & 分类
   └─ 严重级别: P0/P1/P2/P3
   └─ SLA: 响应 & 修复时限

2️⃣ 分析 & 设计
   └─ 根因分析 (5 Whys)
   └─ 最小化修复方案

3️⃣ 开发 & 测试
   └─ 创建分支: fix/mode-{issue}-{desc}
   └─ 添加测试: test_bugfix_{issue}

4️⃣ 审查 & 合并
   └─ 至少 2 人审查
   └─ 功能 + 冻结规范 + 质量

5️⃣ 发布 & 监控
   └─ 更新版本 & CHANGELOG
   └─ 部署并监控 24 小时

关键原则:
✓ 最小化变更
✓ 向后兼容
✓ 完整测试
✓ 充分审查
═══════════════════════════════════════
```

### 7.3 测试速查卡

```
═══════════════════════════════════════
   ✅ 测试速查卡
═══════════════════════════════════════

必须的测试:
□ 回归测试 (Bug 场景)
□ 单元测试 (新增代码)
□ 集成测试 (端到端)
□ 边界测试 (异常输入)

可选的测试 (P0/P1):
□ 性能测试 (无退化)
□ 安全测试 (无漏洞)
□ 压力测试 (高负载)

快速命令:
# 单元测试
pytest tests/unit/mode/ -v

# 集成测试
pytest tests/integration/mode/ -v

# 覆盖率
pytest --cov=agentos/core/mode

# 性能
pytest tests/performance/ -v

验收标准:
✓ 所有测试通过 100%
✓ 新代码覆盖率 100%
✓ 性能无退化 (<5%)
═══════════════════════════════════════
```

---

## 8. 应急响应流程图

```
P0 紧急响应流程 (24小时)
═══════════════════════════════════════

00:00 │ 🚨 发现问题
      │ ├─ 立即通知 On-call
      │ └─ 创建 P0 Issue
      ▼
00:30 │ 🔍 快速评估
      │ ├─ 影响范围
      │ ├─ 数据风险
      │ └─ 业务影响
      ▼
01:00 │ ⚡ 临时缓解
      │ ├─ 回滚版本
      │ ├─ 禁用功能
      │ └─ 降级模式
      ▼
02:00 │ 🔬 根因分析
      │ ├─ 查看日志
      │ ├─ 代码分析
      │ └─ 5 Whys
      ▼
06:00 │ 💻 开发修复
      │ ├─ 最小化变更
      │ ├─ 添加测试
      │ └─ 本地验证
      ▼
08:00 │ 👀 Code Review
      │ ├─ 功能审查
      │ ├─ 安全审查
      │ └─ 冻结规范
      ▼
10:00 │ 🚀 发布部署
      │ ├─ 预发布测试
      │ ├─ 生产部署
      │ └─ 冒烟测试
      ▼
12:00 │ 📊 监控验证
      │ ├─ 关键指标
      │ ├─ 错误日志
      │ └─ 用户反馈
      ▼
24:00 │ ✅ 关闭 Issue
      │ └─ 后续跟踪

═══════════════════════════════════════
```

---

## 相关文档

- [MODE_BUG_FIX_PROCESS.md](./MODE_BUG_FIX_PROCESS.md) - 完整流程
- [MODE_BUG_FIX_WORKFLOW.md](./MODE_BUG_FIX_WORKFLOW.md) - 工作流程图
- [MODE_BUG_FIX_TESTING_GUIDE.md](./MODE_BUG_FIX_TESTING_GUIDE.md) - 测试指南
- [templates/BUG_FIX_TEMPLATE.md](./templates/BUG_FIX_TEMPLATE.md) - Bug 修复模板
- [examples/MODE_BUG_FIX_EXAMPLES.md](./examples/MODE_BUG_FIX_EXAMPLES.md) - 修复示例

---

**文档状态**: ✅ Active
**最后更新**: 2026-01-30
**维护者**: Architecture Committee
**打印友好**: 适合打印为快速参考卡片
