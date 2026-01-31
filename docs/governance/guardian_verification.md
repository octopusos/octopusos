# Guardian 验收角色

## 定位

Guardian **不是**执行者、不是决策者，而是：

**治理验收角色（Verification / Acceptance Authority）**

它回答的问题只有三个：
- ✅ 这个 Task / Decision 是否通过验收？
- 👤 是谁验收的（人 / Agent / 规则集）？
- 📜 依据是什么（规则、快照、证据）？

## 核心原则

### 1. 只读叠加层（Read-Only Overlay）

Guardian 是 Task / Decision 的只读叠加层，**不修改原有状态机**。

```
┌─────────────────────────────────┐
│     Task State Machine          │  ← Core subsystem (read-write)
│  (pending → in_progress → done) │
└─────────────────────────────────┘
              │
              │ (read-only)
              ▼
┌─────────────────────────────────┐
│    Guardian Verification        │  ← Overlay layer (read-only)
│  (PASS / FAIL / NEEDS_REVIEW)   │
└─────────────────────────────────┘
```

**关键行为：**
- ❌ Guardian FAIL verdict **不阻止** Task 继续执行
- ❌ Guardian PASS verdict **不触发** Task 状态变更
- ✅ Guardian 只记录验收事实，供后续查询和审计

### 2. 不可变记录（Immutable Records）

Guardian Review 一旦创建，**永不修改**。

```python
# ✅ 正确：创建新 review
guardian_service.create_review(
    target_type="task",
    target_id="task_123",
    guardian_id="guardian.security.v1",
    verdict="PASS",
    confidence=0.95,
    evidence={"checks": ["all_pass"]}
)

# ❌ 错误：修改已有 review（API 不提供此功能）
# guardian_service.update_review(review_id, verdict="FAIL")  # 不存在
```

**为什么不可变？**
1. **审计完整性**：历史验收记录必须可追溯
2. **时间序列**：可以看到验收意见随时间的演化
3. **责任清晰**：每个 Guardian 的验收结论都有明确记录

### 3. 证据驱动（Evidence-Driven）

每个 Guardian Review 必须包含完整证据。

```python
# ✅ 良好的证据结构
evidence = {
    "checks": [
        "state_machine_valid",
        "dependencies_resolved",
        "security_scan_passed"
    ],
    "metrics": {
        "confidence_score": 0.95,
        "test_coverage": 0.88
    },
    "links": [
        "https://ci.example.com/build/12345",
        "https://security.example.com/scan/67890"
    ],
    "notes": "All automated checks passed. Manual review recommended for edge case X."
}

guardian_service.create_review(
    target_type="task",
    target_id="task_123",
    guardian_id="guardian.ci.v1",
    review_type="AUTO",
    verdict="PASS",
    confidence=0.95,
    evidence=evidence
)
```

**证据的作用：**
- 说明验收依据（为什么 PASS / FAIL）
- 支持审计追溯（事后可以查看验收过程）
- 辅助人工复审（NEEDS_REVIEW 场景）

## 使用场景

### ✅ 适合 Guardian 的场景

#### 1. 合规验收（Compliance Verification）

```python
# 场景：确认 Task 符合安全政策
guardian_service.create_review(
    target_type="task",
    target_id="task_deploy_prod",
    guardian_id="guardian.security_policy.v2",
    review_type="AUTO",
    verdict="PASS",
    confidence=0.92,
    rule_snapshot_id="security_policy:v2.1@sha256:abc123",
    evidence={
        "policy_checks": [
            "no_hardcoded_secrets",
            "dependency_scan_clean",
            "code_signed"
        ],
        "policy_version": "v2.1",
        "scan_timestamp": "2026-01-29T10:00:00Z"
    }
)
```

#### 2. 代码审查（Code Review）

```python
# 场景：人工代码审查
guardian_service.create_review(
    target_type="task",
    target_id="task_feature_x",
    guardian_id="human.alice",
    review_type="MANUAL",
    verdict="PASS",
    evidence={
        "reviewer": "alice",
        "review_notes": "Code quality good. Added comments for complex logic.",
        "review_duration_minutes": 45,
        "approved_at": "2026-01-29T11:30:00Z"
    }
)
```

#### 3. 风险评估（Risk Assessment）

```python
# 场景：高风险操作的二次确认
guardian_service.create_review(
    target_type="task",
    target_id="task_delete_database",
    guardian_id="guardian.risk_analyzer.v1",
    review_type="AUTO",
    verdict="NEEDS_REVIEW",
    confidence=0.55,  # Low confidence → needs human review
    evidence={
        "risk_level": "HIGH",
        "risk_factors": [
            "irreversible_operation",
            "affects_production_data",
            "no_backup_detected"
        ],
        "recommendation": "Require human approval before proceeding"
    }
)
```

#### 4. 审计记录（Audit Trail）

```python
# 场景：为合规审计保留完整验收历史
reviews = guardian_service.get_reviews_by_target("task", "task_123")

# 生成审计报告
for review in reviews:
    print(f"[{review.created_at}] {review.guardian_id}: {review.verdict}")
    print(f"  Evidence: {review.evidence}")
    print(f"  Rule: {review.rule_snapshot_id}")
```

### ❌ 不适合 Guardian 的场景

#### 1. 流程控制（应使用 Supervisor）

```python
# ❌ 错误：试图用 Guardian 阻止 Task 执行
# Guardian FAIL verdict 不会阻止 Task 继续执行
guardian_service.create_review(
    target_id="task_123",
    verdict="FAIL",  # 这不会阻止 task
    ...
)

# ✅ 正确：使用 Supervisor 控制流程
supervisor.enforce_policy(
    task_id="task_123",
    policy="require_approval",
    action="block_until_approved"
)
```

#### 2. 决策执行（应使用 Task Runner）

```python
# ❌ 错误：期望 Guardian verdict 触发自动操作
# Guardian 只记录验收事实，不执行操作

# ✅ 正确：使用 Task Runner 执行操作
task_runner.execute_task(task_id="task_123")
```

#### 3. 状态变更（应使用 Task Manager）

```python
# ❌ 错误：期望 Guardian 修改 Task 状态
# Guardian 不修改 Task 状态机

# ✅ 正确：使用 Task Manager 修改状态
task_manager.update_task(task_id="task_123", status="in_progress")
```

## 最佳实践

### 1. 多 Guardian 协作

一个 Task 可以有多个 Guardian 从不同维度验收：

```python
# Security Guardian
guardian_service.create_review(
    target_id="task_123",
    guardian_id="guardian.security.v1",
    verdict="PASS",
    evidence={"security_checks": ["all_pass"]}
)

# Quality Guardian
guardian_service.create_review(
    target_id="task_123",
    guardian_id="guardian.quality.v1",
    verdict="PASS",
    evidence={"quality_metrics": {"coverage": 0.92}}
)

# Human Reviewer
guardian_service.create_review(
    target_id="task_123",
    guardian_id="human.bob",
    verdict="PASS",
    evidence={"reviewer": "bob", "notes": "LGTM"}
)
```

### 2. 人机结合

自动 Guardian + 人工 Guardian 结合使用：

```python
# Step 1: 自动 Guardian 初步验收
auto_review = guardian_service.create_review(
    target_id="task_123",
    guardian_id="guardian.ci.v1",
    review_type="AUTO",
    verdict="NEEDS_REVIEW",  # Low confidence
    confidence=0.65,
    evidence={"reason": "Edge case detected"}
)

# Step 2: 人工 Guardian 复审
human_review = guardian_service.create_review(
    target_id="task_123",
    guardian_id="human.alice",
    review_type="MANUAL",
    verdict="PASS",  # Human confirms it's OK
    evidence={"notes": "Edge case is expected behavior"}
)
```

### 3. 版本管理

使用 `rule_snapshot_id` 追踪规则变更：

```python
from agentos.core.guardian.policies import get_policy_registry

# 注册规则快照
registry = get_policy_registry()
snapshot_id = registry.create_and_register(
    policy_id="guardian.security",
    name="Security Policy",
    version="v2.1",
    rules={
        "no_hardcoded_secrets": True,
        "dependency_scan": True,
        "code_signing_required": True
    }
)

# 创建 review 时关联规则快照
guardian_service.create_review(
    target_id="task_123",
    guardian_id="guardian.security.v2",
    verdict="PASS",
    confidence=0.95,
    rule_snapshot_id=snapshot_id,  # 关联规则版本
    evidence={"checks": ["all_pass"]}
)
```

### 4. 完整证据

Evidence 字段应包含所有验收依据：

```python
# ✅ 良好的证据结构
evidence = {
    # 检查项列表
    "checks": [
        "dependency_scan_clean",
        "code_coverage_above_threshold",
        "no_security_vulnerabilities"
    ],

    # 量化指标
    "metrics": {
        "code_coverage": 0.88,
        "security_score": 95,
        "complexity_score": 7.2
    },

    # 外部链接
    "links": [
        "https://ci.example.com/build/12345",
        "https://sonar.example.com/project/abc"
    ],

    # 时间戳
    "timestamps": {
        "scan_started": "2026-01-29T10:00:00Z",
        "scan_completed": "2026-01-29T10:05:00Z"
    },

    # 人工备注（如适用）
    "notes": "Automated checks passed. Manual review recommended for DB migration."
}
```

## 反模式（Anti-Patterns）

### ❌ 反模式 1：用 Guardian 做流程卡点

```python
# ❌ 错误思维：Guardian FAIL 应该阻止 Task 执行
review = guardian_service.create_review(
    target_id="task_123",
    verdict="FAIL",
    evidence={"reason": "Security issue"}
)

# 错误期望：Task 会被自动阻止
# 实际行为：Task 不受影响，继续执行

# ✅ 正确做法：使用 Supervisor 做流程卡点
supervisor.block_task(task_id="task_123", reason="Security issue")
```

### ❌ 反模式 2：修改已创建的 Review

```python
# ❌ 错误：试图修改已有 review
review = guardian_service.get_review("review_123")
review.verdict = "PASS"  # 这不会生效
guardian_service.save(review)  # 不存在 save() 方法

# ✅ 正确做法：创建新 review（记录意见变化）
guardian_service.create_review(
    target_id="task_123",
    guardian_id="guardian.security.v1",
    verdict="PASS",  # New verdict
    evidence={"reason": "Issue resolved in updated code"}
)
```

### ❌ 反模式 3：空 Evidence

```python
# ❌ 错误：没有证据的 review
guardian_service.create_review(
    target_id="task_123",
    verdict="PASS",
    evidence={}  # 空证据，无法审计
)

# ✅ 正确做法：提供完整证据
guardian_service.create_review(
    target_id="task_123",
    verdict="PASS",
    evidence={
        "checks": ["all_pass"],
        "scan_id": "scan_12345",
        "timestamp": "2026-01-29T10:00:00Z"
    }
)
```

### ❌ 反模式 4：忽略 Confidence

```python
# ❌ 错误：低置信度仍然给出 PASS/FAIL
guardian_service.create_review(
    target_id="task_123",
    verdict="PASS",
    confidence=0.45,  # 低置信度
    evidence={"reason": "Uncertain result"}
)

# ✅ 正确做法：低置信度应使用 NEEDS_REVIEW
guardian_service.create_review(
    target_id="task_123",
    verdict="NEEDS_REVIEW",  # 需要人工复审
    confidence=0.45,
    evidence={"reason": "Uncertain result, recommend human review"}
)
```

## 查询和统计

### 查询特定目标的验收历史

```python
# 获取某个 Task 的所有 Guardian reviews
reviews = guardian_service.get_reviews_by_target("task", "task_123")

for review in reviews:
    print(f"[{review.created_at}] {review.guardian_id}: {review.verdict}")
    print(f"  Confidence: {review.confidence:.2f}")
    print(f"  Evidence: {review.evidence}")
```

### 获取验收摘要

```python
# 获取最新验收状态
summary = guardian_service.get_verdict_summary("task", "task_123")

print(f"Total reviews: {summary['total_reviews']}")
print(f"Latest verdict: {summary['latest_verdict']}")
print(f"Latest reviewer: {summary['latest_guardian_id']}")
print(f"All verdicts: {summary['all_verdicts']}")
```

### 统计分析

```python
# 获取整体统计
stats = guardian_service.get_statistics()

print(f"Total reviews: {stats['total_reviews']}")
print(f"Pass rate: {stats['pass_rate']:.2%}")
print(f"Guardian activity: {stats['guardians']}")
print(f"Verdict distribution: {stats['by_verdict']}")
```

## 与其他子系统的关系

```
┌──────────────────────────────────────────────────────────┐
│                    AgentOS 架构                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Task      │  │  Decision   │  │  Finding    │    │
│  │  Manager    │  │   Tracker   │  │  Tracker    │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                 │                 │           │
│         └─────────────────┼─────────────────┘           │
│                           │ (read-only)                 │
│                           ▼                             │
│               ┌──────────────────────┐                  │
│               │  Guardian Service    │                  │
│               │  (Verification)      │                  │
│               └──────────────────────┘                  │
│                           │                             │
│                           │ (stores reviews)            │
│                           ▼                             │
│               ┌──────────────────────┐                  │
│               │  guardian_reviews    │                  │
│               │  (Database)          │                  │
│               └──────────────────────┘                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**关键点：**
1. Guardian **只读访问** Task / Decision / Finding
2. Guardian **不依赖** Supervisor（独立验收角色）
3. Supervisor **可查询** Guardian reviews（作为决策依据）

## 总结

Guardian = **验收事实记录器**

✅ **是什么：**
- 记录验收事实（PASS / FAIL / NEEDS_REVIEW）
- 提供审计追踪（完整历史）
- 支持多维度验收（多 Guardian 协作）
- 人机结合验收（AUTO + MANUAL）

❌ **不是什么：**
- 不是流程控制器（不阻止执行）
- 不是决策执行器（不触发操作）
- 不是状态变更器（不修改状态机）

**核心价值：**
让治理验收和流程执行**解耦**，使系统更灵活、可审计、可扩展。
