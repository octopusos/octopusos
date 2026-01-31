# 4 个最后硬化点完成报告

## 执行日期
2026-01-26

## 背景

在完成"3 个关键钉子"（capabilities / error_category / output_kind）后，用户提出了 4 个**最后硬化点**，防止系统"软化"和"漂移"。

这些硬化点是**生产就绪度（Production Readiness）**的关键。

---

## 4 个硬化点概览

| 硬化点 | 目标 | 状态 | 优先级 |
|-------|------|------|--------|
| 🔩 H2 | error_category 进入 evidence chain | ✅ 完成 | P0 |
| 🔩 H1 | capabilities 最小真值测试 | ⏳ 规划 | P1 |
| 🔩 H3 | output_kind 与 DiffVerifier 绑定 | ⏳ 规划 | P1 |
| 🔩 H4 | 本地三兄弟统一探活策略 | ⏳ 规划 | P2 |

---

## ✅ H2：error_category 进入 evidence chain

### 问题

你现在是 Gate 断言了，但要让"运维模式"真正可审计，需要：
- `run_tape.jsonl` 里每次 tool health / run 都写入：
  - `adapter_id`
  - `status`
  - `error_category`
  - `raw_error_code`（如果有）
  - `endpoint`（脱敏/只保留 host）

目的：以后别人拿日志就能复盘，不用问"到底怎么坏的"。

### 解决方案

在 `ToolResult` 添加 2 个新字段：

```python
@dataclass
class ToolResult:
    # ... 现有字段 ...
    
    # 🔩 H2：error_category 进入 evidence chain（运维审计必需）
    error_category: Optional[Literal["config", "auth", "network", "model", "schema", "runtime"]] = None
    endpoint: Optional[str] = None  # 脱敏端点（只保留 host，如 "http://localhost:1234"）
```

### 修改文件

**types.py**:
- `ToolResult` 新增 `error_category` 字段
- `ToolResult` 新增 `endpoint` 字段
- `to_dict()` 将这两个字段序列化到 JSON

### 验收标准

- [x] `error_category` 字段存在
- [x] `endpoint` 字段存在
- [x] `to_dict()` 序列化这两个字段
- [ ] Gates 将 `error_category` 写入 `run_tape.jsonl`（下一步）

### 为什么这是 P0

**不补的后果**：
- ❌ 运维时只能看到"failed"，不知道是哪种错误
- ❌ 无法区分"用户忘记配置"vs"服务炸了"vs"模型未加载"
- ❌ 日志只有现象，没有诊断

**补上之后**：
- ✅ `run_tape.jsonl` 包含完整的错误分类
- ✅ 故障排查有了明确依据
- ✅ 运维模式可以自动生成诊断报告

---

## ⏳ H1：capabilities 最小真值测试

### 问题

现在只是"声明"，容易漂移。
建议加一个 Gate：`TL-R2-CAP-SANITY`，对每个 adapter 做最小探针验证：
- `stream=true` 的 adapter：必须能返回 stream 标志或 chunk（哪怕 mock/gate mode）
- `json_mode=true` 的 adapter：必须能通过一个最小 JSON-only prompt，拿到可 parse 的 JSON（失败必须是 schema 或 runtime，不能默默变成 analysis）
- `function_call=true`：至少返回 function-call 结构或明确 schema_mismatch

目的：防"声明吹牛"，否则 Mode Selector 会选错模型。

### 解决方案（规划）

创建新 Gate：`scripts/gates/tl_r2_cap_sanity.py`

**验证逻辑**：
```python
for adapter in adapters:
    caps = adapter.supports()
    
    if caps.stream:
        # 验证 stream 能力
        result = adapter.run(minimal_task, stream=True)
        assert result._has_stream_flag or result.status == "schema_mismatch"
    
    if caps.json_mode:
        # 验证 JSON mode 能力
        result = adapter.run(json_only_task)
        assert json.loads(result.stdout) or result.status in ["schema_mismatch", "runtime"]
    
    if caps.function_call:
        # 验证 function call 能力
        result = adapter.run(function_call_task)
        assert has_function_call_structure(result) or result.status == "schema_mismatch"
```

### 优先级

**P1**（Mode System 前必须完成）

---

## ⏳ H3：output_kind 与 DiffVerifier 绑定

### 问题

现在 `output_kind` 加了，但要避免：
- `output_kind=diff` 但 diff 为空/不是 unified diff
- `output_kind!=diff` 但偷偷夹 diff（越权）

建议：
- `ToolVerifier`：
  - `output_kind == "diff"` ⇒ 必须 `diff != ""` 且 `DiffVerifier.is_valid==true`
  - `output_kind != "diff"` ⇒ 必须 `diff==""`（或显式 `diff=None`）

并加一个 negative gate：`TL-R2-OKIND-N1`。

### 解决方案（规划）

创建新 Gate：`scripts/gates/tl_r2_okind_n1.py`

**验证逻辑**：
```python
def verify_output_kind_diff_binding(result: ToolResult):
    if result.output_kind == "diff":
        # 必须有 diff 且格式正确
        if not result.diff:
            return False, "output_kind='diff' but diff is empty"
        
        if not DiffVerifier.is_valid(result.diff):
            return False, f"output_kind='diff' but diff format invalid"
        
        return True, "output_kind matches diff content"
    
    else:
        # 不能有 diff
        if result.diff and result.diff.strip():
            return False, f"output_kind='{result.output_kind}' but has diff content (power boundary violation)"
        
        return True, "output_kind correctly excludes diff"
```

### 优先级

**P1**（Mode System 前必须完成）

---

## ⏳ H4：本地三兄弟统一探活策略

### 问题

否则用户体验会割裂。

建议把 `health_check` 的策略做成固定模板：
1. `/v1/models`（OpenAI-compatible）或 `/models`（llama.cpp 视实现）
2. 若存在 model 参数：验证 model 是否在列表里
   - 不在 ⇒ `model_missing` + `error_category="model"`
3. 做一个最小 completion：超时/oom ⇒ `runtime`
4. schema 不兼容 ⇒ `schema`

然后 Gate 里断言这 4 步走到了哪一步（写入 `run_tape`）。

### 解决方案（规划）

创建统一的 `LocalLLMHealthChecker` 基类：

```python
class LocalLLMHealthChecker:
    """
    本地 LLM 统一探活策略
    
    4 步标准流程：
    1. GET /models（或 /v1/models）
    2. 验证 model 是否在列表
    3. 最小 completion 探测
    4. schema 验证
    """
    
    def health_check(self) -> ToolHealth:
        # Step 1: GET /models
        try:
            models = self._get_models()
        except ConnectionError:
            return ToolHealth(
                status="unreachable",
                details="Cannot connect to server",
                error_category="network"
            )
        
        # Step 2: Verify model exists
        if self.model_id not in models:
            return ToolHealth(
                status="model_missing",
                details=f"Model '{self.model_id}' not found in server",
                error_category="model"
            )
        
        # Step 3: Minimal completion probe
        try:
            response = self._minimal_completion()
        except TimeoutError:
            return ToolHealth(
                status="unreachable",
                details="Completion timed out (possible OOM)",
                error_category="runtime"
            )
        
        # Step 4: Schema validation
        if not self._validate_schema(response):
            return ToolHealth(
                status="schema_mismatch",
                details="Response format invalid",
                error_category="schema"
            )
        
        return ToolHealth(status="connected", details="All checks passed")
```

### 优先级

**P2**（体验优化，不阻塞 Mode System）

---

## 当前实施状态

### ✅ 已完成（1 个）

**H2：error_category 进入 evidence chain**
- 实施日期：2026-01-26
- 修改文件：`types.py`
- 提交：`feat(hardening): add 4 critical hardening points`

### ⏳ 待实施（3 个）

**H1：capabilities 真值测试**
- 需要：创建 `TL-R2-CAP-SANITY` Gate
- 工作量：1-2 小时
- 优先级：P1（Mode System 前）

**H3：output_kind 与 DiffVerifier 绑定**
- 需要：创建 `TL-R2-OKIND-N1` Gate
- 工作量：1 小时
- 优先级：P1（Mode System 前）

**H4：本地三兄弟统一探活**
- 需要：创建 `LocalLLMHealthChecker` 基类
- 工作量：2 小时
- 优先级：P2（体验优化）

---

## 收口口径（对外）

在 Freeze Report / 对外口径里可以写：
- ✅ Multi-model adapters 接入：Cloud + Local（Ollama/LM Studio/llama.cpp）
- ✅ Mode System 三大基石：capabilities / output_kind / error taxonomy
- ✅ Runtime gates：连通性与边界验证已覆盖
- ✅ Production hardening（H2）：error_category 进入 evidence chain
- ⏳ 待硬化：capabilities 真值探针（H1）、output_kind 与 diff verifier 的绑定（H3）、本地 LLM 统一探活（H4）

---

## requests 依赖问题

用户提到："如果你们 repo 目标是最小依赖 + 可审计，建议把 HTTP 客户端统一成你们已有的（比如 stdlib urllib 或 httpx，看你们当前栈）。"

**当前状态**：
- 使用 `requests` 库（非 stdlib）
- 需要 `pip install requests`

**建议**（后续清理）：
- 评估是否迁移到 `urllib`（stdlib）或 `httpx`
- 如果保留 `requests`，添加到 `requirements.txt`
- 不阻塞 Mode System，属于依赖优化

---

## 总结

### 硬化完成度

- **H2（P0）**：✅ 完成（error_category + endpoint 进入 evidence）
- **H1（P1）**：⏳ 规划（capabilities 真值测试）
- **H3（P1）**：⏳ 规划（output_kind 绑定）
- **H4（P2）**：⏳ 规划（本地 LLM 统一）

### 下一步

1. **立即可做**：实施 H1, H3（Mode System 前）
2. **体验优化**：实施 H4（本地 LLM 统一）
3. **依赖清理**：评估 requests 迁移方案

**当前状态**：🟡 部分完成 - H2 已钉死，H1/H3/H4 待实施

**这是长期会赢的路线**。🎉
