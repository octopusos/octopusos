# AgentOS Database Architecture

## 概述

AgentOS 使用灵活的数据库架构，支持 SQLite（开发环境）和 PostgreSQL（生产环境）。

## 数据库类型对比

| 特性 | SQLite | PostgreSQL |
|------|--------|------------|
| **并发模型** | 单写者（锁定整个数据库） | MVCC（多版本并发控制） |
| **最大并发** | 低（频繁锁定） | 高（无锁读写） |
| **适用场景** | 开发、原型、单用户 | 生产、多用户、高并发 |
| **部署复杂度** | 低（单文件） | 中（客户端-服务器） |
| **性能** | 小数据量快速 | 大数据量优化 |
| **数据完整性** | 基础约束 | 完整的 ACID + 约束 |
| **扩展性** | 受限 | 优秀（复制、分区） |
| **备份** | 文件复制 | 多种方案 |

## 数据库 Schema

### 核心表

#### 1. tasks - 任务表
```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,           -- ULID
    title TEXT NOT NULL,
    status TEXT DEFAULT 'created',
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    metadata TEXT,                      -- JSON
    -- Router 字段
    route_plan_json TEXT,
    requirements_json TEXT,
    selected_instance_id TEXT,
    router_version TEXT
);
```

#### 2. task_lineage - 任务溯源
```sql
CREATE TABLE task_lineage (
    lineage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    kind TEXT NOT NULL,                 -- nl_request|intent|execution_request|commit
    ref_id TEXT NOT NULL,
    phase TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);
```

#### 3. task_audits - 审计日志
```sql
CREATE TABLE task_audits (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    repo_id TEXT,
    level TEXT DEFAULT 'info',          -- info|warning|error
    event_type TEXT NOT NULL,
    payload TEXT,                       -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Supervisor 字段
    decision_id TEXT,
    source_event_ts TEXT,
    supervisor_processed_at TEXT,
    -- Guardian 字段
    verdict_id TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);
```

#### 4. projects - 项目表
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- v25 新增字段
    name TEXT NOT NULL DEFAULT '',
    description TEXT,
    status TEXT DEFAULT 'active',       -- active|archived|deleted
    tags TEXT,                          -- JSON array
    default_repo_id TEXT,
    default_workdir TEXT,
    settings TEXT,                      -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);
```

#### 5. webui_sessions - WebUI 会话
```sql
CREATE TABLE webui_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT                       -- JSON
);
```

#### 6. webui_messages - WebUI 消息
```sql
CREATE TABLE webui_messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,                 -- user|assistant|system
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata TEXT,                      -- JSON
    FOREIGN KEY (session_id) REFERENCES webui_sessions(session_id) ON DELETE CASCADE
);
```

### 多仓库支持 (Multi-Repo)

#### 7. project_repos - 项目仓库关联
```sql
CREATE TABLE project_repos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    repo_id TEXT NOT NULL,
    repo_path TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, repo_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

#### 8. task_repo_scope - 任务仓库访问范围
```sql
CREATE TABLE task_repo_scope (
    scope_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    repo_id TEXT NOT NULL,
    scope TEXT DEFAULT 'full',          -- full|paths|read_only
    path_filters TEXT,                  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);
```

#### 9. task_dependency - 任务依赖关系
```sql
CREATE TABLE task_dependency (
    dependency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    depends_on_task_id TEXT NOT NULL,
    dependency_type TEXT DEFAULT 'blocks', -- blocks|requires|suggests
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    metadata TEXT,
    UNIQUE(task_id, depends_on_task_id)
);
```

#### 10. task_artifact_ref - 任务产物引用
```sql
CREATE TABLE task_artifact_ref (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    repo_id TEXT NOT NULL,
    ref_type TEXT NOT NULL,             -- commit|branch|pr|patch|file|tag
    ref_value TEXT NOT NULL,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);
```

### 治理系统 (Governance)

#### 11. guardian_verdicts - Guardian 审查结果
```sql
CREATE TABLE guardian_verdicts (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    triggered_by TEXT NOT NULL,         -- event name
    policy_json TEXT NOT NULL,          -- JSON
    decision TEXT NOT NULL,             -- approve|reject|warn
    reasons_json TEXT,                  -- JSON array
    created_at TEXT NOT NULL
);
```

#### 12. supervisor_inbox - Supervisor 收件箱
```sql
CREATE TABLE supervisor_inbox (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_ts TEXT NOT NULL,
    payload_json TEXT,
    status TEXT DEFAULT 'pending',      -- pending|processing|processed|failed
    processed_at TEXT,
    created_at TEXT NOT NULL
);
```

### 知识库 (Knowledge Base)

#### 13. kb_sources - 知识库源
```sql
CREATE TABLE kb_sources (
    source_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source_type TEXT NOT NULL,          -- file|directory|url
    source_path TEXT NOT NULL,
    indexed_at TEXT,
    metadata TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

#### 14. kb_chunks - 知识库分块
```sql
CREATE TABLE kb_chunks (
    chunk_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES kb_sources(source_id) ON DELETE CASCADE
);
```

#### 15. kb_embeddings - 向量嵌入
```sql
CREATE TABLE kb_embeddings (
    chunk_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,            -- Serialized vector
    model_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES kb_chunks(chunk_id) ON DELETE CASCADE
);
```

### 内存系统 (Memory)

#### 16. memory_items - 记忆项
```sql
CREATE TABLE memory_items (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,                -- global|project|repo|task|agent
    type TEXT NOT NULL,                 -- decision|convention|constraint|known_issue
    content TEXT NOT NULL,              -- JSON
    tags TEXT,                          -- JSON array
    sources TEXT,                       -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence REAL DEFAULT 0.5,
    project_id TEXT,
    last_used_at TIMESTAMP,
    use_count INTEGER DEFAULT 0,
    retention_type TEXT DEFAULT 'project',
    expires_at TIMESTAMP,
    auto_cleanup INTEGER DEFAULT 1,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

## 索引策略

### 高频查询索引

```sql
-- 任务查询
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_session ON tasks(session_id);
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);

-- 审计日志查询
CREATE INDEX idx_task_audits_task ON task_audits(task_id);
CREATE INDEX idx_task_audits_created ON task_audits(created_at DESC);
CREATE INDEX idx_task_audits_event ON task_audits(event_type);

-- WebUI 会话查询
CREATE INDEX idx_sessions_user_updated ON webui_sessions(user_id, updated_at DESC);
CREATE INDEX idx_messages_session_created ON webui_messages(session_id, created_at ASC);

-- 项目查询
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_status_created ON projects(status, created_at DESC);
```

### 全文搜索索引 (FTS5)

```sql
-- Memory FTS
CREATE VIRTUAL TABLE memory_fts USING fts5(
    id UNINDEXED,
    content,
    tags,
    content='memory_items',
    content_rowid='rowid'
);

-- KB Chunks FTS
CREATE VIRTUAL TABLE kb_chunks_fts USING fts5(
    chunk_id UNINDEXED,
    content,
    content='kb_chunks',
    content_rowid='rowid'
);
```

## 性能优化

### SQLite 优化

```sql
-- WAL 模式（提升并发）
PRAGMA journal_mode=WAL;

-- 正常同步（平衡性能和安全）
PRAGMA synchronous=NORMAL;

-- 增加锁超时
PRAGMA busy_timeout=5000;

-- 启用外键约束
PRAGMA foreign_keys=ON;
```

### PostgreSQL 优化

```sql
-- 连接池配置
pool_size = 10
max_overflow = 20
pool_timeout = 30
pool_recycle = 3600

-- 查询优化
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
```

## 数据完整性

### 外键约束

```sql
-- 级联删除（清理孤立数据）
FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE

-- 级联更新（保持引用一致）
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
```

### 检查约束

```sql
-- 状态枚举
CHECK (status IN ('active', 'archived', 'deleted'))

-- JSON 验证（SQLite 触发器）
CREATE TRIGGER check_projects_tags_json_insert
BEFORE INSERT ON projects
FOR EACH ROW
WHEN NEW.tags IS NOT NULL
BEGIN
    SELECT CASE
        WHEN json_valid(NEW.tags) = 0
        THEN RAISE(ABORT, 'Invalid tags: must be valid JSON')
    END;
END;
```

### 唯一约束

```sql
-- 防止重复
UNIQUE(project_id, repo_id)
UNIQUE(task_id, depends_on_task_id)
```

## 迁移策略

### 1. Schema 版本管理

```sql
CREATE TABLE schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

当前版本：`0.25.0`

### 2. 迁移文件命名

```
agentos/store/migrations/
├── schema_v01.sql  # 初始 schema
├── schema_v02.sql  # 添加 memory_items
├── schema_v03.sql  # 添加 task_runs
├── ...
├── schema_v25.sql  # 项目元数据增强
```

### 3. 自动迁移

```python
from agentos.store import ensure_migrations

# 应用所有未执行的迁移
migrated = ensure_migrations()
print(f"Applied {migrated} migrations")
```

## 备份策略

### SQLite 备份

```bash
# 文件复制
cp ./store/registry.sqlite ./backups/registry-$(date +%Y%m%d).sqlite

# SQLite 备份命令
sqlite3 ./store/registry.sqlite ".backup ./backups/registry.sqlite"
```

### PostgreSQL 备份

```bash
# 逻辑备份
pg_dump -h localhost -U agentos agentos > backup.sql

# 压缩备份
pg_dump -h localhost -U agentos agentos | gzip > backup.sql.gz

# 恢复
psql -h localhost -U agentos agentos < backup.sql
```

## 故障恢复

### SQLite 恢复

```bash
# 检查数据库完整性
sqlite3 ./store/registry.sqlite "PRAGMA integrity_check;"

# 导出并重建
sqlite3 ./store/registry.sqlite ".dump" | sqlite3 new.sqlite
mv new.sqlite ./store/registry.sqlite
```

### PostgreSQL 恢复

```bash
# 恢复备份
psql -h localhost -U agentos agentos < backup.sql

# 从损坏中恢复
pg_resetwal -f /var/lib/postgresql/data
```

## 性能监控

### SQLite 监控

```bash
# 数据库大小
ls -lh ./store/registry.sqlite

# 表统计
sqlite3 ./store/registry.sqlite "SELECT name, COUNT(*) FROM sqlite_master WHERE type='table';"
```

### PostgreSQL 监控

```sql
-- 数据库大小
SELECT pg_size_pretty(pg_database_size('agentos'));

-- 表大小
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 连接统计
SELECT count(*), state
FROM pg_stat_activity
WHERE datname = 'agentos'
GROUP BY state;
```

## 安全性

### 1. 密码管理

```bash
# 环境变量
export DATABASE_PASSWORD=strong_password_here

# 或使用 .env 文件
echo "DATABASE_PASSWORD=strong_password_here" >> .env
```

### 2. 权限控制

```sql
-- PostgreSQL 用户权限
CREATE USER agentos WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE agentos TO agentos;
```

### 3. 连接加密

```bash
# PostgreSQL SSL
DATABASE_HOST=db.example.com?sslmode=require
```

## 参考资料

- [SQLite 文档](https://www.sqlite.org/docs.html)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)
- [AgentOS 迁移指南](../deployment/DATABASE_MIGRATION.md)
- [Schema 迁移说明](../../agentos/store/migrations/README.md)
