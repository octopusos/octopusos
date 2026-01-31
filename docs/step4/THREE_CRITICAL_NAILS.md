# 🔒 三个关键钉子：Mode System 基础

## 执行时间
- 开始：2026-01-26
- 完成：2026-01-26
- 耗时：30 分钟

## 为什么这三个钉子至关重要？

在 Step 4 完成 LM Studio + llama.cpp 接入后，你指出了 3 个**必须现在钉死**的架构级问题。

如果不现在补上，下一步 Mode System（设计模式/实施模式/运维模式/故障排查模式）**根本做不了**。

---

## 🔒 钉子 1：Adapter Capability 必须声明

### 问题

所有 Adapter 都"看起来一样"，但实际能力完全不同。

Mode System 需要知道：
- 这个模型能不能长上下文？
- 能不能 JSON 严格输出？
- 能不能函数调用？
- Diff 质量如何？

### 解决方案

在 `ToolCapabilities` 添加 6 个新字段：

```python
@dataclass
class ToolCapabilities:
    # 原有字段
    execution_mode: Literal["cloud", "local"]
    supports_diff: bool
    supports_patch: bool
    supports_health_check: bool
    
    # 🔒 钉子 1：模型能力声明（Mode System 必需）
    chat: bool = True  # 是否支持对话
    json_mode: bool = False  # 是否支持 JSON 严格输出
    function_call: bool = False  # 是否支持函数调用
    stream: bool = False  # 是否支持流式输出
    long_context: bool = False  # 是否支持长上下文（>8K tokens）
    diff_quality: Literal["low", "medium", "high"] = "medium"  # Diff 生成质量
```

### 所有 Adapter 声明能力

| Adapter | diff_quality | json_mode | function_call | stream | long_context |
|---------|-------------|-----------|---------------|--------|--------------|
| OpenAI Chat | **high** | ✓ | ✓ | ✓ | ✓ |
| Claude CLI | **high** | ✗ | ✓ | ✗ | ✓ |
| LM Studio | medium | ✗ | ✗ | ✓ | ✗ |
| Ollama | medium | ✗ | ✗ | ✓ | ✗ |
| llama.cpp | **low** | ✗ | ✗ | ✓ | ✗ |

### 为什么现在必须做？

下一步 Mode System 需要根据能力选择模型：
- **设计模式**：需要长上下文 + 高 diff 质量
- **实施模式**：需要 diff 质量 medium 以上
- **故障排查模式**：需要 JSON mode 输出结构化诊断

---

## 🔒 钉子 2：错误必须分类

### 问题

现在 health 有多种状态，但运维时分不清：
- LM Studio 没加载模型 → 是**操作性错误**（用户去 UI 加载）
- llama.cpp 推理 OOM → 是**模型问题**（换小模型/加内存）
- schema mismatch → 是**开发者错误**（修改 adapter 代码）

### 解决方案

在 `ToolHealth` 添加 `error_category` 字段：

```python
@dataclass
class ToolHealth:
    status: Literal["connected", "not_configured", "invalid_token", "unreachable", "model_missing", "schema_mismatch"]
    details: str
    checked_at: str
    
    # 🔒 钉子 2：错误分类（运维排查必需）
    error_category: Optional[Literal["config", "auth", "network", "model", "schema", "runtime"]] = None
    
    def categorize_error(self) -> str:
        """自动分类错误"""
        if self.status == "model_missing":
            return "model"
        elif self.status == "schema_mismatch":
            return "schema"
        elif self.status == "unreachable":
            return "network"  # 或 runtime（timeout 可能是推理失败）
        # ...
```

### 错误分类映射

| 场景 | status | error_category | 运维动作 |
|------|--------|---------------|---------|
| LM Studio 没加载模型 | model_missing | **model** | ✅ 去 UI 加载模型 |
| llama.cpp 推理 OOM | unreachable (timeout) | **runtime** | ✅ 换小模型/加内存 |
| schema mismatch | schema_mismatch | **schema** | ✅ 修改 adapter 代码 |
| 网络不通 | unreachable | **network** | ✅ 检查服务是否启动 |

### Gates 强制断言

```python
def gate_lmstudio_health(adapter):
    health = adapter.health_check()
    
    if health.status == "model_missing":
        error_category = health.categorize_error()
        
        # 🔒 钉子 2：强制分类正确性
        if error_category != "model":
            return False, f"model_missing must be 'model' category, got '{error_category}'"
        
        return False, f"Model not loaded (category: {error_category}): {health.details} (ACTION: Load model in LM Studio)"
```

### 为什么现在必须做？

这不是 UX，而是**运维模式/故障排查模式的基础**。

下一步 Mode System 需要根据错误类别给出可执行的诊断建议。

---

## 🔒 钉子 3：输出语义类型（最重要）

### 问题

现在 `ToolResult` 只有 `diff` / `text` / `flags`，但接下来 Mode System 需要：

- **设计模式** → 产出 `plan`（不能是 diff）
- **实施模式** → 产出 `diff`（必须是 diff）
- **故障排查模式** → 产出 `diagnosis`（不能有写意图）

### 解决方案

在 `ToolResult` 添加 `output_kind` 字段：

```python
@dataclass
class ToolResult:
    tool: str
    status: Literal["success", "partial_success", "failed", "timeout"]
    diff: str
    # ... 原有字段 ...
    
    # 🔒 钉子 3：输出语义类型（Mode System 支点）
    output_kind: Literal["diff", "plan", "analysis", "explanation", "diagnosis"] = "diff"
```

### 语义类型映射

| output_kind | 用途 | Mode | 是否可写 repo |
|-------------|------|------|--------------|
| **diff** | 代码变更 | 实施模式 | ✅ |
| **plan** | 设计方案 | 设计模式 | ❌ |
| **analysis** | 代码分析 | 审查模式 | ❌ |
| **explanation** | 解释说明 | 问答模式 | ❌ |
| **diagnosis** | 故障诊断 | 排查模式 | ❌ |

### Gates 强制断言

```python
def gate_lmstudio_result_structure(result):
    # 检查 output_kind 是否合法
    allowed_output_kinds = ["diff", "plan", "analysis", "explanation", "diagnosis"]
    if result.output_kind not in allowed_output_kinds:
        return False, f"Invalid output_kind '{result.output_kind}'"
    
    # 🔒 钉子 3：实施模式必须是 diff
    if result.output_kind != "diff":
        return False, f"Implementation mode requires output_kind='diff', got '{result.output_kind}'"
```

### 为什么这是 Mode System 的真正支点？

Mode System 的核心判断不是**看模型**，而是**看输出语义**：

```python
# Mode System 决策逻辑（未来）
if mode == "implementation":
    assert result.output_kind == "diff"
    assert result.wrote_files == False  # Tool 不能直接写
    executor.apply(result.diff)  # 只有 Executor 可写

elif mode == "design":
    assert result.output_kind == "plan"
    assert result.diff == ""  # 设计模式不能产生 diff
    store_plan(result.stdout)

elif mode == "diagnosis":
    assert result.output_kind == "diagnosis"
    assert result.wrote_files == False
    report_issue(result.stdout)
```

---

## 三个钉子的相互关系

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

三个钉子共同构成 Mode System 的**基础设施层**。

---

## 实现内容

### 修改文件（10 个）

1. **types.py** - 扩展 3 个核心类型
   - `ToolHealth` 新增 `error_category` + `categorize_error()`
   - `ToolResult` 新增 `output_kind`
   - `ToolCapabilities` 新增 6 个能力字段

2. **所有 Adapter 声明能力**（7 个文件）
   - `claude_cli_adapter.py` - high diff_quality, function_call, long_context
   - `openai_chat_adapter.py` - high diff_quality, json_mode, function_call, stream, long_context
   - `ollama_adapter.py` - medium diff_quality, stream
   - `lmstudio_adapter.py` - medium diff_quality, stream
   - `llamacpp_adapter.py` - low diff_quality, stream
   - `cloud_chat_adapter.py` - 基类默认值
   - `generic_local_http_adapter.py` - 错误分类

3. **Gates 强制断言**（2 个文件）
   - `tl_r2_lmstudio_connectivity.py` - 错误分类断言 + output_kind 断言
   - `tl_r2_llamacpp_connectivity.py` - 错误分类断言 + output_kind 断言

---

## 验收标准

### ✅ 已完成

**钉子 1：Adapter Capability**
- [x] ToolCapabilities 新增 6 个字段
- [x] 所有 Adapter 声明具体能力
- [x] diff_quality 分为 low/medium/high

**钉子 2：错误分类**
- [x] ToolHealth 新增 error_category
- [x] ToolHealth.categorize_error() 自动分类
- [x] Gates 强制断言错误分类正确性
- [x] 区分 model (操作性) / runtime (推理失败) / schema (开发者错误)

**钉子 3：输出语义类型**
- [x] ToolResult 新增 output_kind
- [x] Gates 断言 output_kind = "diff"（实施模式）
- [x] Gates 断言 output_kind 合法性（5 种类型）

---

## 提交记录

```bash
commit e417de7
fix(step4): add 3 critical nails for Mode System foundation

10 files changed, 257 insertions(+), 42 deletions(-)
```

---

## 下一步（Mode System 现在可以做了）

有了这三个钉子，下一步可以做：

1. **Mode 定义层**
   - `ImplementationMode`: output_kind=diff, 需要 diff_quality >= medium
   - `DesignMode`: output_kind=plan, 需要 long_context=True
   - `DiagnosisMode`: output_kind=diagnosis, 需要 json_mode=True

2. **Mode → Model 选择器**
   ```python
   def select_model(mode, available_adapters):
       if mode == "implementation":
           return filter(lambda a: a.capabilities.diff_quality >= "medium")
       elif mode == "design":
           return filter(lambda a: a.capabilities.long_context)
   ```

3. **Mode → 执行路径**
   ```python
   def execute(mode, result):
       if mode == "implementation":
           assert result.output_kind == "diff"
           executor.apply(result.diff)
       elif mode == "design":
           assert result.output_kind == "plan"
           store_plan(result.stdout)
   ```

4. **故障排查 Mode**
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

如果不现在钉死：
- ❌ Mode System 无法根据能力选择模型
- ❌ 运维时无法区分错误类型
- ❌ 无法实现"设计 vs 实施"的核心差异

现在钉死之后：
- ✅ Mode = Workflow + Model Profile 有了数据基础
- ✅ 故障排查有了分类依据
- ✅ 设计/实施/运维/排查 4 种模式有了真正支点

**这是长期会赢的路线**。
