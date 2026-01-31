# PR-3 快速参考

## 一句话总结
✅ 成功将 14 条 webui_sessions 和 97 条 webui_messages 迁移到 chat_sessions/chat_messages，旧表已归档为 `_legacy`。

## 关键数字

```
迁移前: 158 sessions + 14 legacy = 160 sessions (12 重叠)
迁移后: 160 sessions (所有数据统一到 chat_sessions)

Messages: 475 → 572 (增加 97 条)
```

## 快速验证

### 1 行命令验证迁移成功
```bash
sqlite3 store/registry.sqlite "SELECT COUNT(*) FROM webui_sessions_legacy WHERE session_id NOT IN (SELECT session_id FROM chat_sessions);"
# 应返回: 0
```

### 查看迁移记录
```bash
sqlite3 store/registry.sqlite "SELECT * FROM schema_migrations WHERE migration_id = 'merge_webui_sessions';"
```

### 运行完整测试
```bash
python3 -m pytest tests/test_pr3_migration.py -v
# 应显示: 14 passed
```

## 文件位置

| 文件 | 路径 |
|------|------|
| SQL 迁移 | `agentos/store/migrations/schema_v34_merge_webui_sessions.sql` |
| Python 执行器 | `agentos/store/migrations/run_pr3_migration.py` |
| 测试套件 | `tests/test_pr3_migration.py` |
| 详细报告 | `docs/PR3_MIGRATION_REPORT.md` |
| 数据库备份 | `store/registry_backup_20260131_025202.sqlite` |

## 表状态

| 表名 | 状态 | 行数 |
|------|------|------|
| `chat_sessions` | ✅ 活跃 | 160 |
| `chat_messages` | ✅ 活跃 | 572 |
| `webui_sessions_legacy` | 📦 归档 | 14 |
| `webui_messages_legacy` | 📦 归档 | 97 |
| `webui_sessions` | ❌ 已移除 | - |
| `webui_messages` | ❌ 已移除 | - |

## 重要 SQL 查询

### 查看迁移的 sessions
```sql
SELECT session_id, title, created_at,
  json_extract(metadata, '$.source') as source
FROM chat_sessions
WHERE json_extract(metadata, '$.source') = 'webui_migration';
```

### 查看迁移的 messages
```sql
SELECT message_id, session_id, role,
  json_extract(metadata, '$.source') as source
FROM chat_messages
WHERE json_extract(metadata, '$.source') = 'webui_migration';
```

### 统计迁移数据
```sql
SELECT
  (SELECT COUNT(*) FROM chat_sessions WHERE json_extract(metadata, '$.source') = 'webui_migration') as migrated_sessions,
  (SELECT COUNT(*) FROM chat_messages WHERE json_extract(metadata, '$.source') = 'webui_migration') as migrated_messages;
```

## 测试清单

- [x] Legacy 表已创建
- [x] 原始表已移除
- [x] 所有 sessions 已迁移
- [x] 所有 messages 已迁移
- [x] 元数据已补齐
- [x] 迁移记录已创建
- [x] 时间戳已保留
- [x] 幂等性验证通过
- [x] 14/14 测试通过

## 回滚 (紧急情况)

```bash
# 1 行命令回滚
cp store/registry_backup_20260131_025202.sqlite store/registry.sqlite
```

## 下一步

1. ✅ PR-3 完成
2. ⏳ 运行最终验收测试 (任务 #13)
3. ⏳ 监控 1-2 周
4. ⏳ (可选) 删除 `_legacy` 表

---

**状态**: ✅ 完成并验证
**风险等级**: 低 (有完整备份)
**生产就绪**: 是
