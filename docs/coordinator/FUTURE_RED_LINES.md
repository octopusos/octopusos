# Future Red Lines (Post v0.9.2)

**版本**: v0.9.2+  
**状态**: 🔴 **预防性红线 - 必须现在明确**  
**日期**: 2026-01-25

---

## 为什么需要"未来红线"？

v0.9.2 Coordinator 已经建立了5条当前红线（RL1-RL5），确保"不执行、只规划"的核心原则。

但随着系统演进，**新的违规模式会出现**。Future Red Lines (X1-X3) 是**预防性架构约束**，帮助团队在未来开发中避免常见陷阱。

---

## 🚫 Red Line X1: Coordinator 永远不直接调用 Executor

### 完整描述

**禁止**: Coordinator 内部任何代码直接调用、导入、实例化 Executor 或其方法

**包括但不限于**:
- ❌ `from agentos.executor import CommandExecutor`
- ❌ `coordinator.execute_command(cmd)`
- ❌ `coordinator.dry_run(action)`
- ❌ `coordinator.simulate(graph)`
- ❌ `executor.run(graph)` 从 Coordinator 内部调用

### 为什么这是红线

| 违规场景 | 后果 |
|---------|------|
| "我只是想测试一下执行" | 测试代码泄露到生产，规划和执行耦合 |
| "dry-run 不算真执行" | 仍然依赖执行器，破坏了架构边界 |
| "simulate 只是模拟" | 模拟逻辑应该在 GraphBuilder，不在 Executor 调用中 |

**根本问题**: Planning 和 Execution 是两个独立的生命周期阶段，必须**物理隔离**。

### 正确架构

```
┌─────────────────┐
│  Coordinator    │  只产出 ExecutionGraph
│  (Planning)     │  
└────────┬────────┘
         │ outputs: ExecutionGraph (frozen, checksummed)
         ▼
┌─────────────────┐
│  Executor       │  消费 ExecutionGraph
│  (Execution)    │  
└─────────────────┘
```

**契约**: ExecutionGraph 是唯一桥梁，Coordinator 和 Executor 零依赖。

### 强制机制

1. **静态扫描** (Gate X1):
   ```bash
   # 禁止在 coordinator 模块中导入 executor
   rg "from.*executor import|import.*executor" agentos/core/coordinator/
   ```

2. **依赖检查**:
   ```python
   # pyproject.toml 或 setup.py
   # coordinator 包不应依赖 executor 包
   ```

3. **代码审查清单**:
   - [ ] Coordinator 模块无 executor 导入？
   - [ ] 所有"执行"逻辑都在 Executor 模块？
   - [ ] 测试使用 mock ExecutionGraph 消费，不是 mock Executor？

### 违规示例（禁止）

```python
# ❌ 反例 1: 直接调用
class CoordinatorEngine:
    def coordinate(self, intent):
        graph = self.build_graph(intent)
        # 禁止！不应该在这里执行
        result = CommandExecutor().execute(graph)
        return result

# ❌ 反例 2: Dry-run
class CoordinatorEngine:
    def validate_graph(self, graph):
        # 禁止！验证应该通过 schema/gates，不是 dry-run
        executor = CommandExecutor(dry_run=True)
        executor.test_graph(graph)

# ❌ 反例 3: Simulate
class GraphBuilder:
    def build_graph(self, intent):
        graph = self._draft_graph(intent)
        # 禁止！模拟应该在规划层，不调用执行器
        executor.simulate(graph)
        return graph
```

### 正确示例

```python
# ✅ 正确：Coordinator 只产出
class CoordinatorEngine:
    def coordinate(self, intent, policy, factpack):
        # 1. 解析
        parsed = self.parser.parse(intent)
        # 2. 裁决
        decisions = self.adjudicator.adjudicate_all(parsed)
        # 3. 构建图
        graph = self.graph_builder.build_graph(parsed, decisions)
        # 4. 冻结
        frozen_graph = self.freezer.freeze({"graph": graph})
        # 返回计划，不执行
        return CoordinatorRun(graph=frozen_graph)

# ✅ 外部消费（在 main.py 或 workflow 中）
def main():
    coordinator = CoordinatorEngine(registry, memory)
    run = coordinator.coordinate(intent, policy, factpack)
    
    # 交给独立的 Executor
    executor = CommandExecutor()
    result = executor.execute(run.graph)
```

---

## 🚫 Red Line X2: ModelRouter 只能做"选择建议"

### 完整描述

**核心原则**: ModelRouter 是"建议者 (Advisor)"，不是"裁决者 (Adjudicator)"

**允许**:
- ✅ 选择适合的模型（local vs cloud）
- ✅ 估算成本
- ✅ 检查数据合规性
- ✅ 记录模型决策（ModelDecision）

**禁止**:
- ❌ 裁决规则（allow/deny/warn）
- ❌ 批准/拒绝命令
- ❌ 修改执行计划
- ❌ 做任何"业务决策"

### 为什么这是红线

**职责混淆的危险**:

| 如果 ModelRouter 做裁决 | 问题 |
|----------------------|------|
| `model_router.decide_if_action_allowed()` | 裁决逻辑不可回放（模型黑盒） |
| `model_router.approve_command()` | 责任不清（是模型批准还是规则批准？） |
| `model_router.modify_graph()` | 决策链断裂（无法追溯为什么改） |

**根本问题**: 模型选择是"优化问题"，规则裁决是"约束问题"。两者必须分离。

### 职责边界表

| 组件 | 职责 | 输入 | 输出 | 可审计性 |
|------|------|------|------|---------|
| **ModelRouter** | 选择最优模型 | task_type, data_sensitivity, budget | ModelDecision | ✅ (decision record) |
| **RulesAdjudicator** | 裁决是否允许 | command, rules, evidence | RuleDecision | ✅ (decision + reason + evidence) |
| **GraphBuilder** | 构建执行计划 | parsed_intent, decisions | ExecutionGraph | ✅ (graph + lineage) |

### 强制机制

1. **接口约束**:
   ```python
   class ModelRouter:
       """ONLY for model selection, NOT for adjudication"""
       
       def select_model(self, task_type: str, context: dict) -> ModelDecision:
           """✅ Allowed: Suggest model"""
           pass
       
       # ❌ 禁止以下方法存在
       # def decide_if_allowed(self, action) -> bool: ...
       # def adjudicate_rule(self, rule) -> str: ...
       # def approve_command(self, cmd) -> bool: ...
   ```

2. **Audit Log 检查**:
   - 所有 `RuleDecision` 必须来自 `RulesAdjudicator`
   - 所有 `ModelDecision` 只能包含模型选择，不能包含 allow/deny

3. **代码审查清单**:
   - [ ] ModelRouter 没有 `allow/deny/approve` 方法？
   - [ ] 所有裁决都在 RulesAdjudicator？
   - [ ] ModelDecision 只包含模型信息，不包含业务决策？

### 违规示例（禁止）

```python
# ❌ 反例 1: ModelRouter 做裁决
class ModelRouter:
    def select_model_and_decide(self, action, rules):
        model = self.select_model("adjudication")
        # 禁止！裁决应该在 RulesAdjudicator
        decision = model.decide_if_allowed(action, rules)
        return decision

# ❌ 反例 2: 模型批准命令
class ModelRouter:
    def approve_command(self, command):
        model = self.select_model("approval")
        # 禁止！批准是业务决策，不是模型选择
        approved = model.check_if_safe(command)
        return approved

# ❌ 反例 3: 修改计划
class ModelRouter:
    def optimize_graph(self, graph):
        model = self.select_model("optimization")
        # 禁止！图修改应该在 GraphBuilder
        model.rewrite_graph(graph)
```

### 正确示例

```python
# ✅ 正确：职责分离
class ModelRouter:
    """只做模型选择"""
    def select_model(self, task_type: str, context: dict) -> ModelDecision:
        if context["data_sensitivity"] == "confidential":
            model = "local_llama"
            cost = 0.0
        else:
            model = "claude-3-sonnet"
            cost = 1.0
        
        return ModelDecision(
            model=model,
            reason=f"Selected for {task_type}",
            cost=cost
        )

class RulesAdjudicator:
    """只做裁决"""
    def adjudicate(self, command, rules, evidence) -> RuleDecision:
        # 可以使用 ModelRouter 选择推理模型
        model_decision = self.model_router.select_model("rule_reasoning")
        
        # 但裁决逻辑在这里
        if command.risk_level == "high":
            decision = "require_review"
        else:
            decision = "allow"
        
        return RuleDecision(
            decision=decision,
            evidence=evidence,
            reason="Risk-based adjudication"
        )
```

---

## 🚫 Red Line X3: ExecutionGraph 是唯一入口

### 完整描述

**核心原则**: 所有进入执行层的操作**必须**通过 ExecutionGraph，无例外

**唯一合法路径**:
```
Intent → Coordinator → ExecutionGraph → Executor → ExecutionReport
```

**禁止的快捷路径**:
- ❌ 直接命令列表: `executor.run_commands([cmd1, cmd2])`
- ❌ 临时脚本: `executor.run_script("fix.sh")`
- ❌ 快捷修复: `coordinator.quick_fix(patch)`
- ❌ 热更新: `executor.hotfix(code)`

### 为什么这是红线

**快捷路径的危险**:

| 快捷路径 | 丢失的能力 | 后果 |
|---------|-----------|------|
| 命令列表 | Lineage 血缘链 | 无法追溯来源 |
| 临时脚本 | Schema 验证 | 无法保证结构 |
| 快捷修复 | Gate 检查 | 绕过质量门禁 |
| 热更新 | Audit 记录 | 无法审计 |

**根本问题**: ExecutionGraph 是架构的"腰部"，承载了所有质量保证机制。绕过它 = 绕过所有防护。

### ExecutionGraph 的价值

```
ExecutionGraph = Intent + Registry + Rules + Evidence + Checksum + Lineage
                 ────────────────────────────────────────────────────────
                              可审计的执行计划
```

| 字段 | 价值 | 如果缺失 |
|------|------|---------|
| **lineage** | 追溯来源（intent + registry versions） | 不知道为什么这么做 |
| **checksum** | 完整性验证 | 无法检测篡改 |
| **nodes + edges** | 拓扑结构（Gate H 验证） | 可能有环、死节点 |
| **evidence_refs** | 决策依据 | 无法审计合理性 |
| **swimlanes** | 责任映射 | 不知道谁负责 |

### 强制机制

1. **类型约束**:
   ```python
   class CommandExecutor:
       def execute(self, graph: ExecutionGraph) -> ExecutionReport:
           """Only accepts ExecutionGraph"""
           if not isinstance(graph, ExecutionGraph):
               raise TypeError("Must provide ExecutionGraph")
           # ...
   ```

2. **Schema 验证**:
   ```python
   # Gate 前置检查
   def execute(self, graph: ExecutionGraph):
       # 必须通过 schema 验证
       validate_schema(graph, "execution_graph.schema.json")
       # 必须通过 Gate H（拓扑验证）
       if not run_gate_h(graph):
           raise ValueError("Graph failed topology check")
       # 才能执行
   ```

3. **代码审查清单**:
   - [ ] Executor.execute() 只接受 ExecutionGraph？
   - [ ] 没有 run_commands() / run_script() 等快捷方法？
   - [ ] 所有执行都有 lineage 追溯？

### 违规示例（禁止）

```python
# ❌ 反例 1: 直接命令列表
class CommandExecutor:
    def run_commands(self, commands: list):
        # 禁止！缺失 lineage、checksum、evidence
        for cmd in commands:
            self._execute_command(cmd)

# ❌ 反例 2: 临时脚本
class QuickFixer:
    def apply_patch(self, script: str):
        # 禁止！绕过所有 Gates
        os.system(script)

# ❌ 反例 3: 快捷路径
class Coordinator:
    def quick_mode(self, intent):
        # 禁止！跳过 graph 构建
        commands = self._extract_commands(intent)
        executor.run_commands(commands)  # 错误！

# ❌ 反例 4: 多入口
class CommandExecutor:
    def execute(self, graph: ExecutionGraph):
        # ✅ 正确入口
        pass
    
    def execute_dict(self, data: dict):
        # ❌ 禁止！应该先转成 ExecutionGraph
        pass
    
    def execute_yaml(self, yaml_str: str):
        # ❌ 禁止！多入口破坏契约
        pass
```

### 正确示例

```python
# ✅ 正确：唯一入口
class CommandExecutor:
    """Executor only accepts ExecutionGraph"""
    
    def execute(self, graph: ExecutionGraph) -> ExecutionReport:
        """The ONLY entry point"""
        # 1. 验证 graph schema
        self._validate_graph(graph)
        
        # 2. 检查 lineage
        if not graph.lineage:
            raise ValueError("Graph missing lineage")
        
        # 3. 验证 checksum
        if not self._verify_checksum(graph):
            raise ValueError("Graph checksum mismatch")
        
        # 4. 执行
        result = self._execute_graph_nodes(graph)
        
        # 5. 返回报告（也有 lineage）
        return ExecutionReport(
            graph_id=graph.graph_id,
            result=result,
            lineage={"derived_from_graph": graph.checksum}
        )

# ✅ 如果需要从其他格式转换
def convert_to_graph(data: dict) -> ExecutionGraph:
    """独立的转换函数，不在 Executor 内部"""
    # 转换 + 补全 lineage + 计算 checksum
    graph = ExecutionGraph.from_dict(data)
    graph.lineage = {"source": "manual_conversion"}
    graph.checksum = calculate_checksum(graph)
    return graph

# ✅ 使用
data = {"nodes": [...], "edges": [...]}
graph = convert_to_graph(data)  # 先转换
result = executor.execute(graph)  # 再执行
```

---

## Future Red Lines 执行策略

### 阶段1：预防性文档（现在完成）

✅ **已完成**:
- 在 RED_LINE_ENFORCEMENT.md 添加 X1-X3
- 创建 FUTURE_RED_LINES.md 详细说明
- 更新 RESPONSIBILITIES.md 反模式

### 阶段2：代码审查强制（下次 PR 开始）

**检查清单**:
- [ ] X1: 无 `import executor` 在 coordinator 模块
- [ ] X2: ModelRouter 无 adjudication 方法
- [ ] X3: Executor.execute() 只接受 ExecutionGraph

### 阶段3：Gate 扩展（v0.9.3）

**新 Gates**:
- **Gate X1**: 依赖检查（coordinator 不依赖 executor）
- **Gate X2**: 接口检查（ModelRouter 方法命名规范）
- **Gate X3**: 类型检查（Executor 接口强制 ExecutionGraph）

### 阶段4：架构测试（持续）

**集成测试**:
```python
def test_coordinator_executor_isolation():
    """测试 Coordinator 和 Executor 零依赖"""
    import agentos.core.coordinator as coordinator
    import agentos.core.executor as executor
    
    # Coordinator 不应导入 Executor
    assert "executor" not in dir(coordinator)

def test_executor_single_entry():
    """测试 Executor 只有一个入口"""
    executor = CommandExecutor()
    
    # 只应有 execute(ExecutionGraph) 方法
    assert hasattr(executor, "execute")
    assert not hasattr(executor, "run_commands")
    assert not hasattr(executor, "run_script")
```

---

## 违规响应协议

### 如果发现 X1 违规

**检测**: `import executor` 出现在 `agentos/core/coordinator/`

**响应**:
1. 🛑 **立即停止** - 不要合并
2. 识别为什么需要调用 executor（测试？验证？模拟？）
3. 重构为正确架构：
   - 测试 → 使用 mock ExecutionGraph，不调用真 executor
   - 验证 → 通过 schema/gates，不 dry-run executor
   - 模拟 → 在 GraphBuilder 做，不调用 executor
4. 重新提交

### 如果发现 X2 违规

**检测**: ModelRouter 有 `decide/approve/adjudicate` 方法

**响应**:
1. 🛑 **立即停止** - 不要合并
2. 将裁决逻辑移至 RulesAdjudicator
3. ModelRouter 只保留 `select_model()` 类方法
4. 确保 Audit Log 区分"建议"和"裁决"
5. 重新提交

### 如果发现 X3 违规

**检测**: Executor 有多入口或接受非 ExecutionGraph 参数

**响应**:
1. 🛑 **立即停止** - 不要合并
2. 移除所有快捷方法（run_commands/run_script等）
3. 如需转换，创建独立的 `convert_to_graph()` 函数
4. 确保 ExecutionGraph 有完整 lineage + checksum
5. 运行 Gate H（拓扑验证）
6. 重新提交

---

## 总结

| Red Line | 一句话描述 | 强制时机 |
|----------|-----------|---------|
| **X1** | Coordinator 永不调 Executor | 代码审查 + Gate X1 |
| **X2** | ModelRouter 只建议不裁决 | 接口设计 + Audit Log |
| **X3** | ExecutionGraph 是唯一入口 | 类型检查 + Gate X3 |

**为什么现在就要明确？**

因为**架构违规比 bug 更难修复**。一旦形成依赖路径，重构成本是指数级的。

**Future Red Lines 的价值**:
- 🛡️ 预防胜于治疗
- 📋 清晰的边界文档
- 🚫 团队共识的红线
- ⚖️ 代码审查的依据

---

**状态**: 🔴 **CRITICAL - Must Enforce from v0.9.2+**  
**维护**: AgentOS Architecture Team  
**最后更新**: 2026-01-25
