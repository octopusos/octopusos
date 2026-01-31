# Coordinator Red Line Enforcement (v0.9.2)

**Version**: 0.9.2  
**Status**: Enforced  
**Date**: 2026-01-25

---

## Red Line Definition

**Core Principle**: Coordinator MUST NOT execute - only plan!

---

## Three-Tier Enforcement

### 1. Schema Layer (Design Time)

**Mechanism**: JSON Schema with `additionalProperties: false`

**Enforced Rules**:
- ✅ No `execute` field allowed in any schema
- ✅ No `run` field allowed
- ✅ No `shell` field allowed
- ✅ Frozen structure (no ad-hoc fields)

**Files**:
- `agentos/schemas/coordinator/*.schema.json` - All schemas have `additionalProperties: false`

**Validation**: Gate A + Gate B

---

### 2. Runtime Layer (Execution Time)

**Mechanism**: Static scanning + isolation testing

**Gate D**: Static Scan for Execution Symbols
```bash
scripts/gates/v092_gate_d_no_execution_symbols.sh
```

**Forbidden Patterns**:
- `subprocess`
- `shell`
- `execute`
- `run_command`
- `git commit`
- `git push`
- `os.system`
- `eval(`
- `exec(`

**Gate E**: Isolation Testing
```bash
scripts/gates/v092_gate_e_isolation.py
```

**Enforced**:
- Temporary registry (no global state modification)
- Temporary memory (read-only context)
- No file system writes (except designated output paths)

---

### 3. Documentation Layer (Knowledge Time)

**Mechanism**: Clear documentation of boundaries

**Files**:
- `docs/coordinator/RESPONSIBILITIES.md` - What Coordinator does NOT do
- `docs/coordinator/README.md` - Red line warnings
- `docs/coordinator/STATE_MACHINE_SPEC.md` - Red line checks per state

**Anti-Patterns Documented**:
1. Coordinator-as-Executor (execution in planning code)
2. Rule-Skipping (bypassing adjudication)
3. Opaque Decision-Making (no rationale/evidence)

---

## Red Line Matrix

### Current Red Lines (v0.9.2)

| Red Line | Description | Enforcement | Gate |
|----------|-------------|-------------|------|
| **RL1**: No Execution Payload | Intent/Coordinator must not contain execution commands | Schema + Static + Doc | Gate A, Gate D |
| **RL2**: full_auto Constraints | full_auto mode → question_budget = 0 | Schema + Runtime | Gate I |
| **RL3**: High Risk ≠ full_auto | High/critical risk cannot use full_auto | Schema + Runtime | Gate B |
| **RL4**: Evidence Required | All action_proposal nodes must have evidence_refs | Schema + Runtime | Gate H |
| **RL5**: Registry Only | All content must come from ContentRegistry | Schema + Runtime | Gate A |

### Future Red Lines (Post v0.9.2)

| Red Line | Description | Enforcement | Status |
|----------|-------------|-------------|--------|
| **X1**: No Direct Executor Call | Coordinator NEVER calls Command Executor (even mock/dry-run/simulate) | Architecture + Code Review | 🔴 CRITICAL |
| **X2**: ModelRouter is Advisory Only | ModelRouter only suggests; cannot make adjudication decisions | Architecture + Audit | 🔴 CRITICAL |
| **X3**: ExecutionGraph is Sole Entry | ExecutionGraph is the ONLY entry to execution layer (no shortcuts) | Architecture + Gate | 🔴 CRITICAL |

---

## Gate Enforcement Summary

### Design-Time Gates (Pre-Implementation)
- **Gate A**: Schema existence and structure ✅
- **Gate B**: Schema batch validation ✅
- **Gate C**: Negative fixtures testing ✅
- **Gate F**: Explain snapshot stability ✅

### Runtime Gates (Post-Implementation)
- **Gate D**: Static scan for execution symbols ✅
- **Gate E**: Isolation testing ✅
- **Gate G**: State machine completeness ✅
- **Gate H**: Graph topology validation ✅
- **Gate I**: Question governance check ✅
- **Gate J**: Rule adjudication completeness ✅

---

## Enforcement Checklist

### Before Commit
- [ ] Run Gate D (static scan)
- [ ] Review code for execution symbols
- [ ] Verify no `subprocess`, `shell`, `execute` imports
- [ ] Check CoordinatorEngine has no file writes

### Before Release
- [ ] Run all 10 Gates (A-J)
- [ ] All Gates must pass
- [ ] Review negative fixtures (all rejected)
- [ ] Verify documentation updated

### During Code Review
- [ ] Check for anti-patterns
- [ ] Verify all decisions have rationale
- [ ] Confirm evidence_refs present
- [ ] Validate state machine transitions

---

## Violation Response

### If Execution Symbol Detected
1. **STOP** - Do not merge
2. Remove execution code
3. Move execution logic to separate Executor component
4. Re-run Gate D

### If Red Line Violated in Schema
1. Schema validation will fail (Gate B)
2. Fix schema (remove offending field)
3. Update negative fixtures if needed
4. Re-validate

### If Documentation Incomplete
1. Gate checklist will catch it
2. Update RESPONSIBILITIES.md
3. Document the anti-pattern
4. Add to red line matrix

---

## Red Line Philosophy

**Why enforce so strictly?**

1. **Separation of Concerns**: Planning vs Execution must be distinct
2. **Auditability**: Can't audit what you can't see
3. **Safety**: Execution has risks; planning does not
4. **Testability**: Planning is deterministic; execution is not
5. **Reproducibility**: Same Intent → Same Plan (always)

---

## Status

✅ **Red Lines Defined**: 5 core red lines  
✅ **Enforcement Mechanisms**: Schema + Runtime + Documentation  
✅ **Gates Implemented**: 10 gates (A-J)  
✅ **Documentation Complete**: RESPONSIBILITIES.md + README.md  
✅ **Negative Fixtures**: 5 invalid examples

---

## Future Red Lines (详细说明)

### 🚫 Red Line X1: Coordinator 永远不直接调用 Executor

**禁止行为**:
```python
# ❌ 绝对禁止
coordinator.execute_command(cmd)
coordinator.dry_run(cmd)
coordinator.simulate(cmd)
executor.run(graph)  # 从 Coordinator 内部调用
```

**正确做法**:
```python
# ✅ 正确：只产出计划
graph = coordinator.coordinate(intent, policy, factpack)
# 交给外部 Executor 消费
result = external_executor.execute(graph)
```

**强制机制**:
- 静态扫描：禁止 `import executor` 在 coordinator 模块
- 代码审查：任何 executor 调用立即拒绝
- 架构测试：coordinator 模块必须与 executor 模块零依赖

**违规后果**: 架构崩溃 - Planning 与 Execution 耦合，无法审计

---

### 🚫 Red Line X2: ModelRouter 只能做"选择建议"

**核心原则**: ModelRouter 是"建议者"，不是"裁决者"

**禁止行为**:
```python
# ❌ 禁止：ModelRouter 做裁决
model_router.decide_if_action_allowed(action)  
model_router.adjudicate_rule(rule, evidence)
model_router.approve_command(command)
```

**正确做法**:
```python
# ✅ 正确：ModelRouter 只建议模型
model_decision = model_router.select_model(
    task_type="graph_reasoning",
    context={"data_sensitivity": "internal"}
)
# 裁决由 RulesAdjudicator 负责
rule_decision = rules_adjudicator.adjudicate(action, rules, evidence)
```

**职责边界**:

| 组件 | 可以做 | 不能做 |
|------|--------|--------|
| **ModelRouter** | 选择模型、估算成本、检查合规 | 裁决规则、批准命令、修改计划 |
| **RulesAdjudicator** | 裁决规则、评估风险、做决策 | 选择模型 |

**强制机制**:
- 所有裁决必须有 `RuleDecision` 记录（可回放）
- 所有模型选择必须有 `ModelDecision` 记录（可解释）
- Audit Log 必须区分"建议"和"裁决"

**违规后果**: 决策不可回放、审计失效、责任不清

---

### 🚫 Red Line X3: ExecutionGraph 是唯一入口

**核心原则**: 所有执行必须通过 ExecutionGraph，无例外

**禁止行为**:
```python
# ❌ 禁止：绕过 ExecutionGraph 的快捷路径
executor.run_command_list(commands)  # 直接命令列表
executor.run_script(script)  # 临时脚本
executor.quick_fix(patch)  # 快捷修复
coordinator.emit_direct_action(action)  # 直接动作
```

**正确做法**:
```python
# ✅ 正确：所有执行通过 ExecutionGraph
graph = coordinator.coordinate(intent, policy, factpack)
# Graph 包含：nodes、edges、swimlanes、lineage、checksum
result = executor.execute_graph(graph)  # Graph 是唯一输入
```

**架构约束**:
- Executor 的 `execute()` 方法**只接受** `ExecutionGraph`
- 任何其他输入形式（list/dict/script）都是违规
- ExecutionGraph 必须包含完整的 lineage 和 checksum

**为什么这条红线如此重要**:

1. **可审计性**: Graph 有完整血缘链（intent → registry → graph）
2. **可回放性**: Graph 结构固定，可序列化、可存储、可重放
3. **质量门禁**: Graph 必须通过 Gate H（拓扑验证）才能进入执行
4. **责任清晰**: Graph 是 Coordinator 和 Executor 的唯一契约

**强制机制**:
- Executor 接口定义：`execute(graph: ExecutionGraph) -> ExecutionReport`
- 类型检查：graph 必须是 `ExecutionGraph` schema 验证通过的对象
- Gate 前置：未通过 Gate H 的 graph 不允许进入 executor

**违规后果**: 
- 审计断裂（无法追溯来源）
- 质量失控（绕过 Gates）
- 架构崩溃（Planning 和 Execution 边界消失）

---

## Future Red Lines 执行清单

### 在代码审查中强制执行

- [ ] 检查 `agentos/core/coordinator/` 是否有 `import executor`
- [ ] 检查 ModelRouter 是否有裁决逻辑（decision/approve/adjudicate）
- [ ] 检查 Executor 是否接受 Graph 以外的输入

### 在架构设计中强制执行

- [ ] Coordinator 和 Executor 必须在不同模块
- [ ] 接口契约必须明确：`ExecutionGraph` 是唯一桥梁
- [ ] ModelRouter 职责限定在 model selection

### 在文档中强制执行

- [ ] 所有架构图必须显示 Graph 是唯一入口
- [ ] 所有示例代码不能有快捷路径
- [ ] RESPONSIBILITIES.md 必须明确 ModelRouter 边界

---

**Enforcement Level**: 🔴 **CRITICAL - Non-Negotiable**  
**Future Red Lines**: 🔴 **PREVENTIVE - Must Document Now**
