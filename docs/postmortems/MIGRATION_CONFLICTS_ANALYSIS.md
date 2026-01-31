# 数据库迁移文件冲突与依赖分析报告

**生成时间**: 2026-01-29
**分析范围**: `/Users/pangge/PycharmProjects/AgentOS/agentos/store/migrations/schema_v*.sql`
**文件数量**: 23 个迁移文件 (v01-v23)

---

## 执行摘要

通过对所有 23 个数据库迁移文件的全面分析，发现以下关键问题：

- **P0-CRITICAL**: 1 个严重表名冲突
- **P1-HIGH**: 1 个高优先级冲突（已部分处理）
- **P2-MEDIUM**: 1 个设计一致性问题
- **外键依赖**: 所有外键依赖关系正常 ✅
- **session_id 引用**: 所有 session_id 外键正常 ✅

---

## 1. 表名冲突问题

### 1.1 artifacts 表冲突 [P0-CRITICAL]

**问题描述**:
`artifacts` 表在两个不同版本中被定义，且结构完全不同：

#### schema_v01.sql (行 44)
```sql
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    type TEXT NOT NULL, -- 'factpack' | 'agent_spec' | 'agent_md'
    path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);
```
**用途**: 存储 run 执行的产物（factpack、agent_spec 等）

#### schema_v11.sql (行 12)
```sql
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,  -- ULID
    artifact_type TEXT NOT NULL,  -- summary|requirements|decision|plan|analysis
    session_id TEXT,  -- Optional: associated chat session
    task_id TEXT,  -- Optional: associated task
    title TEXT,
    content TEXT NOT NULL,  -- Main content (text)
    content_json TEXT,  -- Optional: structured content (JSON)
    version INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL,  -- Unix epoch milliseconds
    created_by TEXT NOT NULL DEFAULT 'system',
    metadata TEXT,

    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);
```
**用途**: 存储聊天会话中的结构化产物（summary、requirements 等）

**影响**:
- ⚠️ 使用 `CREATE TABLE IF NOT EXISTS` 会导致 v11 的定义被忽略
- ⚠️ v11 的代码假设表有 `artifact_id`、`session_id`、`task_id` 等列，但实际表是 v01 的结构
- ⚠️ 外键约束不同：v01 引用 `runs`，v11 引用 `chat_sessions` 和 `tasks`
- ❌ 这会导致 v11 相关功能完全无法正常工作

**修复方案**:

**推荐方案 1**: 重命名 v11 的表（语义更清晰）
```sql
-- 在 schema_v11.sql 中修改
CREATE TABLE IF NOT EXISTS chat_artifacts (  -- 或 context_artifacts
    artifact_id TEXT PRIMARY KEY,
    -- ... 其余字段保持不变
);
```

**方案 2**: 重命名 v01 的表
```sql
-- 在 schema_v01.sql 中修改
CREATE TABLE IF NOT EXISTS run_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- ... 其余字段保持不变
);
```

**方案 3**: 添加迁移逻辑
```sql
-- 在 schema_v11.sql 开头添加
ALTER TABLE artifacts RENAME TO run_artifacts;
CREATE TABLE IF NOT EXISTS artifacts (...);
```

**建议**: 使用方案 1，将 v11 的表重命名为 `chat_artifacts`，因为：
1. 语义更清晰，避免与 v01 的 run artifacts 混淆
2. 不影响已有数据
3. 代码修改范围更小（只需修改 v11 相关代码）

---

### 1.2 kb_embeddings 表冲突 [P1-HIGH]

**问题描述**:
`kb_embeddings` 表在 v07 和 v08 中都有定义：

#### schema_v07.sql (行 82)
```sql
CREATE TABLE IF NOT EXISTS kb_embeddings (
    chunk_id TEXT PRIMARY KEY,
    vector BLOB NOT NULL,               -- 向量数据 (序列化为 bytes)
    model TEXT NOT NULL,                -- 模型标识
    dims INTEGER NOT NULL,              -- 向量维度
    built_at TEXT NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES kb_chunks(chunk_id) ON DELETE CASCADE
);
```

#### schema_v08.sql (行 50-53)
```sql
-- Drop the old kb_embeddings table if it exists with old schema
DROP TABLE IF EXISTS kb_embeddings;

-- Create new kb_embeddings table with proper schema
CREATE TABLE kb_embeddings (
    chunk_id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    dims INTEGER NOT NULL,
    vector BLOB NOT NULL,
    content_hash TEXT NOT NULL,  -- 新增字段
    built_at INTEGER NOT NULL,   -- 类型从 TEXT 改为 INTEGER
    FOREIGN KEY (chunk_id) REFERENCES kb_chunks(chunk_id) ON DELETE CASCADE
);
```

**影响**:
- ✅ v08 使用 `DROP TABLE IF EXISTS` 主动处理了冲突
- ⚠️ 但这会导致 v07 的数据丢失
- ⚠️ 字段变化：新增 `content_hash`，`built_at` 类型改变

**现状**: 已部分处理（使用 DROP TABLE），但缺少数据迁移逻辑

**修复建议**:
```sql
-- 在 schema_v08.sql 的 DROP TABLE 之前添加数据迁移
-- 1. 备份旧数据到临时表
CREATE TEMP TABLE kb_embeddings_backup AS SELECT * FROM kb_embeddings;

-- 2. 删除旧表
DROP TABLE IF EXISTS kb_embeddings;

-- 3. 创建新表
CREATE TABLE kb_embeddings (...);

-- 4. 迁移数据（如果需要）
INSERT INTO kb_embeddings (chunk_id, model, dims, vector, content_hash, built_at)
SELECT
    chunk_id,
    model,
    dims,
    vector,
    '', -- content_hash 使用空字符串或重新计算
    strftime('%s', built_at) -- 转换时间戳格式
FROM kb_embeddings_backup;
```

---

### 1.3 schema_version 表重复定义 [P2-MEDIUM]

**问题描述**:
`schema_version` 表在多个文件中重复定义：

- schema_v01.sql:9
- schema_v04.sql:102
- schema_v06.sql:117
- schema_v23.sql:9

**影响**:
- ✅ 使用 `IF NOT EXISTS` 可以避免运行时错误
- ⚠️ 但设计不一致，违反 DRY 原则
- ⚠️ 增加维护成本

**修复建议**:
```sql
-- 方案：只在 v01 中定义，其他文件移除 CREATE TABLE 语句

-- schema_v01.sql (保留)
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- schema_v04.sql, v06.sql, v23.sql (移除 CREATE TABLE，只保留 INSERT)
-- 移除:
-- CREATE TABLE IF NOT EXISTS schema_version (...);

-- 保留:
INSERT OR REPLACE INTO schema_version (version) VALUES ('0.X.0');
```

---

## 2. 外键依赖关系分析

### 2.1 总体状态: ✅ 正常

所有外键依赖关系均正常，目标表在外键定义之前已经创建。

### 2.2 session_id 列引用检查

所有 `session_id` 相关的外键引用均正常：

| 源表 | 目标表 | 版本 | 文件 | 状态 |
|------|--------|------|------|------|
| tasks | task_sessions | v06 | schema_v06.sql:19 | ✅ |
| chat_messages | chat_sessions | v08 | schema_v08.sql:34 | ✅ |
| artifacts | chat_sessions | v11 | schema_v11.sql:25 | ✅ |
| context_snapshots | chat_sessions | v11 | schema_v11.sql:69 | ✅ |

**说明**:
- `task_sessions` 在 v06 定义，`tasks` 在同一版本引用 ✅
- `chat_sessions` 在 v08 定义，`chat_messages` 在同一版本引用 ✅
- v11 的 `artifacts` 和 `context_snapshots` 引用 `chat_sessions` 正常 ✅

---

## 3. ALTER TABLE 语句分析

所有 `ALTER TABLE` 语句均正常，目标表在 ALTER 之前已经定义：

| 表名 | 操作 | 版本 | 文件 | 状态 |
|------|------|------|------|------|
| memory_items | ADD COLUMN last_used_at | v04 | schema_v04.sql:10 | ✅ |
| memory_items | ADD COLUMN use_count | v04 | schema_v04.sql:11 | ✅ |
| memory_items | ADD COLUMN retention_type | v04 | schema_v04.sql:12 | ✅ |
| memory_items | ADD COLUMN expires_at | v04 | schema_v04.sql:13 | ✅ |
| memory_items | ADD COLUMN auto_cleanup | v04 | schema_v04.sql:14 | ✅ |
| tasks | ADD COLUMN route_plan_json | v12 | schema_v12.sql:5 | ✅ |
| tasks | ADD COLUMN requirements_json | v12 | schema_v12.sql:6 | ✅ |
| tasks | ADD COLUMN selected_instance_id | v12 | schema_v12.sql:7 | ✅ |
| tasks | ADD COLUMN router_version | v12 | schema_v12.sql:8 | ✅ |
| task_audits | ADD COLUMN decision_id | v15 | schema_v15.sql:28 | ✅ |
| task_audits | ADD COLUMN source_event_ts | v15 | schema_v15.sql:66 | ✅ |
| task_audits | ADD COLUMN supervisor_processed_at | v15 | schema_v15.sql:70 | ✅ |
| task_audits | ADD COLUMN verdict_id | v17 | schema_v17.sql:65 | ✅ |
| task_audits | ADD COLUMN repo_id | v20 | schema_v20.sql:11 | ✅ |
| task_audits | ADD COLUMN source_event_ts | v21 | schema_v21.sql:21 | ⚠️ 重复 |
| task_audits | ADD COLUMN supervisor_processed_at | v21 | schema_v21.sql:22 | ⚠️ 重复 |

**注意**: v21 中重复添加了 v15 已经添加的列，但 SQLite 会忽略已存在的列（如果使用 `IF NOT EXISTS`）。

---

## 4. 完整表清单（按版本排序）

| 表名 | 版本 | 文件 | 冲突 |
|------|------|------|------|
| schema_version | v01 | schema_v01.sql:9 | ⚠️ 多次定义 |
| projects | v01 | schema_v01.sql:18 | ✅ |
| runs | v01 | schema_v01.sql:28 | ✅ |
| artifacts | v01 | schema_v01.sql:44 | ⚠️ 与 v11 冲突 |
| memory_items | v02 | schema_v02.sql:9 | ✅ |
| task_runs | v02 | schema_v02.sql:28 | ✅ |
| run_steps | v02 | schema_v02.sql:48 | ✅ |
| patches | v02 | schema_v02.sql:62 | ✅ |
| commit_links | v02 | schema_v02.sql:76 | ✅ |
| file_locks | v02 | schema_v02.sql:91 | ✅ |
| task_dependencies | v02 | schema_v02.sql:110 | ✅ |
| task_conflicts | v02 | schema_v02.sql:119 | ✅ |
| failure_packs | v03 | schema_v03.sql:5 | ✅ |
| learning_packs | v03 | schema_v03.sql:24 | ✅ |
| policy_lineage | v03 | schema_v03.sql:41 | ✅ |
| run_tapes | v03 | schema_v03.sql:60 | ✅ |
| resource_usage | v03 | schema_v03.sql:72 | ✅ |
| healing_actions | v03 | schema_v03.sql:85 | ✅ |
| memory_audit_log | v04 | schema_v04.sql:20 | ✅ |
| memory_gc_runs | v04 | schema_v04.sql:37 | ✅ |
| content_registry | v05 | schema_v05.sql:9 | ✅ |
| content_lineage | v05 | schema_v05.sql:50 | ✅ |
| content_audit_log | v05 | schema_v05.sql:69 | ✅ |
| tasks | v06 | schema_v06.sql:9 | ✅ |
| task_lineage | v06 | schema_v06.sql:30 | ✅ |
| task_sessions | v06 | schema_v06.sql:56 | ✅ |
| task_agents | v06 | schema_v06.sql:71 | ✅ |
| task_audits | v06 | schema_v06.sql:97 | ✅ |
| kb_sources | v07 | schema_v07.sql:7 | ✅ |
| kb_chunks | v07 | schema_v07.sql:22 | ✅ |
| kb_index_meta | v07 | schema_v07.sql:67 | ✅ |
| kb_embeddings | v07 | schema_v07.sql:82 | ⚠️ 被 v08 替换 |
| chat_sessions | v08 | schema_v08.sql:10 | ✅ |
| chat_messages | v08 | schema_v08.sql:26 | ✅ |
| kb_embeddings | v08 | schema_v08.sql:53 | ⚠️ 替换 v07 |
| kb_embedding_meta | v08 | schema_v08.sql:70 | ✅ |
| command_history | v09 | schema_v09.sql:5 | ✅ |
| pinned_commands | v09 | schema_v09.sql:26 | ✅ |
| artifacts | v11 | schema_v11.sql:12 | ⚠️ 与 v01 冲突 |
| context_snapshots | v11 | schema_v11.sql:44 | ✅ |
| context_snapshot_items | v11 | schema_v11.sql:87 | ✅ |
| schema_capabilities | v11 | schema_v11.sql:110 | ✅ |
| snippets | v13 | schema_v13.sql:8 | ✅ |
| snippet_notes | v13 | schema_v13.sql:23 | ✅ |
| supervisor_inbox | v14 | schema_v14.sql:9 | ✅ |
| supervisor_checkpoint | v14 | schema_v14.sql:36 | ✅ |
| lead_findings | v16 | schema_v16.sql:9 | ✅ |
| guardian_assignments | v17 | schema_v17.sql:9 | ✅ |
| guardian_verdicts | v17 | schema_v17.sql:34 | ✅ |
| project_repos | v18 | schema_v18.sql:9 | ✅ |
| task_repo_scope | v18 | schema_v18.sql:54 | ✅ |
| task_dependency | v18 | schema_v18.sql:91 | ✅ |
| task_artifact_ref | v18 | schema_v18.sql:132 | ✅ |
| auth_profiles | v19 | schema_v19.sql:9 | ✅ |
| auth_profile_usage | v19 | schema_v19.sql:57 | ✅ |
| encryption_keys | v19 | schema_v19.sql:88 | ✅ |
| guardian_reviews | v22 | schema_v22.sql:11 | ✅ |
| content_items | v23 | schema_v23.sql:17 | ✅ |
| answer_packs | v23 | schema_v23.sql:54 | ✅ |
| answer_pack_links | v23 | schema_v23.sql:79 | ✅ |

**统计**:
- 总表数: 60 个（包含重复定义）
- 唯一表数: 57 个
- 表冲突: 3 个 (artifacts, kb_embeddings, schema_version)

---

## 5. 修复优先级与行动计划

### 优先级 P0 (CRITICAL) - 必须立即修复

#### ✅ Task #1: 修复 artifacts 表冲突
- **文件**: schema_v11.sql
- **操作**: 重命名表为 `chat_artifacts`
- **影响范围**: 需要修改引用此表的所有代码
- **预估工作量**: 2-4 小时

**修复步骤**:
1. 修改 `schema_v11.sql`，将 `artifacts` 改为 `chat_artifacts`
2. 全局搜索代码中的 `artifacts` 表引用，更新为 `chat_artifacts`
3. 更新相关的 Python 模型类（如果有）
4. 更新索引名称（`idx_artifacts_*` -> `idx_chat_artifacts_*`）
5. 添加测试验证

**相关文件**（需要代码搜索确认）:
```bash
grep -r "artifacts" agentos/core/chat/
grep -r "artifacts" agentos/core/supervisor/
```

---

### 优先级 P1 (HIGH) - 应尽快修复

#### ✅ Task #2: 添加 kb_embeddings 数据迁移
- **文件**: schema_v08.sql
- **操作**: 添加数据迁移逻辑
- **影响范围**: 现有 kb_embeddings 数据
- **预估工作量**: 1-2 小时

**修复步骤**:
1. 在 `DROP TABLE` 之前添加临时表备份
2. 添加数据转换逻辑（处理 `content_hash` 和 `built_at` 类型变化）
3. 添加回滚机制
4. 测试迁移脚本

---

### 优先级 P2 (MEDIUM) - 建议修复

#### ✅ Task #3: 清理 schema_version 重复定义
- **文件**: schema_v04.sql, schema_v06.sql, schema_v23.sql
- **操作**: 移除重复的 `CREATE TABLE` 语句
- **影响范围**: 无（仅清理代码）
- **预估工作量**: 30 分钟

**修复步骤**:
1. 保留 `schema_v01.sql` 中的定义
2. 移除其他文件中的 `CREATE TABLE IF NOT EXISTS schema_version` 语句
3. 保留所有文件中的 `INSERT OR REPLACE INTO schema_version` 语句

---

#### ✅ Task #4: 修复 v21 重复 ALTER TABLE
- **文件**: schema_v21.sql
- **操作**: 移除重复的 ALTER TABLE 语句或添加检查
- **影响范围**: 无（SQLite 会忽略已存在的列）
- **预估工作量**: 15 分钟

**修复步骤**:
```sql
-- 方案1: 添加条件检查（SQLite 不支持 IF NOT EXISTS for ALTER TABLE）
-- 使用 Python 代码检查列是否存在

-- 方案2: 移除 v21 中的重复语句
-- 因为 v15 已经添加了这些列
```

---

## 6. 测试建议

### 6.1 单元测试
```python
# 测试 artifacts 表冲突修复
def test_chat_artifacts_table_exists():
    """验证 chat_artifacts 表存在且结构正确"""
    db = get_db_connection()
    cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_artifacts'")
    assert cursor.fetchone() is not None

def test_run_artifacts_table_exists():
    """验证 v01 的 artifacts 表（run_artifacts）仍然存在"""
    db = get_db_connection()
    cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artifacts'")
    assert cursor.fetchone() is not None
```

### 6.2 迁移测试
```bash
# 1. 从空数据库测试完整迁移
rm test.db
python agentos/store/migrate.py --db test.db --target v23

# 2. 测试增量迁移
# 创建 v10 数据库
python agentos/store/migrate.py --db test_v10.db --target v10
# 迁移到 v23
python agentos/store/migrate.py --db test_v10.db --target v23
```

---

## 7. 附录

### 7.1 完整外键依赖图

```
projects
  └─> runs (v01)
  └─> memory_items (v02)
  └─> task_runs (v02)
  └─> project_repos (v18)

runs
  └─> artifacts (v01)

tasks (v06)
  └─> task_lineage (v06)
  └─> task_agents (v06)
  └─> task_audits (v06)
  └─> chat_sessions (v08)
  └─> artifacts (v11)
  └─> supervisor_inbox (v14)
  └─> guardian_assignments (v17)
  └─> guardian_verdicts (v17)
  └─> task_repo_scope (v18)
  └─> task_dependency (v18)
  └─> task_artifact_ref (v18)

task_sessions (v06)
  └─> tasks (v06)

chat_sessions (v08)
  └─> chat_messages (v08)
  └─> artifacts (v11)
  └─> context_snapshots (v11)

kb_sources (v07)
  └─> kb_chunks (v07)
      └─> kb_embeddings (v07, v08)

... (其他依赖关系见完整分析)
```

### 7.2 分析脚本

本报告使用以下 Python 脚本生成：
- `/tmp/analyze_schema.py` - 表冲突和外键分析
- `/tmp/dependency_analysis.py` - 完整依赖关系分析

脚本已保存在 `/tmp` 目录，可重新运行以验证修复结果。

---

## 8. 总结

### 关键发现
1. ✅ **外键依赖关系整体健康** - 所有外键引用的目标表都在引用之前定义
2. ⚠️ **artifacts 表冲突是最严重的问题** - 必须立即修复，否则 v11 功能无法正常工作
3. ⚠️ **kb_embeddings 冲突已部分处理** - 需要添加数据迁移逻辑
4. ℹ️ **schema_version 重复定义是代码清洁度问题** - 不影响功能，但应该清理

### 修复建议优先级
1. **P0**: 修复 artifacts 表冲突（重命名为 chat_artifacts）
2. **P1**: 添加 kb_embeddings 数据迁移逻辑
3. **P2**: 清理 schema_version 重复定义
4. **P2**: 修复 v21 重复 ALTER TABLE

### 风险评估
- **当前风险**: HIGH - artifacts 表冲突会导致功能失效
- **修复后风险**: LOW - 所有依赖关系正常

---

**生成工具**: Claude Code + Python 脚本分析
**报告版本**: 1.0
**最后更新**: 2026-01-29
