# PR-0126-2026-2: Fix FTS5 Triggers + P2 Vector Rerank

## Scope

### Hotfix (阻塞修复)
- ✅ 修复 v12 FTS5 trigger 错误（`no such column: T.path`）
- ✅ v14 migration：重建 FTS 表 + triggers
- ✅ 新增 `agentos kb repair` 自愈命令
- ✅ 新增 3 个 Gates（G-FTS-01/02 + G-KB-STAT-DRIFT）

### P2 (Vector Rerank)
- ✅ Embedding Provider 抽象层（local/cloud 可插拔）
- ✅ EmbeddingManager（批量生成、增量更新、持久化）
- ✅ VectorReranker（两段式检索：BM25召回 + Vector重排）
- ✅ CLI 扩展（`agentos kb embed build/refresh/stats`）
- ✅ 完整可审计 Explain（keyword_score, vector_score, alpha, rerank_delta）
- ✅ 6个 Embedding Gates + 单元/集成测试

---

## Why

### Hotfix
- **阻塞**: v12 FTS trigger 错误导致基本搜索失败（`Error: no such column: T.path`）
- **根因**: FTS 触发器引用了不存在的表别名，导致 INSERT/UPDATE/DELETE 失败
- **影响**: P0/P1 基本搜索功能不可用，P2 rerank 无法工作（依赖 BM25 召回）

### P2
- AgentOS 需要支持"自然语言问答"式查询（如 "how to implement OAuth2 flow"）
- 纯关键词检索对长尾查询、同义词覆盖不足
- 但必须保持**可审计性**：向量只做 rerank，不做唯一召回源

---

## Key Decisions

### Hotfix
- **v14 Migration**: 完全重建 FTS 表 + triggers（而非 ALTER）
  - FTS 表直接包含 `path` 列（避免搜索时 join `kb_sources`）
  - 触发器从 `kb_sources` 显式 join 获取 path
- **Repair 命令**: 一键自愈（检查 FTS 健康 + 重建索引）
- **3 个新 Gates**: 防止 FTS 退化（trigger/search/stats）

### P2
- **Two-Stage Retrieval**：BM25 召回 topK（如50） → Vector rerank topN（如10）
- **Score Fusion**：`final = (1-α)*keyword_norm + α*vector_score`（α=0.7 默认）
- **Optional Dependencies**：`pip install agentos[vector]`（不强制）
- **Auditability Red Line**：所有结果同时显示 keyword/vector/alpha/delta

---

## Verification

### 8/8 验收全部通过 ✅

| # | 验收项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | rerank关闭时等价P1 | ✅ PASS | 无vector字段，纯BM25输出 |
| 2 | embeddings缺失时降级 | ✅ PASS | 自动fallback到BM25，无崩溃 |
| 3 | rerank生效且explain显示delta | ✅ PASS | Rerank Δ: +41, Vector: 0.651, Alpha: 0.70 |
| 4 | 增量refresh仅重算受影响chunks | ✅ PASS | 375→376→375，覆盖率100% |
| 5 | 删除文件后embedding同步清理 | ✅ PASS | 搜索不命中，embeddings同步减少 |
| 6 | 中文/Unicode失败可解释 | ⚠️ PASS | 已文档化限制，无崩溃 |
| 7 | 性能边界candidate_k生效 | ✅ PASS | candidate_k=50, final_k=10 |
| 8 | 可选依赖缺失时不影响P0/P1 | ✅ PASS | **Hotfix修复后通过** |

**详细验收报告**: `docs/project_kb/HOTFIX_VERIFICATION.md`

---

## Example Output

### Hotfix 修复后的基本搜索

```bash
$ uv run agentos kb search "authentication" --top-k 3

🔍 Search: authentication
Found 3 result(s)

[1] docs/project_kb/P2_FINAL_VERIFICATION.md
    Score: 0.74
    Matched: authentication
    # 搜索正常工作
```

### P2 Vector Rerank Explain

```bash
$ uv run agentos kb search "how to implement OAuth2 flow" --rerank --top-k 10 --explain

[1] docs/OPEN_PLAN_ARCHITECTURE.md
    Score: 0.76
    Matched: to, implement
    Vector: 0.651, Alpha: 0.70, Rerank Δ: +41  ← 原本第42名，提升到第1！
    Evidence: kb:open_plan_note_317:docs/OPEN_PLAN_ARCHITECTURE.md#L317-L470

[2] docs/demo/RUNTIME_VERIFICATION_STATUS.md
    Score: 0.74
    Matched: to, implement, how
    Vector: 0.630, Alpha: 0.70, Rerank Δ: +37
    Evidence: kb:runtime_verify_immediate:docs/demo/RUNTIME_VERIFICATION_STATUS.md#L199-L280

[3] docs/execution/intent-authoring-guide.md
    Score: 0.74
    Matched: to, flow, implement, how
    Vector: 0.625, Alpha: 0.70, Rerank Δ: +11
    Evidence: kb:intent_guide_intro:docs/execution/intent-authoring-guide.md#L1-L138
```

---

## Files Changed

### Hotfix
- `agentos/store/migrations/v14_fix_fts_triggers.sql` - FTS 表 + triggers 重建
- `agentos/core/project_kb/indexer.py` - 新增 `rebuild_fts()` 方法
- `agentos/cli/kb.py` - 新增 `repair` 命令
- `scripts/gates/kb_gate_fts_01_triggers.py` - Trigger 健康检查
- `scripts/gates/kb_gate_fts_02_search.py` - Search 非空回归
- `scripts/gates/kb_gate_stat_drift.py` - Stats 漂移检测

### P2 (与之前 P2 PR 模板相同)
- `agentos/core/project_kb/embedding/*` - Provider/Manager/Factory
- `agentos/core/project_kb/reranker.py` - 两段式检索逻辑
- `agentos/core/project_kb/service.py` - 集成到 ProjectKBService
- `agentos/cli/kb.py` - `embed` 子命令组
- `agentos/store/migrations/v13_vector_embeddings.sql` - Embedding 表
- `scripts/gates/kb_gate_e{1-6}.py` - 6个 Embedding Gates
- `tests/unit/test_vector_reranker.py` - 重排序单元测试
- `tests/integration/test_kb_vector_rerank.py` - 集成测试
- `pyproject.toml` - `[vector]` extras

---

## Pre-Merge Checklist

在本地验证：

```bash
# 1. 应用 hotfix
sqlite3 store/registry.sqlite < agentos/store/migrations/v14_fix_fts_triggers.sql

# 2. 安装 vector 依赖（P2）
pip install agentos[vector]

# 3. Repair + Refresh
uv run agentos kb repair --rebuild-fts
uv run agentos kb refresh
uv run agentos kb embed build

# 4. 验证基本搜索（Hotfix）
uv run agentos kb search "authentication" --top-k 3
# 期望：返回 3 条结果，无错误

# 5. 验证 rerank（P2）
uv run agentos kb search "how to implement OAuth2 flow" --rerank --top-k 10 --explain
# 期望：看到 Vector/Alpha/Rerank Δ 字段

# 6. 运行所有 gates
uv run python scripts/gates/kb_gate_fts_01_triggers.py
uv run python scripts/gates/kb_gate_fts_02_search.py
uv run python scripts/gates/kb_gate_stat_drift.py
uv run python scripts/gates/kb_gate_e1_coverage.py
# 期望：全部 PASS

# 7. 验证 repair 命令
uv run agentos kb repair
# 期望：✓ FTS queries working, ✓ All triggers present
```

---

## Breaking Changes

无。所有变更向后兼容：
- Hotfix 是透明修复（用户无感知）
- P2 默认 `vector_rerank.enabled = false`
- 不安装 `[vector]` 依赖时，系统自动降级到 P1 功能

---

## Performance Impact

### Hotfix
- **FTS Rebuild**: ~0.5s（375 chunks）
- **Search Latency**: 无变化（甚至略快，因为不需要 join sources）

### P2
- **Build Embeddings**: 375 chunks ~13s（batch_size=16，本地 CPU）
- **Search Latency**: +50-100ms（候选集50 → rerank → top10）
- **Storage**: ~1.5KB/chunk（384维 float32）

---

## Documentation

- `docs/project_kb/HOTFIX_VERIFICATION.md` - Hotfix 8/8 验收报告
- `docs/project_kb/P2_FINAL_VERIFICATION.md` - P2 7/8 验收报告（Hotfix前）
- `docs/project_kb/P2_VECTOR_RERANK_COMPLETE.md` - P2 完成报告
- `docs/project_kb/README.md` - 用户指南（含 Vector Rerank 章节）
- `docs/project_kb/GATE_CHECKLIST.md` - 完整 Gates 清单

---

## Next Steps (Future)

- [ ] 支持 OpenAI/Bedrock embedding provider
- [ ] 中文分词优化（FTS5 custom tokenizer）
- [ ] Hybrid search 权重自适应调整
- [ ] Embedding 增量更新性能优化（并行化）

---

**Status**: ✅ **8/8 VERIFIED** - 可立即合并
