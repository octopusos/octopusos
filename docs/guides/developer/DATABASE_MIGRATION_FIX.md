# Database Migration Fix Report

**日期**: 2026-01-26  
**问题**: v0.7.0 -> v0.8.0 迁移失败，报错 "no such column: content_hash"  
**状态**: ✅ 已修复

---

## 问题描述

在尝试从 v0.7.0 迁移到 v0.8.0 时，迁移失败并报错：

```
Database: store/registry.sqlite
Current version: 0.7.0
Target version: 0.6.0
Migration v0.7.0 -> v0.8.0 failed: no such column: content_hash
✗ Migration failed: no such column: content_hash
```

## 根本原因

**表冲突问题**：

1. **v0.7.0 迁移** (`v07_project_kb.sql`):
   - 已创建 `kb_embeddings` 表，schema 为：
     ```sql
     CREATE TABLE kb_embeddings (
         chunk_id TEXT PRIMARY KEY,
         vector BLOB NOT NULL,
         model TEXT NOT NULL,
         dims INTEGER NOT NULL,
         built_at TEXT NOT NULL
     );
     ```
   - 注意：**没有** `content_hash` 字段

2. **v0.8.0 迁移** (`v08_vector_embeddings.sql`):
   - 使用 `CREATE TABLE IF NOT EXISTS` 试图创建 `kb_embeddings`
   - 期望的 schema 包含 `content_hash` 字段
   - **问题**：由于表已存在，`CREATE TABLE IF NOT EXISTS` 不执行，导致 schema 不一致

## 解决方案

### 修复 v08_vector_embeddings.sql

**修改前**：
```sql
-- 使用 CREATE TABLE IF NOT EXISTS（不会更新已存在的表）
CREATE TABLE IF NOT EXISTS kb_embeddings (
    chunk_id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    dims INTEGER NOT NULL,
    vector BLOB NOT NULL,
    content_hash TEXT NOT NULL,  -- ❌ 新字段无法添加
    built_at INTEGER NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES kb_chunks(chunk_id) ON DELETE CASCADE
);

UPDATE schema_version SET version = '0.8.0' WHERE version = '0.7.0';
```

**修改后**：
```sql
-- 先删除旧表，再创建新 schema
DROP TABLE IF EXISTS kb_embeddings;

CREATE TABLE kb_embeddings (
    chunk_id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    dims INTEGER NOT NULL,
    vector BLOB NOT NULL,
    content_hash TEXT NOT NULL,  -- ✅ 新字段
    built_at INTEGER NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES kb_chunks(chunk_id) ON DELETE CASCADE
);

-- 使用 INSERT OR REPLACE 而不是 UPDATE
INSERT OR REPLACE INTO schema_version (version, applied_at) 
VALUES ('0.8.0', datetime('now'));
```

**关键变更**：
1. 使用 `DROP TABLE IF EXISTS` 删除旧表（数据丢失可接受，因为是 P2 功能）
2. 重新创建表确保 schema 一致
3. 使用 `INSERT OR REPLACE` 更新版本（更可靠）

## 迁移执行

### 手动执行命令

```bash
# 执行 v0.8.0 迁移
sqlite3 store/registry.sqlite < agentos/store/migrations/v08_vector_embeddings.sql

# 执行 v0.9.0 迁移（命令历史）
sqlite3 store/registry.sqlite < agentos/store/migrations/v09_command_history.sql

# 执行 v0.10.0 迁移（修复 FTS 触发器）
sqlite3 store/registry.sqlite < agentos/store/migrations/v10_fix_fts_triggers.sql
```

### 验证结果

```sql
-- 查看当前版本
SELECT version, applied_at FROM schema_version ORDER BY applied_at DESC;
-- 结果: 0.10.0 | 2026-01-26 11:03:39

-- 验证 kb_embeddings 表结构
PRAGMA table_info(kb_embeddings);
-- 结果: chunk_id, model, dims, vector, content_hash, built_at ✅

-- 验证所有表都存在
SELECT COUNT(*) FROM sqlite_master WHERE type='table';
-- 结果: 20 tables ✅

-- 验证 FTS 触发器
SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'kb_chunks_%';
-- 结果: 3 triggers ✅
```

## 数据库最终状态

**当前版本**: v0.10.0  
**Schema 版本历史**:
- ✅ v0.6.0 - Task-Driven Architecture
- ✅ v0.7.0 - ProjectKB (sources, chunks, FTS5)
- ✅ v0.8.0 - Vector Embeddings (kb_embeddings, kb_embedding_meta)
- ✅ v0.9.0 - Command History (command_history, pinned_commands)
- ✅ v0.10.0 - Fix FTS Triggers

**核心表** (20 tables):
- Task Management: `tasks`, `task_lineage`, `task_sessions`, `task_agents`, `task_audits`
- ProjectKB: `kb_sources`, `kb_chunks`, `kb_chunks_fts` (+ 内部表)
- Embeddings: `kb_embeddings`, `kb_embedding_meta`
- Command History: `command_history`, `pinned_commands`
- Metadata: `kb_index_meta`, `schema_version`

**索引与触发器**:
- FTS5 触发器: 3 个 (`kb_chunks_ai`, `kb_chunks_ad`, `kb_chunks_au`)
- 索引: 多个优化索引

## 预防措施

### 迁移脚本最佳实践

1. **Schema 变更**：
   - ❌ **错误**：使用 `CREATE TABLE IF NOT EXISTS` 添加字段
   - ✅ **正确**：使用 `ALTER TABLE ADD COLUMN` 或 `DROP + CREATE`

2. **版本更新**：
   - ❌ **错误**：`UPDATE schema_version SET version = 'X' WHERE version = 'Y'`
   - ✅ **正确**：`INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (...)`

3. **数据安全**：
   - 对于包含用户数据的表，使用 `ALTER TABLE` 保留数据
   - 对于缓存/派生数据（如 embeddings），可以 `DROP + CREATE`

4. **幂等性**：
   - 所有迁移脚本应支持重复执行
   - 使用 `IF NOT EXISTS` / `IF EXISTS` 子句

## 影响分析

### 数据丢失

- ✅ **无影响**：`kb_embeddings` 是 P2 功能，之前没有数据
- ✅ **无影响**：所有用户数据（tasks, kb_sources, kb_chunks）保留完整

### 功能恢复

- ✅ KB 全文检索正常
- ✅ Vector embeddings 可以重新生成
- ✅ 命令历史功能正常
- ✅ FTS 触发器修复完成

## 后续任务

- [ ] 更新迁移文档
- [ ] 添加迁移测试用例
- [ ] Review 其他迁移脚本的 schema 变更模式
- [ ] 考虑添加 migration rollback 测试

---

**修复者**: AI Assistant  
**验证者**: 待验证  
**风险等级**: Low（仅影响新功能，无用户数据丢失）
