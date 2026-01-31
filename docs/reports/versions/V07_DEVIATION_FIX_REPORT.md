# AgentOS v0.7 实施偏差修正报告

## 偏差识别与修正

根据 v0.7 定版方案审查，发现并修正了以下 3 个偏差：

---

## ⚠️ 偏差 #1：Schema 过度约束 ✅ 已修正

### 问题描述
初始实现将 5 条红线的约束过度编码到 JSON Schema 中：
- ❌ `execution` 强制为 `enum: ["forbidden"]`
- ❌ `command_ownership` 强制为 `enum: ["forbidden"]`
- ❌ `allowed_interactions` 强制为 `maxItems: 1, enum: ["question"]`
- ❌ `responsibilities` 强制为 `maxItems: 5`

### 为什么这是问题
1. **锁死未来版本**：v0.8/v0.9 可能允许不同的值（如 `execution: "allowed"`）
2. **Schema 职责越界**：Schema 应该只保证结构合法，不应该承载版本特定的语义约束
3. **违反最小化原则**：v0.6 的 `workflow.schema.json` 是最小化的，v0.7 应该保持一致

### 修正方案
**修改文件**：`agentos/schemas/content/agent.schema.json`

**修正内容**：
```json
// 之前（过度约束）
"execution": {
  "type": "string",
  "description": "🚨 RED LINE #1: Execution constraint (must be forbidden for v0.7)",
  "enum": ["forbidden"]
}

// 之后（最小化）
"execution": {
  "type": "string",
  "description": "Execution constraint"
}
```

同理修正了：
- `command_ownership`: 移除 `enum: ["forbidden"]`
- `allowed_interactions`: 移除 `maxItems: 1` 和 `enum: ["question"]`
- `responsibilities`: 移除 `maxItems: 5`

### 验证
- ✅ Schema 现在只验证结构（字段存在、类型正确）
- ✅ 红线约束移至 `AgentRedlineValidator`（gate helper）
- ✅ 未来 v0.8 可以独立演化约束逻辑，无需改 schema

---

## ⚠️ 偏差 #2：文件命名和职责边界 ✅ 已修正

### 问题描述
初始实现的命名和定位容易引起误解：
- ❌ 文件名：`agent_redlines.py`（听起来像 enforcer）
- ❌ 类名：`AgentRedlineEnforcer`（enforcer 暗示运行时执行）
- ❌ 方法名：`enforce()`（enforce 暗示强制执行）
- ❌ 文档：说"runtime validation"

### 为什么这是问题
1. **混淆职责**：看起来像运行时权限系统，实际是注册前校验
2. **多入口风险**：可能导致 ContentRegistry 之外的另一个权限系统
3. **审计复杂化**：红线 enforcement 入口不唯一

### 修正方案

**文件重命名**：
- `agentos/core/gates/agent_redlines.py` → `validate_agent_redlines.py`
- `tests/gates/test_agent_redlines.py` → `test_validate_agent_redlines.py`

**类和方法重命名**：
- `AgentRedlineEnforcer` → `AgentRedlineValidator`
- `enforce()` → `validate()`

**文档修正**：
```python
"""Agent Red Line Validator - Gate helper for v0.7 Agent constraints.

🎯 PURPOSE: Pre-registration validation, NOT runtime enforcement.

This module is a **gate helper** that validates agent specifications BEFORE
they are registered to ContentRegistry. It is NOT a runtime enforcer.

🚨 RED LINE ENFORCEMENT ENTRY POINTS:
1. ContentRegistry.register() - validates during registration
2. scripts/register_agents.py - validates before batch registration  
3. CI/local gates - validates in development

This validator is called by the above entry points, NOT used directly at runtime.
"""
```

### 验证
- ✅ 文件名和类名明确表示"validator"（校验器），不是"enforcer"（执行器）
- ✅ 文档明确说明是"gate helper"，不是"runtime enforcer"
- ✅ 注释明确列出 3 个合法的调用入口

---

## ⚠️ 偏差 #3：PyYAML 依赖 ✅ 已确认无问题

### 问题描述
用户担心 PyYAML 依赖未在 `pyproject.toml` 中声明。

### 验证结果
**文件**：`pyproject.toml`  
**行 16**：`"pyyaml>=6.0"`

✅ **PyYAML 已在依赖中**，无需修正。

---

## 修正后的红线职责分工

### Schema（最小化）
```json
{
  "constraints": {
    "required": ["execution", "command_ownership"],
    "properties": {
      "execution": {"type": "string"},
      "command_ownership": {"type": "string"}
    }
  }
}
```
- ✅ 只保证字段存在
- ✅ 只保证类型正确
- ❌ 不锁定具体值（不用 enum）

### AgentRedlineValidator（语义校验）
```python
class AgentRedlineValidator:
    def validate_no_execution(self, agent_spec):
        # v0.7: 要求 execution = "forbidden"
        # v0.8: 可能改为允许 "allowed_with_approval"
        # Schema 不变，只改这里
        ...
    
    def validate_no_commands(self, agent_spec):
        # 检查 commands 字段不存在
        # Schema 无法表达"字段不存在"，必须在这里检查
        ...
    
    def validate_organizational_model(self, agent_spec):
        # 检查 agent ID 不包含 "gpt", "model" 等关键词
        # Schema 无法表达"字符串不包含特定子串"
        ...
```

### 调用入口（唯一化）
1. **ContentRegistry.register()** - 注册时验证
2. **scripts/register_agents.py** - 批量注册前验证
3. **CI Gates** - 开发时验证

**禁止**：
- ❌ 运行时调用 validator（不是 runtime enforcer）
- ❌ 在 ContentRegistry 之外创建另一个权限系统

---

## 修正后的文件清单

### 修改的文件（4 个）

1. **agentos/schemas/content/agent.schema.json**
   - 移除 `enum` 约束（execution, command_ownership）
   - 移除 `maxItems` 约束（allowed_interactions, responsibilities）
   - 保持最小化验证（结构 + 类型）

2. **agentos/core/gates/validate_agent_redlines.py**（重命名）
   - 类名：`AgentRedlineEnforcer` → `AgentRedlineValidator`
   - 方法名：`enforce()` → `validate()`
   - 文档：明确定位为"gate helper"，不是"runtime enforcer"

3. **tests/gates/test_validate_agent_redlines.py**（重命名）
   - 导入：`AgentRedlineEnforcer` → `AgentRedlineValidator`
   - fixture：`enforcer` → `validator`
   - 方法调用：`enforce()` → `validate()`

4. **scripts/register_agents.py**
   - 导入：`AgentRedlineEnforcer` → `AgentRedlineValidator`
   - 变量名：`enforcer` → `validator`
   - 方法调用：`enforce()` → `validate()`

### 确认无问题（1 个）

5. **pyproject.toml**
   - ✅ `pyyaml>=6.0` 已存在于依赖中

---

## 验收标准（修正后）

### Schema 验收 ✅
- [x] Schema 只验证结构（字段存在、类型正确）
- [x] Schema 不锁定 v0.7 特定值（不用 enum）
- [x] Schema 与 workflow.schema.json 保持一致性（最小化原则）

### Validator 验收 ✅
- [x] 文件名明确表示"validator"（不是"enforcer"）
- [x] 类名明确表示"validator"（不是"enforcer"）
- [x] 文档明确定位为"gate helper"（不是"runtime enforcer"）
- [x] 注释明确列出 3 个合法入口

### 依赖验收 ✅
- [x] PyYAML 在 pyproject.toml 中声明
- [x] `uv sync` 后可以运行 register_agents.py

---

## 影响评估

### 对 v0.7 的影响 ✅ 无
- ✅ 13 个 Agent YAML 无需修改（已经符合最小化 schema）
- ✅ 注册脚本可正常工作（只是方法名从 enforce → validate）
- ✅ 红线仍然被强制执行（只是入口更清晰）

### 对 v0.8 的影响 ✅ 正面
- ✅ Schema 不会锁死 v0.8 的演化（可以独立修改 validator）
- ✅ 职责边界更清晰（避免多权限系统）
- ✅ 命名更准确（validator vs enforcer）

---

## 修正完成时间

**日期**：2026-01-25  
**修正耗时**：~30 分钟  
**修改文件数**：4 个（+ 1 个确认）  
**影响范围**：最小化（无需修改 Agent YAML 定义）

---

## 总结

所有 3 个偏差已修正：
1. ✅ **Schema 最小化** - 移除过度约束，只验证结构
2. ✅ **职责明确化** - 重命名为 validator，明确定位为 gate helper
3. ✅ **依赖确认** - PyYAML 已在依赖中

修正后的 v0.7 实现：
- ✅ 符合定版方案
- ✅ 为 v0.8 留足演化空间
- ✅ 职责边界清晰
- ✅ 命名准确无歧义

**状态**：✅ 偏差已全部修正，v0.7 可以稳定交付
