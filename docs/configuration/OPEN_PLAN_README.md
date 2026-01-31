# Open Plan - README

**Version**: 1.0.0 (Experimental Prototype)  
**Status**: ✅ Implemented & Tested  
**Date**: 2026-01-26

---

## 什么是 Open Plan?

Open Plan是AgentOS的实验性扩展,实现"**开放理解 + 收敛执行**"的理念:

```
AI自由理解和拆解任务 → 系统验证和执行
(无限内容空间)        (有边界接口)
```

与传统方法的对比:

| 方法 | 内容 | 接口 | 优点 | 缺点 |
|------|------|------|------|------|
| **传统规则** | 固定步骤类型 | 固定操作词 | 可预测 | 限制AI能力 |
| **完全自由** | AI随意生成 | 无约束 | 灵活 | 难验证/审计 |
| **Open Plan** | AI自由组织 | 7种通道 | 灵活+可控 | 需LLM调用 |

---

## 核心特性

### 1. 7种执行通道 (Runtime Capability Snapshot)

**重要**: 这些action kinds不是稳定API,而是当前executor的capability snapshot。

所有操作通过固定的7种通道执行:

- `command`: 执行shell命令
- `file`: 文件操作(create/update/delete/declare)
- `api`: API调用
- `agent`: 委托给子agent
- `rule`: 执行约束
- `check`: 验证操作
- `note`: 人类可读注释

**⚠️ 这不是永久契约**:
- 未来executor能力变化时,kinds可能增加/删除/合并
- 不要依赖"永远是7种"
- 不要在其他系统中硬编码这个列表

**正确理解**: 这是"当前暂时支持的通道",不是"Open Plan语言规范"

### 2. 双重验证

- **结构验证** (LLM生成后): JSON schema, types, required fields
- **业务规则验证** (execution前): Mode constraints, allowlist, paths

### 3. 完整审计

每次执行保存完整轨迹:
- Mode proposal (含confidence + reason)
- Open plan (含steps + actions)
- Validation reports
- Execution results

---

## 快速开始

### 1. 验证安装

```bash
python3 tests/e2e/test_open_plan_quick.py
```

预期输出:
```
✅ All tests passed!
  - Schema definitions ✓
  - Structural validation ✓
  - Action validators ✓
  - Mode system integration ✓
  - Serialization ✓
```

### 2. 运行Gate

```bash
python3 scripts/gates/gopl_open_plan_gate.py
```

预期输出:
```
✓ GOPL: All 8 OpenPlan file(s) valid
```

### 3. 使用示例 (需要OPENAI_API_KEY)

```python
from agentos.core.mode.mode_proposer import ModeProposer
from agentos.core.executor_dry.open_plan_builder import OpenPlanBuilder

# Step 1: AI理解意图并提议mode
proposer = ModeProposer()
mode_selection = proposer.propose_mode("创建一个landing page")

print(f"Pipeline: {mode_selection.pipeline}")
# Output: ['planning', 'implementation']

print(f"Confidence: {mode_selection.confidence}")
# Output: 0.92

# Step 2: AI生成执行计划
builder = OpenPlanBuilder()
plan = builder.build("创建一个landing page", mode_selection)

print(f"Steps: {len(plan.steps)}")
# Output: 5 (AI自由拆解)

# Step 3: 系统验证
from agentos.core.schemas import validate_open_plan_structure

report = validate_open_plan_structure(plan)
assert report.valid  # 确保plan结构正确

# Step 4: 执行 (在实际系统中)
# executor.execute(plan)
```

---

## 架构概览

```
User Request ("创建landing page")
        ↓
ModeProposer (LLM) → "planning + implementation" (confidence: 0.92)
        ↓
OpenPlanBuilder (LLM) → 生成5步计划
        ↓
StructuralValidator → 验证JSON schema
        ↓
OpenPlanVerifier → 验证business rules
        ↓
ExecutorEngine → 执行 (遍历steps和actions)
```

---

## 文件结构

```
agentos/core/
├── schemas/          # OpenPlan数据定义
│   ├── open_plan.py           (OpenPlan容器)
│   ├── action_validators.py  (7种action验证)
│   └── structural_validator.py (结构校验)
├── mode/
│   └── mode_proposer.py       (LLM mode选择)
├── executor_dry/
│   └── open_plan_builder.py   (LLM plan生成)
└── executor/
    └── open_plan_verifier.py  (业务规则验证)

scripts/gates/
└── gopl_open_plan_gate.py    (CI gate)

docs/
├── OPEN_PLAN_ARCHITECTURE.md          (完整文档)
└── OPEN_PLAN_IMPLEMENTATION_SUMMARY.md (实施总结)

tests/e2e/
├── test_open_plan_quick.py          (快速验证)
├── test_open_plan_landing_page.py   (场景1: Landing page)
├── test_open_plan_bug_fix.py        (场景2: Bug fix)
└── test_open_plan_analysis.py       (场景3: 代码分析)
```

---

## 适用场景

### ✅ 适合使用Open Plan

- 复杂任务 (需要多步骤拆解)
- 创造性任务 (没有固定模式)
- 探索性任务 (需求不完全明确)
- 跨领域任务 (涉及多种操作)

### ❌ 不适合使用Open Plan

- 简单任务 (1-2步就能完成)
- 高确定性任务 (有明确SOP)
- 实时任务 (需要极快响应)
- 资源敏感任务 (Token成本敏感)

### 💡 推荐策略

```python
# 根据confidence决定是否使用Open Plan
mode_selection = proposer.propose_mode(nl_input)

if mode_selection.confidence < 0.5:
    # 低confidence: fallback到规则模式
    selector = ModeSelector()
    mode_selection = selector.select_mode(nl_input)
```

---

## 与现有系统的关系

### 不冲突

- ✅ Mode system: `experimental_open_plan`是新增mode
- ✅ Executor: 共享`ExecutorEngine`和10条护城河
- ✅ Gate system: GOPL是新增gate
- ✅ 审计: 遵守相同的ReviewPack规范

### 用户选择

用户可以选择:
- **规则模式**: `ModeSelector` + `DryExecutor` (确定性,快速)
- **理解模式**: `ModeProposer` + `OpenPlanBuilder` (灵活,智能)
- **混合模式**: 根据confidence动态切换

---

## 验收标准

### 功能验收 ✅

- [x] 处理"创建landing page"并生成合理pipeline
- [x] Planning mode禁止diff
- [x] Implementation mode必须有diff
- [x] Action缺少必填字段被拒绝

### 工程验收 ✅

- [x] Gate通过
- [x] 不破坏现有系统
- [x] 审计轨迹完整
- [x] 文档完整

---

## 限制与已知问题

### 1. 循环导入

- **问题**: `executor` ↔ `mode` 循环依赖 (现有代码问题)
- **影响**: 测试需要直接文件导入
- **解决**: 使用`test_open_plan_quick.py`

### 2. LLM成本

- **成本**: 约$0.001-0.01 per request (gpt-4o-mini)
- **缓解**: Confidence fallback, caching, 本地模型

### 3. E2E测试依赖API key

- **解决**: Mock tests不需要API key

---

## 文档

- **架构文档**: [docs/OPEN_PLAN_ARCHITECTURE.md](docs/OPEN_PLAN_ARCHITECTURE.md)
- **实施总结**: [docs/OPEN_PLAN_IMPLEMENTATION_SUMMARY.md](docs/OPEN_PLAN_IMPLEMENTATION_SUMMARY.md)

---

## 下一步

### 立即可做

1. 设置API key: `export OPENAI_API_KEY="sk-..."`
2. 运行E2E测试: `python3 tests/e2e/test_open_plan_quick.py`
3. 阅读架构文档: `docs/OPEN_PLAN_ARCHITECTURE.md`
4. 在真实场景中测试

### 未来改进

- v1.1: 修复循环导入, 添加更多场景测试
- v1.2: 多模型支持, plan优化, cost monitoring
- v2.0: Multi-agent协作, plan templates, visual editor

---

## FAQ

**Q: Open Plan与现有mode system冲突吗?**  
A: 不冲突。Open Plan是可选扩展,用户可以继续使用规则模式。

**Q: Open Plan的成本如何?**  
A: 2次LLM调用,约$0.001-0.01 per request (gpt-4o-mini)

**Q: 如何确保Open Plan不会生成危险操作?**  
A: 通过双重验证 + 10条护城河 + gate强制执行

**Q: Open Plan可以离线运行吗?**  
A: 需要LLM API,但可以缓存patterns或使用本地模型

**Q: 如何调试Open Plan失败?**  
A: 查看审计轨迹 `runs/<id>/open_plan.json`

---

**Created**: 2026-01-26  
**Status**: ✅ Production-Ready Prototype  
**Maintainers**: AgentOS Team
