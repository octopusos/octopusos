# Dry Executor Red Lines (DE1-DE6)

## 概述

Dry Executor 严格执行 6 条红线（DE1-DE6），确保"伪执行"的承诺：不执行、不改文件、不编造数据。

所有红线在以下三个层级强制执行：
1. **Schema Level**: Schema 定义中的约束
2. **Runtime Level**: 代码中的检查和验证
3. **Static Level**: Gates 的静态扫描

## DE1: 禁止执行

### 定义
Dry Executor 绝对禁止任何形式的代码执行、命令运行或外部调用。

### 禁止的操作
- `subprocess.call()`, `subprocess.run()`, `subprocess.Popen()`
- `os.system()`
- `exec()`
- `eval()`
- HTTP 请求（如果涉及执行远程代码）
- 任何会触发实际操作的 API 调用

### 允许的操作
- 读取文件（只读，用于加载 intent/配置）
- 写入输出文件（产物，如 `dryexec_xxx.json`）
- 数据结构操作（纯内存）
- JSON 序列化/反序列化

### 执行层级

#### Schema Level
```json
{
  "metadata": {
    "execution_mode": {
      "const": "dry_run"  // 只能是 dry_run
    },
    "constraints_enforced": {
      "contains": {"const": "DE1_no_exec"}
    }
  }
}
```

#### Runtime Level
在 `utils.py` 中：
```python
def enforce_red_lines(result_data):
    violations = []
    
    # Check for execution-related fields
    metadata = result_data.get("metadata", {})
    forbidden_fields = ["execute_commands", "subprocess_calls", "system_calls"]
    
    for field in forbidden_fields:
        if field in metadata:
            violations.append(f"DE1 violation: Contains forbidden field '{field}'")
    
    return violations
```

#### Static Level
**Gate D**: 扫描 `agentos/core/executor_dry/` 目录：
```bash
# 禁止出现
grep -r "subprocess\.(call|run|Popen)" agentos/core/executor_dry/
grep -r "os\.system(" agentos/core/executor_dry/
grep -r "exec\(" agentos/core/executor_dry/
grep -r "eval\(" agentos/core/executor_dry/
```

### 违反示例
❌ **错误**:
```python
# 在 dry_executor.py 中
subprocess.run(["git", "status"])  # 绝对禁止！
```

✅ **正确**:
```python
# 在 dry_executor.py 中
# 只生成计划，不执行
audit_log.append({
    "decision": "Plan to run 'git status'",
    "rationale": "Checking repository state"
})
```

## DE2: 禁止写项目文件

### 定义
Dry Executor 不得修改项目代码文件，只能写入输出产物目录。

### 禁止的写入
- 任何 `agentos/` 目录下的代码文件
- 任何 `tests/` 目录下的测试文件
- 项目配置文件（如 `.gitignore`, `pyproject.toml`）

### 允许的写入
- 输出目录中的产物文件（如 `outputs/dry/dryexec_xxx.json`）
- 临时日志文件（如需要）
- 快照文件（如 `tests/snapshots/v10_dry_executor_explain.json`，由 Gate F 生成）

### 执行层级

#### Schema Level
```json
{
  "constraints": {
    "no_fs_write": {
      "const": true
    }
  }
}
```

#### Runtime Level
在 CLI (`dry_executor.py`) 中：
```python
@click.option("--out", required=True, type=click.Path())
def plan_cmd(intent, out):
    # 只写到 --out 指定的目录
    out_path = Path(out)
    result_file = out_path / f"{result['result_id']}.json"
    
    # 验证不在项目代码目录内
    if "agentos/" in str(result_file) or "tests/" in str(result_file):
        raise ValueError("Cannot write to project code directories")
    
    with open(result_file, "w") as f:
        json.dump(result, f)
```

#### Static Level
**Gate D**: 扫描文件写入操作（如果写到非 outputs 目录则拒绝）

### 违反示例
❌ **错误**:
```python
# 直接修改代码文件
with open("agentos/api/routes.py", "w") as f:
    f.write("new code")  # 绝对禁止！
```

✅ **正确**:
```python
# 只在 PatchPlan 中记录计划
patch_plan["files"].append({
    "path": "agentos/api/routes.py",
    "action": "modify",
    "rationale": "Add notification endpoint"
})
```

## DE3: 禁止编造路径

### 定义
所有文件路径必须来自 intent 或证据，不得凭空编造不存在的路径。

### 允许的路径来源
1. `intent.scope.targets.files[]`: Intent 中明确指定的文件
2. `intent.evidence_refs[]`: Intent 级别的证据引用
3. `planned_commands[].evidence_refs[]`: 命令级别的证据引用
4. 显式的 `scan://file/` 引用

### 禁止的路径来源
- LLM 推断的路径（除非有证据支持）
- 假设的路径（如 "应该有个 config.py"）
- 模式匹配生成的路径（如 `glob("**/*.py")`）

### 执行层级

#### Schema Level
```json
{
  "constraints": {
    "no_fabrication": {
      "const": true
    }
  }
}
```

#### Runtime Level
在 `patch_planner.py` 中：
```python
from .utils import validate_path_in_intent

def _plan_file_change(self, file_path):
    # 验证路径在 intent 中（DE3）
    if not validate_path_in_intent(file_path, self.intent):
        self.unknowns.append({
            "type": "missing_path",
            "description": f"Path '{file_path}' not found in intent",
            "reason": "Path not in scope.targets.files or evidence_refs",
            "needed_evidence": f"Explicit mention of {file_path}"
        })
        return  # 不添加到 files[] 列表
    
    # 只有验证通过才添加
    self.files.append({...})
```

#### Static Level
**Gate C**: 验证 invalid fixtures 中的编造路径被正确拒绝

### 违反示例
❌ **错误**:
```python
# 编造一个不在 intent 中的路径
patch_plan["files"].append({
    "path": "/totally/made/up/path.py",  # Intent 中没有！
    "action": "modify"
})
```

✅ **正确**:
```python
# 检查路径
for file_path in intent["scope"]["targets"]["files"]:
    if validate_path_in_intent(file_path, intent):
        patch_plan["files"].append({
            "path": file_path,
            "action": "modify"
        })
    else:
        # 放到 unknowns
        patch_plan["unknowns"].append({
            "type": "missing_path",
            "description": f"Cannot validate {file_path}"
        })
```

## DE4: 所有节点必须有 evidence_refs

### 定义
ExecutionGraph 中所有节点（尤其是 action_plan 和 decision_point）必须有 evidence_refs。

### 必需 evidence_refs 的节点
- `action_plan`: 必须（每个操作必须有依据）
- `decision_point`: 必须（决策必须有规则/证据支持）
- `review_checkpoint`: 推荐
- `phase`: 推荐

### 执行层级

#### Schema Level
```json
{
  "nodes": {
    "items": {
      "required": ["node_id", "node_type", "label", "evidence_refs"],
      "properties": {
        "evidence_refs": {
          "type": "array",
          "minItems": 1  // 至少一个证据
        }
      }
    }
  }
}
```

#### Runtime Level
在 `utils.py` 的 `enforce_red_lines()` 中：
```python
# DE4: All nodes must have evidence_refs
graph = result_data.get("graph", {})
for node in graph.get("nodes", []):
    if not node.get("evidence_refs"):
        violations.append(
            f"DE4 violation: Node {node.get('node_id')} missing evidence_refs"
        )
```

#### Static Level
**Gate B**: Schema 验证会捕获缺失 evidence_refs 的节点
**Gate C**: 验证 invalid fixtures 被拒绝

### 违反示例
❌ **错误**:
```json
{
  "node_id": "node_001",
  "node_type": "action_plan",
  "label": "Deploy to production"
  // 缺少 evidence_refs！
}
```

✅ **正确**:
```json
{
  "node_id": "node_001",
  "node_type": "action_plan",
  "label": "Deploy to production",
  "evidence_refs": [
    "intent://intent_id/planned_commands/deploy_production",
    "design://deployment_strategy"
  ]
}
```

## DE5: 高/关键风险必须有 requires_review

### 定义
当 `review_pack_stub.risk_summary.dominant_risk` 为 `high` 或 `critical` 时，必须有非空的 `requires_review[]` 数组。

### 执行层级

#### Schema Level
```json
{
  "allOf": [
    {
      "if": {
        "properties": {
          "review_pack_stub": {
            "properties": {
              "risk_summary": {
                "properties": {
                  "dominant_risk": {"enum": ["high", "critical"]}
                }
              }
            }
          }
        }
      },
      "then": {
        "properties": {
          "review_pack_stub": {
            "properties": {
              "requires_review": {"minItems": 1}
            }
          }
        }
      }
    }
  ]
}
```

#### Runtime Level
在 `utils.py` 的 `enforce_red_lines()` 中：
```python
# DE5: High/critical risk must have requires_review
review_stub = result_data.get("review_pack_stub", {})
risk_summary = review_stub.get("risk_summary", {})
dominant_risk = risk_summary.get("dominant_risk")
requires_review = review_stub.get("requires_review", [])

if dominant_risk in ["high", "critical"] and not requires_review:
    violations.append(
        f"DE5 violation: {dominant_risk} risk without requires_review"
    )
```

#### Static Level
**Gate C**: 验证 `high_risk_no_review.json` fixture 被正确拒绝

### 违反示例
❌ **错误**:
```json
{
  "review_pack_stub": {
    "risk_summary": {
      "dominant_risk": "high",
      "risk_factors": ["Production database change"]
    },
    "requires_review": []  // 空的！违反 DE5
  }
}
```

✅ **正确**:
```json
{
  "review_pack_stub": {
    "risk_summary": {
      "dominant_risk": "high",
      "risk_factors": ["Production database change"]
    },
    "requires_review": ["security", "data", "release"]  // 必须非空
  }
}
```

## DE6: 输出必须可冻结

### 定义
DryExecutionResult 必须包含 checksum、lineage，并且 explain 输出稳定。

### 可冻结的三要素

#### 1. Checksum
- SHA-256 哈希
- 覆盖关键字段（排除 checksum 本身和 timestamps）
- 必须可验证（stored == computed）

#### 2. Lineage
- 记录来源（intent/coordinator/registry）
- 包含版本信息
- 支持追溯

#### 3. Stable Explain
- explain 输出的结构必须稳定
- 用于快照测试（Gate F）
- 字段顺序、必需字段一致

### 执行层级

#### Schema Level
```json
{
  "required": ["checksum", "lineage"],
  "properties": {
    "checksum": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$"
    },
    "lineage": {
      "type": "object",
      "required": ["derived_from", "generation_context"]
    }
  }
}
```

#### Runtime Level
在 `dry_executor.py` 中：
```python
# Compute checksum
result_data["checksum"] = compute_checksum(result_data)

# Include lineage
result_data["lineage"] = {
    "derived_from": [
        {
            "type": "intent",
            "id": intent["id"],
            "checksum": intent["audit"]["checksum"]
        }
    ],
    "generation_context": {
        "environment": "dry_executor_v0.10"
    }
}
```

#### Static Level
**Gate F**: 验证 explain 输出结构稳定

### 违反示例
❌ **错误**:
```json
{
  "result_id": "dryexec_xxx",
  // 缺少 checksum！
  // 缺少 lineage！
  "metadata": {}
}
```

✅ **正确**:
```json
{
  "result_id": "dryexec_xxx",
  "checksum": "a1b2c3...",  // 64字符 SHA-256
  "lineage": {
    "derived_from": [
      {"type": "intent", "id": "intent_xxx", "checksum": "..."}
    ],
    "generation_context": {...}
  }
}
```

## 红线执行总结

| 红线 | Schema | Runtime | Static | 示例 Fixture |
|-----|--------|---------|--------|-------------|
| DE1 | ✅ execution_mode | ✅ 字段检查 | ✅ Gate D | result_contains_execution_field.json |
| DE2 | ✅ no_fs_write | ✅ 路径检查 | ✅ Gate D | （隐式） |
| DE3 | ✅ no_fabrication | ✅ validate_path_in_intent | ✅ Gate C | patch_plan_fabricated_paths.json |
| DE4 | ✅ evidence_refs required | ✅ enforce_red_lines | ✅ Gate B/C | missing_evidence_refs.json |
| DE5 | ✅ allOf constraint | ✅ enforce_red_lines | ✅ Gate C | high_risk_no_review.json |
| DE6 | ✅ checksum/lineage required | ✅ compute_checksum | ✅ Gate F | missing_checksum_lineage.json |

## 相关文档

- [README.md](README.md): Dry Executor 概述
- [AUTHORING_GUIDE.md](AUTHORING_GUIDE.md): 使用指南
- [V10_FREEZE_CHECKLIST_REPORT.md](V10_FREEZE_CHECKLIST_REPORT.md): 冻结验收
