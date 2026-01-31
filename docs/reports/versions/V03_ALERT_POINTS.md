# AgentOS v0.3 架构警戒点

**状态**: 🟡 警戒（v0.2 完成，v0.3 规划前必读）  
**日期**: 2026-01-25

这些不是缺陷，而是下一阶段架构演进必须小心的控制点。

---

## ⚠️ 1. Memory 增长与衰减策略

### 现状（v0.2）
- ✅ 能存储记忆（upsert）
- ✅ 按 confidence 过滤
- ❌ 无增长控制机制

### 问题
Memory 会随时间"变重"：
- 临时决策变成永久记忆
- 过时的约定不会自动清理
- confidence 不会随验证结果调整

### v0.3 必须实现

**Retention 策略**:
```python
# memory_item 新增字段
{
  "retention_policy": {
    "type": "temporary|project|permanent",
    "expires_at": "2026-02-01T00:00:00Z",  # 临时记忆过期时间
    "auto_cleanup": true
  }
}
```

**Decay 机制**:
```python
# 基于使用频率的 confidence 衰减
confidence_new = confidence_old * (0.95 ** days_since_last_used)
```

**Promotion 路径**:
```
temporary (task-level)
    ↓ (验证通过 3 次)
project-level
    ↓ (持续 1 个月无冲突)
global
```

**实现优先级**: P0（v0.3 必做）

---

## ⚠️ 2. ReviewPack 的"人类介入点"

### 现状（v0.2）
- ✅ 生成 review_pack.md
- ✅ 记录 patches + commits
- ❌ 无"必须人工确认"机制

### 问题
哪些 review 只是存档，哪些必须人工批准？

### v0.3 必须定义

**Review 分类**:
```python
class ReviewLevel:
    ARCHIVE_ONLY = "archive_only"        # 只存档，自动通过
    NOTIFICATION = "notification"        # 通知但不阻塞
    APPROVAL_REQUIRED = "approval"       # 必须人工批准
    CRITICAL_APPROVAL = "critical"       # 多人审批
```

**触发条件**:
```python
# 基于风险评估自动判定
if risk_assessment["overall_risk"] == "critical":
    review_level = ReviewLevel.CRITICAL_APPROVAL
elif changed_files_count > 20:
    review_level = ReviewLevel.APPROVAL_REQUIRED
elif execution_mode == "full_auto":
    review_level = ReviewLevel.NOTIFICATION
else:
    review_level = ReviewLevel.ARCHIVE_ONLY
```

**Human-in-the-Loop 流程**:
```
ReviewPack 生成
    ↓
风险评估
    ↓
[需要人工] → 进入 approval_queue
    ↓ (人工批准)
    ↓ (或拒绝 + 原因)
执行 / 回滚
```

**实现优先级**: P0（团队协作必需）

---

## ⚠️ 3. Rebase 的语义一致性

### 现状（v0.2）
- ✅ 检测文件变更
- ✅ 读取 change_notes
- ❌ 不检查 intent 是否仍成立

### 问题
文件被修改后：
- 原 intent 可能不再有效
- Memory 可能需要回滚
- 依赖关系可能被破坏

### v0.3 必须考虑

**Intent 一致性检查**:
```python
class RebaseValidator:
    def validate_intent(
        self,
        original_intent: str,
        changed_files: list[str],
        change_notes: dict
    ) -> tuple[bool, str]:
        """
        检查原意图是否仍然成立
        
        返回: (is_valid, reason)
        """
        # 1. 检查依赖的文件是否被破坏性修改
        # 2. 检查前置条件是否仍满足
        # 3. 检查 Memory 引用是否仍有效
```

**Memory 回滚策略**:
```python
# 如果 rebase 失败，需要回滚相关 Memory
if not rebase_valid:
    # 标记为 invalidated
    memory_service.invalidate(
        sources=["task:task-001"],
        reason="Rebase failed: file semantics changed"
    )
```

**Semantic Diff**:
```python
# 不只是文本 diff，要检查语义变化
semantic_changes = analyze_semantic_diff(
    old_version=original_files,
    new_version=current_files
)

if semantic_changes.breaks_assumptions:
    # 需要重新规划
    return generate_new_plan()
```

**实现优先级**: P1（v0.3 或 v0.4）

---

## ⚠️ 4. Execution Policy 与 TaskGraph 的组合爆炸

### 现状（v0.2）
- ✅ 3 种 execution_mode
- ✅ 3 种 risk_profile
- ✅ TaskGraph 依赖管理
- ❌ 无策略简化机制

### 问题
未来可能有：
- 更多 execution_mode（partial_auto, supervised...）
- 更多 risk_profile（industry-specific...）
- 更多 scheduling 策略（priority-based, resource-aware...）

组合爆炸 → 规则难以理解 → 不可维护

### v0.3 必须防范

**策略组合限制**:
```python
# 定义允许的组合
ALLOWED_COMBINATIONS = {
    ("full_auto", "safe", "sequential"),
    ("full_auto", "aggressive_safe", "parallel"),
    ("semi_auto", "safe", "sequential"),
    ("interactive", "*", "*"),  # interactive 可以任意组合
}

def validate_policy_combination(
    execution_mode: str,
    risk_profile: str,
    scheduling: str
) -> tuple[bool, str]:
    if (execution_mode, risk_profile, scheduling) not in ALLOWED_COMBINATIONS:
        return False, "Invalid policy combination"
    return True, "OK"
```

**Policy Presets（预设）**:
```python
# 不让用户自己组合，提供预设
POLICY_PRESETS = {
    "safe-auto": {
        "execution_mode": "full_auto",
        "risk_profile": "safe",
        "scheduling": "sequential",
        "description": "最安全的自动化模式"
    },
    "fast-parallel": {
        "execution_mode": "semi_auto",
        "risk_profile": "aggressive_safe",
        "scheduling": "parallel",
        "max_workers": 4,
        "description": "快速并行执行"
    },
    "supervised": {
        "execution_mode": "interactive",
        "risk_profile": "safe",
        "scheduling": "sequential",
        "description": "人工监督模式"
    }
}
```

**Policy DSL 简化**:
```python
# 用 DSL 而不是 JSON 配置
task.execute(
    mode="safe-auto",  # 使用预设
    on_error="notify",
    timeout="30m"
)

# 而不是
task.execute(
    execution_mode="full_auto",
    execution_policy={
        "risk_profile": "safe",
        "question_budget": 0,
        "auto_fallback": True,
        ...  # 20+ 个字段
    }
)
```

**实现优先级**: P1（v0.3 必做，否则后续难以维护）

---

## 实施建议

### v0.3 优先级排序

| 警戒点 | 优先级 | 预计工作量 | 风险 |
|--------|--------|-----------|------|
| 1. Memory 增长与衰减 | P0 | 2 周 | 高（会影响性能） |
| 2. ReviewPack 人类介入 | P0 | 2 周 | 高（团队协作必需） |
| 4. Policy 组合爆炸 | P1 | 1 周 | 中（可维护性） |
| 3. Rebase 语义一致性 | P1 | 3 周 | 低（可以分阶段） |

### 建议实施顺序

**Week 1-2: Memory 治理**
- retention_policy 字段
- decay 算法
- promotion 规则
- 自动清理 cron job

**Week 3-4: ReviewPack 人类介入**
- ReviewLevel 分类
- approval_queue 表
- 通知机制
- 审批 UI（CLI 或 Web）

**Week 5: Policy 预设**
- POLICY_PRESETS 定义
- validate_policy_combination()
- 迁移现有任务到预设

**Week 6-8: Rebase 语义（可选）**
- Semantic diff 分析
- Intent 验证
- Memory 回滚机制

---

## 护城河扩展（v0.3）

在 v0.2 的 10 条护城河基础上，v0.3 应新增：

11. ✅ Memory 必须有 retention_policy（禁止无限增长）
12. ✅ 高风险 ReviewPack 必须人工批准（禁止自动执行）
13. ✅ Rebase 必须验证 intent 一致性（禁止盲目重新规划）
14. ✅ Policy 组合必须在预设范围内（禁止任意组合）

---

## 总结

这 4 个警戒点是 v0.2 → v0.3 演进的关键：

1. **Memory 增长** → 防止系统"变重"
2. **人类介入** → 团队协作的基础
3. **Rebase 语义** → 保证一致性
4. **Policy 简化** → 防止不可维护

**核心原则**: 在功能增长的同时，必须控制复杂度增长速度。

---

**维护**: 前端架构团队  
**下次审查**: v0.3 kickoff 前  
**状态**: 🟡 警戒中
