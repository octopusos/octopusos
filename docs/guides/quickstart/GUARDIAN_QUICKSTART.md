# Guardian 快速开始指南

5 分钟上手 Guardian 验收系统。

## 什么是 Guardian？

Guardian = **验收事实记录器**（Verification / Acceptance Authority）

**核心原则：**
- ✅ 只读叠加层（不修改 Task 状态）
- ✅ 不可变记录（一旦创建，永不修改）
- ✅ 证据驱动（每个验收都有完整证据）

## 快速开始

### 1. 安装和初始化

```python
from agentos.core.guardian import GuardianService

# 创建 Guardian 服务实例
guardian = GuardianService()
```

### 2. 创建第一个验收记录

```python
# 自动验收（由 Guardian Agent 执行）
review = guardian.create_review(
    target_type="task",           # 验收目标类型
    target_id="task_123",         # 验收目标 ID
    guardian_id="guardian.ci.v1", # Guardian ID
    review_type="AUTO",           # 自动验收
    verdict="PASS",               # 验收结论：PASS | FAIL | NEEDS_REVIEW
    confidence=0.95,              # 置信度 (0.0 - 1.0)
    evidence={                    # 验收证据
        "checks": ["all_tests_passed"],
        "build_id": "build_12345"
    }
)

print(f"Created review: {review.review_id}")
```

### 3. 人工验收

```python
# 人工验收（由人类执行）
review = guardian.create_review(
    target_type="task",
    target_id="task_123",
    guardian_id="human.alice",    # 人类 ID
    review_type="MANUAL",         # 人工验收
    verdict="PASS",
    confidence=1.0,               # 人工验收置信度固定为 1.0
    evidence={
        "reviewer": "alice",
        "notes": "Code looks good, approved"
    }
)
```

### 4. 查询验收记录

```python
# 获取某个目标的所有验收记录
reviews = guardian.get_reviews_by_target("task", "task_123")

for review in reviews:
    print(f"[{review.created_at}] {review.guardian_id}: {review.verdict}")
    print(f"  Evidence: {review.evidence}")

# 获取最新验收摘要
summary = guardian.get_verdict_summary("task", "task_123")
print(f"Latest verdict: {summary['latest_verdict']}")
print(f"Total reviews: {summary['total_reviews']}")
```

### 5. 统计分析

```python
# 获取整体统计
stats = guardian.get_statistics()

print(f"Total reviews: {stats['total_reviews']}")
print(f"Pass rate: {stats['pass_rate']:.2%}")
print(f"Top guardians: {stats['guardians']}")
```

## 常见用法场景

### 场景 1: CI/CD 自动验收

```python
# CI/CD Pipeline 运行后自动验收
def ci_pipeline_guardian(task_id, build_result):
    """CI Pipeline Guardian: 自动验收 CI 构建结果"""

    verdict = "PASS" if build_result["success"] else "FAIL"

    guardian.create_review(
        target_type="task",
        target_id=task_id,
        guardian_id="guardian.ci.v1",
        review_type="AUTO",
        verdict=verdict,
        confidence=0.98 if build_result["success"] else 0.95,
        evidence={
            "build_id": build_result["build_id"],
            "tests_passed": build_result["tests_passed"],
            "tests_failed": build_result["tests_failed"],
            "coverage": build_result["coverage"],
            "build_url": build_result["url"]
        },
        rule_snapshot_id="ci_policy:v1@sha256:abc123"
    )

# 使用示例
ci_pipeline_guardian("task_123", {
    "success": True,
    "build_id": "build_12345",
    "tests_passed": 150,
    "tests_failed": 0,
    "coverage": 0.88,
    "url": "https://ci.example.com/build/12345"
})
```

### 场景 2: 安全扫描验收

```python
def security_scan_guardian(task_id, scan_result):
    """Security Scanner Guardian: 验收安全扫描结果"""

    # 根据漏洞数量确定 verdict
    if scan_result["critical_vulnerabilities"] > 0:
        verdict = "FAIL"
        confidence = 0.99
    elif scan_result["high_vulnerabilities"] > 0:
        verdict = "NEEDS_REVIEW"
        confidence = 0.75
    else:
        verdict = "PASS"
        confidence = 0.95

    guardian.create_review(
        target_type="task",
        target_id=task_id,
        guardian_id="guardian.security.v2",
        review_type="AUTO",
        verdict=verdict,
        confidence=confidence,
        evidence={
            "scan_id": scan_result["scan_id"],
            "critical_vulnerabilities": scan_result["critical_vulnerabilities"],
            "high_vulnerabilities": scan_result["high_vulnerabilities"],
            "medium_vulnerabilities": scan_result["medium_vulnerabilities"],
            "scan_timestamp": scan_result["timestamp"],
            "scan_url": scan_result["url"]
        },
        rule_snapshot_id="security_policy:v2.1@sha256:def456"
    )

# 使用示例
security_scan_guardian("task_123", {
    "scan_id": "scan_67890",
    "critical_vulnerabilities": 0,
    "high_vulnerabilities": 2,
    "medium_vulnerabilities": 5,
    "timestamp": "2026-01-29T10:00:00Z",
    "url": "https://security.example.com/scan/67890"
})
```

### 场景 3: 人工代码审查

```python
def human_code_review(task_id, reviewer, approved, notes):
    """Human Code Review Guardian: 记录人工代码审查"""

    guardian.create_review(
        target_type="task",
        target_id=task_id,
        guardian_id=f"human.{reviewer}",
        review_type="MANUAL",
        verdict="PASS" if approved else "NEEDS_REVIEW",
        confidence=1.0,
        evidence={
            "reviewer": reviewer,
            "approved": approved,
            "review_notes": notes,
            "review_timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# 使用示例
human_code_review(
    task_id="task_123",
    reviewer="alice",
    approved=True,
    notes="Code quality good. Added comments for complex logic. LGTM."
)
```

### 场景 4: 多 Guardian 协作

```python
def multi_guardian_verification(task_id):
    """多个 Guardian 协作验收同一个 Task"""

    # Guardian 1: CI 验收
    guardian.create_review(
        target_type="task",
        target_id=task_id,
        guardian_id="guardian.ci.v1",
        review_type="AUTO",
        verdict="PASS",
        confidence=0.98,
        evidence={"tests": "all_passed"}
    )

    # Guardian 2: Security 验收
    guardian.create_review(
        target_type="task",
        target_id=task_id,
        guardian_id="guardian.security.v2",
        review_type="AUTO",
        verdict="PASS",
        confidence=0.92,
        evidence={"vulnerabilities": 0}
    )

    # Guardian 3: Quality 验收
    guardian.create_review(
        target_type="task",
        target_id=task_id,
        guardian_id="guardian.quality.v1",
        review_type="AUTO",
        verdict="PASS",
        confidence=0.90,
        evidence={"code_coverage": 0.88}
    )

    # Guardian 4: Human 验收
    guardian.create_review(
        target_type="task",
        target_id=task_id,
        guardian_id="human.bob",
        review_type="MANUAL",
        verdict="PASS",
        confidence=1.0,
        evidence={"reviewer": "bob", "notes": "Approved"}
    )

    # 获取所有验收结果
    reviews = guardian.get_reviews_by_target("task", task_id)
    print(f"Total reviews: {len(reviews)}")
    print(f"All passed: {all(r.verdict == 'PASS' for r in reviews)}")
```

## 使用 REST API

### 创建验收记录

```bash
curl -X POST "http://localhost:8080/api/guardian/reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "target_type": "task",
    "target_id": "task_123",
    "guardian_id": "guardian.ci.v1",
    "review_type": "AUTO",
    "verdict": "PASS",
    "confidence": 0.95,
    "evidence": {
      "checks": ["all_tests_passed"],
      "build_id": "build_12345"
    }
  }'
```

### 查询验收记录

```bash
# 获取目标的所有验收记录
curl "http://localhost:8080/api/guardian/targets/task/task_123/reviews"

# 获取验收摘要
curl "http://localhost:8080/api/guardian/targets/task/task_123/verdict"

# 查询所有 FAIL 的记录
curl "http://localhost:8080/api/guardian/reviews?verdict=FAIL"

# 获取统计数据
curl "http://localhost:8080/api/guardian/statistics"
```

## 常见问题（FAQ）

### Q1: Guardian FAIL verdict 会阻止 Task 执行吗？

**A:** 不会。Guardian 是只读叠加层，不修改 Task 状态机。Guardian FAIL 只是记录验收事实，不阻止 Task 继续执行。

如果需要阻止 Task 执行，应使用 Supervisor 流程控制器。

### Q2: 可以修改已创建的 review 吗？

**A:** 不可以。Guardian review 是不可变的（immutable），一旦创建就无法修改。这是为了保证审计完整性。

如果需要更新验收结论，应创建新的 review（记录验收意见的演化）。

### Q3: 一个 Task 可以有多个 Guardian 验收吗？

**A:** 可以。多个 Guardian 可以从不同维度验收同一个 Task（例如：CI、Security、Quality、Human）。

Guardian 之间是独立的，可以有不同的 verdict（PASS / FAIL）。

### Q4: NEEDS_REVIEW 是什么意思？

**A:** `NEEDS_REVIEW` 表示 Guardian 无法给出明确的 PASS/FAIL 结论，需要人工复审。

通常用于：
- 低置信度场景（confidence < 0.7）
- 发现边界情况（edge case）
- 需要人工判断的场景

### Q5: evidence 字段应该放什么？

**A:** Evidence 应包含验收的完整依据，例如：
- 检查项列表（checks）
- 量化指标（metrics）
- 外部链接（links）
- 时间戳（timestamps）
- 人工备注（notes）

目的是让审计人员能够追溯验收过程。

### Q6: rule_snapshot_id 是做什么的？

**A:** `rule_snapshot_id` 关联规则快照，用于追踪验收使用的规则版本。

当规则演化时（如：从 v1 升级到 v2），可以通过 `rule_snapshot_id` 确定历史验收使用的是哪个版本的规则。

### Q7: Guardian 和 Supervisor 有什么区别？

**A:**
- **Guardian**: 验收事实记录器（只读，不控制流程）
- **Supervisor**: 流程控制器（读写，可阻止/触发操作）

简单类比：
- Guardian = 质检员（记录产品是否合格）
- Supervisor = 生产线控制器（根据质检结果决定产品是否放行）

### Q8: 如何查看某个 Task 的验收历史？

**A:**

```python
# 获取所有验收记录
reviews = guardian.get_reviews_by_target("task", "task_123")

# 按时间排序（最新在前）
for review in reviews:
    print(f"[{review.created_at}] {review.guardian_id}: {review.verdict}")
    print(f"  Confidence: {review.confidence:.2f}")
    print(f"  Evidence: {review.evidence}")
    print()
```

### Q9: 如何统计验收通过率？

**A:**

```python
# 获取整体统计
stats = guardian.get_statistics()
print(f"Pass rate: {stats['pass_rate']:.2%}")

# 按目标类型统计
task_stats = guardian.get_statistics(target_type="task")
print(f"Task pass rate: {task_stats['pass_rate']:.2%}")

# 按 Guardian 统计
for guardian_id, count in stats['guardians'].items():
    print(f"{guardian_id}: {count} reviews")
```

### Q10: 如何处理冲突的 verdict？

**A:** Guardian 允许冲突的 verdict（不同 Guardian 可以有不同意见）。

```python
# 获取验收摘要
summary = guardian.get_verdict_summary("task", "task_123")

# 检查是否有冲突
all_verdicts = set(summary['all_verdicts'])
if len(all_verdicts) > 1:
    print("⚠️ Conflicting verdicts detected!")
    print(f"Verdicts: {all_verdicts}")
    print(f"Latest verdict: {summary['latest_verdict']}")
```

## 故障排查

### 问题 1: ValueError: Invalid confidence

**原因:** confidence 必须在 0.0 - 1.0 范围内

**解决:**
```python
# ❌ 错误
confidence = 1.5  # > 1.0

# ✅ 正确
confidence = 0.95  # 0.0 <= confidence <= 1.0
```

### 问题 2: ValueError: Invalid verdict

**原因:** verdict 必须是 `PASS` | `FAIL` | `NEEDS_REVIEW`

**解决:**
```python
# ❌ 错误
verdict = "SUCCESS"

# ✅ 正确
verdict = "PASS"
```

### 问题 3: 创建的 review 查询不到

**原因:** 可能使用了不同的数据库实例

**解决:**
```python
# 确保使用同一个数据库路径
from pathlib import Path

db_path = Path("~/.agentos/registry.sqlite").expanduser()
guardian = GuardianService(db_path=db_path)
```

### 问题 4: API 返回 500 错误

**原因:** 服务器内部错误

**排查步骤:**
1. 查看服务器日志
2. 检查数据库连接
3. 验证请求参数格式
4. 联系管理员

## 下一步

- 📖 [Guardian 角色文档](docs/governance/guardian_verification.md) - 详细了解 Guardian 的设计原则
- 📖 [Guardian API 文档](docs/governance/guardian_api.md) - 完整的 API 参考
- 🧪 [单元测试示例](tests/unit/guardian/) - 查看测试用例
- 🧪 [集成测试示例](tests/integration/guardian/) - 查看集成测试

## 支持

遇到问题？
- 📖 查看 [FAQ](#常见问题faq)
- 📖 查看 [故障排查](#故障排查)
- 📖 查看测试用例：`tests/unit/guardian/` 和 `tests/integration/guardian/`
- 📧 联系开发团队

---

**快速参考卡片：**

```python
# 创建自动验收
guardian.create_review(
    target_type="task",
    target_id="task_123",
    guardian_id="guardian.v1",
    review_type="AUTO",
    verdict="PASS",
    confidence=0.95,
    evidence={"checks": ["ok"]}
)

# 创建人工验收
guardian.create_review(
    target_type="task",
    target_id="task_123",
    guardian_id="human.alice",
    review_type="MANUAL",
    verdict="PASS",
    confidence=1.0,
    evidence={"notes": "Approved"}
)

# 查询验收记录
reviews = guardian.get_reviews_by_target("task", "task_123")

# 获取验收摘要
summary = guardian.get_verdict_summary("task", "task_123")

# 获取统计数据
stats = guardian.get_statistics()
```
