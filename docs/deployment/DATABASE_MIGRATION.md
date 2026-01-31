# Database Migration Guide: SQLite to PostgreSQL

## 概述

本文档提供从 SQLite（开发环境）迁移到 PostgreSQL（生产环境）的完整指南。

## 为什么迁移到 PostgreSQL？

### SQLite 的限制

- **并发写入限制**：SQLite 使用单写者模型，只能有一个进程同时写入
- **锁定问题**：高并发场景下频繁出现 "database is locked" 错误
- **性能瓶颈**：大数据量下查询和写入性能下降
- **适用场景**：适合单用户、低并发的开发环境

### PostgreSQL 的优势

- **真正的并发**：支持多用户并发读写，MVCC 多版本并发控制
- **生产级性能**：优化的查询计划器、连接池、复制和高可用
- **扩展性**：支持大数据量、复杂查询和事务
- **企业特性**：备份恢复、监控、权限管理、审计日志

## 系统要求

### 软件依赖

```bash
# Python 包
pip install psycopg2-binary  # PostgreSQL adapter

# 可选：SQLAlchemy（未来版本支持）
# pip install sqlalchemy alembic
```

### PostgreSQL 安装

#### macOS (Homebrew)

```bash
brew install postgresql@15
brew services start postgresql@15
```

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install postgresql-15 postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Docker (推荐)

```bash
# 使用项目提供的 docker-compose.yml
docker-compose up -d postgres
```

## 快速开始

### 步骤 1：启动 PostgreSQL

#### 使用 Docker Compose (推荐)

```bash
# 1. 复制环境变量配置
cp .env.example .env

# 2. 编辑 .env 文件，设置数据库密码
# DATABASE_PASSWORD=your_secure_password

# 3. 启动 PostgreSQL
docker-compose up -d postgres

# 4. 验证 PostgreSQL 运行状态
docker-compose ps
docker-compose logs postgres
```

#### 使用本地 PostgreSQL

```bash
# 创建数据库和用户
sudo -u postgres psql

CREATE DATABASE agentos;
CREATE USER agentos WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE agentos TO agentos;
\q
```

### 步骤 2：创建 PostgreSQL Schema

**重要**：在数据迁移前，必须先在 PostgreSQL 中创建相同的表结构。

```bash
# 方式 1：使用 agentos init（推荐）
export DATABASE_TYPE=postgresql
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_NAME=agentos
export DATABASE_USER=agentos
export DATABASE_PASSWORD=your_password

agentos init

# 方式 2：手动执行 SQL 脚本
psql -h localhost -U agentos -d agentos < scripts/create_postgresql_schema.sql
```

### 步骤 3：迁移数据

```bash
# 设置环境变量
export SQLITE_PATH=./store/registry.sqlite
export DATABASE_TYPE=postgresql
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_NAME=agentos
export DATABASE_USER=agentos
export DATABASE_PASSWORD=your_password

# 运行迁移脚本
python scripts/migrate_sqlite_to_postgresql.py \
    --pg-password your_password

# 使用自定义批次大小（可选）
python scripts/migrate_sqlite_to_postgresql.py \
    --pg-password your_password \
    --batch-size 500
```

### 步骤 4：验证迁移

```bash
# 检查表数量
psql -h localhost -U agentos -d agentos -c "\dt"

# 检查行数
psql -h localhost -U agentos -d agentos -c "
SELECT
    schemaname,
    tablename,
    n_tup_ins AS row_count
FROM pg_stat_user_tables
ORDER BY tablename;
"

# 对比 SQLite 表数量
sqlite3 ./store/registry.sqlite "SELECT name FROM sqlite_master WHERE type='table';"
```

### 步骤 5：切换到 PostgreSQL

```bash
# 更新环境变量
echo "DATABASE_TYPE=postgresql" >> .env
echo "DATABASE_HOST=localhost" >> .env
echo "DATABASE_PORT=5432" >> .env
echo "DATABASE_NAME=agentos" >> .env
echo "DATABASE_USER=agentos" >> .env
echo "DATABASE_PASSWORD=your_password" >> .env

# 重启应用
agentos webui
```

## 环境变量配置

### 开发环境 (SQLite)

```bash
# .env
DATABASE_TYPE=sqlite
SQLITE_PATH=./store/registry.sqlite
SQLITE_BUSY_TIMEOUT=5000
```

### 生产环境 (PostgreSQL)

```bash
# .env
DATABASE_TYPE=postgresql
DATABASE_HOST=db.example.com
DATABASE_PORT=5432
DATABASE_NAME=agentos_prod
DATABASE_USER=agentos
DATABASE_PASSWORD=strong_password_here

# 连接池配置
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
```

## 性能调优

### PostgreSQL 配置优化

编辑 `postgresql.conf`（通常位于 `/etc/postgresql/15/main/postgresql.conf`）：

```ini
# 内存配置
shared_buffers = 256MB          # 25% of RAM (for 1GB RAM)
effective_cache_size = 1GB      # 50-75% of RAM
work_mem = 4MB                  # Per operation memory
maintenance_work_mem = 64MB     # For VACUUM, CREATE INDEX

# 并发配置
max_connections = 100
max_worker_processes = 4

# WAL 配置
wal_level = replica
max_wal_size = 1GB
min_wal_size = 80MB

# 查询优化
random_page_cost = 1.1          # For SSD
effective_io_concurrency = 200  # For SSD
```

重启 PostgreSQL：

```bash
sudo systemctl restart postgresql
```

### 连接池配置

AgentOS 自动配置连接池，可通过环境变量调整：

```bash
# 增大连接池（高并发场景）
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# 减少连接池（低并发场景）
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
```

## 故障排查

### 问题 1：连接被拒绝

**症状**：`connection refused` 或 `could not connect to server`

**解决方案**：

```bash
# 检查 PostgreSQL 是否运行
sudo systemctl status postgresql  # Linux
brew services list                # macOS
docker-compose ps                 # Docker

# 检查端口监听
netstat -an | grep 5432

# 检查防火墙
sudo ufw allow 5432/tcp  # Ubuntu
```

### 问题 2：认证失败

**症状**：`authentication failed` 或 `password authentication failed`

**解决方案**：

```bash
# 编辑 pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf

# 添加或修改以下行（开发环境）
host    all             all             127.0.0.1/32            md5

# 重启 PostgreSQL
sudo systemctl restart postgresql
```

### 问题 3：数据库不存在

**症状**：`database "agentos" does not exist`

**解决方案**：

```bash
# 连接到 PostgreSQL
sudo -u postgres psql

# 创建数据库
CREATE DATABASE agentos;

# 授予权限
GRANT ALL PRIVILEGES ON DATABASE agentos TO agentos;
```

### 问题 4：迁移失败

**症状**：`Migration failed: ...`

**解决方案**：

```bash
# 1. 检查表结构是否存在
psql -h localhost -U agentos -d agentos -c "\dt"

# 2. 清理 PostgreSQL 数据（如果需要重新迁移）
psql -h localhost -U agentos -d agentos -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO agentos;
"

# 3. 重新创建 schema
agentos init

# 4. 重新迁移数据
python scripts/migrate_sqlite_to_postgresql.py --pg-password your_password
```

## 回滚方案

如果迁移后发现问题，可以快速回滚到 SQLite：

### 方式 1：修改环境变量

```bash
# 编辑 .env 文件
DATABASE_TYPE=sqlite
SQLITE_PATH=./store/registry.sqlite

# 重启应用
agentos webui
```

### 方式 2：使用备份

```bash
# 迁移前备份 SQLite 数据库
cp ./store/registry.sqlite ./store/registry.sqlite.backup

# 回滚时恢复备份
cp ./store/registry.sqlite.backup ./store/registry.sqlite
```

## 数据库备份

### SQLite 备份

```bash
# 方式 1：文件复制
cp ./store/registry.sqlite ./backups/registry-$(date +%Y%m%d).sqlite

# 方式 2：使用 sqlite3
sqlite3 ./store/registry.sqlite ".backup ./backups/registry-$(date +%Y%m%d).sqlite"
```

### PostgreSQL 备份

```bash
# 完整备份
pg_dump -h localhost -U agentos agentos > backup-$(date +%Y%m%d).sql

# 压缩备份
pg_dump -h localhost -U agentos agentos | gzip > backup-$(date +%Y%m%d).sql.gz

# 恢复备份
psql -h localhost -U agentos agentos < backup-20260129.sql
```

### 自动备份脚本

```bash
#!/bin/bash
# backup-postgresql.sh

BACKUP_DIR="/var/backups/agentos"
DATE=$(date +%Y%m%d-%H%M%S)
FILENAME="agentos-$DATE.sql.gz"

mkdir -p $BACKUP_DIR
pg_dump -h localhost -U agentos agentos | gzip > $BACKUP_DIR/$FILENAME

# 保留最近 7 天的备份
find $BACKUP_DIR -name "agentos-*.sql.gz" -mtime +7 -delete

echo "Backup completed: $FILENAME"
```

添加到 crontab：

```bash
# 每天凌晨 2 点备份
0 2 * * * /path/to/backup-postgresql.sh
```

## 监控和维护

### 监控连接数

```sql
-- 查看当前连接
SELECT count(*), state
FROM pg_stat_activity
WHERE datname = 'agentos'
GROUP BY state;

-- 查看连接详情
SELECT pid, usename, application_name, state, query
FROM pg_stat_activity
WHERE datname = 'agentos';
```

### 数据库大小

```sql
-- 数据库总大小
SELECT pg_size_pretty(pg_database_size('agentos'));

-- 各表大小
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 定期维护

```bash
# 1. VACUUM（清理死元组）
psql -h localhost -U agentos -d agentos -c "VACUUM ANALYZE;"

# 2. 重建索引
psql -h localhost -U agentos -d agentos -c "REINDEX DATABASE agentos;"

# 3. 更新统计信息
psql -h localhost -U agentos -d agentos -c "ANALYZE;"
```

## 常见问题 (FAQ)

### Q1: SQLite 和 PostgreSQL 有什么主要区别？

**A**: 主要区别包括：
- **并发性**：PostgreSQL 支持多用户并发，SQLite 是单写者
- **性能**：PostgreSQL 针对大数据量优化，SQLite 适合小数据
- **功能**：PostgreSQL 提供更多企业级特性（复制、分区、全文搜索）
- **部署**：SQLite 是文件数据库，PostgreSQL 是客户端-服务器架构

### Q2: 迁移会丢失数据吗？

**A**: 不会。迁移脚本包含验证步骤，对比源和目标表的行数。建议迁移前备份 SQLite 数据库。

### Q3: 可以同时使用 SQLite 和 PostgreSQL 吗？

**A**: 可以。通过 `DATABASE_TYPE` 环境变量切换，但同一时间只能使用一个数据库。

### Q4: 迁移需要多长时间？

**A**: 取决于数据量：
- 小型数据库（<10MB）：< 1 分钟
- 中型数据库（10-100MB）：1-5 分钟
- 大型数据库（>100MB）：5-30 分钟

### Q5: PostgreSQL 需要多少资源？

**A**: 最低配置：
- CPU: 1 核
- 内存: 512MB（推荐 1GB+）
- 磁盘: 取决于数据量（推荐 SSD）

## 参考资料

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [psycopg2 文档](https://www.psycopg.org/docs/)
- [AgentOS 架构设计](../architecture/DATABASE_ARCHITECTURE.md)
- [环境变量配置](./.env.example)

## 支持

如有问题，请：
1. 查看故障排查章节
2. 查看 GitHub Issues
3. 提交新的 Issue 并附上日志
