# 数据库迁移快速指南

## 🚀 快速开始

### 查看可用迁移
```bash
python3 -m agentos.store.migrations list
```

### 迁移到最新版本
```bash
python3 -m agentos.store.migrations migrate
```

### 迁移到指定版本
```bash
python3 -m agentos.store.migrations migrate 0.8.0
```

## 📝 添加新迁移（3 步）

### 1. 创建迁移文件
文件名格式：`vXX_feature_name.sql`

```bash
# 例如：v11_user_auth.sql
cat > agentos/store/migrations/v11_user_auth.sql << 'EOF'
-- Migration v0.11.0: User Authentication

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Update schema version
INSERT OR REPLACE INTO schema_version (version, applied_at) 
VALUES ('0.11.0', datetime('now'));
EOF
```

### 2. 验证迁移文件
```bash
python3 -m agentos.store.migrations list
# 应该看到 v0.11.0: User Auth
```

### 3. 测试迁移
```bash
# 在测试数据库上执行
python3 -m agentos.store.migrations migrate
```

**完成！** 🎉 无需修改任何 Python 代码。

## 📋 迁移文件规范

### 文件命名
- 格式：`vXX_feature_name.sql`
- 版本号：`XX` 对应 `0.XX.0`
- 示例：`v11_user_auth.sql` → `0.11.0`

### 文件内容结构
```sql
-- Migration v0.XX.0: Feature Description

-- 1. 创建表/索引
CREATE TABLE IF NOT EXISTS ...;
CREATE INDEX IF NOT EXISTS ...;

-- 2. 数据迁移（如需要）
-- UPDATE/INSERT ...

-- 3. 更新版本号（必需）
INSERT OR REPLACE INTO schema_version (version, applied_at) 
VALUES ('0.XX.0', datetime('now'));
```

### 重要规则
1. **幂等性**: 使用 `IF NOT EXISTS`、`OR REPLACE`
2. **版本号**: 必须在文件末尾更新 `schema_version`
3. **注释**: 清晰说明迁移目的

## 🔍 迁移状态检查

### 查看数据库当前版本
```bash
sqlite3 store/registry.sqlite "SELECT version, applied_at FROM schema_version ORDER BY version"
```

### 查看迁移历史
```bash
sqlite3 store/registry.sqlite "SELECT version, applied_at FROM schema_version"
```

## 🐛 常见问题

### Q1: 迁移失败怎么办？
**A**: 检查错误信息，通常是：
- SQL 语法错误
- 表/列已存在（缺少 `IF NOT EXISTS`）
- 外键约束冲突

### Q2: 如何跳过某个版本？
**A**: 不支持跳过。迁移必须按顺序执行。

### Q3: 可以回滚吗？
**A**: 默认不支持自动回滚。需要手动编写回滚 SQL。

### Q4: 版本号可以不连续吗？
**A**: 可以。系统按数字大小排序，不要求连续。
- 例如：v10 → v15 → v20（跳过 v11-v14）

## 📚 更多信息

- 完整报告：`MIGRATION_REFACTOR_REPORT.md`
- 迁移文件：`agentos/store/migrations/`
- 主代码：`agentos/store/migrations.py`

---

**更新日期**: 2026-01-27
