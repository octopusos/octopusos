# PR-0126-2026-2 文件变更清单

## 核心代码变更

### 1. Indexer 增强 (改进 1, 2, 3)
**文件**: `agentos/core/project_kb/indexer.py`

**新增方法**:
- `rebuild_fts(allow_drift: bool = False) -> dict`
  - 默认强一致性（0 差异）
  - 显式参数控制容忍模式
  - 返回详细统计信息
  
- `cleanup_orphan_chunks() -> dict`
  - 清理无对应 source 的 chunks
  - 清理无对应 chunk 的 embeddings
  - 返回清理统计
  
- `record_fts_signature(migration_version: str = "14")`
  - 记录 FTS 版本签名到 meta 表
  - 包含: fts_mode, fts_columns, trigger_set, migration_version
  
- `get_fts_signature() -> dict`
  - 读取当前 FTS 签名
  - 用于未来迁移检查

**变更统计**:
- 新增行数: ~150 行
- 修改方法: 1 个 (rebuild_fts)
- 新增方法: 3 个

---

### 2. CLI 增强 (改进 4)
**文件**: `agentos/cli/kb.py`

**修改命令**: `repair`

**新增参数**:
```python
@click.option("--rebuild-fts", is_flag=True, help="重建 FTS 索引")
@click.option("--allow-drift", is_flag=True, help="允许 <5% 差异容忍（并发模式）")
@click.option("--cleanup-orphans", is_flag=True, default=True, help="清理孤儿 chunks（默认启用）")
@click.option("--explain/--no-explain", default=True, help="显示详细报告")
```

**5-Step Audit Output**:
1. Step 1/5: Checking FTS integrity
2. Step 2/5: Checking triggers
3. Step 3/5: Cleaning orphan chunks
4. Step 4/5: Rebuilding FTS index
5. Step 5/5: Recording FTS signature

**变更统计**:
- 新增行数: ~100 行
- 修改方法: 1 个 (repair)

---

## 文档变更

### 1. PR 描述文档 (改进 5)
**文件**: `docs/project_kb/PR_0126_2026_2_FINAL.md`

**内容**:
- Summary (3 点改进)
- Key Guarantees (BM25 + Vector)
- Changes (6 个核心变更)
- Verification (Gates + Manual)
- Evidence (3 份文档链接)
- Commit Strategy (3-step logical split)
- Risk Assessment (Low + Zero)
- Rollback Plan

**行数**: ~450 行

---

### 2. Merge Ready Summary
**文件**: `docs/project_kb/MERGE_READY_SUMMARY.md`

**内容**:
- 3 个收尾改进详解
- Enhanced Repair CLI 说明
- Verification Status
- Why These 3 Improvements Matter
- Ready to Merge Checklist

**行数**: ~250 行

---

### 3. 文件变更清单（本文档）
**文件**: `docs/project_kb/PR_0126_FILE_CHANGES.md`

---

## 验证脚本

### 1. Quick Verification Script
**文件**: `scripts/verify_pr_0126.sh`

**功能**:
- 验证改进 1: 严格模式（默认 0 差异）
- 验证改进 2: 孤儿清理
- 验证改进 3: FTS 签名
- 完整 Repair 测试（5-Step Audit）
- 搜索功能验证

**行数**: ~80 行

---

## 变更统计汇总

### 代码变更
| 文件 | 类型 | 新增行 | 修改方法 | 新增方法 |
|------|------|--------|----------|----------|
| `agentos/core/project_kb/indexer.py` | Core | ~150 | 1 | 3 |
| `agentos/cli/kb.py` | CLI | ~100 | 1 | 0 |
| **总计** | | **~250** | **2** | **3** |

### 文档变更
| 文件 | 类型 | 行数 |
|------|------|------|
| `docs/project_kb/PR_0126_2026_2_FINAL.md` | PR Description | ~450 |
| `docs/project_kb/MERGE_READY_SUMMARY.md` | Summary | ~250 |
| `docs/project_kb/PR_0126_FILE_CHANGES.md` | This File | ~120 |
| **总计** | | **~820** |

### 脚本变更
| 文件 | 类型 | 行数 |
|------|------|------|
| `scripts/verify_pr_0126.sh` | Verification | ~80 |
| **总计** | | **~80** |

---

## Git Diff Summary

```bash
# 预期 git diff 输出
git diff --stat

agentos/cli/kb.py                              | +100 -20
agentos/core/project_kb/indexer.py             | +150 -15
docs/project_kb/MERGE_READY_SUMMARY.md         | +250
docs/project_kb/PR_0126_2026_2_FINAL.md        | +450
docs/project_kb/PR_0126_FILE_CHANGES.md        | +120
scripts/verify_pr_0126.sh                      | +80
6 files changed, ~1150 insertions(+), ~35 deletions(-)
```

---

## Commit Split Strategy

### Commit 1: `fix(projectkb): rebuild FTS5 contentless + correct triggers`
**Files**:
- `agentos/store/migrations/v14_fix_fts_triggers.sql` (if needed)
- `agentos/core/project_kb/indexer.py` (trigger verification)

**Focus**: P0 Hotfix - FTS5 correctness

---

### Commit 2: `fix(projectkb): idempotent repair + orphan cleanup + signature`
**Files**:
- `agentos/core/project_kb/indexer.py`:
  - `rebuild_fts()` enhancement
  - `cleanup_orphan_chunks()` new
  - `record_fts_signature()` new
  - `get_fts_signature()` new
- `agentos/cli/kb.py`:
  - Enhanced `repair` command

**Focus**: Repair infrastructure + 3 final improvements

---

### Commit 3: `feat(projectkb): vector rerank (optional extras)`
**Files**:
- `agentos/store/migrations/v13_vector_embeddings.sql`
- `agentos/core/project_kb/embedding/` (module)
- `agentos/core/project_kb/reranker.py`
- `agentos/core/project_kb/service.py` (rerank integration)
- `agentos/cli/kb.py` (embed commands)

**Focus**: P2 Feature (opt-in only)

---

## Review Checklist

### For Code Reviewers
- [ ] `indexer.py` - Verify `rebuild_fts()` is truly idempotent
- [ ] `indexer.py` - Check `cleanup_orphan_chunks()` SQL logic
- [ ] `indexer.py` - Verify `record_fts_signature()` writes correct meta
- [ ] `kb.py` - Check repair CLI audit output formatting
- [ ] `kb.py` - Verify parameter handling (allow_drift, cleanup_orphans)

### For QA Testers
- [ ] Run `scripts/verify_pr_0126.sh` on test environment
- [ ] Verify `agentos kb repair --rebuild-fts` output
- [ ] Check orphan cleanup (before/after counts)
- [ ] Verify FTS signature in `kb_index_meta` table
- [ ] Test search functionality post-repair

### For Documentation Reviewers
- [ ] Review `PR_0126_2026_2_FINAL.md` completeness
- [ ] Check `MERGE_READY_SUMMARY.md` accuracy
- [ ] Verify all code examples are correct
- [ ] Check commit message templates

---

## Post-Merge Tasks

### Immediate (Day 1)
1. Monitor production logs for repair usage
2. Check for any drift warnings in strict mode
3. Verify orphan cleanup statistics

### Short-term (Week 1)
1. Update internal wiki with new repair options
2. Create runbook for `--allow-drift` usage scenarios
3. Train support team on 5-step audit output interpretation

### Long-term (Month 1)
1. Collect metrics on drift ratios across deployments
2. Evaluate need for auto-repair cron job
3. Consider adding `--dry-run` mode for repair

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-26  
**Author**: AI Assistant  
**Status**: ✅ Complete
