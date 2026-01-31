# Mode Bug 修复示例集

**版本**: 1.0.0
**生效日期**: 2026-01-30
**状态**: Active

---

## 目录

1. [P0 Bug 示例](#1-p0-bug-示例)
2. [P1 Bug 示例](#2-p1-bug-示例)
3. [P2 Bug 示例](#3-p2-bug-示例)
4. [安全补丁示例](#4-安全补丁示例)
5. [性能优化示例](#5-性能优化示例)

---

## 1. P0 Bug 示例

### 示例 1.1: Mode Policy 崩溃导致系统不可用

#### 问题描述

**Issue #123**: Mode policy evaluation crash when rules is None

**严重级别**: P0 (Critical)

**发现时间**: 2026-01-15 14:30

**报告人**: Alice Chen

**现象**:
```
当 Mode policy 配置文件加载失败或 rules 字段为 null 时，
调用 ModePolicy.evaluate() 会导致 AttributeError 崩溃，
进而导致整个 AgentOS 进程退出。
```

**影响范围**:
- 影响所有使用自定义 policy 配置的用户
- 系统完全不可用
- 估计影响 100% 生产用户
- 导致约 2 小时的服务中断

**错误日志**:
```python
Traceback (most recent call last):
  File "agentos/core/mode/mode_policy.py", line 45, in evaluate
    return self.rules.check(mode)
AttributeError: 'NoneType' object has no attribute 'check'
```

#### 严重性评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 系统可用性 | 40/40 | 系统完全崩溃 |
| 影响用户数 | 30/30 | 100% 用户受影响 |
| 数据影响 | 0/20 | 无数据丢失 |
| 安全影响 | 0/10 | 无安全问题 |
| **总分** | **70/100** | **P0: Critical** |

#### 根因分析

**直接原因**:
```python
# agentos/core/mode/mode_policy.py, line 45
def evaluate(self, mode: str) -> bool:
    # 问题：未检查 self.rules 是否为 None
    return self.rules.check(mode)  # 当 rules 为 None 时崩溃
```

**根本原因 (5 Whys)**:

1. **为什么系统崩溃？** 因为访问了 None 对象的属性
2. **为什么 rules 是 None？** 因为配置文件加载失败
3. **为什么配置加载失败？** 因为配置文件被误删除
4. **为什么没有检测到配置文件缺失？** 因为缺少防御性检查
5. **为什么缺少防御性检查？** 因为开发时假设配置总是存在

**根本原因**: 代码缺少防御性编程，未处理配置异常情况。

#### 修复过程

**1. 紧急响应 (14:30-15:00)**

```bash
# 14:30 - 发现问题
# 14:35 - 通知 On-call 工程师
# 14:40 - 确认根因
# 14:45 - 实施临时缓解措施

# 临时缓解：回滚到上一个版本
git checkout v1.0.0
systemctl restart agentos

# 14:55 - 服务恢复
# 15:00 - 开始开发永久修复
```

**2. 修复开发 (15:00-17:00)**

创建修复分支:
```bash
git checkout master
git pull origin master
git checkout -b fix/mode-123-policy-crash
```

代码修复:
```python
# agentos/core/mode/mode_policy.py

def evaluate(self, mode: str) -> bool:
    """
    评估给定模式是否被允许

    Args:
        mode: 要评估的模式（如 "read", "write"）

    Returns:
        True 如果允许，False 如果拒绝

    Note:
        修复 Issue #123: 添加了 None 检查以避免崩溃
        当 rules 为 None 时，采用 deny-by-default 策略
    """
    # 修复 Issue #123: 添加 None 检查
    if self.rules is None:
        logger.warning(
            "Mode policy rules is None, denying by default. "
            "Check your configuration file at %s",
            self.config_path
        )
        return False  # deny-by-default 策略

    # 额外的防御：检查 mode 是否有效
    if not mode or not isinstance(mode, str):
        logger.error("Invalid mode: %r", mode)
        return False

    # 原有逻辑
    return self.rules.check(mode)
```

添加回归测试:
```python
# tests/unit/mode/test_mode_policy_bugfix_123.py

import pytest
from agentos.core.mode import ModePolicy

def test_evaluate_with_none_rules(caplog):
    """
    回归测试：修复 Issue #123
    当 rules 为 None 时，evaluate 应该返回 False 而不是崩溃
    """
    policy = ModePolicy(rules=None)

    # 修复前：会抛出 AttributeError
    # 修复后：应该返回 False（deny-by-default）
    result = policy.evaluate("read")

    assert result is False
    assert "Mode policy rules is None" in caplog.text


def test_evaluate_with_empty_mode():
    """测试边界条件：空字符串 mode"""
    policy = ModePolicy(rules=None)

    assert policy.evaluate("") is False
    assert policy.evaluate(None) is False


def test_evaluate_with_invalid_mode_type():
    """测试边界条件：无效的 mode 类型"""
    policy = ModePolicy(rules=None)

    assert policy.evaluate(123) is False
    assert policy.evaluate([]) is False


def test_evaluate_normal_case_still_works():
    """确保修复不影响正常情况"""
    policy = ModePolicy.load_from_config("configs/mode/default_policy.json")

    # 正常情况应该仍然工作
    assert policy.evaluate("read") is True
    assert policy.evaluate("write") is True
    assert policy.evaluate("invalid_mode") is False


def test_evaluate_performance_no_regression():
    """性能回归测试：确保修复不影响性能"""
    import time

    policy = ModePolicy.load_from_config("configs/mode/default_policy.json")

    # 基准测试：评估 10000 次
    start = time.perf_counter()
    for _ in range(10000):
        policy.evaluate("read")
    duration = time.perf_counter() - start

    # 期望：平均每次 < 0.1ms (总共 < 1秒)
    assert duration < 1.0, f"Performance regression: {duration}s for 10000 calls"
```

运行测试:
```bash
# 运行新增测试
pytest tests/unit/mode/test_mode_policy_bugfix_123.py -v

# 运行所有 Mode 测试
pytest tests/unit/mode/ -v
pytest tests/integration/mode/ -v

# 检查代码覆盖率
pytest tests/unit/mode/ --cov=agentos/core/mode --cov-report=term-missing

# 代码质量检查
flake8 agentos/core/mode/mode_policy.py
mypy agentos/core/mode/mode_policy.py
```

**3. Code Review (17:00-19:00)**

提交 PR:
```bash
git add agentos/core/mode/mode_policy.py tests/unit/mode/test_mode_policy_bugfix_123.py
git commit -m "fix(mode): fix policy crash when rules is None (#123)

Problem:
- ModePolicy.evaluate() crashes with AttributeError when
  self.rules is None
- This happens when policy config is incomplete or corrupted
- Caused 2-hour production outage affecting 100% users

Solution:
- Added None check before accessing self.rules
- Return False (deny by default) when rules is None
- Added additional validation for mode parameter
- Added warning log to help users diagnose config issues

Impact:
- Fixes P0 crash issue
- No API changes
- Backward compatible
- Added comprehensive regression tests

Testing:
- Added 5 regression tests
- All existing tests pass
- Performance tests pass (no regression)
- Code coverage: 100% for new code

Closes #123"

git push origin fix/mode-123-policy-crash
```

GitHub PR:
```markdown
## Pull Request: Fix mode policy crash (#123)

### 🚨 P0 Critical Bug Fix

**Issue**: #123
**Severity**: P0 (Critical)
**Impact**: System-wide outage, 100% users affected

### Problem
Mode policy evaluation crashes when rules is None, causing entire system to fail.

### Solution
- Added defensive None check
- Implemented deny-by-default fallback
- Added comprehensive logging

### Testing
- ✅ 5 new regression tests
- ✅ All existing tests pass
- ✅ Performance validated (no regression)
- ✅ Manual testing in staging

### Checklist
- [x] Bug is fixed
- [x] Regression tests added
- [x] All tests pass
- [x] No API changes
- [x] Backward compatible
- [x] Documentation updated
- [x] CHANGELOG updated

### Reviewers
@tech-lead @mode-maintainer
```

Code Review 反馈和响应:
```
Reviewer 1 (tech-lead):
> 建议：在日志中包含配置文件路径，方便用户诊断。

Author:
✅ 已添加。更新了日志消息包含 self.config_path

Reviewer 2 (mode-maintainer):
> 问题：为什么选择 deny-by-default 而不是 allow-by-default？

Author:
从安全角度考虑，deny-by-default 更安全。如果配置加载失败，
拒绝所有操作比允许所有操作更安全。这符合 fail-safe 原则。

Reviewer 2:
✅ Approved. 同意你的理由。

Reviewer 1:
✅ Approved. LGTM!
```

**4. 发布 (19:00-20:00)**

合并和发布:
```bash
# 合并到 master
git checkout master
git merge --no-ff fix/mode-123-policy-crash
git push origin master

# 更新版本号 (v1.0.0 -> v1.0.1)
echo "1.0.1" > VERSION

# 更新 CHANGELOG
cat >> CHANGELOG.md << 'EOF'
## [1.0.1] - 2026-01-15

### Fixed
- **mode-policy**: Fix crash when policy rules is None ([#123](https://github.com/company/agentos/issues/123))
  - **Impact**: P0 - System-wide crash affecting 100% users
  - **Fix**: Added None check and deny-by-default fallback
  - **Regression Test**: Added comprehensive test suite
  - **Downtime**: Caused 2-hour outage (14:30-16:30)
EOF

# 创建 Git Tag
git add VERSION CHANGELOG.md
git commit -m "chore: bump version to v1.0.1"
git tag -a v1.0.1 -m "Release v1.0.1: Fix critical mode policy crash

Emergency release to fix P0 bug #123.

- Fixed system crash when policy rules is None
- Added defensive checks and fallback behavior
- Restored service after 2-hour outage
"
git push origin master --tags

# 触发 CI/CD 发布
# (自动构建和发布)
```

部署到生产:
```bash
# 19:30 - 部署到预发布环境
# 19:45 - 预发布验证通过
# 19:50 - 部署到生产环境
# 20:00 - 生产环境验证通过
```

**5. 监控验证 (20:00-次日 20:00)**

监控指标:
```
时间: 20:00 - 次日 20:00 (24小时)

指标监控:
✅ 错误率: 0.0% (之前 100%)
✅ 崩溃次数: 0 (之前每分钟数十次)
✅ 响应时间: 95ms P95 (无变化)
✅ 用户投诉: 0

结论: 修复成功，系统稳定
```

#### Code Review 记录

**PR #456**: fix/mode-123-policy-crash

**审查者 1**: Bob Wilson (Tech Lead)
- ✅ 批准
- 评论: "修复方案合理，测试充分，LGTM"

**审查者 2**: Carol Liu (Mode Maintainer)
- ✅ 批准
- 评论: "安全考虑周到，deny-by-default 是正确的选择"

**合并时间**: 2026-01-15 19:00

#### 发布记录

**发布版本**: v1.0.1
**发布时间**: 2026-01-15 19:50
**发布类型**: Emergency Patch
**发布原因**: P0 Critical Bug Fix

**发布说明**:
```
紧急修复版本，修复了导致系统崩溃的 P0 级别 Bug。
强烈建议所有用户立即升级。
```

**部署结果**:
- ✅ 预发布环境: 成功
- ✅ 生产环境: 成功
- ✅ 回滚方案: 已准备（未使用）

**后续跟踪**:
- 24小时内无新增问题
- 用户反馈积极
- Issue #123 已关闭

#### 经验教训

**做得好的地方**:
1. ✅ 快速响应（30分钟内恢复服务）
2. ✅ 完整的回归测试
3. ✅ 充分的代码审查
4. ✅ 清晰的沟通

**需要改进的地方**:
1. ❌ 应该在开发时就添加防御性检查
2. ❌ 配置加载失败应该有更好的错误处理
3. ❌ 应该有配置文件验证机制

**预防措施**:
1. 在 CI 中添加配置文件验证
2. 为所有外部输入添加防御性检查
3. 改进错误处理和日志记录
4. 增加配置加载的单元测试

---

## 2. P1 Bug 示例

### 示例 2.1: Mode 决策逻辑错误

#### 问题描述

**Issue #145**: Mode selector incorrectly blocks all write operations

**严重级别**: P1 (High)

**发现时间**: 2026-01-20 10:00

**报告人**: David Zhang

**现象**:
```
Mode selector 在评估 "write" 模式时，错误地拒绝所有写操作，
即使 policy 配置允许。导致用户无法执行任何需要写权限的任务。
```

**影响范围**:
- 影响使用 "write" 模式的用户
- 核心功能不可用
- 估计影响 40% 用户
- 可通过降级到 "read" 模式临时缓解

**重现步骤**:
```python
from agentos.core.mode import ModeSelector

selector = ModeSelector()
# 预期: 返回 True (允许写操作)
# 实际: 返回 False (错误地拒绝)
result = selector.can_execute("write", task_context)
print(result)  # False (错误)
```

#### 严重性评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 系统可用性 | 20/40 | 核心功能不可用 |
| 影响用户数 | 15/30 | 40% 用户受影响 |
| 数据影响 | 5/20 | 数据一致性问题 |
| 安全影响 | 0/10 | 无安全问题 |
| **总分** | **40/100** | **P1: High** |

#### 根因分析

**直接原因**:
```python
# agentos/core/mode/mode_selector.py, line 78
def can_execute(self, mode: str, context: dict) -> bool:
    # 问题：逻辑错误，应该是 OR 而不是 AND
    return self.policy.allows(mode) and self.guard.permits(mode)
    #                                   ^
    #                                   应该是 OR
```

**根本原因**:
在代码重构时，错误地将条件从 OR 改为了 AND，
导致需要 policy 和 guard 都允许才能执行，
而实际应该是任一允许即可。

#### 修复过程

**1. 问题验证 (10:00-11:00)**

```bash
# 创建测试环境
python -m venv venv_bug145
source venv_bug145/bin/activate
pip install -e .[dev]

# 重现问题
python tests/manual/reproduce_bug_145.py
# 输出: can_execute("write") = False (应该是 True)
```

**2. 修复开发 (11:00-13:00)**

创建分支:
```bash
git checkout -b fix/mode-145-write-blocked
```

代码修复:
```python
# agentos/core/mode/mode_selector.py

def can_execute(self, mode: str, context: dict) -> bool:
    """
    判断给定模式是否可以执行

    Args:
        mode: 模式名称
        context: 执行上下文

    Returns:
        True 如果可以执行，False 否则

    Note:
        修复 Issue #145: 修正了条件逻辑错误
        policy 和 guard 任一允许即可执行 (OR 而非 AND)
    """
    # 修复 Issue #145: 修正逻辑从 AND 到 OR
    # 原因：policy 和 guard 是两个独立的检查层，
    #       任一通过即表示允许执行
    policy_allows = self.policy.allows(mode)
    guard_permits = self.guard.permits(mode)

    # 记录决策过程便于调试
    logger.debug(
        "Mode decision for %s: policy=%s, guard=%s",
        mode, policy_allows, guard_permits
    )

    # OR 逻辑：任一允许即可
    return policy_allows or guard_permits
```

添加回归测试:
```python
# tests/unit/mode/test_mode_selector_bugfix_145.py

def test_can_execute_write_with_policy_allow():
    """
    回归测试：修复 Issue #145
    当 policy 允许时，应该返回 True
    """
    selector = ModeSelector(
        policy=MockPolicy(allows_write=True),
        guard=MockGuard(permits_write=False)
    )

    # 修复前：返回 False (AND 逻辑)
    # 修复后：返回 True (OR 逻辑)
    assert selector.can_execute("write", {}) is True


def test_can_execute_write_with_guard_permit():
    """
    回归测试：修复 Issue #145
    当 guard 允许时，应该返回 True
    """
    selector = ModeSelector(
        policy=MockPolicy(allows_write=False),
        guard=MockGuard(permits_write=True)
    )

    assert selector.can_execute("write", {}) is True


def test_can_execute_write_both_deny():
    """测试两者都拒绝的情况"""
    selector = ModeSelector(
        policy=MockPolicy(allows_write=False),
        guard=MockGuard(permits_write=False)
    )

    # 两者都拒绝时，应该返回 False
    assert selector.can_execute("write", {}) is False


def test_can_execute_write_both_allow():
    """测试两者都允许的情况"""
    selector = ModeSelector(
        policy=MockPolicy(allows_write=True),
        guard=MockGuard(permits_write=True)
    )

    # 两者都允许时，应该返回 True
    assert selector.can_execute("write", {}) is True
```

**3. 测试验证**

```bash
pytest tests/unit/mode/test_mode_selector_bugfix_145.py -v
# ✅ 所有测试通过

pytest tests/unit/mode/ -v
# ✅ 所有单元测试通过

pytest tests/integration/mode/ -v
# ✅ 所有集成测试通过
```

**4. Code Review (13:00-15:00)**

提交 PR #478:
```bash
git commit -m "fix(mode): correct write operation blocking logic (#145)

Problem:
- Mode selector incorrectly blocks all write operations
- Logic error: uses AND instead of OR
- Affects 40% of users trying to perform write operations

Solution:
- Changed condition from AND to OR
- Added debug logging for decision tracing
- Policy and Guard are independent checks

Impact:
- Fixes P1 blocking issue
- No API changes
- Backward compatible
- Write operations now work correctly

Testing:
- Added 4 regression tests covering all combinations
- All existing tests pass

Closes #145"
```

审查反馈:
```
Reviewer: Eve Adams
> 问题：为什么是 OR 而不是 AND？这样不会降低安全性吗？

Author:
不会。Policy 和 Guard 是两个独立的授权机制：
- Policy: 基于静态规则的授权
- Guard: 基于运行时状态的授权

任一机制授权成功都应该允许执行。这是多层授权的标准做法。
如果两者都拒绝，才应该拒绝执行。

Reviewer:
✅ Approved. 理解了，感谢解释。
```

**5. 发布 (15:00-16:00)**

```bash
# v1.0.1 -> v1.0.2
echo "1.0.2" > VERSION

# 更新 CHANGELOG
cat >> CHANGELOG.md << 'EOF'
## [1.0.2] - 2026-01-20

### Fixed
- **mode-selector**: Correct write operation blocking logic ([#145](https://github.com/company/agentos/issues/145))
  - **Impact**: P1 - Write operations incorrectly blocked for 40% users
  - **Fix**: Changed condition logic from AND to OR
  - **Root Cause**: Logic error introduced in refactoring
EOF

git commit -m "chore: bump version to v1.0.2"
git tag -a v1.0.2 -m "Release v1.0.2: Fix write operation blocking"
git push origin master --tags
```

**6. 验证 (16:00-次日 16:00)**

```
监控 24 小时:
✅ 写操作成功率: 100% (之前 0%)
✅ 用户投诉: 0
✅ 性能: 无变化
✅ 错误率: 无增加

结论: 修复成功
```

#### 经验教训

**做得好的地方**:
- 快速定位问题
- 逻辑分析清晰
- 测试覆盖全面

**需要改进的地方**:
- 应该有更好的逻辑测试覆盖
- 代码审查应该更仔细

**预防措施**:
- 增加决策逻辑的单元测试
- 在 Code Review 中重点关注条件逻辑
- 添加逻辑决策表文档

---

## 3. P2 Bug 示例

### 示例 3.1: 监控面板数据显示不准确

#### 问题描述

**Issue #167**: Mode monitoring dashboard shows incorrect statistics

**严重级别**: P2 (Medium)

**发现时间**: 2026-01-25 14:00

**报告人**: Frank Miller

**现象**:
```
Mode 监控面板显示的执行次数统计有时不准确，
与实际日志记录不一致。不影响核心功能，仅影响监控可视化。
```

**影响范围**:
- 影响使用监控面板的用户
- 不影响核心功能
- 估计影响 10% 用户
- 数据不一致率约 5%

**重现率**: 约 20%

#### 严重性评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 系统可用性 | 5/40 | 不影响核心功能 |
| 影响用户数 | 3/30 | 10% 用户受影响 |
| 数据影响 | 5/20 | 显示数据不准确 |
| 安全影响 | 0/10 | 无安全问题 |
| **总分** | **13/100** | **P2: Medium** |

#### 处理决定

**决定**: 推迟到冻结期结束后处理

**理由**:
1. 不影响核心功能
2. 有缓解措施（查看日志）
3. 影响范围小
4. 不符合 P0/P1 紧急修复标准

**临时缓解措施**:
```bash
# 用户可以直接查看日志获取准确数据
grep "mode_execution" /var/log/agentos/agentos.log | wc -l
```

**处理计划**:
- 创建 Issue 记录问题
- 标记为 "mode-freeze-deferred"
- 在冻结期结束后的下个 Sprint 处理
- 预计修复时间: 2026-05-01

**记录**:
```markdown
Issue #167 已创建并标记为延期处理。
- 标签: bug, mode-monitoring, P2, mode-freeze-deferred
- Milestone: v1.1.0 (Post-Freeze)
- 预计修复: 2026-05-01
```

---

## 4. 安全补丁示例

### 示例 4.1: Mode Policy 路径遍历漏洞

#### 问题描述

**Issue #189**: Path traversal vulnerability in mode policy loader

**严重级别**: P0 (Critical Security)

**发现时间**: 2026-01-28 09:00

**报告人**: Security Team

**CVE 编号**: CVE-2026-1234

**CVE 评分**: 9.1 (Critical)

**现象**:
```
Mode policy loader 在加载自定义策略文件时，
未验证文件路径，存在路径遍历漏洞。
攻击者可以通过构造特殊路径读取任意系统文件。
```

**漏洞代码**:
```python
def load_policy(self, path: str) -> Policy:
    # 漏洞：未验证路径，直接打开文件
    with open(path, 'r') as f:
        return json.load(f)
```

**攻击示例**:
```python
# 攻击者可以读取任意文件
policy = loader.load_policy("../../../etc/passwd")
```

**影响范围**:
- 影响所有用户
- 可能泄露敏感信息
- 需要立即修复

#### 修复过程

**1. 安全评估 (09:00-10:00)**

```
CVE 评分: 9.1 (Critical)
- 攻击复杂度: 低
- 权限要求: 无
- 用户交互: 不需要
- 影响范围: 系统文件读取
- 保密性影响: 高
- 完整性影响: 无
- 可用性影响: 无

结论: P0 Critical Security, 需要立即修复
```

**2. 修复开发 (10:00-12:00)**

```bash
git checkout -b security/cve-2026-1234-path-traversal
```

修复代码:
```python
# agentos/core/mode/mode_policy.py

import os
from pathlib import Path

def load_policy(self, path: str) -> Policy:
    """
    加载 mode policy 配置文件

    Args:
        path: 策略文件路径

    Returns:
        Policy 对象

    Raises:
        SecurityError: 如果路径不安全
        PolicyNotFoundError: 如果文件不存在

    Security:
        修复 CVE-2026-1234: 添加路径验证防止路径遍历攻击
    """
    # 修复 CVE-2026-1234: 路径验证
    # 1. 获取绝对路径
    abs_path = os.path.abspath(path)

    # 2. 获取允许的策略目录
    allowed_dirs = [
        os.path.abspath(self.policy_dir),
        os.path.abspath(os.path.expanduser("~/.agentos/policies")),
    ]

    # 3. 验证路径在允许的目录内
    path_safe = any(
        abs_path.startswith(allowed_dir)
        for allowed_dir in allowed_dirs
    )

    if not path_safe:
        logger.error(
            "Security: Attempt to load policy from unauthorized path: %s",
            abs_path
        )
        raise SecurityError(
            f"Policy path outside allowed directories: {path}. "
            f"Allowed directories: {allowed_dirs}"
        )

    # 4. 验证文件存在
    if not os.path.exists(abs_path):
        raise PolicyNotFoundError(f"Policy file not found: {abs_path}")

    # 5. 验证是文件而非目录
    if not os.path.isfile(abs_path):
        raise SecurityError(f"Policy path is not a file: {abs_path}")

    # 6. 安全地加载文件
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise PolicyLoadError(f"Invalid policy JSON: {e}")
    except Exception as e:
        logger.error("Failed to load policy from %s: %s", abs_path, e)
        raise
```

添加安全测试:
```python
# tests/security/test_mode_policy_cve_2026_1234.py

import pytest
from agentos.core.mode import ModePolicy, SecurityError

def test_path_traversal_attack_blocked():
    """
    安全测试：CVE-2026-1234
    路径遍历攻击应该被阻止
    """
    policy_loader = ModePolicy()

    # 尝试路径遍历攻击
    with pytest.raises(SecurityError, match="outside allowed directories"):
        policy_loader.load_policy("../../../etc/passwd")

    with pytest.raises(SecurityError, match="outside allowed directories"):
        policy_loader.load_policy("/etc/shadow")


def test_valid_policy_path_allowed():
    """
    测试合法路径仍然可以加载
    """
    policy_loader = ModePolicy()

    # 合法路径应该可以加载
    policy = policy_loader.load_policy("configs/mode/default_policy.json")
    assert policy is not None


def test_symlink_attack_blocked():
    """
    安全测试：符号链接攻击应该被阻止
    """
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建符号链接指向敏感文件
        link_path = os.path.join(tmpdir, "evil.json")
        os.symlink("/etc/passwd", link_path)

        policy_loader = ModePolicy()

        # 尝试通过符号链接访问
        with pytest.raises(SecurityError):
            policy_loader.load_policy(link_path)
```

**3. 安全审查 (12:00-14:00)**

```
安全审查清单:
✅ 路径验证实现正确
✅ 无绕过可能
✅ 错误处理安全
✅ 日志记录攻击尝试
✅ 测试覆盖充分
✅ 无其他安全问题

审查结果: 批准
```

**4. 发布 (14:00-15:00)**

```bash
# 紧急安全补丁
echo "1.0.3" > VERSION

cat >> CHANGELOG.md << 'EOF'
## [1.0.3] - 2026-01-28

### Security
- **mode-policy**: Fix path traversal vulnerability ([CVE-2026-1234](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2026-1234))
  - **Severity**: Critical (CVSS 9.1)
  - **Impact**: Arbitrary file read vulnerability
  - **Fix**: Added path validation and sandboxing
  - **Credit**: Security Team

**⚠️ Security Advisory**: All users should upgrade immediately.
EOF

git commit -m "security(mode): fix path traversal vulnerability (CVE-2026-1234)

CVE-2026-1234: Path traversal in mode policy loader

Severity: Critical (CVSS 9.1)

Problem:
- Mode policy loader does not validate file paths
- Attackers can read arbitrary system files via path traversal
- Example: load_policy('../../../etc/passwd')

Solution:
- Added strict path validation
- Restricted policy loading to allowed directories
- Added symlink attack protection
- Enhanced error handling and logging

Security Impact:
- Fixes critical security vulnerability
- No API changes
- Backward compatible (normal usage unaffected)

Testing:
- Added comprehensive security tests
- Tested path traversal attempts
- Tested symlink attacks
- All existing tests pass

Closes #189
CVE-2026-1234"

git tag -a v1.0.3 -m "Security release v1.0.3: Fix CVE-2026-1234"
git push origin master --tags
```

**5. 安全公告**

```markdown
# Security Advisory: CVE-2026-1234

**Published**: 2026-01-28
**Severity**: Critical (CVSS 9.1)
**Affected Versions**: AgentOS < 1.0.3
**Fixed Version**: AgentOS 1.0.3

## Summary
A path traversal vulnerability in the Mode policy loader allows
attackers to read arbitrary files on the system.

## Impact
Attackers can read sensitive files including:
- System configuration files
- User credentials
- Application secrets

## Mitigation
Upgrade to AgentOS 1.0.3 or later immediately:

\`\`\`bash
pip install --upgrade agentos>=1.0.3
\`\`\`

## Workaround
If immediate upgrade is not possible:
- Restrict access to policy configuration
- Audit policy file paths in use
- Monitor for suspicious file access patterns

## Credit
Discovered by: AgentOS Security Team

## References
- CVE-2026-1234: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2026-1234
- Fix PR: #501
```

#### 经验教训

**做得好的地方**:
- 快速响应安全问题
- 完整的安全测试
- 及时发布公告

**需要改进的地方**:
- 应该在开发时进行安全审查
- 应该有自动化安全扫描

**预防措施**:
- 在 CI/CD 中集成安全扫描
- 定期进行安全审查
- 安全培训

---

## 5. 性能优化示例

### 示例 5.1: Mode Policy 评估性能优化

#### 问题描述

**Issue #201**: Mode policy evaluation performance degradation

**类型**: 性能优化

**发现时间**: 2026-01-30 11:00

**报告人**: Performance Team

**现象**:
```
Mode policy 评估性能随着规则数量增加而线性下降。
在有 100 条规则时，评估时间从 1ms 增加到 50ms。
```

**性能数据**:
```
规则数量   评估时间 (P95)
10         1.2ms
50         15.8ms
100        45.3ms
200        98.7ms
```

#### 优化方案

**问题分析**:
```python
# 当前实现：O(n) 线性扫描
def evaluate(self, mode: str) -> bool:
    for rule in self.rules:  # O(n)
        if rule.matches(mode):
            return rule.action == "allow"
    return False
```

**优化方案**: 使用缓存和索引

```python
# 优化后：O(1) 查找
from functools import lru_cache

def __init__(self):
    self.rules = []
    self._rule_index = {}  # mode -> rule 索引

def _build_index(self):
    """构建 mode 到 rule 的索引"""
    self._rule_index = {}
    for rule in self.rules:
        for mode in rule.modes:
            if mode not in self._rule_index:
                self._rule_index[mode] = []
            self._rule_index[mode].append(rule)

@lru_cache(maxsize=256)
def evaluate(self, mode: str) -> bool:
    """使用索引和缓存优化的评估"""
    # O(1) 查找
    rules = self._rule_index.get(mode, [])
    for rule in rules:  # 只遍历相关规则
        if rule.matches(mode):
            return rule.action == "allow"
    return False
```

**性能测试**:
```python
def test_performance_improvement():
    """验证性能优化效果"""
    import time

    # 创建 200 条规则的策略
    policy = ModePolicy.load_from_config("configs/mode/large_policy.json")

    # 基准测试
    iterations = 10000

    start = time.perf_counter()
    for _ in range(iterations):
        policy.evaluate("read")
    duration = time.perf_counter() - start

    avg_ms = (duration / iterations) * 1000

    # 期望：< 5ms (之前是 100ms)
    assert avg_ms < 5.0, f"Performance regression: {avg_ms}ms"

    print(f"Performance: {avg_ms}ms per call (target: <5ms)")
```

**验证结果**:
```
优化后性能:
规则数量   评估时间 (P95)   改进
10         0.8ms           33% faster
50         2.1ms           87% faster
100        3.5ms           92% faster
200        4.2ms           96% faster

结论: 性能显著提升，符合优化目标
```

**符合冻结规范**:
- ✅ 不改变功能行为
- ✅ 不改变 API
- ✅ 输出完全一致
- ✅ 所有测试通过
- ✅ 性能显著提升

---

## 总结

本文档提供了 5 个完整的 Bug 修复示例，涵盖了：

1. **P0 Critical Bug**: 系统崩溃修复（完整的紧急响应流程）
2. **P1 High Bug**: 逻辑错误修复（标准修复流程）
3. **P2 Medium Bug**: 延期处理示例（符合冻结规范）
4. **Security Patch**: 安全漏洞修复（安全响应流程）
5. **Performance**: 性能优化（不改变行为的优化）

每个示例都包含：
- 完整的问题描述
- 严重性评估
- 根因分析
- 修复过程
- Code Review 记录
- 发布记录
- 经验教训

这些示例可以作为实际 Bug 修复的参考模板。

---

## 相关文档

- [MODE_BUG_FIX_PROCESS.md](../MODE_BUG_FIX_PROCESS.md) - Bug 修复流程
- [MODE_BUG_FIX_WORKFLOW.md](../MODE_BUG_FIX_WORKFLOW.md) - Bug 修复工作流程图
- [templates/BUG_FIX_TEMPLATE.md](../templates/BUG_FIX_TEMPLATE.md) - Bug 修复模板

---

**文档状态**: ✅ Active
**最后更新**: 2026-01-30
**维护者**: Architecture Committee
