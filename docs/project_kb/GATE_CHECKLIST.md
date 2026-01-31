# ProjectKB 验收 Gate 清单

## Gate #1-18 验收标准

本文档定义了 ProjectKB 合并前必须通过的验收标准（P0/P1 + P2）。

---

## P0/P1 Gates (基础功能)

### A. 数据库与迁移（高风险）

#### Gate A1: FTS5 可用性检测

**要求**: 目标环境的 SQLite 必须启用 FTS5

**实现**: `agentos/core/project_kb/indexer.py::check_fts5_available()`

**验证**:
```bash
python -c "from agentos.core.project_kb import ProjectKBService; kb = ProjectKBService(); print('FTS5 available')"
```

**失败行为**: 抛出 `FTS5NotAvailableError` 并提示用户

---

#### Gate A2: 迁移幂等

**要求**: 重复执行 migrations 不应报错；schema version 可追溯

**实现**: 
- SQL 使用 `IF NOT EXISTS`
- WAL 模式避免长事务锁
- 元数据表记录 schema_version

**验证**:
```bash
# 执行两次应无报错
agentos kb refresh
agentos kb refresh
```

---

#### Gate A3: 回滚策略

**要求**: 至少要有"删库重建索引"的灾备路径

**实现**: 删除表并重新执行迁移

**回滚命令**:
```bash
# 方案 1: 删除 ProjectKB 表
sqlite3 store/registry.sqlite "DROP TABLE IF EXISTS kb_chunks_fts;"
sqlite3 store/registry.sqlite "DROP TABLE IF EXISTS kb_chunks;"
sqlite3 store/registry.sqlite "DROP TABLE IF EXISTS kb_sources;"
sqlite3 store/registry.sqlite "DROP TABLE IF EXISTS kb_embeddings;"
sqlite3 store/registry.sqlite "DROP TABLE IF EXISTS kb_index_meta;"

# 方案 2: 重新刷新
agentos kb refresh --full
```

---

### B. 切片器（知识质量核心）

#### Gate B4: 代码块保护

**要求**: Markdown 里的 code 不能被切断成半截

**实现**: `agentos/core/project_kb/chunker.py::_split_into_sections()` 
- 检测 ``` 边界
- in_code_block 标记防止切分

**验证**:
```python
# tests/unit/test_project_kb_chunker.py
def test_code_block_protection():
    content = '''# Title
    
```python
def foo():
    return "bar"
```

Content after.
'''
    chunks = list(chunker.chunk_file("test", tmp_path / "test.md"))
    # 确保代码块在单个 chunk 中
    assert any("def foo():" in c.content for c in chunks)
```

---

#### Gate B5: Heading 边界

**要求**: #/##/### 切片要保持"标题 + 段落"同块，避免标题孤儿

**实现**: Section 始终包含 heading 行 + 后续内容行

**验证**: 检查 chunk.heading 非 None 时，content 必须包含对应段落

---

#### Gate B6: 行号准确

**要求**: start_line/end_line 必须和原文一致

**实现**: 使用 enumerate(lines, start=1) 确保行号从 1 开始

**验证**:
```bash
# 搜索结果中的行号应该能在原文件中精确定位
agentos kb search "JWT" --explain | grep "L[0-9]"
# 手动验证行号对应原文
```

---

### C. 索引与增量刷新（一致性风险）

#### Gate C7: file_hash 计算统一

**要求**: 明确 hash 基于内容（SHA256）

**实现**: `scanner.py::_compute_file_hash()` 使用 SHA256

**文档**: 已在 scanner.py 注释中说明

---

#### Gate C8: 删除文件处理

**要求**: 源文件被删除时，chunks/index 必须清理掉

**实现**: 
- `scanner.find_deleted()` 检测已删除文件
- `indexer.delete_source()` 触发 CASCADE 删除

**验证**:
```bash
# 1. 创建测试文件并索引
echo "# Test" > docs/test_delete.md
agentos kb refresh

# 2. 搜索应能找到
agentos kb search "Test"

# 3. 删除文件并重新刷新
rm docs/test_delete.md
agentos kb refresh

# 4. 搜索应找不到
agentos kb search "Test" | grep "test_delete.md" && echo "FAIL" || echo "PASS"
```

---

#### Gate C9: 重建一致性

**要求**: refresh 后，stats（文件数/chunk 数）要可重复、稳定

**验证**:
```bash
# 多次全量刷新，统计应一致
agentos kb refresh --full > /tmp/kb1.txt
agentos kb refresh --full > /tmp/kb2.txt
diff <(grep "Total chunks" /tmp/kb1.txt) <(grep "Total chunks" /tmp/kb2.txt)
```

---

### D. 搜索与 Explain（审计红线）

#### Gate D10: Explain 必含 5 件事

**要求**: path、heading、line_range、bm25_score、boosts_breakdown

**实现**: `explainer.py::explain_result()` + `types.py::Explanation`

**Gate 脚本**: `scripts/gates/kb_gate_explain.py`

**验证**:
```bash
python scripts/gates/kb_gate_explain.py
```

**必需字段**:
- `path` (str)
- `heading` (str | None)
- `lines` (str, format: "L45-L68")
- `score` (float)
- `explanation.matched_terms` (list)
- `explanation.term_frequencies` (dict)
- `explanation.document_boost` (float)
- `explanation.recency_boost` (float)

---

#### Gate D11: 权重可解释

**要求**: 新鲜度权重/文档类型权重必须进入 explain

**实现**: `searcher.py::_row_to_result()` 计算并记录到 Explanation

**验证**: 
```bash
agentos kb search "auth" --explain | grep "document_boost\|recency_boost"
```

---

#### Gate D12: Evidence 格式稳定

**要求**: kb:<chunk_id>:<path>#Lx-Ly 格式锁死

**实现**: `types.py::ChunkResult.to_evidence_ref()`

**格式规范**:
```
kb:<chunk_id>:<path>#<line_range>

示例:
kb:chunk_abc123:docs/architecture/auth_design.md#L45-L68
```

**验证**:
```python
from agentos.core.project_kb import ProjectKBService
kb = ProjectKBService()
results = kb.search("JWT", top_k=1)
evidence = results[0].to_evidence_ref()
assert evidence.startswith("kb:")
assert "#L" in evidence
```

---

## 执行所有 Gates

```bash
# 运行验收脚本
./scripts/gates/run_projectkb_gates.sh
```

## Gate 失败处理

如果任何 Gate 失败：

1. **不要合并 PR**
2. 修复对应实现
3. 重新运行 Gate
4. 更新本文档记录修复

---

## P2 Gates (向量增强)

### E. Embedding 与 Vector Rerank

#### Gate E1: Embedding 覆盖率

**要求**: 当 rerank 启用时，候选 topK 中 embedding 覆盖率 >= 95%

**实现**: `agentos/core/project_kb/embedding/manager.py`

**验证**:
```bash
python scripts/gates/kb_gate_e1_coverage.py
```

**失败行为**: 提示运行 `agentos kb embed build`

---

#### Gate E2: Explain 完整性 (Vector)

**要求**: rerank 开启时，explain 必须包含所有向量评分字段

**必须字段**:
- `keyword_score`
- `vector_score`
- `alpha`
- `final_score`
- `rerank_delta`
- `final_rank`

**实现**: `agentos/core/project_kb/reranker.py`

**验证**:
```bash
python scripts/gates/kb_gate_e2_explain.py
```

---

#### Gate E3: Determinism

**要求**: 同一 query 多次执行结果稳定（在相同库状态下）

**实现**: 所有随机性因素（如向量计算）必须确定

**验证**:
```bash
python scripts/gates/kb_gate_e3_determinism.py
```

---

#### Gate E4: Graceful Fallback

**要求**: provider 不可用或模型缺失时，自动退回 BM25 + 记录 audit

**实现**: `agentos/core/project_kb/service.py::__init__` (fail_safe)

**验证**:
```bash
python scripts/gates/kb_gate_e4_fallback.py
```

**失败行为**: 打印警告并使用关键词检索

---

#### Gate E5: 增量一致性

**要求**: 修改文档后 embedding 同步更新

**实现**: 
- `service.py::refresh()` 调用 `embedding_manager.refresh_embeddings()`
- 基于 `content_hash` 判断是否需要重新生成

**验证**:
```bash
python scripts/gates/kb_gate_e5_incremental.py
```

---

#### Gate E6: 性能阈值

**要求**: `candidate_k` ≤ 100，防止性能退化

**实现**: 配置验证

**验证**:
```bash
python scripts/gates/kb_gate_e6_performance.py
```

---

## 运行所有 Gates

```bash
./scripts/gates/run_projectkb_gates.sh
```

输出示例：

```
======================================================================
ProjectKB Gate Validation
======================================================================

[Gate A1] FTS5 Availability Check
✓ FTS5 available

[Gate A2] Migration Idempotence
✓ Migrations are idempotent

...

[Gate E1] Embedding Coverage
✓ Gate E1: PASS (coverage 98.5% >= 95%)

[Gate E2] Explain Completeness (Vector)
✓ Gate E2: PASS (all explain fields present)

...

======================================================================
Gate Summary
======================================================================
Passed: 18
Failed: 0

✅ All gates PASSED
```

---

## Gate 失败处理

如果任何 Gate 失败：

1. **不要合并 PR**
2. 修复对应实现
3. 重新运行 Gate
4. 更新本文档记录修复

## 文档链接

- 完整实现报告: `ENGINEERING_DELIVERABLE.md`
- 使用指南: `docs/project_kb/README.md`
- 测试: `tests/integration/test_kb_service.py`
- P2 测试: `tests/integration/test_kb_vector_rerank.py`
