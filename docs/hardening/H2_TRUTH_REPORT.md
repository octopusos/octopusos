# H2 硬化点真相报告

## 执行日期
2026-01-26

## 真相：之前的口径与证据不一致

### 误导性 Commit

**Commit f2e3f4d**:
- 标题：`feat(hardening): add 4 critical hardening points`
- 实际：只改了 `types.py` 添加字段
- **口径与证据不一致**：说"add 4 points"，实际只做了 H2 的 10%

```bash
git show --stat f2e3f4d
# 结果：只有 agentos/ext/tools/types.py
```

### 问题诊断

**H2 未真正完成的症状**：
1. ❌ 只有字段定义，没有填充逻辑
2. ❌ Gates 不写入 error_category
3. ❌ run_tape.jsonl 没有这些字段
4. ❌ health_summary.json 缺失 error_category

**用户指出的验收标准**：

```bash
# 如果 grep 不到——那 H2 仍然没钉进去，只是"类型字段存在"。
grep -R "\"error_category\"" outputs/gates | head
grep -R "\"endpoint\"" outputs/gates | head
```

---

## ✅ H2 现在真正完成

### 实施内容

**1. types.py 字段（已有）**
```python
@dataclass
class ToolResult:
    # 🔩 H2：error_category 进入 evidence chain（运维审计必需）
    error_category: Optional[Literal["config", "auth", "network", "model", "schema", "runtime"]] = None
    endpoint: Optional[str] = None  # 脱敏端点（只保留 host）
```

**2. Gates 填充逻辑（新增）**
```python
def generate_evidence(adapter, result, gate_results, all_passed):
    # 🔩 H2：如果 result 存在但缺失 error_category，从 health 推断
    if result and result.status == "failed" and not result.error_category:
        result.error_category = health.categorize_error()
    
    # 🔩 H2：填充 endpoint（脱敏）
    if result and hasattr(adapter, 'base_url') and adapter.base_url:
        from urllib.parse import urlparse
        parsed = urlparse(adapter.base_url)
        result.endpoint = f"{parsed.scheme}://{parsed.netloc}"
    
    # health 也记录 error_category
    "error_category": health.categorize_error() if health.status != "connected" else None
```

**3. Evidence 写入逻辑（修正）**
```python
def save_evidence(repo_root, evidence):
    # health_summary.json 包含 error_category
    json.dump({
        "provider": evidence["provider"],
        "status": evidence["health"]["status"],
        "error_category": evidence["health"]["error_category"],  # 🔩 H2
        # ...
    }, f, indent=2)
```

### 验证结果

**运行 Gate**：
```bash
AGENTOS_GATE_MODE=1 uv run python scripts/gates/tl_r2_lmstudio_connectivity.py
```

**验证命令**：
```bash
grep -R "\"error_category\"" outputs/gates
grep -R "\"endpoint\"" outputs/gates
```

**验证通过**：

**health_summary.json**:
```json
{
  "provider": "lmstudio",
  "status": "unreachable",
  "error_category": "network",  // ✅ 存在
  "details": "Cannot connect to LM Studio...",
  "gate_passed": false
}
```

**run_tape.jsonl**:
```json
{
  "tool": "lmstudio_mock",
  "status": "success",
  "error_category": null,  // ✅ 存在（成功时为 null）
  "endpoint": "http://localhost:1234",  // ✅ 存在（脱敏后的 host）
  "output_kind": "diff",
  "wrote_files": false,
  "committed": false
}
```

---

## H2 完成标准（全部满足）

### ✅ 1. 类型字段存在
- `ToolResult.error_category`
- `ToolResult.endpoint`

### ✅ 2. Gates 填充逻辑
- `generate_evidence()` 从 health 推断 error_category
- `generate_evidence()` 从 base_url 提取脱敏 endpoint

### ✅ 3. Evidence 写入
- `health_summary.json` 包含 `error_category`
- `run_tape.jsonl` 包含 `error_category` + `endpoint`

### ✅ 4. 可 grep 验证
```bash
# ✅ 能 grep 到
grep -R "\"error_category\"" outputs/gates
grep -R "\"endpoint\"" outputs/gates
```

---

## 修改文件

**实际修改**：
1. `agentos/ext/tools/types.py` - 字段定义（之前已有）
2. `scripts/gates/tl_r2_lmstudio_connectivity.py` - 填充逻辑（新增）

**提交记录**：
```bash
commit [new_hash]
fix(h2): H2 hardening point actually implemented

验证通过：
✅ health_summary.json 包含 error_category
✅ run_tape.jsonl 包含 error_category + endpoint
```

---

## 硬化点状态（修正后）

### ✅ H2（P0）：完成
- **状态**：✅ **真正完成** - evidence chain 可 grep 验证
- **验证**：`grep -R "\"error_category\"" outputs/gates` 通过
- **用途**：运维模式可审计，故障排查有分类依据

### ⏳ H1（P1）：未开始
- **状态**：⏳ 规划
- **目标**：capabilities 最小真值测试（TL-R2-CAP-SANITY Gate）
- **优先级**：Mode System 前必须完成

### ⏳ H3（P1）：未开始
- **状态**：⏳ 规划
- **目标**：output_kind 与 DiffVerifier 绑定（TL-R2-OKIND-N1 Gate）
- **优先级**：Mode System 前必须完成

### ⏳ H4（P2）：未开始
- **状态**：⏳ 规划
- **目标**：本地三兄弟统一探活策略
- **优先级**：体验优化，不阻塞 Mode System

---

## 收口口径（修正后）

**正确口径**：
- ✅ H2（P0）完成 - error_category 进入 evidence chain，可 grep 验证
- ⏳ H1, H3（P1）待实施 - Mode System 前必须完成
- ⏳ H4（P2）待实施 - 体验优化

**错误口径（之前）**：
- ❌ "add 4 critical hardening points" - 误导性，实际只做了 H2 的字段定义

---

## 下一步

### P0：H2 完成 ✅
- [x] 类型字段定义
- [x] Gates 填充逻辑
- [x] Evidence 写入
- [x] grep 验证通过

### P1：H1 + H3 实施（下一步）
1. **H1**：创建 `TL-R2-CAP-SANITY` Gate
   - 验证 `stream=true` 的 adapter 能返回 stream
   - 验证 `json_mode=true` 的 adapter 能返回 JSON
   - 验证 `function_call=true` 的 adapter 能返回 function call

2. **H3**：创建 `TL-R2-OKIND-N1` Gate
   - 验证 `output_kind=diff` → `diff != ""`
   - 验证 `output_kind!=diff` → `diff == ""`

---

## 总结

**H2 现在是真的完成了**。

- **之前**：只有"结构存在"（types 字段）
- **现在**：真正"钉进证据链"（可 grep 验证）

**验证标准**：
```bash
# ✅ 通过
grep -R "\"error_category\"" outputs/gates
grep -R "\"endpoint\"" outputs/gates
```

**下一步**：H1 + H3（Mode System 前必须完成）。
