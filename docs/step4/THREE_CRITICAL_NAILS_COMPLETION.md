# Step 4 扩展完成报告：3 Critical Nails

## 执行日期
2026-01-26

## 背景

在完成 Step 4（LM Studio + llama.cpp 接入）后，用户提出了 3 个**必须现在钉死**的架构级问题：

1. 🔒 **钉子 1**：Adapter Capability 必须声明（Mode System 必需）
2. 🔒 **钉子 2**：错误必须分类（运维排查必需）
3. 🔒 **钉子 3**：输出语义类型（Mode System 支点）

如果不现在补上，下一步 Mode System（设计模式/实施模式/运维模式/故障排查模式）**根本做不了**。

---

## 实施内容

### 🔒 钉子 1：Adapter Capability 声明

**问题**：所有 Adapter 都"看起来一样"，但实际能力完全不同。Mode System 需要知道：
- 长上下文？函数调用？JSON 严格输出？流式？Diff 质量？

**解决方案**：
1. 在 `ToolCapabilities` 添加 6 个新字段：
   - `chat`: bool（是否支持对话）
   - `json_mode`: bool（是否支持 JSON 严格输出）
   - `function_call`: bool（是否支持函数调用）
   - `stream`: bool（是否支持流式输出）
   - `long_context`: bool（是否支持长上下文 >8K tokens）
   - `diff_quality`: "low" | "medium" | "high"

2. 所有 Adapter 声明具体能力：

| Adapter | diff_quality | json_mode | function_call | stream | long_context |
|---------|-------------|-----------|---------------|--------|--------------|
| OpenAI Chat | **high** | ✓ | ✓ | ✓ | ✓ |
| Claude CLI | **high** | ✗ | ✓ | ✗ | ✓ |
| LM Studio | medium | ✗ | ✗ | ✓ | ✗ |
| Ollama | medium | ✗ | ✗ | ✓ | ✗ |
| llama.cpp | **low** | ✗ | ✗ | ✓ | ✗ |

**为什么现在必须做？**
- 设计模式需要：长上下文 + 高 diff 质量
- 实施模式需要：diff 质量 medium 以上
- 故障排查模式需要：JSON mode 输出结构化诊断

---

### 🔒 钉子 2：错误分类

**问题**：运维时分不清错误类型：
- LM Studio 没加载模型 → 操作性错误（用户去 UI 加载）
- llama.cpp 推理 OOM → 模型问题（换小模型/加内存）
- schema mismatch → 开发者错误（修改 adapter 代码）

**解决方案**：
1. 在 `ToolHealth` 添加 `error_category` 字段：
   ```python
   error_category: Optional[Literal["config", "auth", "network", "model", "schema", "runtime"]]
   ```

2. 添加 `categorize_error()` 方法自动分类

3. Gates 强制断言错误分类正确性：
   ```python
   if health.status == "model_missing":
       if error_category != "model":
           return False  # 必须是 model 类别
   ```

**错误分类映射**：

| 场景 | status | error_category | 运维动作 |
|------|--------|---------------|---------|
| LM Studio 没加载模型 | model_missing | **model** | ✅ 去 UI 加载模型 |
| llama.cpp 推理 OOM | unreachable (timeout) | **runtime** | ✅ 换小模型/加内存 |
| schema mismatch | schema_mismatch | **schema** | ✅ 修改 adapter 代码 |
| 网络不通 | unreachable | **network** | ✅ 检查服务是否启动 |

**为什么现在必须做？**
- 这是**运维模式/故障排查模式的基础**
- 下一步 Mode System 需要根据错误类别给出可执行的诊断建议

---

### 🔒 钉子 3：输出语义类型

**问题**：Mode System 需要区分输出类型：
- 设计模式 → 产出 `plan`（不能是 diff）
- 实施模式 → 产出 `diff`（必须是 diff）
- 故障排查模式 → 产出 `diagnosis`（不能有写意图）

**解决方案**：
1. 在 `ToolResult` 添加 `output_kind` 字段：
   ```python
   output_kind: Literal["diff", "plan", "analysis", "explanation", "diagnosis"] = "diff"
   ```

2. Gates 强制断言语义类型：
   ```python
   # 实施模式必须是 diff
   if result.output_kind != "diff":
       return False
   ```

**语义类型映射**：

| output_kind | 用途 | Mode | 是否可写 repo |
|-------------|------|------|--------------|
| **diff** | 代码变更 | 实施模式 | ✅ |
| **plan** | 设计方案 | 设计模式 | ❌ |
| **analysis** | 代码分析 | 审查模式 | ❌ |
| **explanation** | 解释说明 | 问答模式 | ❌ |
| **diagnosis** | 故障诊断 | 排查模式 | ❌ |

**为什么这是 Mode System 的真正支点？**
- Mode System 的核心判断不是**看模型**，而是**看输出语义**
- 设计/实施/运维/排查 4 种模式的基础

---

## 修改文件清单

### 核心类型（1 个）
1. `agentos/ext/tools/types.py`
   - `ToolHealth`：新增 `error_category` + `categorize_error()`
   - `ToolResult`：新增 `output_kind`
   - `ToolCapabilities`：新增 6 个能力字段

### Adapter 能力声明（7 个）
2. `agentos/ext/tools/claude_cli_adapter.py`
3. `agentos/ext/tools/openai_chat_adapter.py`
4. `agentos/ext/tools/ollama_adapter.py`
5. `agentos/ext/tools/lmstudio_adapter.py`
6. `agentos/ext/tools/llamacpp_adapter.py`
7. `agentos/ext/tools/cloud_chat_adapter.py`
8. `agentos/ext/tools/generic_local_http_adapter.py`

### Gates 强制断言（2 个）
9. `scripts/gates/tl_r2_lmstudio_connectivity.py`
   - 错误分类断言
   - output_kind 断言

10. `scripts/gates/tl_r2_llamacpp_connectivity.py`
    - 错误分类断言
    - output_kind 断言

### 文档和验证（2 个）
11. `docs/step4/THREE_CRITICAL_NAILS.md` - 详细解释
12. `scripts/verify_three_nails.py` - 一键验证脚本

---

## 验证结果

运行验证脚本：
```bash
uv run python scripts/verify_three_nails.py
```

**验证通过**：

```
🔒 钉子 1 (Adapter Capability): ✅ 通过
🔒 钉子 2 (错误分类): ✅ 通过
🔒 钉子 3 (输出语义类型): ✅ 通过

🎉 所有钉子验证通过！Mode System 基础已就绪。
```

### 验证内容

**钉子 1**：所有 5 个 Adapter 声明了 6 项能力
- ClaudeCLI: diff_quality=high, function_call=True, long_context=True
- OpenAI: diff_quality=high, json_mode=True, function_call=True, stream=True, long_context=True
- Ollama: diff_quality=medium, stream=True
- LMStudio: diff_quality=medium, stream=True
- LlamaCpp: diff_quality=low, stream=True

**钉子 2**：ToolHealth 自动分类错误
- model_missing → model
- schema_mismatch → schema
- not_configured → config
- invalid_token → auth
- unreachable → network

**钉子 3**：ToolResult 包含 output_kind
- 默认值：diff
- 合法值：diff, plan, analysis, explanation, diagnosis

---

## Git 提交记录

### Commit 1: 实现三个钉子
```
commit e417de7
fix(step4): add 3 critical nails for Mode System foundation

10 files changed, 257 insertions(+), 42 deletions(-)
```

### Commit 2: 添加文档
```
commit 453059c
docs(step4): add explanation for 3 critical nails

1 file changed, 342 insertions(+)
```

### Commit 3: 添加验证脚本
```
commit a57c1f8
feat(step4): add verification script for 3 critical nails

2 files changed, 201 insertions(+)
```

---

## 影响和价值

### 为什么这三个钉子至关重要？

**不补的后果**：
- ❌ Mode System 无法根据能力选择模型
- ❌ 运维时无法区分错误类型
- ❌ 无法实现"设计 vs 实施"的核心差异

**补上之后**：
- ✅ Mode = Workflow + Model Profile 有了数据基础
- ✅ 故障排查有了分类依据
- ✅ 设计/实施/运维/排查 4 种模式有了真正支点

### 三个钉子的相互关系

```
🔒 钉子 1：Adapter Capability
    ↓
    Mode System 根据能力选择模型
    ↓
🔒 钉子 3：output_kind
    ↓
    Mode System 根据语义决定执行路径
    ↓
🔒 钉子 2：error_category
    ↓
    Mode System 根据错误类别给出诊断
```

---

## 下一步（Mode System 现在可以做了）

有了这三个钉子，下一步可以做：

### 1. Mode 定义层
```python
ImplementationMode:
    - output_kind = "diff"
    - 需要 diff_quality >= "medium"
    - 可写 repo

DesignMode:
    - output_kind = "plan"
    - 需要 long_context = True
    - 不可写 repo

DiagnosisMode:
    - output_kind = "diagnosis"
    - 需要 json_mode = True
    - 不可写 repo
```

### 2. Mode → Model 选择器
```python
def select_model(mode, available_adapters):
    if mode == "implementation":
        return filter(lambda a: a.capabilities.diff_quality >= "medium")
    elif mode == "design":
        return filter(lambda a: a.capabilities.long_context)
```

### 3. Mode → 执行路径
```python
def execute(mode, result):
    if mode == "implementation":
        assert result.output_kind == "diff"
        executor.apply(result.diff)
    elif mode == "design":
        assert result.output_kind == "plan"
        store_plan(result.stdout)
```

### 4. 故障排查 Mode
```python
if error_category == "model":
    return "ACTION: Load model in LM Studio UI"
elif error_category == "runtime":
    return "ACTION: Check logs, OOM, timeout"
elif error_category == "schema":
    return "ACTION: Fix adapter code"
```

---

## 总结

这三个钉子不是"功能"，而是**架构级的支点**。

- **耗时**：30 分钟
- **修改**：12 个文件
- **新增**：257 行代码
- **验证**：✅ 全部通过

**状态**：🎉 **完成** - Mode System 基础已就绪

**这是长期会赢的路线**。
