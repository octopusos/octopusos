# Shadow Classifier Registry - 快速参考

## 核心概念

### Shadow Classifier 是什么？
Shadow Classifier 是 InfoNeedClassifier 的**观察版本**，与 active 版本并行运行但**永不影响用户行为**。用于：
1. 安全地测试新分类规则
2. 收集对比数据以评估改进
3. 逐步验证后再升级为 active

### 关键约束（红线）
- ❌ Shadow 决策**永不执行**
- ❌ Shadow 决策**永不影响用户**
- ✅ Shadow 决策**仅用于事后对比和学习**

## 快速开始

### 1. 初始化 Shadow System
```python
from agentos.core.chat.shadow_init import initialize_shadow_classifiers

# 使用默认配置
initialize_shadow_classifiers()

# 或自定义配置
config = {
    "enabled": True,
    "active_versions": ["v2-shadow-expand-keywords"],
    "max_concurrent_shadows": 2,
}
initialize_shadow_classifiers(config)
```

### 2. 查询 Shadow Classifiers
```python
from agentos.core.chat.shadow_registry import get_shadow_registry

registry = get_shadow_registry()

# 获取所有激活的 shadows
active_shadows = registry.get_active_shadows()

# 获取特定版本
shadow = registry.get_classifier("v2-shadow-expand-keywords")

# 查询版本信息
info = registry.get_version_info("v2-shadow-expand-keywords")
print(info["change_description"])
```

### 3. 运行 Shadow 评估
```python
import asyncio

question = "What's the latest Python version?"
context = {
    "message_id": "msg-001",
    "session_id": "sess-123",
    "phase": "planning"
}

# 并行运行所有激活的 shadows
tasks = [
    shadow.classify_shadow(question, context)
    for shadow in active_shadows
]
shadow_decisions = await asyncio.gather(*tasks)

# 检查决策结果
for decision in shadow_decisions:
    print(f"Version: {decision.classifier_version.version_id}")
    print(f"Decision: {decision.decision_action}")
    print(f"Confidence: {decision.confidence_level}")
```

## Registry API 参考

### 注册管理
```python
registry = get_shadow_registry()

# 注册新 shadow
shadow = ShadowClassifierV2ExpandKeywords()
registry.register(shadow)

# 注销 shadow
registry.unregister("v2-shadow-expand-keywords")
```

### 激活控制
```python
# 激活单个版本
registry.activate("v2-shadow-expand-keywords")

# 批量激活
await registry.activate_batch([
    "v2-shadow-expand-keywords",
    "v2-shadow-adjust-threshold"
])

# 停用
registry.deactivate("v2-shadow-expand-keywords")

# 停用所有
await registry.deactivate_all()
```

### 查询操作
```python
# 列出所有版本
versions = registry.list_all_versions()

# 检查是否激活
is_active = registry.is_active("v2-shadow-expand-keywords")

# 统计
total = registry.count_total()
active_count = registry.count_active()

# 获取版本详情
info = registry.get_version_info("v2-shadow-expand-keywords")
# Returns:
# {
#     "version_id": "v2-shadow-expand-keywords",
#     "version_type": "shadow",
#     "change_description": "...",
#     "created_at": "2026-01-31T...",
#     "is_active": True,
#     "detailed_changes": "..."
# }
```

## 创建新 Shadow Classifier

### 步骤 1: 继承 BaseShadowClassifier
```python
from agentos.core.chat.shadow_classifier import BaseShadowClassifier
from agentos.core.chat.models.decision_candidate import ClassifierVersion

class MyShadowClassifier(BaseShadowClassifier):
    def __init__(self):
        version = ClassifierVersion(
            version_id="v2-shadow-my-experiment",
            version_type="shadow",
            change_description="My experimental changes"
        )
        super().__init__(version)

        # 初始化自定义配置
        self.my_config = {}

    async def classify_shadow(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> DecisionCandidate:
        """实现分类逻辑"""
        # 1. 执行分类
        classification = await self._my_classify_logic(question, context)

        # 2. 返回决策候选
        return self._create_decision_candidate(
            message_id=context.get("message_id", "unknown"),
            question_text=question,
            classification=classification,
            latency_ms=10.0,
            session_id=context.get("session_id", "unknown"),
            phase=context.get("phase", "planning")
        )

    def get_change_description(self) -> str:
        """返回详细变更说明"""
        return "My Shadow Classifier: Detailed changes..."
```

### 步骤 2: 注册和激活
```python
# 注册
my_shadow = MyShadowClassifier()
registry.register(my_shadow)

# 激活
registry.activate("v2-shadow-my-experiment")
```

### 步骤 3: 添加到配置文件
编辑 `agentos/config/shadow_classifiers.yaml`:
```yaml
shadow_classifiers:
  active_versions:
    - v2-shadow-expand-keywords
    - v2-shadow-my-experiment  # 添加新版本

  versions:
    v2-shadow-my-experiment:
      enabled: true
      priority: 3
      description: "My experimental shadow classifier"
      risk_level: "low"
```

## DecisionCandidate 结构

### 关键字段
```python
decision = DecisionCandidate(
    # 角色标识
    decision_role=DecisionRole.SHADOW,  # ACTIVE | SHADOW

    # 版本信息
    classifier_version=ClassifierVersion(...),

    # 输入（与 active 必须一致）
    question_text="What's the latest Python version?",
    question_hash="abc123...",
    phase="planning",
    session_id="sess-123",
    message_id="msg-001",

    # 分类结果
    info_need_type="external_fact_uncertain",
    confidence_level="low",
    decision_action="require_comm",

    # 信号数据
    rule_signals={
        "has_time_sensitive_keywords": True,
        "signal_strength": 0.85
    },
    llm_confidence_score=0.3,

    # Shadow 元数据
    shadow_metadata={
        "reasoning": "...",
        # ❌ 禁止: "execution_result"
    }
)
```

### 访问字段
```python
# 角色
assert decision.decision_role == DecisionRole.SHADOW

# 分类结果
print(decision.info_need_type)        # "external_fact_uncertain"
print(decision.decision_action)        # "require_comm"
print(decision.confidence_level)       # "low"

# 信号数据
signals = decision.rule_signals
print(signals["signal_strength"])      # 0.85

# 版本信息
print(decision.classifier_version.version_id)  # "v2-shadow-expand-keywords"
```

## 配置文件参考

### 全局配置
```yaml
shadow_classifiers:
  enabled: true                      # 全局开关
  max_concurrent_shadows: 2          # 最大并行数
  evaluation_timeout_ms: 500         # 超时（毫秒）

  active_versions:                   # 激活列表
    - v2-shadow-expand-keywords
```

### 版本配置
```yaml
  versions:
    v2-shadow-expand-keywords:
      enabled: true
      priority: 1                    # 优先级（越高越早激活）
      description: "Expanded keyword coverage"
      risk_level: "low"              # low | medium | high
```

### 审计配置
```yaml
audit:
  log_shadow_evaluations: true       # 记录所有评估
  store_shadow_decisions: true       # 存储到数据库
  detailed_log_sample_rate: 1.0      # 详细日志采样率
```

### 告警配置
```yaml
alerts:
  alert_on_divergence: true          # 决策分歧时告警
  divergence_threshold: "decision_action"
  alert_on_timeout: true             # 超时时告警
```

## 现有 Shadow 版本

### v2-shadow-expand-keywords
- **风险等级**: LOW
- **变更内容**: 扩展关键词覆盖
  - EXTERNAL_FACT: +7 keywords (including Chinese)
  - AMBIENT_STATE: +9 keywords (including Chinese)
- **影响**: 更激进地检测时间敏感和环境状态问题
- **推荐**: 第一个启用的 shadow

### v2-shadow-adjust-threshold
- **风险等级**: MEDIUM
- **变更内容**: 降低 EXTERNAL_FACT 阈值 0.6 → 0.5
- **影响**: 更容易触发外部信息需求
- **推荐**: 在 v2.a 验证成功后启用

## 性能指标

### 性能目标
- Shadow 评估延迟: < 100ms
- 并行评估总延迟: < 200ms（2 shadows）
- 规则匹配: < 10ms

### 监控指标
```python
# 延迟监控
assert decision.latency_ms < 100

# 并行效率
start = time.perf_counter()
await asyncio.gather(*tasks)
total_time = (time.perf_counter() - start) * 1000
assert total_time < 200  # 不应线性叠加
```

## 常见问题

### Q: Shadow 决策会影响用户吗？
**A**: 不会。Shadow 决策的 `decision_role=SHADOW`，系统保证永不执行。

### Q: Shadow 决策存储在哪里？
**A**: 存储在 `decision_candidates` 表，与 active 决策一起，但 role 字段不同。

### Q: 如何比较 shadow 和 active 决策？
**A**: 使用 Decision Comparison API（任务 #6）或 Shadow Score 引擎（任务 #4）。

### Q: 可以同时运行多少个 shadow？
**A**: 默认最多 2 个（`max_concurrent_shadows: 2`），可配置。

### Q: Shadow 决策可以调用 LLM 吗？
**A**: 可以，但第一阶段的 shadow 版本不调用 LLM，专注规则系统。

### Q: 如何升级 shadow 为 active？
**A**: 使用 Shadow → Active 迁移工具（任务 #11），需要经过验证和审批流程。

## 测试工具

### 单元测试 Mock
```python
from tests.unit.core.chat.test_shadow_registry import MockShadowClassifier

# 创建测试用 shadow
mock_shadow = MockShadowClassifier("test-shadow-v1")
registry.register(mock_shadow)
```

### 集成测试示例
```python
@pytest.mark.asyncio
async def test_my_shadow():
    shadow = MyShadowClassifier()
    registry = ShadowClassifierRegistry()
    registry.register(shadow)
    registry.activate(shadow.version.version_id)

    question = "Test question"
    context = {"message_id": "test-001", "session_id": "sess-1"}

    decision = await shadow.classify_shadow(question, context)

    assert decision.decision_role == DecisionRole.SHADOW
    assert decision.latency_ms > 0
```

## 相关文档
- [Shadow Classifier Registry 验收报告](../../SHADOW_CLASSIFIER_REGISTRY_ACCEPTANCE_REPORT.md)
- [DecisionCandidate 数据模型](../models/decision_candidate.md)
- [InfoNeedClassifier 实现](../chat/info_need_classifier.md)

## 相关任务
- ✅ 任务 #2: 实现 Shadow Classifier Registry (已完成)
- ⏳ 任务 #3: 扩展 Audit Log 支持多决策记录
- ⏳ 任务 #4: 实现 Shadow Score 计算引擎
- ⏳ 任务 #5: 实现决策对比指标生成

---
*最后更新: 2026-01-31*
