# 数据库迁移快速指南

## 🚀 常用命令

```bash
# 查看当前版本
sqlite3 store/registry.sqlite "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1;"

# 执行迁移到最新版本
agentos migrate

# 执行迁移到指定版本
agentos migrate 0.8.0

# 查看所有版本历史
sqlite3 store/registry.sqlite "SELECT * FROM schema_version ORDER BY applied_at;"
```

## 📊 版本演进

| 版本 | 功能 | 关键表 |
|------|------|--------|
| v0.5.0 | 基础架构 | projects, runs, artifacts |
| v0.6.0 | Task-Driven | tasks, task_lineage, task_sessions |
| v0.7.0 | ProjectKB | kb_sources, kb_chunks, kb_chunks_fts |
| v0.8.0 | Vector Embeddings | kb_embeddings, kb_embedding_meta |
| v0.9.0 | Command History | command_history, pinned_commands |
| v0.10.0 | Fix FTS Triggers | (修复 v0.7.0 触发器问题) |

## ⚠️ 常见问题

### 问题 1: UNIQUE constraint failed

**症状**:
```
Migration failed: UNIQUE constraint failed: schema_version.version
```

**原因**: 版本记录重复（通常是部分成功的迁移）

**解决**: 
```bash
# 方案 1: 清理重复版本（推荐）
sqlite3 store/registry.sqlite "DELETE FROM schema_version WHERE version = '0.10.0';"
agentos migrate

# 方案 2: 直接修复（如果表结构已正确）
sqlite3 store/registry.sqlite "UPDATE schema_version SET version = '0.10.0' WHERE version = '0.9.0';"
```

### 问题 2: no such column

**症状**:
```
Migration failed: no such column: content_hash
```

**原因**: 表 schema 不一致

**解决**:
```bash
# 查看表结构
sqlite3 store/registry.sqlite "PRAGMA table_info(kb_chunks);"

# 如果确认字段缺失，重新运行迁移
agentos migrate
```

### 问题 3: database is locked

**症状**:
```
Migration failed: database is locked
```

**原因**: 另一个进程正在使用数据库

**解决**:
```bash
# 1. 关闭所有 agentos 进程
pkill -f agentos

# 2. 检查数据库锁
lsof | grep registry.sqlite

# 3. 重新尝试
agentos migrate
```

## 🔧 手动迁移（紧急情况）

如果自动迁移失败，可以手动执行 SQL：

```bash
# 执行单个迁移
sqlite3 store/registry.sqlite < agentos/store/migrations/v08_vector_embeddings.sql

# 验证结果
sqlite3 store/registry.sqlite "SELECT version FROM schema_version;"
```

## 📦 备份与恢复

### 备份

```bash
# 迁移前备份
cp store/registry.sqlite store/registry.sqlite.backup.$(date +%Y%m%d_%H%M%S)
```

### 恢复

```bash
# 从备份恢复
cp store/registry.sqlite.backup.20260126_110338 store/registry.sqlite
```

## 🛡️ 安全检查清单

迁移前：
- [ ] 备份数据库文件
- [ ] 确认没有正在运行的 agentos 进程
- [ ] 检查磁盘空间充足
- [ ] 查看当前版本

迁移后：
- [ ] 验证版本正确
- [ ] 检查关键表存在
- [ ] 测试基本功能
- [ ] 查看日志无错误

## 📚 相关文档

- [DATABASE_MIGRATION_FIX.md](./DATABASE_MIGRATION_FIX.md) - v0.8.0 schema 冲突修复
- [MIGRATION_ERROR_HANDLING_ENHANCEMENT.md](./MIGRATION_ERROR_HANDLING_ENHANCEMENT.md) - 错误处理改进
- [agentos/store/migrations.py](../agentos/store/migrations.py) - 迁移源码

## 🆘 获取帮助

遇到问题？
1. 查看完整日志: `agentos migrate --verbose`
2. 搜索 GitHub Issues: https://github.com/agentos/issues
3. 提交新 Issue 并附带：
   - 错误信息
   - 当前版本 (`SELECT * FROM schema_version`)
   - 表列表 (`SELECT name FROM sqlite_master WHERE type='table'`)

---

**最后更新**: 2026-01-26  
**维护者**: AgentOS Team
