# Database Quick Reference Card

## 快速决策树

```
需要部署 AgentOS？
│
├─ 单用户、本地开发？
│  └─ ✅ 使用 SQLite（默认）
│     无需配置
│
└─ 多用户、生产环境？
   └─ ✅ 使用 PostgreSQL
      需要配置服务器
```

## 一分钟快速启动

### SQLite (开发)

```bash
# 就这么简单
uv run agentos init
```

### PostgreSQL (生产)

```bash
# 1. 启动数据库
docker-compose up -d postgres

# 2. 配置环境
cat > .env <<EOF
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=agentos
DATABASE_USER=agentos
DATABASE_PASSWORD=changeme
EOF

# 3. 初始化
uv run agentos init
```

## 环境变量速查

### SQLite

```bash
DATABASE_TYPE=sqlite
SQLITE_PATH=./store/registry.sqlite
```

### PostgreSQL

```bash
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=agentos
DATABASE_USER=agentos
DATABASE_PASSWORD=your_password
```

## 常用命令

### 数据库状态检查

```bash
# SQLite
ls -lh ./store/registry.sqlite

# PostgreSQL
psql -h localhost -U agentos -d agentos -c "\dt"
```

### 备份

```bash
# SQLite
cp ./store/registry.sqlite backup.sqlite

# PostgreSQL
pg_dump -h localhost -U agentos agentos > backup.sql
```

### 数据迁移

```bash
# SQLite → PostgreSQL
python scripts/migrate_sqlite_to_postgresql.py \
  --pg-password your_password
```

## 性能基准 (参考值)

| 操作 | SQLite | PostgreSQL |
|------|--------|------------|
| 单线程写入 | ~1000 ops/s | ~2000 ops/s |
| 10线程并发写 | ~500 ops/s (锁竞争) | ~5000 ops/s |
| 查询 (50条) | ~10ms | ~5ms |
| 复杂JOIN | ~50ms | ~20ms |

## 故障排查

### 问题：database is locked

**症状**：SQLite 报 "database is locked"

**解决**：
```bash
# 方案 1：增加超时
export SQLITE_BUSY_TIMEOUT=10000

# 方案 2：切换到 PostgreSQL
export DATABASE_TYPE=postgresql
```

### 问题：连接被拒绝

**症状**：PostgreSQL 报 "connection refused"

**解决**：
```bash
# 检查服务状态
docker-compose ps postgres
docker-compose logs postgres

# 重启服务
docker-compose restart postgres
```

### 问题：认证失败

**症状**：PostgreSQL 报 "authentication failed"

**解决**：
```bash
# 检查密码
echo $DATABASE_PASSWORD

# 重置密码
docker-compose down
docker-compose up -d postgres
```

## 何时迁移？

### 继续使用 SQLite

- ✅ 单用户开发
- ✅ 数据量 < 100MB
- ✅ 并发请求 < 10/秒
- ✅ 本地原型开发

### 迁移到 PostgreSQL

- ⚠️ 出现频繁的 "database is locked" 错误
- ⚠️ 多用户访问需求
- ⚠️ 数据量 > 100MB
- ⚠️ 并发请求 > 10/秒
- ⚠️ 需要数据复制/高可用

## 资源需求

### SQLite
- CPU: 任意
- RAM: 256MB
- 磁盘: 根据数据量

### PostgreSQL
- CPU: 1核+
- RAM: 512MB+ (推荐 1GB+)
- 磁盘: 根据数据量 (推荐 SSD)

## 更多信息

- 📖 [完整迁移指南](DATABASE_MIGRATION.md)
- 🏗️ [数据库架构文档](../architecture/DATABASE_ARCHITECTURE.md)
- 🔧 [环境变量配置](../../.env.example)
- 🐳 [Docker Compose配置](../../docker-compose.yml)
