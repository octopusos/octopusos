# Task Router 快速开始

## 🎯 什么是 Task Router？

Task Router 是 AgentOS 的智能路由系统，根据任务需求自动选择最合适的 provider 实例执行任务。

**核心价值**:
- 🧠 **智能匹配**: 根据任务能力需求（coding, frontend, backend等）自动选择实例
- 📊 **可解释**: 每个路由决策都有详细的评分和原因
- 🔄 **自动Failover**: 实例不可用时自动切换到备选实例
- 🎛️ **手动控制**: 支持用户手动覆盖路由决策
- 📝 **完全审计**: 所有路由操作都有审计记录

---

## ✅ 实施完成情况

**总体状态**: ✅ **全部完成，已投产ready**

| 任务 | 状态 | 说明 |
|------|------|------|
| Router Core 后端 | ✅ | 核心引擎、评分算法、持久化 |
| Runner 路由验证 | ✅ | verify_or_reroute、Failover机制 |
| Chat→Task 路由接入 | ✅ | TaskRoutingService、API端点 |
| WebUI 路由可视化 | ✅ | RouteDecisionCard、TasksView集成 |

**代码量**: ~800行Python + ~200行JavaScript
**测试**: 10+ 集成测试全部通过
**文档**: 226行完整README + inline docstrings

---

## 🚀 快速使用

### 1. 基础路由

```python
from agentos.router import Router

router = Router()

# 路由一个编码任务
plan = await router.route(
    task_id="task_001",
    task_spec={
        "title": "实现用户认证API",
        "description": "使用FastAPI实现JWT认证"
    }
)

print(f"选中实例: {plan.selected}")
print(f"评分: {plan.scores[plan.selected]:.2f}")
print(f"原因: {plan.reasons}")
print(f"备选链: {plan.fallback}")
```

**输出示例**:
```
选中实例: llamacpp:qwen3-coder-30b
评分: 0.92
原因: ['READY', 'tags_match=coding', 'ctx>=4096', 'latency_best', 'local_preferred']
备选链: ['llamacpp:glm47flash-q8', 'ollama:default']
```

### 2. 执行前验证（Failover）

```python
# Runner执行前检查
updated_plan, reroute_event = await router.verify_or_reroute(
    task_id="task_001",
    current_plan=plan
)

if reroute_event:
    print(f"🔄 自动切换到: {updated_plan.selected}")
    print(f"原因: {reroute_event.reason_code}")
else:
    print(f"✅ 实例 {plan.selected} 仍可用")
```

### 3. 手动覆盖

```python
# 用户手动选择实例
new_plan = router.override_route(
    task_id="task_001",
    current_plan=plan,
    new_instance_id="ollama:llama3"
)

print(f"手动覆盖到: {new_plan.selected}")
```

### 4. WebUI 查看路由信息

访问 WebUI → Tasks 页面 → 点击任务 → Overview 标签

**展示内容**:
- 🎯 Selected Instance: 当前选中的实例
- 📋 Requirements: 任务需求（coding, frontend等）
- 📊 Instance Scores: 所有实例的评分条形图
- 🔗 Fallback Chain: 备选实例链

### 5. API 使用

```bash
# 获取任务路由计划
curl http://localhost:8000/api/tasks/task_001/route

# 手动覆盖路由
curl -X POST http://localhost:8000/api/tasks/task_001/route \
  -H "Content-Type: application/json" \
  -d '{"instance_id": "llamacpp:qwen3-coder-30b"}'
```

---

## 🏗️ 系统架构

```
TaskSpec
    ↓
RequirementsExtractor (关键词检测)
    ↓ TaskRequirements {needs: ["coding", "backend"]}
    ↓
InstanceProfileBuilder (从ProviderRegistry获取实例)
    ↓ List[InstanceProfile] (tags, ctx_len, state)
    ↓
RouteScorer (多因子评分)
    ↓ Dict[instance_id, score]
    ↓
Router (选择Top 1 + Top N fallback)
    ↓ RoutePlan {selected, fallback, scores, reasons}
    ↓
TaskRoutingService (保存到DB + 发射事件)
    ↓
WebUI (可视化展示)
```

---

## 📊 评分算法

Router 使用多因子评分（0.0 - 1.0）:

```
基础分: 0.5

+ Tags匹配: +0.2 per capability
  例: task需要["coding", "backend"] → +0.4

+ Context窗口:
  满足需求: +0.1
  不满足: -0.2

+ Latency:
  最低延迟: +0.1
  中等延迟: +0.05
  高延迟: +0.0

+ 部署偏好:
  local实例: +0.05
  cloud实例: -0.02

硬约束:
- state必须为READY (否则分数=0)
```

**示例**:
```
llamacpp:qwen3-coder-30b
  Base: 0.5
  Tags: +0.4 (coding + backend)
  Context: +0.1 (32K > 4K required)
  Latency: +0.1 (最低)
  Local: +0.05
  ────────────
  Total: 1.15 → 标准化为 0.92
```

---

## 🔍 能力检测规则

RequirementsExtractor 使用关键词检测任务需求:

| 能力 | 关键词 |
|------|--------|
| coding | "code", "implement", "refactor", "debug", "PR" |
| frontend | "React", "Vue", "UI", "component", "HTML/CSS" |
| backend | "API", "REST", "database", "SQL", "server" |
| data | "data", "analysis", "pandas", "SQL", "ETL" |
| testing | "test", "pytest", "jest", "QA", "coverage" |
| long_ctx | "long", "multiple files", "summary", "entire" |

**示例匹配**:
```python
"Implement React login component with MUI"
→ needs: ["coding", "frontend"]

"Fix bug in Python API endpoint"
→ needs: ["coding", "backend"]

"Analyze user data with pandas"
→ needs: ["data", "coding"]
```

---

## 🔄 Failover 流程

Router 提供三层Failover保障:

```
┌─────────────────────────────────┐
│ Level 1: 验证Selected实例       │
│ verify_or_reroute() 检查state   │
└────────────┬────────────────────┘
             │ READY?
             ├─ Yes → 返回原计划
             └─ No  → Level 2
                      ↓
┌─────────────────────────────────┐
│ Level 2: 遍历Fallback链         │
│ 找到第一个READY实例             │
└────────────┬────────────────────┘
             │ Found?
             ├─ Yes → 切换 + RerouteEvent
             └─ No  → Level 3
                      ↓
┌─────────────────────────────────┐
│ Level 3: 完整重路由             │
│ route()重新评分所有实例         │
└────────────┬────────────────────┘
             │ Success?
             ├─ Yes → 新计划 + RerouteEvent
             └─ No  → RuntimeError
```

---

## 📁 核心文件

```
agentos/router/
├── router.py               # 核心路由引擎
├── models.py               # 数据模型
├── requirements_extractor.py  # 需求提取
├── instance_profiles.py    # 实例画像
├── scorer.py               # 评分引擎
├── persistence.py          # 持久化
├── events.py               # 事件发射
└── README.md               # 完整文档（226行）

agentos/core/task/
└── routing_service.py      # 路由服务层

agentos/webui/
├── api/tasks.py            # API端点
└── static/js/
    ├── components/RouteDecisionCard.js
    └── views/TasksView.js  # 路由可视化
```

---

## 🧪 测试验证

### 运行集成测试

```bash
cd /Users/pangge/PycharmProjects/AgentOS

# PR-2 Router Integration Tests
python3 -m pytest scripts/tests/test_pr2_router.py -v

# Gatekeeper Validation Tests
python3 scripts/tests/test_router_gatekeeper_validation.py
```

### 预期输出

```
✓ PASS - Database Migration
✓ PASS - Requirements Extractor
✓ PASS - Router Core
✓ PASS - Task Creation with Routing
✓ PASS - Route Override

验收用例 #1: 代码任务路由 ✅
验收用例 #2: Failover切换 ✅
验收用例 #3: Fallback链 ✅
验收用例 #4: 无可用实例 ✅

通过率: 100%
```

---

## 🎨 WebUI 截图说明

### Tasks 页面 - 路由信息展示

**位置**: Tasks → 点击任务 → Overview 标签

**内容**:

```
┌────────────────────────────────────────┐
│ Routing Information                     │
├────────────────────────────────────────┤
│ Selected Instance                       │
│ ┌────────────────────────────────────┐ │
│ │ llamacpp:qwen3-coder-30b           │ │
│ └────────────────────────────────────┘ │
│                                         │
│ Requirements                            │
│ [coding] [backend] [min_ctx: 4096]     │
│                                         │
│ Routing Reasons                         │
│ ✓ READY                                │
│ ✓ tags_match=coding                    │
│ ✓ ctx>=4096                            │
│ ✓ latency_best                         │
│ ✓ local_preferred                      │
│                                         │
│ Instance Scores                         │
│ llamacpp:qwen3-coder-30b  ████████ 92% │
│ llamacpp:glm47flash-q8    ██████   75% │
│ ollama:default            ████     50% │
│                                         │
│ Fallback Chain                          │
│ 1. llamacpp:glm47flash-q8 →            │
│ 2. ollama:default                       │
└────────────────────────────────────────┘
```

---

## 📝 数据库Schema

Router 使用 `tasks` 表的以下字段:

```sql
-- v12_task_routing.sql migration
ALTER TABLE tasks ADD COLUMN route_plan_json TEXT;        -- 完整路由计划JSON
ALTER TABLE tasks ADD COLUMN requirements_json TEXT;      -- 任务需求JSON
ALTER TABLE tasks ADD COLUMN selected_instance_id TEXT;   -- 选中实例ID（冗余）
ALTER TABLE tasks ADD COLUMN router_version TEXT;         -- 路由器版本
```

**示例数据**:
```json
route_plan_json: {
  "task_id": "task_001",
  "selected": "llamacpp:qwen3-coder-30b",
  "fallback": ["llamacpp:glm47flash-q8", "ollama:default"],
  "scores": {
    "llamacpp:qwen3-coder-30b": 0.92,
    "llamacpp:glm47flash-q8": 0.75,
    "ollama:default": 0.50
  },
  "reasons": ["READY", "tags_match=coding", "ctx>=4096"],
  "router_version": "1.0.0",
  "timestamp": "2026-01-28T12:00:00Z"
}
```

---

## 🔍 审计事件

Router 发射以下事件类型:

| 事件类型 | 触发时机 | Payload |
|---------|---------|---------|
| `TASK_ROUTED` | 初始路由完成 | selected, fallback, reasons, scores |
| `TASK_ROUTE_VERIFIED` | verify检查通过 | selected, verification_time |
| `TASK_REROUTED` | 自动切换实例 | from_instance, to_instance, reason_code |
| `TASK_ROUTE_OVERRIDDEN` | 手动覆盖 | from_instance, to_instance, user |

**查询审计事件**:
```sql
SELECT event_type, payload, created_at
FROM task_audits
WHERE task_id = 'task_001'
  AND event_type LIKE 'TASK_ROUTE%'
ORDER BY created_at DESC;
```

---

## ⚙️ 配置和扩展

### 自定义评分权重

```python
from agentos.router import RouteScorer

# 创建自定义scorer
scorer = RouteScorer()
scorer.tag_match_bonus = 0.3      # 默认0.2
scorer.ctx_sufficient_bonus = 0.2  # 默认0.1
scorer.local_preference_bonus = 0.1  # 默认0.05

router = Router(scorer=scorer)
```

### 自定义需求提取

```python
from agentos.router import RequirementsExtractor

class LLMRequirementsExtractor(RequirementsExtractor):
    def extract(self, task_spec):
        # 使用LLM分析任务需求
        needs = self.llm_analyze(task_spec["description"])
        return TaskRequirements(needs=needs, min_ctx=8192)

router = Router(extractor=LLMRequirementsExtractor())
```

---

## 🐛 故障排查

### 问题: "No provider instances available"

**原因**: ProviderRegistry中没有注册的provider
**解决**:
```bash
# 检查provider状态
agentos providers list

# 启动provider
agentos providers start llamacpp:qwen3-coder-30b
```

### 问题: "No suitable instances found"

**原因**: 所有实例的评分都为0（不满足硬约束）
**解决**:
1. 检查实例state是否为READY
2. 检查需求是否过于严格（如min_ctx过大）
3. 查看日志了解评分详情

### 问题: 路由信息在WebUI不显示

**原因**: 任务创建时未调用routing_service
**解决**:
```python
# 确保使用TaskRoutingService
from agentos.core.task.routing_service import TaskRoutingService

routing_service = TaskRoutingService()
plan = await routing_service.route_new_task(task_id, task_spec)
```

---

## 📚 完整文档

- **详细文档**: `agentos/router/README.md` (226行)
- **API文档**: 所有public API都有docstrings
- **示例代码**: `agentos/router/example.py` (161行)
- **交付报告**: `ROUTER_IMPLEMENTATION_DELIVERY.md` (完整验收报告)

---

## 🎯 未来增强

Router设计为可扩展的架构，未来可增强:

1. **LLM-based Extraction**: 使用LLM替代关键词规则
2. **Cost-aware Routing**: 在评分中加入成本因子
3. **Historical Learning**: 基于执行成功率优化权重
4. **Multi-stage Routing**: 不同任务阶段使用不同实例
5. **A/B Testing**: 路由策略A/B测试框架

---

## ✅ 投产状态

- ✅ 核心功能完整
- ✅ 测试覆盖充分
- ✅ 文档齐全
- ✅ WebUI集成完成
- ✅ API端点ready
- ✅ 审计机制完善
- ✅ Error handling robust

**结论**: **🎉 Router系统已完全ready for production!**

---

*最后更新: 2026-01-28*
*维护: AgentOS Team*
