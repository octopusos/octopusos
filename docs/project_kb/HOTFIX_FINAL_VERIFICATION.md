# FTS5 Hotfix - 最终验收输出（真实命令）

**Date**: 2026-01-26 (Final)  
**Status**: ✅ **所有验收通过** - UPDATE/DELETE triggers 已修复

---

## 验证1：UPDATE/DELETE Trigger 完整性

### 1.1 修改文件触发 UPDATE

```bash
$ echo -e "\n## Update Test\n\nUniqueUpdateTokenXYZ for trigger validation\n" >> docs/project_kb/README.md
$ uv run agentos kb refresh

Refreshing ProjectKB index...
Changed files: 1
New chunks: 0  # 内容更新，chunk 未新增
```

### 1.2 搜索新增内容

```bash
$ uv run agentos kb search "UniqueUpdateTokenXYZ" --top-k 3

🔍 Search: UniqueUpdateTokenXYZ
Found 1 result(s)

[1] docs/project_kb/README.md
    Score: 0.75
    Matched: UniqueUpdateTokenXYZ
    # UPDATE trigger 工作正常，新内容已索引
```

### 1.3 删除内容触发 UPDATE

```bash
$ git checkout docs/project_kb/README.md
$ uv run agentos kb refresh

Refreshing ProjectKB index...
Changed files: 1
```

### 1.4 确认内容已删除

```bash
$ uv run agentos kb search "UniqueUpdateTokenXYZ" --top-k 3

No results found for: UniqueUpdateTokenXYZ  # DELETE 功能正常，旧内容已清理
```

**结论**: ✅ UPDATE/DELETE triggers 正常工作，无幽灵命中

---

## 验证2：G-FTS-01 Trigger 健康检查

```bash
$ uv run python scripts/gates/kb_gate_fts_01_triggers.py

Gate G-FTS-01: FTS5 Trigger Health Check
============================================================

1. Checking triggers...
  ✓ kb_chunks_ai exists
  ✓ kb_chunks_ad exists
  ✓ kb_chunks_au exists

2. Testing INSERT trigger...
  ✓ INSERT trigger works (chunk_id=test_chunk_fts_4621980656, path=test.md)

3. Testing UPDATE trigger...
  ✓ UPDATE trigger works

4. Testing DELETE trigger...
  ✓ DELETE trigger works

============================================================
✅ Gate G-FTS-01 PASSED
```

---

## 验证3：G-FTS-02 Search 非空回归

```bash
$ uv run python scripts/gates/kb_gate_fts_02_search.py

Gate G-FTS-02: Search Non-Empty Regression
============================================================

1. Checking index state...
  Total chunks: 384

2. Testing basic search...
  ✓ Query 'the' found 5 results

3. Testing new document indexing...
  ✓ New document indexed and searchable

4. Testing deletion cleanup...
  ✓ Deleted document no longer in index

============================================================
✅ Gate G-FTS-02 PASSED
```

---

## v14 Migration 最终版本

### 关键修复点

1. ✅ **FTS 表模式**: Contentless 模式（不使用 `content='kb_chunks'`）
2. ✅ **INSERT trigger**: 从 `kb_sources` join 获取 path
3. ✅ **DELETE trigger**: `DELETE FROM kb_chunks_fts WHERE rowid = OLD.rowid`
4. ✅ **UPDATE trigger**: 先 DELETE 再 INSERT（防止幽灵命中）

### SQL 代码

```sql
-- 2. 创建新 FTS 表（contentless 模式，触发器维护内容）
CREATE VIRTUAL TABLE kb_chunks_fts USING fts5(
    chunk_id UNINDEXED,
    path,
    heading,
    content
);

-- 3. INSERT trigger
CREATE TRIGGER kb_chunks_ai AFTER INSERT ON kb_chunks BEGIN
    INSERT INTO kb_chunks_fts(rowid, chunk_id, path, heading, content)
    SELECT NEW.rowid, NEW.chunk_id, s.path, NEW.heading, NEW.content
    FROM kb_sources s WHERE s.source_id = NEW.source_id;
END;

-- 4. DELETE trigger
CREATE TRIGGER kb_chunks_ad AFTER DELETE ON kb_chunks BEGIN
    DELETE FROM kb_chunks_fts WHERE rowid = OLD.rowid;
END;

-- 5. UPDATE trigger
CREATE TRIGGER kb_chunks_au AFTER UPDATE ON kb_chunks BEGIN
    DELETE FROM kb_chunks_fts WHERE rowid = OLD.rowid;
    INSERT INTO kb_chunks_fts(rowid, chunk_id, path, heading, content)
    SELECT NEW.rowid, NEW.chunk_id, s.path, NEW.heading, NEW.content
    FROM kb_sources s WHERE s.source_id = NEW.source_id;
END;
```

---

## 为什么不用 content='kb_chunks'

**问题**: `content='kb_chunks'` 要求 kb_chunks 表有 path 列，但实际 path 在 kb_sources 表。

**错误示例**:
```sql
-- ❌ 错误
CREATE VIRTUAL TABLE kb_chunks_fts USING fts5(
    ..., path, ...,
    content='kb_chunks'  -- 会导致 "no such column: T.path"
);
```

**解决方案**: 使用 contentless 模式，由触发器维护内容：
```sql
-- ✅ 正确
CREATE VIRTUAL TABLE kb_chunks_fts USING fts5(
    ..., path, ...
    -- 不指定 content，触发器负责同步
);
```

---

## 准入结论

✅ **可以开 PR**

- UPDATE/DELETE triggers 正确实现
- G-FTS-01/02 全部通过
- 无幽灵命中风险
- rowid 对齐通过触发器保证

**推荐 PR 标题**:
```
PR-0126-2026-2-hotfix: Fix FTS5 Triggers + P2 Vector Rerank
```

**PR 验证命令** (不需要手工 sqlite3):
```bash
# 用户友好的验证步骤
uv run agentos kb repair --rebuild-fts
uv run agentos kb refresh
uv run agentos kb search "authentication" --top-k 3
uv run python scripts/gates/kb_gate_fts_01_triggers.py
uv run python scripts/gates/kb_gate_fts_02_search.py
```

---

**Final Status**: ✅ **3/3 验证通过** - Hotfix 准入
